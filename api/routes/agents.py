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
    "digest",      # Compress, summarize — platform recap
    "prepare",     # Anticipate, assemble — meeting prep
    "monitor",     # Track, diff, alert — domain watching
    "research",    # Investigate, analyze — bounded research
    "synthesize",  # Connect, derive insight — cross-source synthesis
    "act",         # Execute, respond, post — platform actions (future)
    "custom",      # User-defined
]


# ADR-111: Scope inference moved to shared agent_creation module
from services.agent_creation import infer_scope


# =============================================================================
# ADR-109: Role Configs
# =============================================================================

class DigestConfig(BaseModel):
    """Config for digest role. Platform inferred from sources[] at assembly time."""
    focus: str = "key discussions and decisions"
    reply_threshold: int = 3    # Min replies to flag as hot thread (Slack)
    reaction_threshold: int = 2  # Min reactions to surface a message (Slack)


class PrepareConfig(BaseModel):
    """Config for prepare role (auto meeting prep, daily calendar-driven)."""
    delivery_time: Optional[str] = "08:00"  # Preferred morning delivery time


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

class RecipientContext(BaseModel):
    """Who receives the agent and what they care about."""
    name: Optional[str] = None
    role: Optional[str] = None
    priorities: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ScheduleConfig(BaseModel):
    """Schedule configuration for recurring execution."""
    frequency: Literal["daily", "weekly", "biweekly", "monthly", "custom"]
    day: Optional[str] = None  # e.g., "monday", "1", "15"
    time: Optional[str] = None  # e.g., "09:00"
    timezone: str = "America/Los_Angeles"
    cron: Optional[str] = None  # For custom frequency


# =============================================================================
# ADR-031 Phase 4: Event Trigger Definitions
# =============================================================================

class CooldownConfig(BaseModel):
    """Cooldown configuration to prevent rapid re-triggering."""
    type: Literal["per_thread", "per_channel", "per_sender", "global"] = "global"
    duration_minutes: int = 5
    max_triggers_per_duration: int = 1


class EventTriggerConfig(BaseModel):
    """
    Event trigger configuration for agents.

    Used when trigger_type='event'.
    """
    platform: Literal["slack", "gmail", "notion"]
    event_types: list[str] = Field(default_factory=list)  # ["app_mention", "message_im"]
    resource_ids: list[str] = Field(default_factory=list)  # ["C123", "D456"]
    cooldown: Optional[CooldownConfig] = None
    # ADR-092: Reactive mode — number of observations before generating a version
    observation_threshold: int = 5
    # Optional filters
    sender_filter: Optional[list[str]] = None  # Only trigger for specific senders
    keyword_filter: Optional[list[str]] = None  # Only trigger if content contains keywords


class DataSource(BaseModel):
    """A source of information for the agent.

    ADR-104: scope and filters fields removed — never consumed by execution pipeline.
    Targeting is handled entirely by agent_instructions.
    """
    type: Literal["url", "document", "description", "integration_import"]
    value: str  # URL, document_id, or description text
    label: Optional[str] = None
    # Integration source fields
    provider: Optional[Literal["gmail", "slack", "notion"]] = None
    source: Optional[str] = None  # inbox, query:..., channel_id, page_id


class AgentCreate(BaseModel):
    """Create agent request — ADR-109 Scope × Role × Trigger."""
    title: str
    # ADR-109: Role is user-selected, scope is auto-inferred
    role: Role = "custom"
    type_config: Optional[dict] = None  # Role-specific config, validated per role
    recipient_context: Optional[RecipientContext] = None
    # Trigger configuration
    trigger_type: Literal["schedule", "event", "manual"] = "schedule"
    schedule: Optional[ScheduleConfig] = None  # Required if trigger_type='schedule'
    trigger_config: Optional[EventTriggerConfig] = None  # Required if trigger_type='event'
    sources: list[DataSource] = Field(default_factory=list)
    # ADR-028: Destination-first agents
    destination: Optional[dict] = None  # { platform, target, format, options }
    # ADR-092: Mode taxonomy (trigger axis in ADR-109)
    mode: Literal["recurring", "goal", "reactive", "proactive", "coordinator"] = "recurring"
    # ADR-087: Agent-scoped context
    agent_instructions: Optional[str] = None
    description: Optional[str] = None


class AgentUpdate(BaseModel):
    """Update agent request — ADR-109."""
    title: Optional[str] = None
    role: Optional[Role] = None
    type_config: Optional[dict] = None
    recipient_context: Optional[RecipientContext] = None
    trigger_type: Optional[Literal["schedule", "event", "manual"]] = None
    schedule: Optional[ScheduleConfig] = None
    trigger_config: Optional[EventTriggerConfig] = None
    sources: Optional[list[DataSource]] = None
    status: Optional[Literal["active", "paused", "archived"]] = None
    destination: Optional[dict] = None
    agent_instructions: Optional[str] = None
    mode: Optional[Literal["recurring", "goal", "reactive", "proactive", "coordinator"]] = None
    description: Optional[str] = None


class AgentResponse(BaseModel):
    """Agent response — ADR-109 Scope × Role × Trigger."""
    id: str
    title: str
    # ADR-109: Scope × Role (replaces agent_type + type_classification)
    scope: str = "cross_platform"
    role: str = "custom"
    type_config: Optional[dict] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None  # For UI display
    recipient_context: Optional[dict] = None
    # ADR-031 Phase 4: Trigger configuration
    trigger_type: str = "schedule"  # schedule, event, manual
    schedule: Optional[dict] = None
    trigger_config: Optional[dict] = None  # Event trigger config
    sources: list[dict] = Field(default_factory=list)
    status: str
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None
    next_pulse_at: Optional[str] = None
    last_triggered_at: Optional[str] = None  # ADR-031: Last event trigger
    version_count: int = 0
    latest_version_status: Optional[str] = None
    # ADR-028: Destination-first agents
    destination: Optional[dict] = None  # { platform, target, format, options }
    # Quality metrics (ADR-018: feedback loop)
    quality_score: Optional[float] = None
    quality_trend: Optional[str] = None
    avg_edit_distance: Optional[float] = None
    # ADR-030: Source freshness
    source_freshness: Optional[list[dict]] = None
    # ADR-068: Agent origin
    origin: str = "user_configured"  # user_configured | coordinator_created
    # ADR-087: Agent-scoped context
    agent_instructions: Optional[str] = None
    agent_memory: Optional[dict] = None
    # ADR-092: Mode taxonomy (trigger axis in ADR-109)
    mode: str = "recurring"  # recurring | goal | reactive | proactive | coordinator
    description: Optional[str] = None


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
    from services.platform_limits import check_agent_limit
    from services.agent_creation import create_agent_record

    # ADR-053: Check agent limit before creation (route concern — not in shared function)
    allowed, message = check_agent_limit(auth.client, auth.user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "agent_limit_reached",
                "message": message,
                "upgrade_url": "/settings?tab=billing",
            }
        )

    # Handle type_config - use provided or get defaults
    type_config = request.type_config
    if type_config is None:
        if request.role == "custom" and request.description:
            type_config = {"description": request.description or ""}
        else:
            type_config = get_default_config(request.role)

    # Validate type_config against the role
    validated_config = validate_role_config(request.role, type_config)

    sources_raw = [s.model_dump() for s in request.sources]

    # ADR-111: Single creation path via create_agent_record()
    result = await create_agent_record(
        client=auth.client,
        user_id=auth.user_id,
        title=request.title,
        role=request.role,
        origin="user_configured",
        description=request.description,
        agent_instructions=request.agent_instructions,
        sources=sources_raw,
        schedule=request.schedule.model_dump() if request.schedule else None,
        mode=request.mode,
        trigger_type=request.trigger_type if request.trigger_type != "schedule" else None,
        recipient_context=request.recipient_context.model_dump() if request.recipient_context else None,
        type_config=validated_config,
        destination=request.destination,
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

        project_id=None,  # ADR-034: Deprecated
        recipient_context=agent.get("recipient_context"),
        schedule=agent["schedule"],
        sources=agent.get("sources", []),
        status=agent["status"],
        created_at=agent["created_at"],
        updated_at=agent["updated_at"],
        next_pulse_at=agent.get("next_pulse_at"),
        destination=agent.get("destination"),
        origin=agent.get("origin", "user_configured"),
        agent_instructions=intelligence.get("agent_instructions"),
        agent_memory=intelligence.get("agent_memory"),
        mode=agent.get("mode", "recurring"),
        description=agent.get("description"),
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
    # Fetch agents with versions
    # Note: ADR-034 removed projects table, agents are now user-scoped
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
    agents = result.data or []

    # ADR-106: Read workspace intelligence for all agents in parallel
    import asyncio
    from services.workspace import get_agent_intelligence

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

        # ADR-034: Projects removed, agents are user-scoped
        responses.append(AgentResponse(
            id=d["id"],
            title=d["title"],
            scope=d.get("scope", "cross_platform"),
            role=d.get("role", "custom"),
            type_config=d.get("type_config"),
            project_id=None,  # ADR-034: Deprecated
            project_name=None,  # ADR-034: Deprecated
            recipient_context=d.get("recipient_context"),
            schedule=d["schedule"],
            sources=d.get("sources", []),
            status=d["status"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            last_run_at=d.get("last_run_at"),
            next_pulse_at=d.get("next_pulse_at"),
            version_count=version_count,
            latest_version_status=latest_version["status"] if latest_version else None,
            # ADR-028: Destination-first agents
            destination=d.get("destination"),
            quality_score=quality_score,
            quality_trend=quality_trend,
            avg_edit_distance=avg_edit_distance,
            # ADR-068: Agent origin
            origin=d.get("origin", "user_configured"),
            # ADR-106: Workspace is source of truth
            agent_instructions=intel.get("agent_instructions"),
            agent_memory=intel.get("agent_memory"),
            mode=d.get("mode", "recurring"),
            description=d.get("description"),
        ))

    return responses


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
            # ADR-031: Platform-native variants
    
            project_id=None,  # ADR-034: Deprecated
            project_name=None,  # ADR-034: Deprecated
            recipient_context=agent.get("recipient_context"),
            schedule=agent["schedule"],
            sources=agent.get("sources", []),
            status=agent["status"],
            created_at=agent["created_at"],
            updated_at=agent["updated_at"],
            last_run_at=agent.get("last_run_at"),
            next_pulse_at=agent.get("next_pulse_at"),
            version_count=len(versions),
            # ADR-028: Destination-first agents
            destination=agent.get("destination"),
            # ADR-068: Agent origin
            origin=agent.get("origin", "user_configured"),
            # ADR-106: Workspace is source of truth
            agent_instructions=intelligence.get("agent_instructions"),
            agent_memory=intelligence.get("agent_memory"),
            mode=agent.get("mode", "recurring"),
            description=agent.get("description"),
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
    if request.recipient_context is not None:
        update_data["recipient_context"] = request.recipient_context.model_dump()
    if request.schedule is not None:
        update_data["schedule"] = request.schedule.model_dump()
        update_data["next_pulse_at"] = calculate_next_run(request.schedule)
    if request.sources is not None:
        update_data["sources"] = [s.model_dump() for s in request.sources]
        # ADR-109: Re-infer scope when sources change
        new_role = request.role or check.data.get("role", "custom")
        new_mode = request.mode or check.data.get("mode", "recurring")
        update_data["scope"] = infer_scope(update_data["sources"], new_role, new_mode)
    if request.status is not None:
        update_data["status"] = request.status
    # ADR-028: Destination-first agents
    if request.destination is not None:
        update_data["destination"] = request.destination
    # ADR-106: agent_instructions written to workspace only (not DB column)
    if request.mode is not None:
        update_data["mode"] = request.mode
    # Legacy fields
    if request.description is not None:
        update_data["description"] = request.description

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
        project_id=None,  # ADR-034: Deprecated
        recipient_context=d.get("recipient_context"),
        schedule=d["schedule"],
        sources=d.get("sources", []),
        status=d["status"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        last_run_at=d.get("last_run_at"),
        next_pulse_at=d.get("next_pulse_at"),
        # ADR-028: Destination-first agents
        destination=d.get("destination"),
        # ADR-068: Agent origin
        origin=d.get("origin", "user_configured"),
        # ADR-106: Workspace is source of truth
        agent_instructions=intelligence.get("agent_instructions"),
        agent_memory=intelligence.get("agent_memory"),
        mode=d.get("mode", "recurring"),
        # Legacy: description still consumed by Research/Hybrid strategies
        description=d.get("description"),
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
    """
    Trigger an ad-hoc agent run.

    ADR-042: Uses simplified single-call execute_agent_generation().
    """
    from services.agent_execution import execute_agent_generation

    # Get agent
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

    logger.info(f"[AGENT] Triggering run: {agent_id}")

    # ADR-042: Execute with simplified single-call flow
    exec_result = await execute_agent_generation(
        client=auth.client,
        user_id=auth.user_id,
        agent=agent,
        trigger_context={"type": "manual"},
    )

    return {
        "success": exec_result.get("success", False),
        "run_id": exec_result.get("run_id"),
        "version_number": exec_result.get("version_number"),
        "status": exec_result.get("status"),
        "message": exec_result.get("message"),
    }


# =============================================================================
# ADR-030: Source Freshness Routes
# =============================================================================

class SourceFreshnessItem(BaseModel):
    """ADR-030: Freshness info for a single source."""
    source_index: int
    source_type: str
    provider: Optional[str] = None
    last_fetched_at: Optional[str] = None
    last_status: Optional[str] = None
    items_fetched: int = 0
    is_stale: bool = True


@router.get("/{agent_id}/sources/freshness")
async def get_source_freshness(
    agent_id: UUID,
    auth: UserClient,
) -> list[SourceFreshnessItem]:
    """
    ADR-030: Get freshness info for all sources of an agent.

    Returns when each source was last fetched, how many items were retrieved,
    and whether the source is considered stale (>7 days since last fetch).
    """
    # Verify ownership
    check = (
        auth.client.table("agents")
        .select("id, sources")
        .eq("id", str(agent_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = check.data
    sources = agent.get("sources", [])

    # Get latest source run for each source
    runs_result = (
        auth.client.table("agent_source_runs")
        .select("source_index, source_type, provider, completed_at, status, items_fetched")
        .eq("agent_id", str(agent_id))
        .order("completed_at", desc=True)
        .execute()
    )

    runs = runs_result.data or []

    # Group by source_index, taking the most recent
    latest_by_index: dict[int, dict] = {}
    for run in runs:
        idx = run["source_index"]
        if idx not in latest_by_index:
            latest_by_index[idx] = run

    # Build response for all sources
    result = []
    from datetime import datetime, timedelta, timezone

    stale_threshold = datetime.now(timezone.utc) - timedelta(days=7)

    for idx, source in enumerate(sources):
        source_type = source.get("type", "description")

        # Only integration sources have freshness tracking
        if source_type != "integration_import":
            continue

        latest = latest_by_index.get(idx)
        if latest:
            completed_at = latest.get("completed_at")
            is_stale = True
            if completed_at:
                try:
                    from dateutil import parser as dateparser
                    completed_dt = dateparser.parse(completed_at)
                    is_stale = completed_dt < stale_threshold
                except Exception as e:
                    logger.debug(f"Failed to parse completed_at '{completed_at}': {e}")

            result.append(SourceFreshnessItem(
                source_index=idx,
                source_type=source_type,
                provider=source.get("provider") or source.get("platform"),
                last_fetched_at=completed_at,
                last_status=latest.get("status"),
                items_fetched=latest.get("items_fetched", 0),
                is_stale=is_stale,
            ))
        else:
            # No run yet - definitely stale
            result.append(SourceFreshnessItem(
                source_index=idx,
                source_type=source_type,
                provider=source.get("provider") or source.get("platform"),
                last_fetched_at=None,
                last_status=None,
                items_fetched=0,
                is_stale=True,
            ))

    return result


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
        .select("id, title, role, scope, destination, type_config")
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

    logger.info(f"[AGENT] Version updated: {version_id} -> {v['status']}")

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


def calculate_next_run(schedule: ScheduleConfig) -> str:
    """
    Calculate the next pulse timestamp based on schedule configuration.

    Delegates to the unified scheduler's calculate_next_pulse_from_schedule()
    to ensure consistency across all creation and update paths (ADR-126).
    """
    from jobs.unified_scheduler import calculate_next_pulse_from_schedule

    sched_dict = schedule.model_dump()
    return calculate_next_pulse_from_schedule(sched_dict).isoformat()
