"""
TP Composer — ADR-111 Phases 3-5: Heartbeat + Composer Assessment + Lifecycle

TP's compositional capability, implemented as:
1. Heartbeat data query (cheap DB checks, zero LLM)
2. Composer assessment (LLM reasoning, only when warranted)
3. Lifecycle progression (maturity signals, dissolution, scope expansion)

The Heartbeat runs on the unified scheduler cadence. It queries the user's
substrate (platforms, agents, content, feedback, maturity) and decides whether
Composer needs to reason about creating/adjusting/dissolving agents.

Cost model (per ADR-111):
- Heartbeat data query: ~0 cost (DB queries + per-agent maturity signals)
- Lifecycle actions: ~0 cost (deterministic, no LLM)
- LLM reasoning: only when assessment identifies potential action
- "Nothing to do" is first-class outcome (HEARTBEAT_OK)

Tier gating:
- Free: daily heartbeat (runs in midnight UTC window alongside memory extraction)
- Pro: more frequent (every scheduler cycle, but cheap-first means negligible cost)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Composer uses Haiku for cost-efficiency (same as proactive_review)
COMPOSER_MODEL = "claude-haiku-4-5-20251001"
COMPOSER_MAX_TOKENS = 2048


# =============================================================================
# Heartbeat Data Query (Zero LLM — cheap DB checks)
# =============================================================================

async def heartbeat_data_query(client: Any, user_id: str) -> dict:
    """
    Cheap data-only assessment of a user's agent workforce and substrate.

    Returns a structured dict that `should_composer_act()` evaluates.
    Zero LLM cost — pure DB queries.
    """
    now = datetime.now(timezone.utc)

    # 1. Connected platforms
    # selected_sources lives inside landscape JSONB, not as a top-level column
    platforms = []
    try:
        result = (
            client.table("platform_connections")
            .select("platform, status, landscape")
            .eq("user_id", user_id)
            .in_("status", ["connected", "active"])
            .execute()
        )
        # Extract selected_sources from landscape JSONB for downstream use
        for row in (result.data or []):
            landscape = row.get("landscape") or {}
            platforms.append({
                "platform": row["platform"],
                "status": row["status"],
                "selected_sources": landscape.get("selected_sources", []),
            })
    except Exception as e:
        logger.warning(f"[COMPOSER] Platform query failed: {e}")

    connected_platforms = [p["platform"] for p in platforms]

    # 2. Existing agents — skill, scope, mode, origin, status, last_run_at, feedback
    agents = []
    try:
        result = (
            client.table("agents")
            .select("id, title, skill, scope, mode, origin, status, created_at, last_run_at, sources")
            .eq("user_id", user_id)
            .neq("status", "archived")
            .execute()
        )
        # Note: origin IS selected above — used by maturity signals and lifecycle guards
        agents = result.data or []
    except Exception as e:
        logger.warning(f"[COMPOSER] Agent query failed: {e}")

    active_agents = [a for a in agents if a.get("status") == "active"]
    paused_agents = [a for a in agents if a.get("status") == "paused"]

    # 3. Agent skills coverage map
    skills_present = set(a.get("skill", "custom") for a in active_agents)

    # 4. Platform coverage — which platforms have digest agents?
    # Check both sources[].provider AND bootstrap title patterns (bootstrap agents
    # may have empty sources before first sync populates them — ADR-110/113)
    _TITLE_TO_PLATFORM = {"Slack Recap": "slack", "Gmail Digest": "google", "Notion Summary": "notion"}
    platforms_with_digest = set()
    for agent in active_agents:
        if agent.get("skill") == "digest":
            # Source-based detection (populated agents)
            for src in (agent.get("sources") or []):
                if isinstance(src, dict):
                    provider = src.get("provider")
                    if provider:
                        platforms_with_digest.add(provider)
            # Title-based detection (bootstrap agents with empty sources)
            title_platform = _TITLE_TO_PLATFORM.get(agent.get("title"))
            if title_platform:
                platforms_with_digest.add(title_platform)

    platforms_without_digest = [
        p for p in connected_platforms
        if p not in platforms_with_digest and p != "calendar"  # Calendar excluded per ADR-110
    ]

    # 5. Stale agents — active but haven't run in 2x their schedule frequency
    stale_agents = []
    for agent in active_agents:
        last_run = agent.get("last_run_at")
        if not last_run:
            # Never run — stale if created more than 48h ago
            created = agent.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if now - created_dt > timedelta(hours=48):
                    stale_agents.append(agent)
            except (ValueError, TypeError):
                pass
            continue
        try:
            last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            if now - last_dt > timedelta(days=14):
                stale_agents.append(agent)
        except (ValueError, TypeError):
            pass

    # 6. Recent feedback signals (last 7 days)
    # agent_runs has no user_id — query through agents table
    feedback_count = 0
    try:
        week_ago = (now - timedelta(days=7)).isoformat()
        agent_ids = [a["id"] for a in agents]
        if agent_ids:
            result = (
                client.table("agent_runs")
                .select("id", count="exact")
                .in_("agent_id", agent_ids)
                .in_("status", ["approved", "delivered"])
                .gte("approved_at", week_ago)
                .execute()
            )
            feedback_count = result.count or 0
    except Exception as e:
        logger.warning(f"[COMPOSER] Feedback query failed: {e}")

    # 7. ADR-111 Phase 5: Per-agent maturity signals
    # Run count, approval rate, edit distance trend, tenure
    maturity_signals = []
    try:
        for agent in active_agents:
            aid = agent["id"]
            runs_result = (
                client.table("agent_runs")
                .select("status, edit_distance_score, approved_at, created_at")
                .eq("agent_id", aid)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            runs = runs_result.data or []
            total_runs = len(runs)

            if total_runs == 0:
                maturity_signals.append({
                    "agent_id": aid,
                    "title": agent["title"],
                    "skill": agent.get("skill"),
                    "scope": agent.get("scope"),
                    "origin": agent.get("origin"),
                    "total_runs": 0,
                    "maturity": "nascent",
                })
                continue

            # Approval rate: weighted signal from explicit approval vs auto-delivery
            # Explicit approval (user reviewed and approved) = full trust signal
            # Delivered (auto-delivered, never reviewed) = partial signal (0.5 weight)
            # This prevents maturity inflation from unreviewed outputs
            completed = [r for r in runs if r.get("status") in ("approved", "delivered", "rejected")]
            explicitly_approved = len([r for r in runs if r.get("status") == "approved"])
            auto_delivered = len([r for r in runs if r.get("status") == "delivered"])
            rejected = len([r for r in runs if r.get("status") == "rejected"])
            if completed:
                weighted_approvals = explicitly_approved + (auto_delivered * 0.5)
                approval_rate = weighted_approvals / len(completed)
            else:
                approval_rate = 0.0

            # Edit distance trend: are edits decreasing? (convergence = agent improving)
            distances = [
                r["edit_distance_score"] for r in runs
                if r.get("edit_distance_score") is not None
            ]
            edit_trend = None  # None = insufficient data
            if len(distances) >= 3:
                recent_avg = sum(distances[:3]) / 3
                older_avg = sum(distances[3:min(6, len(distances))]) / max(1, min(3, len(distances) - 3))
                if older_avg > 0:
                    # Negative = improving (less editing needed), positive = degrading
                    edit_trend = (recent_avg - older_avg) / older_avg

            # Tenure: days since agent created
            tenure_days = 0
            created_at = agent.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                tenure_days = (now - created_dt).days
            except (ValueError, TypeError):
                pass

            # Classify maturity stage
            if total_runs >= 10 and approval_rate >= 0.8:
                maturity = "mature"
            elif total_runs >= 5 and approval_rate >= 0.6:
                maturity = "developing"
            elif total_runs >= 1:
                maturity = "nascent"
            else:
                maturity = "nascent"

            # Underperformer detection: 5+ runs with <40% approval
            is_underperformer = total_runs >= 5 and approval_rate < 0.4

            maturity_signals.append({
                "agent_id": aid,
                "title": agent["title"],
                "skill": agent.get("skill"),
                "scope": agent.get("scope"),
                "origin": agent.get("origin"),
                "total_runs": total_runs,
                "approval_rate": round(approval_rate, 2),
                "edit_trend": round(edit_trend, 2) if edit_trend is not None else None,
                "tenure_days": tenure_days,
                "maturity": maturity,
                "is_underperformer": is_underperformer,
            })
    except Exception as e:
        logger.warning(f"[COMPOSER] Maturity signal query failed: {e}")

    # 8. Tier check — how many agents can user have?
    from services.platform_limits import check_agent_limit
    can_create, limit_message = check_agent_limit(client, user_id)

    # 9. Knowledge corpus signals (ADR-114 Phase 1)
    # Single DB query on workspace_files with indexed path prefix. Zero LLM cost.
    _VERSION_FILE_RE = re.compile(r"/v\d+\.md$")
    KNOWLEDGE_CLASSES = ["digests", "analyses", "briefs", "research", "insights"]
    knowledge = {
        "total_files": 0,
        "by_class": {c: 0 for c in KNOWLEDGE_CLASSES},
        "latest_at": None,
        "agents_producing": [],
    }
    try:
        ws_result = (
            client.table("workspace_files")
            .select("path, metadata, updated_at")
            .eq("user_id", user_id)
            .like("path", "/knowledge/%")
            .execute()
        )
        rows = [r for r in (ws_result.data or []) if not _VERSION_FILE_RE.search(r.get("path", ""))]

        # Count by content class
        for row in rows:
            path = row.get("path", "")
            for cls in KNOWLEDGE_CLASSES:
                if path.startswith(f"/knowledge/{cls}/"):
                    knowledge["by_class"][cls] += 1
                    break

        knowledge["total_files"] = sum(knowledge["by_class"].values())

        # Latest file timestamp
        timestamps = [r.get("updated_at") for r in rows if r.get("updated_at")]
        if timestamps:
            knowledge["latest_at"] = max(timestamps)

        # Agents producing: distinct agent_id from metadata → agent titles
        producing_ids = set()
        for row in rows:
            meta = row.get("metadata") or {}
            aid = meta.get("agent_id")
            if aid:
                producing_ids.add(aid)
        agent_id_to_title = {a["id"]: a["title"] for a in agents}
        knowledge["agents_producing"] = sorted(
            agent_id_to_title[aid] for aid in producing_ids if aid in agent_id_to_title
        )
    except Exception as e:
        logger.warning(f"[COMPOSER] Knowledge corpus query failed: {e}")

    return {
        "user_id": user_id,
        "timestamp": now.isoformat(),
        "connected_platforms": connected_platforms,
        "platform_details": platforms,
        "agents": {
            "total": len(agents),
            "active": len(active_agents),
            "paused": len(paused_agents),
            "skills_present": list(skills_present),
            "active_list": [
                {"id": a["id"], "title": a["title"], "skill": a.get("skill"), "scope": a.get("scope")}
                for a in active_agents
            ],
        },
        "coverage": {
            "platforms_with_digest": list(platforms_with_digest),
            "platforms_without_digest": platforms_without_digest,
        },
        "health": {
            "stale_agents": [
                {"id": a["id"], "title": a["title"], "last_run_at": a.get("last_run_at")}
                for a in stale_agents
            ],
        },
        "maturity": {
            "signals": maturity_signals,
            "mature_agents": [s for s in maturity_signals if s.get("maturity") == "mature"],
            "underperformers": [s for s in maturity_signals if s.get("is_underperformer")],
        },
        "feedback": {
            "recent_count": feedback_count,
        },
        "tier": {
            "can_create": can_create,
            "limit_message": limit_message if not can_create else None,
        },
        "knowledge": knowledge,  # ADR-114 Phase 1
    }


# =============================================================================
# Should Composer Act? (Pure logic — no LLM)
# =============================================================================

def should_composer_act(assessment: dict) -> tuple[bool, str]:
    """
    Given a heartbeat assessment, decide if Composer should reason (LLM call).

    Returns (should_act, reason).
    "Nothing to do" is first-class — most heartbeats should return False.
    """
    # No substrate at all — no platforms, no agents, nothing to compose from
    # Platform connections are the onramp, not the engine (FOUNDATIONS.md).
    # Users with agents but no platforms (e.g., research agents, file uploads) still get heartbeat.
    if not assessment["connected_platforms"] and assessment["agents"]["active"] == 0:
        return False, "HEARTBEAT_OK: no substrate (no platforms, no agents)"

    # ADR-111 Phase 5: Lifecycle — underperformers need attention (even at tier limit)
    underperformers = assessment.get("maturity", {}).get("underperformers", [])
    if underperformers:
        titles = [u["title"] for u in underperformers[:3]]
        return True, f"lifecycle_underperformer: {len(underperformers)} agents underperforming (<40% approval): {titles}"

    # ADR-111 Phase 5: Lifecycle — mature agents ready for scope expansion
    mature = assessment.get("maturity", {}).get("mature_agents", [])
    expandable = [
        m for m in mature
        if m.get("scope") == "platform" and m.get("skill") == "digest"
        and m.get("total_runs", 0) >= 10
    ]
    if expandable and len(assessment["connected_platforms"]) >= 2:
        titles = [e["title"] for e in expandable[:2]]
        return True, f"lifecycle_expansion: {len(expandable)} mature digest agents may warrant cross-platform synthesis: {titles}"

    # Can't create agents if at tier limit (but lifecycle checks above still fire)
    if not assessment["tier"]["can_create"]:
        return False, "HEARTBEAT_OK: at tier agent limit"

    # Coverage gap: platform connected but no digest agent
    gaps = assessment["coverage"]["platforms_without_digest"]
    if gaps:
        return True, f"coverage_gap: platforms without digest: {gaps}"

    # Stale agents worth investigating
    stale = assessment["health"]["stale_agents"]
    if len(stale) >= 2:
        titles = [a["title"] for a in stale[:3]]
        return True, f"stale_agents: {len(stale)} agents haven't run recently: {titles}"

    # Multi-platform opportunity: 2+ platforms connected but no cross-platform agent
    if len(assessment["connected_platforms"]) >= 2:
        skills = assessment["agents"]["skills_present"]
        if "synthesize" not in skills and assessment["agents"]["active"] >= 2:
            return True, "cross_platform_opportunity: 2+ platforms, no synthesize agent"

    # Active feedback suggests engaged user — check for expansion opportunities
    if assessment["feedback"]["recent_count"] >= 5 and assessment["agents"]["active"] <= 2:
        return True, "engaged_user: high feedback + low agent count — may benefit from more agents"

    # ADR-111 Phase 5: Cross-agent pattern — multiple digest agents producing
    # similar content from overlapping sources (consolidation opportunity)
    signals = assessment.get("maturity", {}).get("signals", [])
    digest_agents = [s for s in signals if s.get("skill") == "digest" and s.get("total_runs", 0) >= 3]
    if len(digest_agents) >= 3 and "synthesize" not in assessment["agents"]["skills_present"]:
        return True, f"cross_agent_pattern: {len(digest_agents)} active digest agents — synthesis agent would consolidate insights"

    # ADR-114 Phase 2: Knowledge-substrate heuristics
    knowledge = assessment.get("knowledge", {})
    by_class = knowledge.get("by_class", {})
    total_knowledge = knowledge.get("total_files", 0)

    # knowledge_gap_analysis: many digests, no analyses, no synthesize agent
    if (by_class.get("digests", 0) >= 10
            and by_class.get("analyses", 0) == 0
            and "synthesize" not in assessment["agents"]["skills_present"]):
        return True, (
            f"knowledge_gap_analysis: {by_class['digests']} digest files but 0 analyses "
            "— system is perceiving but not reasoning"
        )

    # stale_knowledge: latest /knowledge/ file > 7 days old, agents still active
    if knowledge.get("latest_at") and assessment["agents"]["active"] > 0:
        try:
            latest_dt = datetime.fromisoformat(knowledge["latest_at"].replace("Z", "+00:00"))
            days_stale = (now - latest_dt).days
            if days_stale > 7:
                return True, (
                    f"stale_knowledge: most recent knowledge file is {days_stale}d old "
                    f"but {assessment['agents']['active']} agents active"
                )
        except (ValueError, TypeError):
            pass

    # knowledge_asymmetry: 80%+ of knowledge is digests, minimal reasoning output
    if total_knowledge >= 10:
        digest_count = by_class.get("digests", 0)
        non_digest = total_knowledge - digest_count
        if digest_count / total_knowledge >= 0.8 and non_digest <= 1:
            return True, (
                f"knowledge_asymmetry: {digest_count}/{total_knowledge} knowledge files are digests "
                "— system needs reasoning agents (analyses/research)"
            )

    return False, "HEARTBEAT_OK: workforce healthy, no gaps detected"


# =============================================================================
# Composer Assessment (LLM — only when warranted)
# =============================================================================

# Agent templates Composer can create (extends bootstrap templates)
COMPOSER_TEMPLATES = {
    "digest": {
        "skill": "digest",
        "mode": "recurring",
        "frequency": "daily",
    },
    "synthesize": {
        "skill": "synthesize",
        "mode": "recurring",
        "frequency": "weekly",
    },
    "monitor": {
        "skill": "monitor",
        "mode": "recurring",
        "frequency": "daily",
    },
}

# Platform-specific digest templates (same as bootstrap, but used by Composer for gap-filling)
PLATFORM_DIGEST_TITLES = {
    "slack": "Slack Recap",
    "gmail": "Gmail Digest",
    "notion": "Notion Summary",
}


async def run_composer_assessment(
    client: Any,
    user_id: str,
    assessment: dict,
    reason: str,
) -> dict:
    """
    Run Composer's assessment and auto-create/adjust agents when warranted.

    Routes to appropriate handler based on trigger reason:
    - coverage_gap → deterministic gap-fill (no LLM)
    - lifecycle_* / cross_agent_* → lifecycle assessment (no LLM)
    - everything else → LLM reasoning

    Returns:
        {
            "action": "created" | "lifecycle" | "observed" | "skipped",
            "agents_created": [...],
            "lifecycle_actions": [...],
            "observations": [...],
        }
    """
    result = {
        "action": "observed",
        "agents_created": [],
        "lifecycle_actions": [],
        "observations": [],
    }

    # Fast path: deterministic gap-filling (no LLM needed)
    gaps = assessment["coverage"]["platforms_without_digest"]
    if gaps and reason.startswith("coverage_gap"):
        for platform in gaps:
            agent_id = await _create_digest_for_platform(client, user_id, platform, assessment)
            if agent_id:
                result["agents_created"].append({
                    "agent_id": agent_id,
                    "platform": platform,
                    "skill": "digest",
                    "reason": "coverage_gap",
                })
        if result["agents_created"]:
            result["action"] = "created"
        return result

    # ADR-111 Phase 5: Lifecycle assessment path (no LLM — deterministic)
    if reason.startswith(("lifecycle_", "cross_agent_")):
        lifecycle_result = await run_lifecycle_assessment(client, user_id, assessment, reason)
        result["lifecycle_actions"] = lifecycle_result.get("actions_taken", [])
        result["observations"].extend(lifecycle_result.get("observations", []))

        # Lifecycle actions that create agents go into agents_created too
        for action in result["lifecycle_actions"]:
            if action.get("action") == "created":
                result["agents_created"].append(action)

        if result["lifecycle_actions"]:
            result["action"] = "lifecycle"
        return result

    # LLM assessment path for non-obvious cases
    try:
        created = await _llm_composer_assessment(client, user_id, assessment, reason)
        result["agents_created"] = created
        if created:
            result["action"] = "created"
        else:
            result["observations"].append(f"Composer assessed: {reason}. No action taken.")
    except Exception as e:
        logger.error(f"[COMPOSER] LLM assessment failed: {e}")
        result["observations"].append(f"Assessment error: {e}")

    return result


async def _create_digest_for_platform(
    client: Any,
    user_id: str,
    platform: str,
    assessment: dict,
) -> Optional[str]:
    """Create a digest agent for a platform gap. Deterministic, no LLM."""
    from services.agent_creation import create_agent_record

    title = PLATFORM_DIGEST_TITLES.get(platform)
    if not title:
        return None

    # Get sources for this platform from assessment
    sources = []
    for p in assessment["platform_details"]:
        if p.get("platform") == platform:
            sources = p.get("selected_sources") or []
            break

    if not sources:
        logger.info(f"[COMPOSER] No sources for {platform}, skipping digest creation")
        return None

    result = await create_agent_record(
        client=client,
        user_id=user_id,
        title=title,
        skill="digest",
        origin="composer",
        frequency="daily",
        sources=sources,
        execute_now=True,
    )

    if not result.get("success"):
        logger.warning(f"[COMPOSER] Digest creation failed for {platform}: {result.get('message')}")
        return None

    agent_id = result["agent_id"]
    logger.info(f"[COMPOSER] Created {title} ({agent_id}) for user {user_id}")
    return agent_id


async def _llm_composer_assessment(
    client: Any,
    user_id: str,
    assessment: dict,
    reason: str,
) -> list[dict]:
    """
    LLM-driven assessment for non-obvious agent creation decisions.

    Uses Haiku for cost efficiency. Returns list of created agents.
    """
    import json
    from services.anthropic import chat_completion_with_tools

    # Build context for LLM
    prompt = _build_composer_prompt(assessment, reason)

    try:
        response = await chat_completion_with_tools(
            messages=[{"role": "user", "content": prompt}],
            system=COMPOSER_SYSTEM_PROMPT,
            tools=[],  # No tools — pure reasoning
            model=COMPOSER_MODEL,
            max_tokens=COMPOSER_MAX_TOKENS,
        )

        if not response.text:
            return []

        # Parse LLM response for agent creation decisions
        return await _execute_composer_decisions(client, user_id, response.text, assessment)

    except Exception as e:
        logger.error(f"[COMPOSER] LLM assessment failed: {e}")
        return []


# Composer Prompt v1.1 — ADR-114 Phases 1-3: knowledge corpus signals.
# Changes require: version bump, CHANGELOG entry, expected behavior delta.
COMPOSER_SYSTEM_PROMPT = """You are TP's Composer capability — the meta-cognitive layer that decides what agents should exist for a user's workspace.

You assess the user's connected platforms, existing agents, and work patterns to identify gaps in their agent workforce.

## Principles
- Bias toward action: if an agent would clearly help, recommend creating it
- Start with highest-value agents: platform digests before cross-platform synthesis before research
- Respect what exists: don't duplicate coverage. If a digest already exists, don't create another.
- One agent per decision: recommend at most ONE new agent per assessment

## Response Format
Respond with ONLY a JSON object:

To create an agent:
```json
{"action": "create", "title": "Weekly Cross-Platform Status", "skill": "synthesize", "frequency": "weekly", "reason": "User has 2+ platforms connected with active digests — synthesis would surface cross-cutting themes"}
```

To observe (no action):
```json
{"action": "observe", "reason": "Workforce is healthy. No clear gaps."}
```

Valid skills: digest, prepare, monitor, research, synthesize, custom
Valid frequencies: daily, weekly, biweekly, monthly"""


def _build_composer_prompt(assessment: dict, reason: str) -> str:
    """Build the user message for Composer LLM assessment."""
    agents_summary = []
    for a in assessment["agents"]["active_list"]:
        agents_summary.append(f"- {a['title']} (skill={a['skill']}, scope={a['scope']})")

    # ADR-114 Phase 3: Knowledge corpus summary
    knowledge = assessment.get("knowledge", {})
    by_class = knowledge.get("by_class", {})
    knowledge_lines = []
    for cls in ["digests", "analyses", "research", "briefs", "insights"]:
        knowledge_lines.append(f"- {cls.title()}: {by_class.get(cls, 0)} files")
    if knowledge.get("latest_at"):
        knowledge_lines.append(f"- Most recent: {knowledge['latest_at']}")
    producing = knowledge.get("agents_producing", [])
    if producing:
        knowledge_lines.append(f"- Producing agents: {', '.join(producing)}")
    else:
        knowledge_lines.append("- No agents have produced knowledge yet")
    knowledge_section = chr(10).join(knowledge_lines)

    # ADR-111 Phase 5: Include maturity data when available
    maturity_summary = []
    for s in assessment.get("maturity", {}).get("signals", []):
        parts = [f"- {s['title']}: {s['maturity']}"]
        if s.get("total_runs"):
            parts.append(f"{s['total_runs']} runs")
        if s.get("approval_rate") is not None:
            parts.append(f"{s['approval_rate']:.0%} approval")
        if s.get("edit_trend") is not None:
            direction = "improving" if s["edit_trend"] < 0 else "degrading"
            parts.append(f"edits {direction}")
        maturity_summary.append(", ".join(parts))

    return f"""Assess this user's agent workforce and recommend action.

## Trigger
{reason}

## Connected Platforms
{', '.join(assessment['connected_platforms']) or 'None'}

## Active Agents ({assessment['agents']['active']})
{chr(10).join(agents_summary) if agents_summary else 'None'}

## Coverage
- Platforms with digest: {assessment['coverage']['platforms_with_digest']}
- Platforms without digest: {assessment['coverage']['platforms_without_digest']}

## Knowledge Corpus ({knowledge.get('total_files', 0)} files)
{knowledge_section}

## Health
- Stale agents (not run recently): {len(assessment['health']['stale_agents'])}
- Recent user feedback events: {assessment['feedback']['recent_count']}

## Agent Maturity
{chr(10).join(maturity_summary) if maturity_summary else 'No maturity data yet'}

## Constraints
- Can create new agents: {assessment['tier']['can_create']}

What should be done?"""


async def _execute_composer_decisions(
    client: Any,
    user_id: str,
    response_text: str,
    assessment: dict,
) -> list[dict]:
    """Parse and execute Composer's LLM decisions."""
    import json
    from services.agent_creation import create_agent_record

    # Parse JSON from response
    clean = response_text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        inner = [l for l in lines if not l.startswith("```")]
        clean = "\n".join(inner).strip()

    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        logger.warning(f"[COMPOSER] Could not parse LLM response: {response_text[:200]}")
        return []

    try:
        decision = json.loads(clean[start:end + 1])
    except json.JSONDecodeError as e:
        logger.warning(f"[COMPOSER] JSON parse error: {e}")
        return []

    action = decision.get("action", "observe")
    if action != "create":
        logger.info(f"[COMPOSER] LLM decided: {action} — {decision.get('reason', '')}")
        return []

    # Create the recommended agent
    title = decision.get("title", "").strip()
    skill = decision.get("skill", "custom")
    frequency = decision.get("frequency", "weekly")

    if not title:
        logger.warning("[COMPOSER] LLM recommended create but no title provided")
        return []

    # Dedup: check if an agent with this title already exists
    try:
        existing = (
            client.table("agents")
            .select("id")
            .eq("user_id", user_id)
            .eq("title", title)
            .neq("status", "archived")
            .execute()
        )
        if existing.data:
            logger.info(f"[COMPOSER] Agent '{title}' already exists, skipping")
            return []
    except Exception:
        pass

    # Infer sources for the new agent
    sources = _infer_sources_for_skill(skill, assessment)

    result = await create_agent_record(
        client=client,
        user_id=user_id,
        title=title,
        skill=skill,
        origin="composer",
        frequency=frequency,
        sources=sources,
        execute_now=True,
    )

    if not result.get("success"):
        logger.warning(f"[COMPOSER] Agent creation failed: {result.get('message')}")
        return []

    agent_id = result["agent_id"]
    logger.info(f"[COMPOSER] Created '{title}' ({agent_id}), skill={skill}, reason={decision.get('reason', '')}")

    return [{
        "agent_id": agent_id,
        "title": title,
        "skill": skill,
        "reason": decision.get("reason", ""),
    }]


def _infer_sources_for_skill(skill: str, assessment: dict) -> list:
    """Infer appropriate sources for a new agent based on skill and available platforms."""
    # Synthesize/cross-platform: include all platform sources
    if skill in ("synthesize", "custom"):
        all_sources = []
        for p in assessment["platform_details"]:
            all_sources.extend(p.get("selected_sources") or [])
        return all_sources

    # Platform-specific skills: use first platform's sources
    if skill in ("digest", "monitor", "prepare"):
        for p in assessment["platform_details"]:
            sources = p.get("selected_sources") or []
            if sources:
                return sources

    return []


# =============================================================================
# Lifecycle Progression (ADR-111 Phase 5)
# =============================================================================

async def run_lifecycle_assessment(
    client: Any,
    user_id: str,
    assessment: dict,
    reason: str,
) -> dict:
    """
    ADR-111 Phase 5: Handle lifecycle triggers — dissolution, adjustment, expansion.

    Unlike Composer creation assessment, lifecycle operates on EXISTING agents.
    Returns: {"actions_taken": [...], "observations": [...]}
    """
    result = {
        "actions_taken": [],
        "observations": [],
    }

    # Underperformer dissolution: pause agents with consistently poor approval
    if reason.startswith("lifecycle_underperformer"):
        underperformers = assessment.get("maturity", {}).get("underperformers", [])
        for up in underperformers:
            agent_id = up["agent_id"]
            title = up["title"]
            approval_rate = up.get("approval_rate", 0)
            total_runs = up.get("total_runs", 0)

            # Only auto-pause if clearly underperforming (many runs, low approval)
            # NEVER auto-pause user_configured agents — respect manual overrides (ADR-111)
            origin = up.get("origin", "user_configured")
            if origin == "user_configured":
                result["observations"].append(
                    f"Underperformer '{title}' is user-configured — skipping auto-pause "
                    f"({total_runs} runs, {approval_rate:.0%} approval)"
                )
                continue

            if total_runs >= 8 and approval_rate < 0.3:
                try:
                    client.table("agents").update({
                        "status": "paused",
                    }).eq("id", agent_id).eq("user_id", user_id).execute()

                    result["actions_taken"].append({
                        "action": "paused",
                        "agent_id": agent_id,
                        "title": title,
                        "reason": f"Underperforming: {total_runs} runs, {approval_rate:.0%} approval rate",
                    })
                    logger.info(f"[COMPOSER] Paused underperformer: {title} ({agent_id}), "
                                f"approval={approval_rate:.0%}, runs={total_runs}")
                except Exception as e:
                    logger.warning(f"[COMPOSER] Failed to pause {title}: {e}")
            else:
                result["observations"].append(
                    f"Monitoring underperformer: {title} ({total_runs} runs, "
                    f"{approval_rate:.0%} approval) — needs more data before action"
                )

    # Scope expansion: mature platform digest → suggest cross-platform synthesis
    elif reason.startswith("lifecycle_expansion"):
        mature = assessment.get("maturity", {}).get("mature_agents", [])
        expandable = [
            m for m in mature
            if m.get("scope") == "platform" and m.get("skill") == "digest"
            and m.get("total_runs", 0) >= 10
        ]
        if expandable and assessment["tier"]["can_create"]:
            # Auto-create a synthesis agent that builds on mature digests
            from services.agent_creation import create_agent_record

            # Gather all platform sources for cross-platform agent
            all_sources = []
            for p in assessment["platform_details"]:
                all_sources.extend(p.get("selected_sources") or [])

            if all_sources:
                titles = [e["title"] for e in expandable]
                create_result = await create_agent_record(
                    client=client,
                    user_id=user_id,
                    title="Weekly Cross-Platform Insights",
                    skill="synthesize",
                    origin="composer",
                    frequency="weekly",
                    sources=all_sources,
                    description=f"Cross-platform synthesis based on mature agents: {', '.join(titles)}",
                )
                if create_result.get("success"):
                    result["actions_taken"].append({
                        "action": "created",
                        "agent_id": create_result["agent_id"],
                        "title": "Weekly Cross-Platform Insights",
                        "skill": "synthesize",
                        "reason": f"Lifecycle expansion: {len(expandable)} mature digest agents warrant synthesis",
                    })
                    logger.info(f"[COMPOSER] Lifecycle expansion: created synthesis agent "
                                f"({create_result['agent_id']})")
        else:
            result["observations"].append(
                f"{len(expandable)} mature digest agents detected but can't expand "
                f"(tier limit: {not assessment['tier']['can_create']})"
            )

    # Cross-agent pattern: multiple digests → synthesis consolidation
    elif reason.startswith("cross_agent_pattern"):
        # Same action as expansion — create synthesis agent
        if assessment["tier"]["can_create"]:
            from services.agent_creation import create_agent_record

            all_sources = []
            for p in assessment["platform_details"]:
                all_sources.extend(p.get("selected_sources") or [])

            if all_sources:
                create_result = await create_agent_record(
                    client=client,
                    user_id=user_id,
                    title="Weekly Cross-Platform Insights",
                    skill="synthesize",
                    origin="composer",
                    frequency="weekly",
                    sources=all_sources,
                )
                if create_result.get("success"):
                    result["actions_taken"].append({
                        "action": "created",
                        "agent_id": create_result["agent_id"],
                        "title": "Weekly Cross-Platform Insights",
                        "skill": "synthesize",
                        "reason": "Cross-agent pattern: consolidating multiple digest agents into synthesis",
                    })

    return result


# =============================================================================
# Per-Agent Supervisory Review (ADR-111 Phase 4)
# =============================================================================

async def _get_due_supervisory_agents(client: Any, user_id: str) -> list[dict]:
    """
    Query proactive/coordinator agents due for TP supervisory review.

    ADR-111 Phase 4: These are now triggered by Heartbeat (TP's cadence),
    not directly by the scheduler. The agent provides domain assessment;
    TP (Heartbeat) decides action.
    """
    now = datetime.now(timezone.utc)
    try:
        result = (
            client.table("agents")
            .select("id, user_id, title, scope, skill, type_config, schedule, sources, "
                    "destination, recipient_context, last_run_at, agent_instructions, "
                    "agent_memory, mode, trigger_config")
            .eq("user_id", user_id)
            .eq("status", "active")
            .in_("mode", ["proactive", "coordinator"])
            .or_(f"proactive_next_review_at.is.null,proactive_next_review_at.lte.{now.isoformat()}")
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"[COMPOSER] Supervisory query failed for {user_id}: {e}")
        return []


async def _run_supervisory_review(client: Any, agent: dict) -> dict:
    """
    Run TP's per-agent supervisory review for a proactive/coordinator agent.

    ADR-111 Phase 4: The agent provides domain assessment via proactive_review.py.
    TP (Heartbeat) invokes and logs the result. Mechanical flow is preserved;
    conceptual ownership is TP's.

    Returns: {"agent_id": str, "action": str, "note": str}
    """
    from services.proactive_review import run_proactive_review, apply_review_decision
    from services.trigger_dispatch import dispatch_trigger
    from services.activity_log import write_activity

    agent_id = agent["id"]
    user_id = agent["user_id"]
    title = agent["title"]
    mode = agent.get("mode", "proactive")

    logger.info(f"[COMPOSER] Supervisory review: {title} ({agent_id}), mode={mode}")

    try:
        decision = await run_proactive_review(
            client=client,
            user_id=user_id,
            agent=agent,
        )

        action = decision.get("action", "observe")
        note = decision.get("note", "")

        if action == "generate":
            # Update memory + scheduling BEFORE generation
            await apply_review_decision(client, agent, decision)

            # Full generation path via dispatch
            result = await dispatch_trigger(
                client=client,
                agent=agent,
                trigger_type="schedule",
                trigger_context={"type": "proactive_review", "review_decision": decision},
                signal_strength="high",
            )

            try:
                await write_activity(
                    client=client,
                    user_id=user_id,
                    event_type="agent_scheduled",
                    summary=f"TP supervisory generation: {title}",
                    event_ref=agent_id,
                    metadata={"mode": mode, "review_action": "generate", "trigger": "heartbeat"},
                )
            except Exception:
                pass

            return {"agent_id": agent_id, "action": "generate", "note": note,
                    "success": result.get("success", False)}
        else:
            # observe or sleep — update memory, no generation
            await apply_review_decision(client, agent, decision)

            try:
                await write_activity(
                    client=client,
                    user_id=user_id,
                    event_type="memory_written",
                    summary=f"TP supervisory [{action}]: {title}",
                    event_ref=agent_id,
                    metadata={"mode": mode, "review_action": action, "trigger": "heartbeat",
                              "note": note[:200] if note else ""},
                )
            except Exception:
                pass

            return {"agent_id": agent_id, "action": action, "note": note}

    except Exception as e:
        logger.error(f"[COMPOSER] Supervisory review failed for {title}: {e}")
        return {"agent_id": agent_id, "action": "error", "note": str(e)}


# =============================================================================
# Heartbeat Entry Point (called from unified_scheduler.py)
# =============================================================================

async def run_heartbeat(client: Any, user_id: str) -> dict:
    """
    Full heartbeat cycle for one user:
    1. Cheap data query (workforce assessment)
    2. Should Composer act? (create/adjust agents)
    3. If yes: run Composer assessment
    4. Per-agent supervisory review (proactive/coordinator agents due for review)
    5. Log results

    ADR-111 Phase 4: Heartbeat is TP's single autonomous cadence for both
    workforce composition AND per-agent supervision.

    Returns heartbeat result dict for activity logging.
    """
    # Step 1: Data query (zero LLM cost)
    assessment = await heartbeat_data_query(client, user_id)

    # Step 2: Should Composer act?
    should_act, reason = should_composer_act(assessment)

    heartbeat_result = {
        "user_id": user_id,
        "should_act": should_act,
        "reason": reason,
        "assessment_summary": {
            "platforms": len(assessment["connected_platforms"]),
            "active_agents": assessment["agents"]["active"],
            "coverage_gaps": len(assessment["coverage"]["platforms_without_digest"]),
            "stale_agents": len(assessment["health"]["stale_agents"]),
            "mature_agents": len(assessment.get("maturity", {}).get("mature_agents", [])),
            "underperformers": len(assessment.get("maturity", {}).get("underperformers", [])),
            "knowledge_files": assessment.get("knowledge", {}).get("total_files", 0),
        },
        "composer_result": None,
        "supervisory_reviews": [],
    }

    # Step 3: Composer assessment (LLM only when warranted)
    if should_act:
        logger.info(f"[COMPOSER] Heartbeat triggered Composer for {user_id}: {reason}")
        composer_result = await run_composer_assessment(client, user_id, assessment, reason)
        heartbeat_result["composer_result"] = composer_result

        # Activity log for created agents
        if composer_result.get("agents_created"):
            try:
                from services.activity_log import write_activity
                for created in composer_result["agents_created"]:
                    await write_activity(
                        client=client,
                        user_id=user_id,
                        event_type="agent_bootstrapped",
                        summary=f"Composer created: {created.get('title', 'Unknown')}",
                        event_ref=created.get("agent_id"),
                        metadata={
                            "origin": "composer",
                            "skill": created.get("skill"),
                            "reason": created.get("reason"),
                            "trigger": "heartbeat",
                        },
                    )
            except Exception:
                pass  # Non-fatal

        # ADR-111 Phase 5: Activity log for lifecycle actions (pause, adjust)
        if composer_result.get("lifecycle_actions"):
            try:
                from services.activity_log import write_activity
                for action in composer_result["lifecycle_actions"]:
                    if action.get("action") == "paused":
                        await write_activity(
                            client=client,
                            user_id=user_id,
                            event_type="agent_scheduled",
                            summary=f"Composer paused: {action.get('title', 'Unknown')} — {action.get('reason', '')}",
                            event_ref=action.get("agent_id"),
                            metadata={
                                "lifecycle_action": "paused",
                                "reason": action.get("reason"),
                                "trigger": "heartbeat",
                            },
                        )
            except Exception:
                pass  # Non-fatal
    else:
        logger.info(f"[COMPOSER] Heartbeat for {user_id}: {reason}")

    # Step 4: Per-agent supervisory review (ADR-111 Phase 4)
    # TP's Heartbeat invokes per-agent reviews for proactive/coordinator agents.
    # Independent of Composer — always runs when agents are due.
    due_agents = await _get_due_supervisory_agents(client, user_id)
    for agent in due_agents:
        try:
            review_result = await _run_supervisory_review(client, agent)
            heartbeat_result["supervisory_reviews"].append(review_result)
        except Exception as e:
            logger.warning(f"[COMPOSER] Supervisory review error for {agent.get('title')}: {e}")

    return heartbeat_result


# =============================================================================
# Event-Driven Heartbeat Trigger (ADR-114)
# =============================================================================

# Debounce window — how recently a heartbeat must have fired to skip.
# Pro: 3 minutes (responsive to substrate changes, not spammy).
# Free: midnight-window only (same constraint as cron — keeps Free truly daily).
#
# Known limitation: DB-backed debounce is not atomic. Cron and an event-driven
# trigger can both pass the check concurrently if they race within the same
# window. Blast radius is low (two idempotent heartbeats, worst case two Haiku
# calls). True mutual exclusion would require advisory locks or a debounce table.
_DEBOUNCE_PRO = timedelta(minutes=3)


async def maybe_trigger_heartbeat(
    client: Any,
    user_id: str,
    trigger_event: str,
    trigger_metadata: dict | None = None,
) -> dict | None:
    """
    Event-driven Composer heartbeat with DB-backed debounce.

    Called after substrate-changing events (agent run delivered, platform synced).
    Checks whether a heartbeat fired recently enough to skip, then runs the full
    heartbeat + writes activity_log if not debounced.

    This is a *responsiveness* upgrade — it changes *when* Composer looks, not
    *what* it sees. Substrate-awareness (Composer reading /knowledge/ corpus) is
    ADR-114 Phase 1, separate from this.

    Cost: 1 DB query (debounce check). If debounced, zero additional cost.
    If not debounced, same cost as cron heartbeat.

    Returns heartbeat result dict, or None if debounced/skipped.
    """
    logger.info(f"[COMPOSER] maybe_trigger_heartbeat called: user={user_id[:8]}, trigger={trigger_event}")
    now = datetime.now(timezone.utc)

    # Determine tier — Free users only get event-driven heartbeats in midnight window
    try:
        from services.platform_limits import get_user_tier
        tier = get_user_tier(client, user_id)
    except Exception:
        tier = "free"

    if tier == "free":
        # Same constraint as cron: midnight UTC window only
        if not (now.hour == 0 and now.minute < 5):
            logger.debug(f"[COMPOSER] Event heartbeat skipped for free user {user_id} (not midnight window)")
            return None

    cutoff = (now - _DEBOUNCE_PRO).isoformat()

    # Check last heartbeat time (single DB query)
    try:
        result = (
            client.table("activity_log")
            .select("created_at")
            .eq("user_id", user_id)
            .eq("event_type", "composer_heartbeat")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            logger.debug(
                f"[COMPOSER] Event heartbeat debounced for {user_id} "
                f"(last: {result.data[0]['created_at']}, trigger: {trigger_event})"
            )
            return None
    except Exception as e:
        logger.warning(f"[COMPOSER] Debounce check failed for {user_id}: {e}")
        # On debounce check failure, skip rather than risk runaway heartbeats
        return None

    # Not debounced — run full heartbeat
    logger.info(f"[COMPOSER] Event-driven heartbeat for {user_id} (trigger: {trigger_event})")
    try:
        hb_result = await run_heartbeat(client, user_id)

        # Write activity_log event (same shape as cron, plus event origin)
        try:
            from services.activity_log import write_activity
            composer_result = hb_result.get("composer_result") or {}
            supervisory = hb_result.get("supervisory_reviews", [])
            lifecycle_actions = composer_result.get("lifecycle_actions", [])
            created_count = len(composer_result.get("agents_created", []))

            await write_activity(
                client=client,
                user_id=user_id,
                event_type="composer_heartbeat",
                summary=f"Composer heartbeat: {hb_result.get('reason', 'OK')}",
                metadata={
                    "origin": "event",
                    "trigger_event": trigger_event,
                    "trigger_metadata": trigger_metadata or {},
                    "should_act": hb_result.get("should_act", False),
                    "reason": hb_result.get("reason", ""),
                    "agents_created": created_count,
                    "lifecycle_actions": len(lifecycle_actions),
                    "supervisory_reviews": len(supervisory),
                    **hb_result.get("assessment_summary", {}),
                },
            )
        except Exception:
            pass  # Non-fatal

        return hb_result
    except Exception as e:
        logger.warning(f"[COMPOSER] Event-driven heartbeat failed for {user_id}: {e}")
        return None
