"""
Agents routes - Recurring agent management

ADR-109: Scope × Role × Trigger Framework

Endpoints:
- POST /agents - Create a new agent
- GET /agents - List user's agents
- GET /agents/:id - Get agent with version history
- PATCH /agents/:id - Update agent settings
- DELETE /agents/:id - Archive an agent
- POST /agents/:id/run - Trigger an ad-hoc run
- GET /agents/:id/outputs - Output folder history (ADR-119 P4b)
- GET /agents/:id/versions - List versions
- GET /agents/:id/versions/:version_id - Get version detail
- PATCH /agents/:id/versions/:version_id - Update version (approve, reject, save edits)
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
from uuid import UUID
from datetime import datetime, timezone

from services.supabase import UserClient
from services.orchestration import get_agent_class_and_domain

logger = logging.getLogger(__name__)


router = APIRouter()


# =============================================================================
# ADR-109: Scope × Role × Trigger Framework
# =============================================================================

Scope = Literal[
    "platform",        # Single platform (inferred: 1 provider in sources)
    "cross_platform",  # Multiple platforms (inferred: 2+ providers)
    "knowledge",       # Accumulated /knowledge/ filesystem
    "research",        # Knowledge + WebSearch
    "autonomous",      # Full primitive set, agent-driven
]

Role = Literal[
    # v2 types (ADR-130)
    "briefer",     # Keeps you briefed on what's happening
    "monitor",     # Watches for what matters and alerts you
    "researcher",  # Investigates topics and produces analysis
    "drafter",     # Produces deliverables and documents
    "analyst",     # Tracks metrics and surfaces patterns
    "writer",      # Crafts communications and content
    "planner",     # Prepares plans, agendas, and follow-ups
    "scout",       # Tracks competitors and market movements
    # Legacy (DB compat)
    "digest", "prepare", "research", "synthesize", "act", "custom",
]


# ADR-111: Scope inference in shared agent_creation module (used by create_agent_record)


# =============================================================================
# ADR-109: Role Configs
# =============================================================================

class DigestConfig(BaseModel):
    """Config for digest role. Platform inferred from sources[] at assembly time."""
    focus: str = "key discussions and decisions"
    reply_threshold: int = 3    # Min replies to flag as hot thread (Slack)
    reaction_threshold: int = 2  # Min reactions to surface a message (Slack)


class PrepareConfig(BaseModel):
    """Config for prepare role. ADR-131: Calendar sunset — prepare role is legacy."""
    delivery_time: Optional[str] = "08:00"


class SynthesizeConfig(BaseModel):
    """Config for synthesize role (cross-platform status update, proactive insights)."""
    subject: str = ""  # "Engineering Team", "Project Alpha"
    audience: Literal["manager", "stakeholders", "team", "executive"] = "stakeholders"
    detail_level: Literal["brief", "standard", "detailed"] = "standard"
    tone: Literal["formal", "conversational"] = "formal"


class MonitorConfig(BaseModel):
    """Config for monitor role (standing-order intelligence monitoring)."""
    domain: str = ""  # "competitive landscape", "AI regulation", "customer feedback"
    signals: list[str] = Field(default_factory=list)  # What to look for


class ResearchConfig(BaseModel):
    """Config for research role (bounded investigation)."""
    pulse_frequency: Literal["daily", "weekly"] = "weekly"


class CustomConfig(BaseModel):
    """Config for custom role."""
    description: str = ""
    structure_notes: Optional[str] = None


SkillConfig = Union[
    DigestConfig,
    PrepareConfig,
    SynthesizeConfig,
    MonitorConfig,
    ResearchConfig,
    CustomConfig,
]


class FeedbackSummary(BaseModel):
    """Summary of learned preferences from user feedback (ADR-018)."""
    has_feedback: bool = False
    total_runs: int = 0
    approved_runs: int = 0
    avg_quality: Optional[float] = None  # Average (1 - edit_distance_score) as percentage
    learned_preferences: list[str] = Field(default_factory=list)  # Human-readable preferences


def compute_feedback_summary(approved_versions: list[dict]) -> FeedbackSummary:
    """
    Compute feedback summary from approved versions (ADR-018).

    Analyzes edit patterns and feedback notes to determine what YARNNN has learned.
    """
    if not approved_versions:
        return FeedbackSummary(
            has_feedback=False,
            total_runs=0,
            approved_runs=0,
        )

    # Calculate average quality (1 - edit_distance = quality)
    scores = [
        v.get("edit_distance_score")
        for v in approved_versions
        if v.get("edit_distance_score") is not None
    ]
    avg_quality = None
    if scores:
        avg_quality = round((1 - sum(scores) / len(scores)) * 100, 1)

    # Aggregate learned preferences from edit categories and feedback
    learned = []
    addition_counts: dict[str, int] = {}
    deletion_counts: dict[str, int] = {}

    for v in approved_versions:
        # Collect edit categories
        categories = v.get("edit_categories", {})
        if categories:
            for addition in categories.get("additions", []):
                addition_counts[addition] = addition_counts.get(addition, 0) + 1
            for deletion in categories.get("deletions", []):
                deletion_counts[deletion] = deletion_counts.get(deletion, 0) + 1

        # Collect explicit feedback
        if v.get("feedback_notes"):
            note = v["feedback_notes"].strip()
            if note and note not in learned:
                learned.append(f'"{note}"')

    # Convert category patterns to human-readable preferences
    if addition_counts:
        top_additions = sorted(addition_counts.items(), key=lambda x: -x[1])[:3]
        for item, count in top_additions:
            if count >= 2:
                learned.append(f"You often add {item}")
            else:
                learned.append(f"You've added {item}")

    if deletion_counts:
        top_deletions = sorted(deletion_counts.items(), key=lambda x: -x[1])[:3]
        for item, count in top_deletions:
            if count >= 2:
                learned.append(f"You often remove {item}")
            else:
                learned.append(f"You've removed {item}")

    return FeedbackSummary(
        has_feedback=len(learned) > 0 or avg_quality is not None,
        total_runs=len(approved_versions),
        approved_runs=len(approved_versions),
        avg_quality=avg_quality,
        learned_preferences=learned[:8],  # Limit to 8 items
    )


def get_default_config(role: str) -> dict:
    """Get default configuration for a role (ADR-109)."""
    defaults = {
        "digest": DigestConfig(),
        "prepare": PrepareConfig(),
        "synthesize": SynthesizeConfig(),
        "monitor": MonitorConfig(),
        "research": ResearchConfig(),
        "custom": CustomConfig(),
    }
    return defaults.get(role, defaults["custom"]).model_dump()


# =============================================================================
# Request/Response Models
# =============================================================================

class AgentCreate(BaseModel):
    """Create agent request — ADR-138: identity-only agent schema."""
    title: str
    # ADR-109: Role is user-selected, scope is auto-inferred
    role: Role = "custom"
    type_config: Optional[dict] = None  # Role-specific config, validated per role
    # ADR-087: Agent-scoped context
    agent_instructions: Optional[str] = None


class AgentUpdate(BaseModel):
    """Update agent request — ADR-138: identity-only agent schema."""
    title: Optional[str] = None
    role: Optional[Role] = None
    type_config: Optional[dict] = None
    status: Optional[Literal["active", "paused", "archived"]] = None
    agent_instructions: Optional[str] = None


class AgentResponse(BaseModel):
    """Agent response — ADR-138: identity-only agent schema."""
    id: str
    title: str
    slug: Optional[str] = None  # Stable URL slug — derived server-side from title
    # ADR-109: Scope × Role
    scope: str = "cross_platform"
    role: str = "custom"
    type_config: Optional[dict] = None
    status: str
    created_at: str
    updated_at: str
    version_count: int = 0
    latest_version_status: Optional[str] = None
    # Quality metrics (ADR-018: feedback loop)
    quality_score: Optional[float] = None
    quality_trend: Optional[str] = None
    avg_edit_distance: Optional[float] = None
    # ADR-068: Agent origin
    origin: str = "user_configured"  # user_configured | coordinator_created
    # ADR-087: Agent-scoped context
    agent_instructions: Optional[str] = None
    agent_memory: Optional[dict] = None
    # ADR-118: Avatar
    avatar_url: Optional[str] = None
    # SURFACE-ARCHITECTURE v3: agent class + owned context domain
    agent_class: str = "domain-steward"  # domain-steward | synthesizer | platform-bot
    context_domain: Optional[str] = None  # owned domain key (e.g., "competitors"), None for synthesizers


class SourceFetchSummary(BaseModel):
    """ADR-030: Summary of source fetches for a version."""
    sources_total: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    delta_mode_used: bool = False
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None


class SourceSnapshot(BaseModel):
    """ADR-049: Snapshot of source state at generation time."""
    platform: str
    resource_id: str
    resource_name: Optional[str] = None
    synced_at: str
    platform_cursor: Optional[str] = None
    item_count: Optional[int] = None
    source_latest_at: Optional[str] = None
    items_used: Optional[int] = None  # ADR-049 evolution: actual items consumed



class VersionResponse(BaseModel):
    """Agent version response."""
    id: str
    agent_id: str
    version_number: int
    status: str  # generating, staged, reviewing, approved, rejected
    draft_content: Optional[str] = None
    final_content: Optional[str] = None
    edit_distance_score: Optional[float] = None
    edit_categories: Optional[dict] = None  # ADR-018: categorized edits
    feedback_notes: Optional[str] = None
    created_at: str
    staged_at: Optional[str] = None
    approved_at: Optional[str] = None
    # ADR-028: Delivery tracking
    delivery_status: Optional[str] = None  # pending, delivering, delivered, failed
    delivery_external_id: Optional[str] = None
    delivery_external_url: Optional[str] = None
    delivered_at: Optional[str] = None
    delivery_error: Optional[str] = None
    # ADR-032: Platform-centric draft delivery
    delivery_mode: Optional[str] = None  # draft, direct
    # ADR-030: Source fetch summary
    source_fetch_summary: Optional[SourceFetchSummary] = None
    # ADR-049: Source snapshots for freshness tracking
    source_snapshots: Optional[list[SourceSnapshot]] = None
    # ADR-101: Execution metadata (tokens, model, provenance)
    metadata: Optional[dict] = None


class VersionUpdate(BaseModel):
    """Update version request (for approval/rejection/editing)."""
    status: Optional[Literal["staged", "reviewing", "approved", "rejected"]] = None
    final_content: Optional[str] = None
    feedback_notes: Optional[str] = None


def _parse_source_fetch_summary(summary_dict: Optional[dict]) -> Optional[SourceFetchSummary]:
    """Parse raw source_fetch_summary dict from DB into typed response."""
    if not summary_dict:
        return None
    return SourceFetchSummary(
        sources_total=summary_dict.get("sources_total", 0),
        sources_succeeded=summary_dict.get("sources_succeeded", 0),
        sources_failed=summary_dict.get("sources_failed", 0),
        delta_mode_used=summary_dict.get("delta_mode_used", False),
        time_range_start=summary_dict.get("time_range_start"),
        time_range_end=summary_dict.get("time_range_end"),
    )


def _parse_source_snapshots(snapshots_list: Optional[list]) -> Optional[list[SourceSnapshot]]:
    """Parse raw source_snapshots list from DB into typed response (ADR-049)."""
    if not snapshots_list:
        return None
    return [
        SourceSnapshot(
            platform=s.get("platform", ""),
            resource_id=s.get("resource_id", ""),
            resource_name=s.get("resource_name"),
            synced_at=s.get("synced_at", ""),
            platform_cursor=s.get("platform_cursor"),
            item_count=s.get("item_count"),
            source_latest_at=s.get("source_latest_at"),
        )
        for s in snapshots_list
        if isinstance(s, dict)
    ]


# =============================================================================
# Agent CRUD Routes
# =============================================================================

@router.post("")
async def create_agent(
    request: AgentCreate,
    auth: UserClient,
) -> AgentResponse:
    """
    Create a new recurring agent.

    ADR-053: Enforces active agent limits based on user tier.
    ADR-111: Delegates to shared create_agent_record() for singular implementation.
    """
    from services.agent_creation import create_agent_record

    # ADR-172: No agent limit gate — balance is the only gate

    # Handle type_config - use provided or get defaults
    type_config = request.type_config
    if type_config is None:
        type_config = get_default_config(request.role)

    # Validate type_config against the role
    validated_config = validate_role_config(request.role, type_config)

    # ADR-111: Single creation path via create_agent_record()
    # ADR-138: Identity-only — no schedule, sources, destination, recipient_context
    result = await create_agent_record(
        client=auth.client,
        user_id=auth.user_id,
        title=request.title,
        role=request.role,
        origin="user_configured",
        agent_instructions=request.agent_instructions,
        type_config=validated_config,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    agent = result["agent"]

    # ADR-106: Workspace intelligence for response
    from services.workspace import get_agent_intelligence
    intelligence = await get_agent_intelligence(auth.client, auth.user_id, agent)

    return AgentResponse(
        id=agent["id"],
        title=agent["title"],
        scope=agent.get("scope", "cross_platform"),
        role=agent.get("role", "custom"),
        type_config=agent.get("type_config"),
        status=agent["status"],
        created_at=agent["created_at"],
        updated_at=agent["updated_at"],
        origin=agent.get("origin", "user_configured"),
        agent_instructions=intelligence.get("agent_instructions"),
        agent_memory=intelligence.get("agent_memory"),
        avatar_url=agent.get("avatar_url"),
    )


@router.get("")
async def list_agents(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[AgentResponse]:
    """
    List user's agents with quality metrics.

    Args:
        status: Filter by status (active, paused, archived)
        limit: Maximum results

    Quality metrics are computed from the last 5 approved versions:
    - quality_score: Latest edit_distance_score (lower = better)
    - quality_trend: "improving" | "stable" | "declining"
    - avg_edit_distance: Average over recent versions
    """
    # Fetch agents with versions.
    # ADR-214: the /agents list shows judgment-bearing Agents only (ADR-212
    # taxonomy): Systemic (Reviewer) + Domain (user-authored).
    # ADR-272 (2026-05-14): the `thinking_partner` row that previously
    # surfaced as the "System Agent" cockpit entity is now FILTERED OUT here.
    # The orchestration LLM identity persists in the DB (used by routes/feed.py
    # for chat-mode profile resolution) but is not cockpit-visible per the
    # ADR-272 collapse — orchestration is ambient activity, not a peer agent.
    # Reviewer is synthesized below as a pseudo-agent.
    query = (
        auth.client.table("agents")
        .select("*, agent_runs(id, status, version_number, edit_distance_score, approved_at)")
        .eq("user_id", auth.user_id)
        .neq("role", "pm")  # PM agents are project infrastructure, not user-facing
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    raw_agents = result.data or []
    # ADR-272: filter out the orchestration substrate row (role='thinking_partner').
    # Filter out other system_bootstrap rows (legacy infrastructure) per ADR-189.
    agents = [
        a for a in raw_agents
        if a.get("origin") != "system_bootstrap" and a.get("role") != "thinking_partner"
    ]

    # ADR-106: Read workspace intelligence for all agents in parallel
    import asyncio
    from services.workspace import get_agent_intelligence, get_agent_slug as _get_slug

    intelligence_map = {}
    async def _fetch_intelligence(agent_dict):
        try:
            return agent_dict["id"], await get_agent_intelligence(
                auth.client, auth.user_id, agent_dict
            )
        except Exception as e:
            logger.warning(f"[AGENTS] Workspace read failed for {agent_dict.get('id')}: {e}")
            return agent_dict["id"], {"agent_instructions": None, "agent_memory": None}

    intelligence_results = await asyncio.gather(
        *[_fetch_intelligence(d) for d in agents]
    )
    intelligence_map = dict(intelligence_results)

    responses = []
    for d in agents:
        versions = d.get("agent_runs", [])
        version_count = len(versions)
        latest_version = max(versions, key=lambda v: v["version_number"]) if versions else None

        # Calculate quality metrics from approved versions
        quality_score = None
        quality_trend = None
        avg_edit_distance = None

        approved_versions = [
            v for v in versions
            if v.get("status") == "approved" and v.get("edit_distance_score") is not None
        ]

        if approved_versions:
            # Sort by version_number descending
            approved_versions.sort(key=lambda v: v["version_number"], reverse=True)
            recent = approved_versions[:5]  # Last 5 approved versions

            # Latest score
            quality_score = recent[0]["edit_distance_score"]

            # Average
            scores = [v["edit_distance_score"] for v in recent]
            avg_edit_distance = sum(scores) / len(scores)

            # Trend: compare first half vs second half
            if len(recent) >= 3:
                older = recent[len(recent)//2:]  # Older versions
                newer = recent[:len(recent)//2]  # Newer versions
                older_avg = sum(v["edit_distance_score"] for v in older) / len(older)
                newer_avg = sum(v["edit_distance_score"] for v in newer) / len(newer)

                # Lower score = better quality (fewer edits needed)
                if newer_avg < older_avg - 0.05:
                    quality_trend = "improving"
                elif newer_avg > older_avg + 0.05:
                    quality_trend = "declining"
                else:
                    quality_trend = "stable"
            elif len(recent) >= 2:
                # Only 2 versions: compare directly
                if recent[0]["edit_distance_score"] < recent[1]["edit_distance_score"] - 0.05:
                    quality_trend = "improving"
                elif recent[0]["edit_distance_score"] > recent[1]["edit_distance_score"] + 0.05:
                    quality_trend = "declining"
                else:
                    quality_trend = "stable"

        intel = intelligence_map.get(d["id"], {})
        role = d.get("role", "custom")
        agent_class, context_domain = get_agent_class_and_domain(role)
        responses.append(AgentResponse(
            id=d["id"],
            title=d["title"],
            slug=_get_slug(d),
            scope=d.get("scope", "cross_platform"),
            role=role,
            type_config=d.get("type_config"),
            status=d["status"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            version_count=version_count,
            latest_version_status=latest_version["status"] if latest_version else None,
            quality_score=quality_score,
            quality_trend=quality_trend,
            avg_edit_distance=avg_edit_distance,
            origin=d.get("origin", "user_configured"),
            agent_instructions=intel.get("agent_instructions"),
            agent_memory=intel.get("agent_memory"),
            avatar_url=d.get("avatar_url"),
            agent_class=agent_class,
            context_domain=context_domain,
        ))

    # ADR-214: Synthesize Reviewer as a systemic pseudo-agent. No DB row —
    # substrate at /workspace/review/{IDENTITY,principles,decisions}.md stays
    # authoritative per ADR-194 v2 Axiom 1. Frontend dispatches on
    # agent_class='reviewer' to render ReviewerDetailView.
    # Status filter: Reviewer is always 'active'; skip synthesis only if
    # caller asked to filter to a different status.
    if not status or status == "active":
        _now_iso = datetime.now(timezone.utc).isoformat()
        responses.insert(0, AgentResponse(
            id="reviewer",
            title="Reviewer",
            slug="reviewer",
            scope="workspace",
            role="reviewer",
            type_config=None,
            status="active",
            created_at=_now_iso,
            updated_at=_now_iso,
            version_count=0,
            origin="system_bootstrap",
            agent_instructions=None,
            agent_memory=None,
            avatar_url=None,
            agent_class="reviewer",
            context_domain=None,
        ))

    return responses


@router.get("/reviewer/activity")
async def get_reviewer_activity(auth: UserClient) -> dict:
    """Reviewer activity surface — answers the operator's supervision
    questions: is the Reviewer alive, what did it do, when does it next fire?

    Post-ADR-260/261 rewrite (2026-05-14): reads canonical
    `/workspace/_recurrences.yaml` and treats every `mode: judgment`
    entry as a Reviewer wake (ADR-263 D1: judgment mode wakes the
    Reviewer with a prompt). The earlier implementation read
    `/workspace/_shared/back-office.yaml` (substrate dissolved by
    ADR-261) and filtered on the `back-office-reviewer-` slug prefix
    (legacy taxonomy; current slugs are `morning-reflection`,
    `signal-evaluation`, `pre-market-brief`, etc.) — under-counted
    Reviewer activity by ~80% in production.

    Joins three substrate sources:

    1. **`_recurrences.yaml`** — judgment-mode entries (slug, schedule,
       prompt). The schedule list + the slug allowlist for the run
       query both derive from this. Mechanical-mode entries (deterministic
       Python, no Reviewer wake) are intentionally excluded.

    2. **`execution_events`** — recent runs of any judgment-mode slug
       (last 7 days). The liveness signal — empty = scheduler dead OR
       Reviewer not wired up.

    3. **`action_proposals`** — recent Reviewer-originated proposals
       (auto-approved, OR sourced from `reviewer_*` triggers regardless
       of approval). The "what did the Reviewer do for me" trail.

    Returns the structured shape the FE Activity tab renders directly.
    Never raises — returns empty arrays on any read failure so the panel
    can degrade gracefully.

    Distinct from `/activity` (workspace-wide execution-lens — every
    recurrence, every mode, cost-aware): this surface is the **Reviewer
    supervision lens** — judgment-mode only, Reviewer-action only,
    answers "is my Reviewer operating the way I told it to?"
    """
    import yaml as _yaml
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    RECURRENCES_PATH = "/workspace/_recurrences.yaml"
    # ADR-307: Reviewer-authored proposals carry source 'reviewer:<occupant>'
    # (matched via like below); the legacy exact-value list is retired.
    LOOKBACK = _dt.now(_tz.utc) - _td(days=7)

    # --- 1. Parse judgment-mode recurrences from canonical substrate ---
    # Build (a) the slug allowlist for the run query and (b) the schedule
    # list for the next-fires section. Both come from one yaml read.
    judgment_slugs: set[str] = set()
    schedules: list[dict] = []
    try:
        from services.schedule_utils import calculate_next_run_at

        yaml_result = (
            auth.client.table("workspace_files")
            .select("content")
            .eq("user_id", auth.user_id)
            .eq("path", RECURRENCES_PATH)
            .limit(1)
            .execute()
        )
        if yaml_result.data:
            raw = _yaml.safe_load(yaml_result.data[0].get("content") or "") or {}
            now_utc = _dt.now(_tz.utc)
            for entry in raw.get("recurrences") or []:
                # Default mode = judgment per ADR-261 parse-time semantics
                # (legacy compat). Mechanical-mode entries get excluded; they
                # don't wake the Reviewer.
                mode = entry.get("mode") or "judgment"
                if mode != "judgment":
                    continue
                slug = entry.get("slug") or ""
                if not slug:
                    continue
                judgment_slugs.add(slug)

                cron = entry.get("schedule")
                paused = bool(entry.get("paused", False))
                # schedule may be a string, a list (multiple fires per day),
                # or null (reactive — no scheduled fire). For multi-string
                # schedules we use the first as a rough next-fire signal;
                # exact multi-fire-per-day expansion is downstream UX.
                cron_for_calc: str | None = None
                if isinstance(cron, list) and cron:
                    cron_for_calc = cron[0] if isinstance(cron[0], str) else None
                elif isinstance(cron, str):
                    cron_for_calc = cron
                next_at = None
                if cron_for_calc and not paused:
                    try:
                        nxt = calculate_next_run_at(
                            schedule=cron_for_calc,
                            last_run_at=now_utc,
                        )
                        next_at = nxt.isoformat() if nxt else None
                    except Exception:
                        next_at = None
                schedules.append({
                    "slug": slug,
                    "display_name": entry.get("display_name") or slug,
                    "schedule": cron_for_calc,
                    "paused": paused,
                    "next_fires_at": next_at,
                })
            # Sort: not-scheduled (no next_at) to the end; nearest fire first.
            schedules.sort(key=lambda s: s["next_fires_at"] or "9999")
    except Exception as e:
        logger.warning("[REVIEWER_ACTIVITY] recurrences read failed: %s", e)

    # --- 2. Recent runs (last 7 days, any judgment-mode slug) ---
    runs: list[dict] = []
    if judgment_slugs:
        try:
            events_result = (
                auth.client.table("execution_events")
                .select("slug, status, created_at, error_reason, duration_ms")
                .eq("user_id", auth.user_id)
                .in_("slug", list(judgment_slugs))
                .gte("created_at", LOOKBACK.isoformat())
                .order("created_at", desc=True)
                .limit(40)
                .execute()
            )
            runs = events_result.data or []
        except Exception as e:
            logger.warning("[REVIEWER_ACTIVITY] execution_events read failed: %s", e)

    # --- 3. Recent autonomous actions (last 7 days) ---
    # Two sources: auto-approved proposals (any source), or Reviewer-originated
    # proposals (any status). Union covers both "Reviewer did something" cases.
    actions: list[dict] = []
    try:
        # ADR-307: Reviewer-originated proposals (source 'reviewer:<occupant>').
        # The dead `approved_by='auto_reversible'` query (no live writer — only
        # 'user' is ever written) is removed. Columns: primitive + family +
        # decision_context replace action_type + expected_effect.
        reviewer_result = (
            auth.client.table("action_proposals")
            .select(
                "id, primitive, family, decision_context, status, "
                "approved_at, executed_at, approved_by, source, created_at"
            )
            .eq("user_id", auth.user_id)
            .like("source", "reviewer:%")
            .gte("created_at", LOOKBACK.isoformat())
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        for row in reviewer_result.data or []:
            actions.append(row)

        actions.sort(key=lambda a: a.get("created_at") or "", reverse=True)
        actions = actions[:20]
    except Exception as e:
        logger.warning("[REVIEWER_ACTIVITY] action_proposals read failed: %s", e)

    return {
        "runs": runs,
        "actions": actions,
        "schedules": schedules,
        "window_days": 7,
    }


@router.get("/reviewer/capabilities")
async def get_reviewer_capabilities(auth: UserClient) -> dict:
    """Reviewer capability library — operator-facing view of /workspace/specs/.

    Surfaces the Reviewer's capability library (analog of Claude Code's
    skills.md) as first-class cockpit content. Each spec is a quality
    contract: schema, sections, anti-patterns. Specs are load-bearing —
    the Reviewer reads them by explicit path reference in recurrence
    prompts (e.g. "Schema in /workspace/specs/performance-rollup.md").

    Before this route shipped, the capability library was entirely
    backend-internal: Reviewer reads them, operator never sees them
    (would need to manually browse /files?path=/workspace/specs/).

    Three substrate operations:

    1. **List specs** — `/workspace/specs/*.md` files for this workspace.
    2. **Parse each spec** — title from `# {Title}` heading; description
       from the first prose paragraph (typically under `## Purpose` or
       the intro). No-cost markdown parse.
    3. **Correlate used_by** — best-effort grep of `_recurrences.yaml`
       prompt text for explicit `/workspace/specs/{slug}` references.
       Each spec's `used_by` lists the recurrence slugs that name it.

    Returns one dict per spec; FE renders as cards.

    Read-only. Mutations route through chat per ADR-235 D1.

    Never raises — empty arrays on read failure for graceful degradation.
    """
    import yaml as _yaml
    import re as _re

    SPECS_PREFIX = "/workspace/specs/"
    RECURRENCES_PATH = "/workspace/_recurrences.yaml"

    # --- 1. List spec files ---
    specs_rows: list[dict] = []
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content, updated_at")
            .eq("user_id", auth.user_id)
            .like("path", f"{SPECS_PREFIX}%.md")
            .order("path")
            .execute()
        )
        specs_rows = result.data or []
    except Exception as e:
        logger.warning("[REVIEWER_CAPABILITIES] specs list failed: %s", e)
        return {"specs": []}

    if not specs_rows:
        return {"specs": []}

    # --- 2. Load _recurrences.yaml once for used_by correlation ---
    recurrences_text = ""
    try:
        rec_result = (
            auth.client.table("workspace_files")
            .select("content")
            .eq("user_id", auth.user_id)
            .eq("path", RECURRENCES_PATH)
            .limit(1)
            .execute()
        )
        if rec_result.data:
            recurrences_text = rec_result.data[0].get("content") or ""
    except Exception as e:
        logger.warning("[REVIEWER_CAPABILITIES] recurrences read failed: %s", e)

    # Parse recurrence slugs → prompt body so used_by correlation is precise
    # (each spec is associated with the recurrence slugs whose prompt text
    # references it). Falls back to plain text grep if yaml parse fails.
    recurrence_prompts: dict[str, str] = {}
    if recurrences_text:
        try:
            parsed = _yaml.safe_load(recurrences_text) or {}
            for entry in parsed.get("recurrences") or []:
                slug = entry.get("slug") or ""
                prompt = entry.get("prompt") or ""
                if slug:
                    recurrence_prompts[slug] = str(prompt)
        except Exception as e:
            logger.warning("[REVIEWER_CAPABILITIES] recurrences yaml parse failed: %s", e)

    # --- 3. Parse + correlate each spec ---
    specs: list[dict] = []
    for row in specs_rows:
        path = row.get("path") or ""
        content = row.get("content") or ""
        slug = path.removeprefix(SPECS_PREFIX).removesuffix(".md")

        title = _extract_spec_title(content) or slug
        description = _extract_spec_description(content)
        sections = _extract_spec_sections(content)

        # used_by — recurrences whose prompt mentions this spec path
        spec_path_substr = f"{SPECS_PREFIX}{slug}.md"
        used_by = [
            rslug for rslug, rprompt in recurrence_prompts.items()
            if spec_path_substr in rprompt
        ]

        specs.append({
            "slug": slug,
            "path": path,
            "title": title,
            "description": description,
            "sections": sections,
            "used_by": used_by,
            "updated_at": row.get("updated_at"),
            "size_bytes": len(content),
        })

    return {"specs": specs}


def _extract_spec_title(content: str) -> str | None:
    """First # heading in the spec body."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return None


def _extract_spec_description(content: str) -> str | None:
    """First substantive prose paragraph after the title.

    Skips:
      - the H1 line itself
      - blank lines
      - `>` blockquote lines (often "Spec for ..." metadata)
    Stops at the first `##` (sub-heading boundary) or after collecting
    one paragraph of prose.
    """
    lines = content.splitlines()
    paragraph: list[str] = []
    started = False
    for raw in lines:
        line = raw.strip()
        if not line:
            if started:
                break
            continue
        if line.startswith("# "):
            continue
        if line.startswith("##"):
            if started:
                break
            continue
        if line.startswith(">"):
            continue
        paragraph.append(line)
        started = True
    if not paragraph:
        return None
    joined = " ".join(paragraph).strip()
    # Truncate to a reasonable card-render length.
    return joined[:280] + ("…" if len(joined) > 280 else "")


_SECTION_RE = __import__("re").compile(r"^##\s+(.+?)\s*$", __import__("re").MULTILINE)


def _extract_spec_sections(content: str) -> list[str]:
    """List of `## {section}` titles, in document order. Caps at 12."""
    return _SECTION_RE.findall(content)[:12]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Get agent with recent version history.
    """
    # Get agent with project name
    # ADR-034: Projects removed, agents are user-scoped
    result = (
        auth.client.table("agents")
        .select("*")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = result.data

    # Get recent versions
    versions_result = (
        auth.client.table("agent_runs")
        .select("*")
        .eq("agent_id", str(agent_id))
        .order("version_number", desc=True)
        .limit(10)
        .execute()
    )

    versions = versions_result.data or []

    # Compute feedback summary from approved versions
    approved_versions = [v for v in versions if v.get("status") == "approved"]
    feedback_summary = compute_feedback_summary(approved_versions)

    # ADR-106: Read from workspace (source of truth)
    from services.workspace import get_agent_intelligence, get_agent_slug
    intelligence = await get_agent_intelligence(auth.client, auth.user_id, agent)

    # ADR-119 P4b: Read project memberships from agent workspace
    project_memberships = []
    try:
        import json as _json
        slug = get_agent_slug(agent)
        from services.workspace import AgentWorkspace
        _aw = AgentWorkspace(auth.client, auth.user_id, slug)
        _projects_raw = await _aw.read("memory/projects.json")
        if _projects_raw:
            project_memberships = _json.loads(_projects_raw)
    except Exception:
        pass  # Non-fatal

    # ADR-118: Query rendered outputs for this agent
    rendered_outputs = []
    try:
        slug = get_agent_slug(agent)
        ro_result = (
            auth.client.table("workspace_files")
            .select("path, content_url, content_type, metadata, updated_at")
            .eq("user_id", auth.user_id)
            .like("path", f"/agents/{slug}/outputs/%")
            .not_.is_("content_url", "null")
            .order("updated_at", desc=True)
            .limit(10)
            .execute()
        )
        for f in (ro_result.data or []):
            rendered_outputs.append({
                "filename": f["path"].rsplit("/", 1)[-1],
                "url": f["content_url"],
                "content_type": f.get("content_type", ""),
                "size_bytes": (f.get("metadata") or {}).get("size_bytes", 0),
                "render_type": (f.get("metadata") or {}).get("render_type", ""),
                "updated_at": f.get("updated_at"),
            })
    except Exception:
        pass  # Non-fatal

    return {
        "agent": AgentResponse(
            id=agent["id"],
            title=agent["title"],
            scope=agent.get("scope", "cross_platform"),
            role=agent.get("role", "custom"),
            type_config=agent.get("type_config"),
            status=agent["status"],
            created_at=agent["created_at"],
            updated_at=agent["updated_at"],
            version_count=len(versions),
            origin=agent.get("origin", "user_configured"),
            agent_instructions=intelligence.get("agent_instructions"),
            agent_memory=intelligence.get("agent_memory"),
            avatar_url=agent.get("avatar_url"),
        ),
        "versions": [
            VersionResponse(
                id=v["id"],
                agent_id=v["agent_id"],
                version_number=v["version_number"],
                status=v["status"],
                draft_content=v.get("draft_content"),
                final_content=v.get("final_content"),
                edit_distance_score=v.get("edit_distance_score"),
                edit_categories=v.get("edit_categories"),
                feedback_notes=v.get("feedback_notes"),
                created_at=v["created_at"],
                staged_at=v.get("staged_at"),
                approved_at=v.get("approved_at"),
                # ADR-028: Delivery fields
                delivery_status=v.get("delivery_status"),
                delivery_external_id=v.get("delivery_external_id"),
                delivery_external_url=v.get("delivery_external_url"),
                delivered_at=v.get("delivered_at"),
                delivery_error=v.get("delivery_error"),
                # ADR-030: Source fetch summary
                source_fetch_summary=_parse_source_fetch_summary(v.get("source_fetch_summary")),
                # ADR-049: Source snapshots
                source_snapshots=v.get("source_snapshots"),
                # ADR-101: Execution metadata
                metadata=v.get("metadata"),
            )
            for v in versions
        ],
        "feedback_summary": feedback_summary,
        "rendered_outputs": rendered_outputs,
        "project_memberships": project_memberships,
    }


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    request: AgentUpdate,
    auth: UserClient,
) -> AgentResponse:
    """
    Update agent settings.
    """
    # Verify ownership
    check = (
        auth.client.table("agents")
        .select("id")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Build update data
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if request.title is not None:
        update_data["title"] = request.title
    if request.role is not None:
        update_data["role"] = request.role
        # If role changes but no new config provided, reset to defaults
        if request.type_config is None:
            update_data["type_config"] = get_default_config(request.role)
    if request.type_config is not None:
        # Validate against current or new role
        target_role = request.role or check.data.get("role", "custom")
        update_data["type_config"] = validate_role_config(target_role, request.type_config)
    if request.status is not None:
        update_data["status"] = request.status
    # ADR-106: agent_instructions written to workspace only (not DB column)
    # ADR-138: mode removed from agents — mode is on tasks

    result = (
        auth.client.table("agents")
        .update(update_data)
        .eq("id", str(agent_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update agent")

    d = result.data[0]

    # ADR-106: Write instructions to workspace (singular source of truth)
    from services.workspace import AgentWorkspace, get_agent_slug, get_agent_intelligence
    if request.agent_instructions is not None:
        ws = AgentWorkspace(auth.client, auth.user_id, get_agent_slug(d))
        await ws.write("AGENT.md", request.agent_instructions,
                       summary="Agent identity and behavioral instructions")

    intelligence = await get_agent_intelligence(auth.client, auth.user_id, d)

    return AgentResponse(
        id=d["id"],
        title=d["title"],
        scope=d.get("scope", "cross_platform"),
        role=d.get("role", "custom"),
        type_config=d.get("type_config"),
        status=d["status"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        origin=d.get("origin", "user_configured"),
        agent_instructions=intelligence.get("agent_instructions"),
        agent_memory=intelligence.get("agent_memory"),
        avatar_url=d.get("avatar_url"),
    )


@router.delete("/{agent_id}")
async def archive_agent(
    agent_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Archive an agent (soft delete).
    """
    result = (
        auth.client.table("agents")
        .update({"status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    logger.info(f"[AGENT] Archived: {agent_id}")

    return {"success": True, "message": "Agent archived"}


# =============================================================================
# Pipeline Execution Routes
# =============================================================================

@router.post("/{agent_id}/run")
async def trigger_run(
    agent_id: UUID,
    auth: UserClient,
) -> dict:
    """Trigger an ad-hoc agent run.

    Per ADR-261 D7: agents are tools the Reviewer dispatches via
    DispatchSpecialist (Phase C.2). "Operator clicked Run on agent X" is
    expressed as a synthetic addressed-equivalent invocation — a one-shot
    Recurrence whose prompt asks the Reviewer to dispatch this specific
    agent now. The Reviewer's loop then routes to DispatchSpecialist.
    """
    from services.wake_sources.manual_fire import fire as wake_manual_fire
    from services.recurrence import Recurrence
    from services.supabase import get_service_client

    result = (
        auth.client.table("agents")
        .select("*")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = result.data
    if agent["status"] == "archived":
        raise HTTPException(status_code=400, detail="Cannot run archived agent")

    agent_slug = agent.get("slug", "")
    if not agent_slug:
        raise HTTPException(status_code=400, detail="Agent has no slug")

    logger.info(f"[AGENT] Triggering run: {agent_id} ({agent_slug})")

    svc_client = get_service_client()
    synthetic = Recurrence(
        slug=f"manual-run-{agent_slug}",
        schedule=None,
        prompt=(
            f"Operator manually requested a run of agent '{agent_slug}'. "
            f"Dispatch this specialist now via DispatchSpecialist with a "
            f"focused brief derived from the operator's standing context "
            f"(MANDATE, IDENTITY, recent decisions). Read the resulting "
            f"output, decide whether to ProposeAction or stand down, and "
            f"narrate your reasoning."
        ),
        options={
            "manual_run": True,
            "agent_slug": agent_slug,
            "agent_id": str(agent_id),
        },
    )
    # ADR-296 v2 D1: operator-clicked agent runs are manual fires routed
    # through the manual_fire wake source. The funnel auto-escalates;
    # the synthetic recurrence's prompt carries the dispatch instruction
    # to the Reviewer (which will then invoke DispatchSpecialist).
    exec_result = await wake_manual_fire(svc_client, auth.user_id, synthetic)
    return {
        "success": exec_result.get("success", False),
        "trigger": exec_result.get("trigger"),
        "actions_taken": exec_result.get("actions_taken"),
        "proposals": exec_result.get("proposals"),
        "message": exec_result.get("message"),
        "slug": exec_result.get("slug"),
    }


# =============================================================================
# ADR-030: Source Freshness Routes
# =============================================================================


# ADR-138: Source freshness route removed — sources column dropped from agents table


# =============================================================================
# Run Management Routes
# =============================================================================

@router.get("/{agent_id}/runs")
async def list_runs(
    agent_id: UUID,
    auth: UserClient,
    limit: int = 20,
) -> list[VersionResponse]:
    """
    List all runs for an agent.
    """
    # Verify ownership
    check = (
        auth.client.table("agents")
        .select("id")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = (
        auth.client.table("agent_runs")
        .select("*")
        .eq("agent_id", str(agent_id))
        .order("version_number", desc=True)
        .limit(limit)
        .execute()
    )

    versions = result.data or []

    return [
        VersionResponse(
            id=v["id"],
            agent_id=v["agent_id"],
            version_number=v["version_number"],
            status=v["status"],
            draft_content=v.get("draft_content"),
            final_content=v.get("final_content"),
            edit_distance_score=v.get("edit_distance_score"),
            feedback_notes=v.get("feedback_notes"),
            created_at=v["created_at"],
            staged_at=v.get("staged_at"),
            approved_at=v.get("approved_at"),
            # ADR-030: Source fetch summary
            source_fetch_summary=_parse_source_fetch_summary(v.get("source_fetch_summary")),
            # ADR-049: Source snapshots for freshness tracking
            source_snapshots=_parse_source_snapshots(v.get("source_snapshots")),
            # ADR-101: Execution metadata
            metadata=v.get("metadata"),
        )
        for v in versions
    ]


@router.get("/{agent_id}/runs/{run_id}")
async def get_run(
    agent_id: UUID,
    run_id: UUID,
    auth: UserClient,
) -> VersionResponse:
    """
    Get a specific version with full content.
    """
    # Verify ownership through agent
    check = (
        auth.client.table("agents")
        .select("id")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = (
        auth.client.table("agent_runs")
        .select("*")
        .eq("id", str(run_id))
        .eq("agent_id", str(agent_id))
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Version not found")

    v = result.data

    return VersionResponse(
        id=v["id"],
        agent_id=v["agent_id"],
        version_number=v["version_number"],
        status=v["status"],
        draft_content=v.get("draft_content"),
        final_content=v.get("final_content"),
        edit_distance_score=v.get("edit_distance_score"),
        feedback_notes=v.get("feedback_notes"),
        created_at=v["created_at"],
        staged_at=v.get("staged_at"),
        approved_at=v.get("approved_at"),
        # ADR-028: Delivery fields
        delivery_status=v.get("delivery_status"),
        delivery_external_id=v.get("delivery_external_id"),
        delivery_external_url=v.get("delivery_external_url"),
        delivered_at=v.get("delivered_at"),
        # ADR-030: Source fetch summary
        source_fetch_summary=_parse_source_fetch_summary(v.get("source_fetch_summary")),
        # ADR-049: Source snapshots for freshness tracking
        source_snapshots=_parse_source_snapshots(v.get("source_snapshots")),
        # ADR-101: Execution metadata
        metadata=v.get("metadata"),
    )


@router.patch("/{agent_id}/runs/{run_id}")
async def update_run(
    agent_id: UUID,
    run_id: UUID,
    request: VersionUpdate,
    auth: UserClient,
) -> VersionResponse:
    """
    Update a version (approve, reject, or save edits).

    When final_content differs from draft_content, computes edit diff and score.
    """
    from services.feedback_engine import compute_edit_metrics

    # Verify ownership through agent
    check = (
        auth.client.table("agents")
        .select("id, title, role, scope, type_config")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get current version
    version_result = (
        auth.client.table("agent_runs")
        .select("*")
        .eq("id", str(run_id))
        .eq("agent_id", str(agent_id))
        .single()
        .execute()
    )

    if not version_result.data:
        raise HTTPException(status_code=404, detail="Version not found")

    current = version_result.data

    # Build update
    update_data = {}

    if request.status is not None:
        update_data["status"] = request.status
        if request.status == "approved":
            update_data["approved_at"] = datetime.now(timezone.utc).isoformat()

    if request.final_content is not None:
        update_data["final_content"] = request.final_content

        # Compute edit metrics if we have both draft and final
        if current.get("draft_content"):
            metrics = compute_edit_metrics(
                draft=current["draft_content"],
                final=request.final_content,
            )
            update_data["edit_diff"] = metrics.get("diff")
            update_data["edit_categories"] = metrics.get("categories")
            update_data["edit_distance_score"] = metrics.get("distance_score")

    if request.feedback_notes is not None:
        update_data["feedback_notes"] = request.feedback_notes

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    result = (
        auth.client.table("agent_runs")
        .update(update_data)
        .eq("id", str(run_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update version")

    v = result.data[0]

    logger.info(f"[AGENT] Version updated: {run_id} -> {v['status']}")

    # Activity log: record approval or rejection (ADR-063)
    if request.status in ("approved", "rejected"):
        try:
            from services.activity_log import write_activity, resolve_agent_project_slug
            from services.supabase import get_service_client
            import asyncio
            agent_title = check.data.get("title") or str(agent_id)
            event_type = "agent_approved" if request.status == "approved" else "agent_rejected"

            # ADR-064: Enhanced metadata for pattern detection
            metadata = {
                "agent_id": str(agent_id),
                "run_id": str(run_id),
                "role": check.data.get("role"),
            }
            # ADR-129: Enrich with project_slug
            _proj_slug = resolve_agent_project_slug(check.data)
            if _proj_slug:
                metadata["project_slug"] = _proj_slug

            # Track edit patterns for memory extraction
            if request.status == "approved":
                had_edits = bool(request.final_content and current.get("draft_content") and request.final_content.strip() != current.get("draft_content", "").strip())
                metadata["had_edits"] = had_edits
                if had_edits and request.final_content and current.get("draft_content"):
                    metadata["final_length"] = len(request.final_content)
                    metadata["draft_length"] = len(current.get("draft_content", ""))

            asyncio.create_task(write_activity(
                client=get_service_client(),
                user_id=auth.user_id,
                event_type=event_type,
                summary=f"{request.status.capitalize()} version of {agent_title}",
                event_ref=str(run_id),
                metadata=metadata,
            ))
        except Exception:
            pass  # Non-fatal

    # ADR-117 Phase 1: Distill cumulative feedback into workspace preferences
    if request.final_content or request.feedback_notes:
        try:
            from services.feedback_distillation import distill_feedback_to_workspace
            import asyncio
            asyncio.create_task(distill_feedback_to_workspace(
                client=auth.client,
                user_id=auth.user_id,
                agent=check.data,
            ))
        except Exception:
            pass  # Non-fatal — feedback persists in agent_runs regardless

    return VersionResponse(
        id=v["id"],
        agent_id=v["agent_id"],
        version_number=v["version_number"],
        status=v["status"],
        draft_content=v.get("draft_content"),
        final_content=v.get("final_content"),
        edit_distance_score=v.get("edit_distance_score"),
        feedback_notes=v.get("feedback_notes"),
        created_at=v["created_at"],
        staged_at=v.get("staged_at"),
        approved_at=v.get("approved_at"),
        # ADR-028: Delivery fields
        delivery_status=v.get("delivery_status"),
        delivery_external_id=v.get("delivery_external_id"),
        delivery_external_url=v.get("delivery_external_url"),
        delivered_at=v.get("delivered_at"),
    )


# =============================================================================
# ADR-119 Phase 4b: Agent Output History
# =============================================================================


@router.get("/{agent_id}/outputs")
async def list_agent_outputs(
    agent_id: UUID,
    auth: UserClient,
    limit: int = 20,
) -> dict:
    """
    List output folders for an agent with parsed manifests.

    ADR-119 P4b: Chronological output history for the agent detail Outputs tab.
    Each output folder contains output.md + manifest.json.
    """
    import json as _json
    from services.workspace import AgentWorkspace, get_agent_slug

    # Verify ownership and get slug
    agent_result = (
        auth.client.table("agents")
        .select("id, title")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .maybe_single()
        .execute()
    )
    if not agent_result or not agent_result.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    slug = get_agent_slug(agent_result.data)
    ws = AgentWorkspace(auth.client, auth.user_id, slug)

    # List output date-folders
    items = await ws.list("outputs/")
    folders = sorted([item.rstrip("/") for item in items if item.endswith("/")])

    outputs = []
    for full_folder in reversed(folders[-limit:]):
        manifest_raw = await ws.read(f"{full_folder}/manifest.json")
        if not manifest_raw:
            continue
        try:
            manifest = _json.loads(manifest_raw)
        except _json.JSONDecodeError:
            continue

        folder_id = full_folder.removeprefix("outputs/")
        outputs.append({
            "folder": folder_id,
            "version": manifest.get("version", 0),
            "created_at": manifest.get("created_at"),
            "status": manifest.get("status", "active"),
            "files": manifest.get("files", []),
            "sources": manifest.get("sources", []),
            "delivery": manifest.get("delivery"),
        })

    return {"outputs": outputs, "total": len(outputs)}


# =============================================================================
# ADR-087 Phase 3: Scoped Sessions
# =============================================================================


@router.get("/{agent_id}/sessions")
async def list_agent_sessions(
    agent_id: UUID,
    auth: UserClient,
    limit: int = 10,
) -> list[dict]:
    """
    List scoped chat sessions for an agent.

    ADR-087: Sessions are scoped to agents via chat_sessions.agent_id FK.
    Returns recent sessions with summary and message count.
    """
    # Verify ownership
    check = (
        auth.client.table("agents")
        .select("id")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Query scoped sessions
    result = (
        auth.client.table("chat_sessions")
        .select("id, created_at, summary")
        .eq("agent_id", str(agent_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    sessions = result.data or []

    # Get message counts per session
    response = []
    for s in sessions:
        count_result = (
            auth.client.table("session_messages")
            .select("id", count="exact")
            .eq("session_id", s["id"])
            .execute()
        )
        response.append({
            "id": s["id"],
            "created_at": s["created_at"],
            "summary": s.get("summary"),
            "message_count": count_result.count or 0,
        })

    return response


# =============================================================================
# Helper Functions
# =============================================================================

def validate_role_config(role: str, config: dict) -> dict:
    """
    Validate and normalize type_config for a given role (ADR-109).
    Returns the validated config dict.
    """
    config_classes: dict[str, type[BaseModel]] = {
        "digest": DigestConfig,
        "prepare": PrepareConfig,
        "synthesize": SynthesizeConfig,
        "monitor": MonitorConfig,
        "research": ResearchConfig,
        "custom": CustomConfig,
    }

    try:
        config_class = config_classes.get(role, CustomConfig)
        validated = config_class(**config)
        return validated.model_dump()
    except Exception as e:
        logger.warning(f"[AGENT] Invalid type_config for role={role}: {e}")
        return get_default_config(role)



# ADR-138: calculate_next_run() removed — schedule/next_pulse_at columns dropped from agents table
