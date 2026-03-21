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

from services.agent_framework import classify_seniority

logger = logging.getLogger(__name__)

# Composer uses Haiku for cost-efficiency (same as agent_pulse)
COMPOSER_MODEL = "claude-haiku-4-5-20251001"
COMPOSER_MAX_TOKENS = 2048


# =============================================================================
# Workspace Density Classification (ADR-115)
# =============================================================================

def _classify_workspace_density(
    total_knowledge_files: int,
    total_agent_runs: int,
    maturity_signals: list[dict],
) -> str:
    """
    Classify workspace density from signals already in the assessment dict.

    Returns "sparse", "developing", or "dense". Determines Composer eagerness:
    - sparse: eager — bias toward creating work (junior employee mode)
    - developing: proactive — still propose new agent types the workspace lacks
    - dense: conservative — quality-focused, accumulation thesis
    """
    non_new = sum(1 for s in maturity_signals if s.get("maturity") not in ("new", None))

    # Dense: substantial knowledge + agents with proven track record
    # This is the graduation threshold — Composer trusts the workforce
    if total_knowledge_files > 50 and non_new >= 3:
        return "dense"

    # Sparse: bootstrap phase — very early, needs immediate scaffolding
    if total_knowledge_files < 5 and total_agent_runs < 10:
        return "sparse"

    # Developing: the system is producing but hasn't graduated.
    # Composer should still be proactive about proposing new agent types.
    return "developing"


def _get_last_assessed_state(client: Any, user_id: str) -> dict | None:
    """
    Fetch the state tuple from the most recent composer_heartbeat where should_act=true.

    Returns {"knowledge_files": N, "total_agent_runs": N, "active_agents": N} or None
    if no prior LLM assessment exists (first-time fire is always allowed).

    ADR-115: Used by should_composer_act() to skip LLM when workspace state hasn't
    changed since last assessment. One cheap DB query on activity_log (indexed).
    """
    try:
        # Query recent heartbeats (limit 20 — most will be should_act=false,
        # so we scan a small window to find the last should_act=true).
        # PostgREST can't filter on JSONB boolean directly, so we fetch and scan.
        result = (
            client.table("activity_log")
            .select("metadata")
            .eq("user_id", user_id)
            .eq("event_type", "composer_heartbeat")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        for row in (result.data or []):
            meta = row.get("metadata") or {}
            if str(meta.get("should_act")).lower() == "true":
                return {
                    "knowledge_files": int(meta.get("knowledge_files", 0)),
                    "total_agent_runs": int(meta.get("total_agent_runs", 0)),
                    "active_agents": int(meta.get("active_agents", 0)),
                }
        return None  # No prior LLM assessment — first fire allowed
    except Exception as e:
        logger.warning(f"[COMPOSER] Last-assessed state query failed: {e}")
        return None  # Fail-open: allow LLM fire if query fails


def _get_work_budget_status(client: Any, user_id: str) -> dict:
    """ADR-120 Phase 3: Get work budget status for heartbeat data."""
    try:
        from services.platform_limits import check_work_budget
        budget_ok, used, limit = check_work_budget(client, user_id)
        return {"used": used, "limit": limit, "exhausted": not budget_ok}
    except Exception:
        return {"used": 0, "limit": -1, "exhausted": False}


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

    # 2. Existing agents — role, scope, mode, origin, status, last_run_at, feedback
    agents = []
    try:
        result = (
            client.table("agents")
            .select("id, title, role, scope, mode, origin, status, created_at, last_run_at, sources, duties")
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

    # 3. Agent roles coverage map
    roles_present = set(a.get("role", "custom") for a in active_agents)

    # 4. Platform coverage — which platforms have project coverage? (ADR-122)
    # Check workspace_files for projects with platform type_key
    from services.project_registry import get_platform_project_type
    platforms_with_project = set()
    try:
        project_files = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .like("path", "/projects/%/PROJECT.md")
            .execute()
        )
        for row in (project_files.data or []):
            content = row.get("content", "")
            # Parse type_key from PROJECT.md
            for line in content.split("\n"):
                if line.strip().startswith("**Type**:"):
                    tk = line.strip()[9:].strip()
                    # Map type_key back to platform
                    from services.project_registry import get_project_type
                    ptype = get_project_type(tk)
                    if ptype and ptype.get("platform"):
                        platforms_with_project.add(ptype["platform"])
                    break
    except Exception as e:
        logger.warning(f"[HEARTBEAT] Project coverage check failed: {e}")
        # Fallback: also check agent sources for backward compatibility with pre-ADR-122 agents
        for agent in active_agents:
            if agent.get("role") == "digest":
                for src in (agent.get("sources") or []):
                    if isinstance(src, dict):
                        provider = src.get("provider") or src.get("platform")
                        if provider:
                            platforms_with_project.add(provider)

    platforms_without_coverage = [
        p for p in connected_platforms
        if p not in platforms_with_project and p != "calendar"
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

    # 7. ADR-126: Agent health from pulse events + lightweight maturity
    # Instead of N+1 per-agent queries on agent_runs (old approach), we:
    # (a) Read recent pulse events from activity_log — agents self-report health
    # (b) Single batch query for run counts + approval rates (maturity still needed
    #     for duty promotion heuristics in should_composer_act)
    maturity_signals = []
    pulse_health = {
        "recent_pulses": [],        # Last 24h of agent_pulsed events
        "escalations": [],          # Agents that pulsed "escalate"
        "waiting": [],              # Agents that pulsed "wait"
        "generating": [],           # Agents that pulsed "generate"
    }
    try:
        # (a) Read recent pulse events — single query, all agents
        day_ago = (now - timedelta(days=1)).isoformat()
        pulse_result = (
            client.table("activity_log")
            .select("event_ref, metadata, created_at, summary")
            .eq("user_id", user_id)
            .in_("event_type", ["agent_pulsed", "pm_pulsed"])
            .gte("created_at", day_ago)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        for pe in (pulse_result.data or []):
            meta = pe.get("metadata") or {}
            pulse_health["recent_pulses"].append(pe)
            action = meta.get("action", "")
            if action == "escalate":
                pulse_health["escalations"].append(pe)
            elif action == "wait":
                pulse_health["waiting"].append(pe)
            elif action == "generate":
                pulse_health["generating"].append(pe)
    except Exception as e:
        logger.warning(f"[COMPOSER] Pulse event query failed: {e}")

    try:
        # (b) Lightweight maturity: single batch query for all agent run counts
        # This replaces the old N+1 per-agent query with one query per user
        agent_ids = [a["id"] for a in active_agents]
        if agent_ids:
            all_runs = (
                client.table("agent_runs")
                .select("agent_id, status")
                .in_("agent_id", agent_ids)
                .in_("status", ["approved", "delivered", "rejected"])
                .execute()
            )
            # Aggregate per agent
            from collections import Counter
            agent_run_counts: dict[str, Counter] = {}
            for r in (all_runs.data or []):
                aid = r["agent_id"]
                if aid not in agent_run_counts:
                    agent_run_counts[aid] = Counter()
                agent_run_counts[aid][r["status"]] += 1

            for agent in active_agents:
                aid = agent["id"]
                counts = agent_run_counts.get(aid, Counter())
                total_runs = sum(counts.values())

                if total_runs == 0:
                    maturity_signals.append({
                        "agent_id": aid,
                        "title": agent["title"],
                        "role": agent.get("role"),
                        "scope": agent.get("scope"),
                        "origin": agent.get("origin"),
                        "total_runs": 0,
                        "maturity": "new",
                    })
                    continue

                # Weighted approval: explicit=1.0, auto-delivered=0.5
                weighted = counts.get("approved", 0) + (counts.get("delivered", 0) * 0.5)
                approval_rate = weighted / total_runs if total_runs > 0 else 0.0
                maturity = classify_seniority(total_runs, approval_rate)
                is_underperformer = total_runs >= 5 and approval_rate < 0.4

                maturity_signals.append({
                    "agent_id": aid,
                    "title": agent["title"],
                    "role": agent.get("role"),
                    "scope": agent.get("scope"),
                    "origin": agent.get("origin"),
                    "duties": agent.get("duties"),
                    "total_runs": total_runs,
                    "approval_rate": round(approval_rate, 2),
                    "maturity": maturity,
                    "is_underperformer": is_underperformer,
                })
        else:
            # No active agents — no maturity to compute
            pass
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

    # 10. ADR-116 Phase 5: Agent dependency graph from consumption tracking
    # Read memory/references.json from each agent's workspace to build producer→consumer edges.
    agent_id_to_title = {a["id"]: a.get("title", "Untitled") for a in agents}
    agent_graph = {
        "edges": [],
        "orphaned_producers": [],
        "consumed_producer_ids": [],
    }
    try:
        from services.workspace import AgentWorkspace, get_agent_slug
        import json as _json

        consumed_ids = set()

        # Read references from each active agent
        for agent_data in active_agents:
            slug = get_agent_slug(agent_data)
            ws = AgentWorkspace(client, user_id, slug)
            refs_content = await ws.read("memory/references.json")
            if refs_content:
                try:
                    refs = _json.loads(refs_content)
                    for producer_id in refs:
                        agent_graph["edges"].append({
                            "producer_id": producer_id,
                            "producer_title": agent_id_to_title.get(producer_id, "Unknown"),
                            "consumer_id": agent_data["id"],
                            "consumer_title": agent_data.get("title", "Untitled"),
                        })
                        consumed_ids.add(producer_id)
                except (_json.JSONDecodeError, TypeError):
                    pass

        agent_graph["consumed_producer_ids"] = list(consumed_ids)

        # Detect orphaned producers: agents producing knowledge that no one consumes
        # Use knowledge["agents_producing"] titles + agent_id_to_title inverse lookup
        title_to_id = {v: k for k, v in agent_id_to_title.items()}
        for title in knowledge.get("agents_producing", []):
            aid = title_to_id.get(title)
            if aid and aid not in consumed_ids:
                agent_graph["orphaned_producers"].append({
                    "agent_id": aid,
                    "title": title,
                })
    except Exception as e:
        logger.warning(f"[COMPOSER] Agent graph query failed: {e}")

    # 11. Workspace density classification (ADR-115)
    # Pure function over signals already computed — zero additional queries.
    total_runs = sum(s.get("total_runs", 0) for s in maturity_signals)
    workspace_density = _classify_workspace_density(
        total_knowledge_files=knowledge["total_files"],
        total_agent_runs=total_runs,
        maturity_signals=maturity_signals,
    )

    # 12. ADR-120: Project health signals — active projects + PM status
    projects_health = {
        "total_projects": 0,
        "active_pms": 0,
        "stale_projects": [],
        "projects_without_pm": [],
    }
    try:
        project_files = (
            client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", user_id)
            .like("path", "/projects/%/PROJECT.md")
            .execute()
        )
        project_slugs = []
        for f in (project_files.data or []):
            # Extract slug from path: /projects/{slug}/PROJECT.md
            parts = f["path"].split("/")
            if len(parts) >= 3:
                project_slugs.append(parts[2])

        projects_health["total_projects"] = len(project_slugs)

        # Check PM agents for each project
        pm_agents = [a for a in active_agents if a.get("role") == "pm"]
        pm_project_slugs = set()
        for pm in pm_agents:
            # PM's project_slug is in type_config — but we don't have type_config in the select above
            # So look it up if PM agents exist
            pass

        # Simpler approach: count PM role agents and check staleness
        projects_health["active_pms"] = len(pm_agents)

        for pm in pm_agents:
            last_run = pm.get("last_run_at")
            if last_run:
                try:
                    last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                    if now - last_dt > timedelta(days=7):
                        projects_health["stale_projects"].append({
                            "pm_agent_id": pm["id"],
                            "pm_title": pm["title"],
                            "last_run_at": last_run,
                        })
                except (ValueError, TypeError):
                    pass

        # Projects without PM: total_projects > active_pms
        if projects_health["total_projects"] > projects_health["active_pms"]:
            projects_health["projects_without_pm_count"] = (
                projects_health["total_projects"] - projects_health["active_pms"]
            )
    except Exception as e:
        logger.warning(f"[COMPOSER] Project health query failed: {e}")

    return {
        "user_id": user_id,
        "timestamp": now.isoformat(),
        "connected_platforms": connected_platforms,
        "platform_details": platforms,
        "agents": {
            "total": len(agents),
            "active": len(active_agents),
            "paused": len(paused_agents),
            "roles_present": list(roles_present),
            "active_list": [
                {"id": a["id"], "title": a["title"], "role": a.get("role"), "scope": a.get("scope")}
                for a in active_agents
            ],
        },
        "coverage": {
            "platforms_with_coverage": list(platforms_with_project),
            "platforms_without_coverage": platforms_without_coverage,
        },
        "health": {
            "stale_agents": [
                {"id": a["id"], "title": a["title"], "last_run_at": a.get("last_run_at")}
                for a in stale_agents
            ],
        },
        "maturity": {
            "signals": maturity_signals,
            "senior_agents": [s for s in maturity_signals if s.get("maturity") == "senior"],
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
        "workspace_density": workspace_density,  # ADR-115
        "total_agent_runs": total_runs,  # ADR-115 — surfaced for prompt/logging
        "last_assessed_state": _get_last_assessed_state(client, user_id),  # ADR-115 state-change gate
        "agent_graph": agent_graph,  # ADR-116 Phase 5
        "projects": projects_health,  # ADR-120 Phase 1
        "work_budget": _get_work_budget_status(client, user_id),  # ADR-120 Phase 3
        "pulse_health": pulse_health,  # ADR-126: agent self-reported health from pulse events
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

    # ADR-111 Phase 5: Lifecycle — senior agents ready for scope expansion
    seniors = assessment.get("maturity", {}).get("senior_agents", [])
    expandable = [
        m for m in seniors
        if m.get("scope") == "platform" and m.get("role") == "digest"
        and m.get("total_runs", 0) >= 10
    ]
    if expandable and len(assessment["connected_platforms"]) >= 2:
        titles = [e["title"] for e in expandable[:2]]
        return True, f"lifecycle_expansion: {len(expandable)} senior digest agents may warrant cross-platform synthesis: {titles}"

    # Can't create agents if at tier limit (but lifecycle checks above still fire)
    if not assessment["tier"]["can_create"]:
        return False, "HEARTBEAT_OK: at tier agent limit"

    # ADR-126: Pulse escalations — agents asking for Composer attention
    escalations = assessment.get("pulse_health", {}).get("escalations", [])
    if escalations:
        agent_refs = list(set(e.get("event_ref", "?") for e in escalations))[:3]
        return True, f"pulse_escalation: {len(escalations)} agent(s) escalated in last 24h: {agent_refs}"

    # Coverage gap: platform connected but no project covering it (ADR-122)
    gaps = assessment["coverage"]["platforms_without_coverage"]
    if gaps:
        return True, f"coverage_gap: platforms without project coverage: {gaps}"

    # Multi-platform opportunity: 2+ platforms connected but no cross-platform agent
    if len(assessment["connected_platforms"]) >= 2:
        roles = assessment["agents"]["roles_present"]
        if "synthesize" not in roles and assessment["agents"]["active"] >= 2:
            return True, "cross_platform_opportunity: 2+ platforms, no synthesize agent"

    # Active feedback suggests engaged user — check for expansion opportunities
    if assessment["feedback"]["recent_count"] >= 5 and assessment["agents"]["active"] <= 2:
        return True, "engaged_user: high feedback + low agent count — may benefit from more agents"

    # ADR-111 Phase 5: Cross-agent pattern — multiple digest agents producing
    # similar content from overlapping sources (consolidation opportunity)
    signals = assessment.get("maturity", {}).get("signals", [])
    digest_agents = [s for s in signals if s.get("role") == "digest" and s.get("total_runs", 0) >= 3]
    if len(digest_agents) >= 3 and "synthesize" not in assessment["agents"]["roles_present"]:
        return True, f"cross_agent_pattern: {len(digest_agents)} active digest agents — synthesis agent would consolidate insights"

    # ADR-116 Phase 5: Orphaned producers — agents producing knowledge nobody consumes
    orphaned = assessment.get("agent_graph", {}).get("orphaned_producers", [])
    if len(orphaned) >= 2:
        titles = [o["title"] for o in orphaned[:3]]
        return True, f"orphaned_producers: {len(orphaned)} agents produce knowledge no agent consumes: {titles}"

    # ADR-114 Phase 2: Knowledge-substrate heuristics
    knowledge = assessment.get("knowledge", {})
    by_class = knowledge.get("by_class", {})
    total_knowledge = knowledge.get("total_files", 0)

    # knowledge_gap_analysis: many digests, no analyses, no synthesize agent
    if (by_class.get("digests", 0) >= 10
            and by_class.get("analyses", 0) == 0
            and "synthesize" not in assessment["agents"]["roles_present"]):
        return True, (
            f"knowledge_gap_analysis: {by_class['digests']} digest files but 0 analyses "
            "— system is perceiving but not reasoning"
        )

    # stale_knowledge: latest /knowledge/ file > 7 days old, agents still active
    if knowledge.get("latest_at") and assessment["agents"]["active"] > 0:
        try:
            _now = datetime.now(timezone.utc)
            latest_dt = datetime.fromisoformat(knowledge["latest_at"].replace("Z", "+00:00"))
            days_stale = (_now - latest_dt).days
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

    # ADR-115: Workspace density + state-change gate.
    # Non-dense workspaces route to LLM, but ONLY when workspace state has
    # actually changed since last LLM assessment. Prevents repeated Haiku calls
    # with identical context (288/day → ~2-5/day).
    workspace_density = assessment.get("workspace_density", "developing")
    if workspace_density != "dense":
        has_substrate = assessment["agents"]["active"] > 0 or assessment["connected_platforms"]
        if has_substrate:
            total_runs = assessment.get("total_agent_runs", 0)
            total_kf = assessment.get("knowledge", {}).get("total_files", 0)
            active_agents = assessment["agents"]["active"]

            # State-change gate: compare current state against last LLM assessment.
            # If nothing changed, skip — the LLM has no new information.
            # None means no prior assessment exists → always fire (first time).
            last = assessment.get("last_assessed_state")
            if last is not None:
                state_changed = (
                    total_kf != last.get("knowledge_files", 0)
                    or total_runs != last.get("total_agent_runs", 0)
                    or active_agents != last.get("active_agents", 0)
                )
                if not state_changed:
                    return False, (
                        f"HEARTBEAT_OK: {workspace_density} workspace, awaiting new signal "
                        f"(kf={total_kf}, runs={total_runs}, agents={active_agents})"
                    )

            if workspace_density == "sparse":
                return True, (
                    f"sparse_workspace: {total_kf} knowledge files, {total_runs} total runs "
                    "— eager scaffolding mode"
                )
            else:
                return True, (
                    f"developing_workspace: {total_kf} knowledge files, {total_runs} total runs "
                    "— propose agents for missing skills"
                )

    # ADR-120: Project health heuristics
    projects = assessment.get("projects", {})
    stale_pms = projects.get("stale_projects", [])
    if stale_pms:
        titles = [p["pm_title"] for p in stale_pms[:3]]
        return True, f"project_pm_stale: {len(stale_pms)} PM agents haven't run in 7+ days: {titles}"

    no_pm_count = projects.get("projects_without_pm_count", 0)
    if no_pm_count > 0:
        return True, f"project_no_pm: {no_pm_count} project(s) exist without a PM agent"

    # ADR-120 Phase 5: Composition opportunity — 2+ senior agents with different
    # roles and no project linking them suggests outputs could be assembled.
    total_projects = projects.get("total_projects", 0)
    if total_projects == 0:
        senior_agents = assessment.get("maturity", {}).get("senior_agents", [])
        if len(senior_agents) >= 2:
            senior_roles = {m.get("role") for m in senior_agents if m.get("role")}
            # Different roles = complementary outputs (e.g., digest + analyst)
            # Exclude PM-role agents — they don't produce combinable content
            senior_roles.discard("pm")
            if len(senior_roles) >= 2:
                titles = [m["title"] for m in senior_agents[:3]]
                return True, (
                    f"composition_opportunity: {len(senior_agents)} senior agents with "
                    f"roles {sorted(senior_roles)} but no project — outputs may benefit "
                    f"from assembly: {titles}"
                )

    # ADR-117 Phase 3: Duty promotion — senior agents eligible for expanded duties
    from services.agent_framework import get_promotion_duty, ROLE_PORTFOLIOS
    senior_agents = assessment.get("maturity", {}).get("senior_agents", [])
    for sa in senior_agents:
        agent_role = sa.get("role")
        if not agent_role or agent_role not in ROLE_PORTFOLIOS:
            continue
        current_duties = sa.get("duties") or [{"duty": agent_role}]
        promo = get_promotion_duty(agent_role, "senior", current_duties)
        if promo:
            return True, (
                f"duty_promotion: {sa['title']} is senior ({sa.get('total_runs', 0)} runs, "
                f"{sa.get('approval_rate', 0):.0%} approval) — eligible for {promo['duty']} duty"
            )

    return False, "HEARTBEAT_OK: workforce healthy, no gaps detected"


# =============================================================================
# Composer Assessment (LLM — only when warranted)
# =============================================================================

# Agent templates Composer can create (extends bootstrap templates)
COMPOSER_TEMPLATES = {
    "digest": {
        "role": "digest",
        "mode": "recurring",
        "frequency": "daily",
    },
    "synthesize": {
        "role": "synthesize",
        "mode": "recurring",
        "frequency": "weekly",
    },
    "monitor": {
        "role": "monitor",
        "mode": "recurring",
        "frequency": "daily",
    },
}

# ADR-122: Platform digest gap-filling now uses project_registry.scaffold_project()
# PLATFORM_DIGEST_TITLES — DELETED (ADR-122). Use get_platform_project_type() instead.


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
            "contributors_created": [...],
            "lifecycle_actions": [...],
            "observations": [...],
        }
    """
    result = {
        "action": "observed",
        "contributors_created": [],
        "lifecycle_actions": [],
        "observations": [],
    }

    # Fast path: deterministic gap-filling via project registry (ADR-122, no LLM needed)
    gaps = assessment["coverage"]["platforms_without_coverage"]
    if gaps and reason.startswith("coverage_gap"):
        from services.project_registry import get_platform_project_type, scaffold_project
        for platform in gaps:
            type_info = get_platform_project_type(platform)
            if not type_info:
                continue
            type_key, _ = type_info
            scaffold_result = await scaffold_project(client, user_id, type_key, execute_now=True)
            if scaffold_result.get("success"):
                for cm in scaffold_result.get("contributors_created", []):
                    result["contributors_created"].append({
                        "agent_id": cm["agent_id"],
                        "platform": platform,
                        "role": cm["role"],
                        "reason": "coverage_gap",
                        "project_slug": scaffold_result["project_slug"],
                    })
        if result["contributors_created"]:
            result["action"] = "created"
        return result

    # ADR-111 Phase 5: Lifecycle assessment path (no LLM — deterministic)
    if reason.startswith(("lifecycle_", "cross_agent_")):
        lifecycle_result = await run_lifecycle_assessment(client, user_id, assessment, reason)
        result["lifecycle_actions"] = lifecycle_result.get("actions_taken", [])
        result["observations"].extend(lifecycle_result.get("observations", []))

        # Lifecycle actions that create contributors go into contributors_created too
        for action in result["lifecycle_actions"]:
            if action.get("action") == "created":
                result["contributors_created"].append(action)

        if result["lifecycle_actions"]:
            result["action"] = "lifecycle"
        return result

    # LLM assessment path for non-obvious cases
    try:
        created = await _llm_composer_assessment(client, user_id, assessment, reason)
        result["contributors_created"] = created
        if created:
            result["action"] = "created"
        else:
            result["observations"].append(f"Composer assessed: {reason}. No action taken.")
    except Exception as e:
        logger.error(f"[COMPOSER] LLM assessment failed: {e}")
        result["observations"].append(f"Assessment error: {e}")

    return result


    # _create_digest_for_platform — DELETED (ADR-122).
    # Gap-filling now uses scaffold_project() in run_composer_assessment().


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


# Composer Prompt v2.1 — promote_duty action, seniority rename (ADR-117 P3).
# v2.0: project awareness, skill library, PM delegation (ADR-120 P5).
# Changes require: version bump, CHANGELOG entry, expected behavior delta.
COMPOSER_SYSTEM_PROMPT = """You are TP's Composer capability — the meta-cognitive layer that decides what agents and projects should exist for a user's workspace.

You assess the user's knowledge substrate — accumulated agent outputs, platform connections, workspace files, and work patterns — to identify gaps in their cognitive workforce.

## Principles
- Bias toward action: if an agent or project would clearly help, recommend creating it
- In sparse workspaces (few knowledge files, few runs): be eager. Propose research or analysis agents even without perfect signal. Early outputs that the user corrects are more valuable than silence. Think like a junior employee — attempt the task, accept feedback, improve.
- In developing workspaces (some knowledge, no senior agents): be proactive. If the workspace only has digest agents, propose a research or analysis agent. If it has no cross-platform synthesis, propose one. The goal is to build out the full role spectrum — not wait for perfect conditions.
- In dense workspaces (many knowledge files, senior agents): be conservative. The workforce has proven itself. Only propose agents that fill clear gaps — or a project if 2+ agents produce complementary outputs that would benefit from assembly.
- Start with highest-value agents: digests (perception) before synthesis (cross-cutting themes) before analysis (deep reasoning) before research (external knowledge). Each layer builds on accumulated outputs from the layer below.
- Respect what exists: don't duplicate coverage. If a digest already exists, don't create another.
- One action per decision: recommend at most ONE new agent OR one new project per assessment
- Budget awareness: if work budget is exhausted, observe rather than propose new work that can't execute

## Response Format
Respond with ONLY a JSON object:

To create an agent:
```json
{"action": "create", "title": "Weekly Cross-Platform Synthesis", "role": "synthesize", "frequency": "weekly", "description": "Connects patterns across Slack, Gmail, and Notion to surface cross-cutting themes.", "instructions": "Synthesize activity across all connected platforms. Lead with cross-platform connections.", "reason": "2+ platforms with active digests producing knowledge"}
```

To create a project (combines 2+ agents' outputs into an assembled deliverable):
```json
{"action": "create_project", "title": "Q2 Business Review", "objective": {"deliverable": "Executive presentation", "audience": "Leadership", "format": "pptx", "purpose": "Quarterly review"}, "contributors": ["agent-slug-1", "agent-slug-2"], "assembly_spec": "Combine analyst data with writer narrative into slide deck", "delivery": {"channel": "email", "target": "user@example.com"}, "reason": "These agents produce complementary outputs ideal for assembly"}
```

To promote an agent's duties (expand responsibilities for a senior agent):
```json
{"action": "promote_duty", "agent_id": "uuid", "new_duty": "monitor", "reason": "Senior digest agent with 80%+ approval — ready for monitoring capability"}
```

To observe (no action):
```json
{"action": "observe", "reason": "Workforce is healthy. No clear gaps."}
```

IMPORTANT for promote_duty actions:
- Only promote agents marked as "senior" in the maturity signals
- The new duty must be part of the agent's role portfolio (pre-configured career track)
- Valid duty promotions: digest→monitor, synthesize→research, research→monitor, monitor→act
- Do NOT promote if the agent already has the duty

IMPORTANT for create actions:
- "description" (required): One sentence explaining what this agent does and why it's valuable. Shown to the user on the dashboard.
- "instructions" (required): Specific behavioral directives for the agent — what to focus on, how to structure output, what to prioritize. Be specific to this workspace's context, not generic.

IMPORTANT for create_project actions:
- A project combines outputs from 2+ existing agents into assembled deliverables (e.g., deck, report)
- A PM (Project Manager) agent is auto-created to coordinate the project
- contributors is a list of agent slugs (lowercase-hyphenated titles) already in the workspace
- intent.format determines which skill is used for rendering (pptx, pdf, xlsx, etc.)

Valid roles: digest, prepare, monitor, research, synthesize, custom
Valid frequencies: daily, weekly, biweekly, monthly

## Skill Library (8 skills for RuntimeDispatch)
Agents produce rich outputs via these skills:
- **pdf**: Reports and documents (pandoc)
- **pptx**: Slide deck presentations (python-pptx)
- **xlsx**: Spreadsheets with formatted tables (openpyxl)
- **chart**: PNG/SVG data visualizations (matplotlib)
- **mermaid**: Diagrams and flowcharts (mermaid-cli)
- **image**: Generated images (pillow)
- **data**: Structured data exports (CSV, JSON)
- **html**: Web-ready formatted content

All agents default to email delivery. When scaffolding agents, consider whether rich outputs would serve the user better than plain text. Include this in the agent's instructions if appropriate.

## Projects (ADR-120)
Projects are cross-agent collaboration spaces. When 2+ agents produce complementary outputs (e.g., data + narrative → deck), a project assembles them into a unified deliverable. A PM agent coordinates the project: tracks contributor freshness, triggers assembly when all contributions are ready, manages work plan and budget.

Only recommend create_project when:
- 2+ senior agents exist with complementary roles (e.g., digest + synthesize, analyst + writer)
- Their outputs would clearly benefit from assembly into a richer format (deck, report)
- No existing project already covers this combination"""


def _format_projects_section(assessment: dict) -> str:
    """ADR-120 P5: Format project portfolio for Composer LLM prompt."""
    projects = assessment.get("projects", {})
    total = projects.get("total_projects", 0)
    if total == 0:
        return "No active projects."

    lines = [f"{total} project(s):"]
    pms = projects.get("active_pms", 0)
    lines.append(f"- PM agents: {pms}")
    stale = projects.get("stale_projects", [])
    if stale:
        titles = [p.get("pm_title", "?") for p in stale[:3]]
        lines.append(f"- Stale PMs (7+ days): {', '.join(titles)}")
    no_pm = projects.get("projects_without_pm_count", 0)
    if no_pm:
        lines.append(f"- Projects without PM: {no_pm}")
    return "\n".join(lines)


def _format_budget_section(assessment: dict) -> str:
    """ADR-120 P5: Format work budget status for Composer LLM prompt."""
    wb = assessment.get("work_budget", {})
    used = wb.get("used", 0)
    limit = wb.get("limit", -1)
    if limit <= 0:
        return "Unlimited"
    pct = int(used / limit * 100) if limit > 0 else 0
    if wb.get("exhausted"):
        return f"EXHAUSTED — {used}/{limit} units ({pct}%). Do NOT propose new agents or projects."
    elif pct >= 80:
        return f"LOW — {used}/{limit} units ({pct}%). Be conservative with new proposals."
    return f"{used}/{limit} units ({pct}%)."


def _build_composer_prompt(assessment: dict, reason: str) -> str:
    """Build the user message for Composer LLM assessment."""
    agents_summary = []
    for a in assessment["agents"]["active_list"]:
        agents_summary.append(f"- {a['title']} (role={a['role']}, scope={a['scope']})")

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

    # ADR-115: Workspace density context
    density = assessment.get("workspace_density", "developing")
    total_runs = assessment.get("total_agent_runs", 0)
    density_label = {
        "sparse": f"SPARSE ({knowledge.get('total_files', 0)} knowledge files, {total_runs} total runs) — be eager, propose new agents even without perfect signal",
        "developing": f"DEVELOPING ({knowledge.get('total_files', 0)} knowledge files, {total_runs} total runs) — propose agents for role types the workspace lacks (research, analysis)",
        "dense": f"DENSE ({knowledge.get('total_files', 0)} knowledge files, {total_runs} total runs) — workforce is senior, only act on clear gaps",
    }.get(density, "DEVELOPING")

    return f"""Assess this user's agent workforce and recommend action.

## Trigger
{reason}

## Workspace Density
{density_label}

## Connected Platforms
{', '.join(assessment['connected_platforms']) or 'None'}

## Active Agents ({assessment['agents']['active']})
{chr(10).join(agents_summary) if agents_summary else 'None'}

## Coverage
- Platforms with project coverage: {assessment['coverage']['platforms_with_coverage']}
- Platforms without coverage: {assessment['coverage']['platforms_without_coverage']}

## Knowledge Corpus ({knowledge.get('total_files', 0)} files)
{knowledge_section}

## Health
- Stale agents (not run recently): {len(assessment['health']['stale_agents'])}
- Recent user feedback events: {assessment['feedback']['recent_count']}

## Agent Maturity
{chr(10).join(maturity_summary) if maturity_summary else 'No maturity data yet'}

## Active Projects
{_format_projects_section(assessment)}

## Work Budget
{_format_budget_section(assessment)}

## Skill Library
pdf, pptx, xlsx, chart, mermaid, image, data, html (8 skills available via RuntimeDispatch)

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

    # ADR-120 P5: Handle create_project action
    if action == "create_project":
        return await _execute_create_project(client, user_id, decision, assessment)

    # ADR-117 Phase 3: Handle promote_duty action
    if action == "promote_duty":
        return await _execute_promote_duty(client, user_id, decision, assessment)

    if action != "create":
        logger.info(f"[COMPOSER] LLM decided: {action} — {decision.get('reason', '')}")
        return []

    # Create the recommended agent
    title = decision.get("title", "").strip()
    role = decision.get("role", "custom")
    frequency = decision.get("frequency", "weekly")
    description = decision.get("description", "").strip() or None
    instructions = decision.get("instructions", "").strip() or None

    if not title:
        logger.warning("[COMPOSER] LLM recommended create but no title provided")
        return []

    # Dedup: check title match OR role match (prevents creative title variants)
    try:
        # Check 1: exact title match
        title_match = (
            client.table("agents")
            .select("id, title")
            .eq("user_id", user_id)
            .eq("title", title)
            .neq("status", "archived")
            .execute()
        )
        if title_match.data:
            logger.info(f"[COMPOSER] Agent '{title}' already exists, skipping")
            return []

        # Check 2: role match — one agent per role type (except digest, which is per-platform)
        if role not in ("digest", "monitor"):
            role_match = (
                client.table("agents")
                .select("id, title")
                .eq("user_id", user_id)
                .eq("role", role)
                .neq("status", "archived")
                .execute()
            )
            if role_match.data:
                existing_title = role_match.data[0].get("title", "unknown")
                logger.info(
                    f"[COMPOSER] Role '{role}' already covered by '{existing_title}', "
                    f"skipping '{title}'"
                )
                return []
    except Exception:
        pass

    # Infer sources for the new agent
    sources = _infer_sources_for_role(role, assessment)

    # ADR-118: Default email delivery
    destination = None
    try:
        from services.agent_execution import get_user_email
        user_email = get_user_email(client, user_id)
        if user_email:
            destination = {"platform": "email", "target": user_email, "format": "send"}
    except Exception:
        pass

    result = await create_agent_record(
        client=client,
        user_id=user_id,
        title=title,
        role=role,
        origin="composer",
        description=description,
        agent_instructions=instructions,
        frequency=frequency,
        sources=sources,
        destination=destination,
        execute_now=True,
    )

    if not result.get("success"):
        logger.warning(f"[COMPOSER] Agent creation failed: {result.get('message')}")
        return []

    agent_id = result["agent_id"]
    logger.info(f"[COMPOSER] Created '{title}' ({agent_id}), role={role}, reason={decision.get('reason', '')}")

    return [{
        "agent_id": agent_id,
        "title": title,
        "role": role,
        "reason": decision.get("reason", ""),
    }]


async def _execute_create_project(
    client: Any,
    user_id: str,
    decision: dict,
    assessment: dict,
) -> list[dict]:
    """
    ADR-120 P5: Execute Composer's create_project decision.

    Resolves contributor slugs → agent_ids, then calls handle_create_project()
    which auto-creates the PM agent and seeds contributor workspaces.
    """
    from services.primitives.project import handle_create_project
    from services.workspace import get_agent_slug

    title = decision.get("title", "").strip()
    if not title:
        logger.warning("[COMPOSER] create_project but no title provided")
        return []

    objective = decision.get("objective", decision.get("intent", {}))  # ADR-123: accept both during transition
    contributor_slugs = decision.get("contributors", [])
    assembly_spec = decision.get("assembly_spec", "")
    delivery = decision.get("delivery", {})
    reason = decision.get("reason", "")

    # Resolve slugs to agent_ids
    contributors = []
    active_agents = assessment.get("agents", {}).get("active_list", [])
    for slug in contributor_slugs:
        for a in active_agents:
            a_slug = get_agent_slug(a)
            if a_slug == slug:
                contributors.append({
                    "agent_id": a["id"],
                    "expected_contribution": f"{a.get('role', 'custom')} output",
                })
                break
        else:
            logger.warning(f"[COMPOSER] Contributor slug '{slug}' not found in active agents")

    if len(contributors) < 2:
        logger.warning(f"[COMPOSER] create_project needs 2+ contributors, got {len(contributors)}")
        return []

    # Build auth-like object for the primitive
    class _ComposerAuth:
        def __init__(self, c, uid):
            self.client = c
            self.user_id = uid

    result = await handle_create_project(
        _ComposerAuth(client, user_id),
        {
            "title": title,
            "objective": objective,
            "contributors": contributors,
            "assembly_spec": assembly_spec,
            "delivery": delivery,
            "type_key": "custom",  # ADR-122: LLM-driven projects use custom type
        },
    )

    if not result.get("success"):
        logger.warning(f"[COMPOSER] Project creation failed: {result.get('message')}")
        return []

    project_slug = result.get("project_slug", "")
    pm_agent_id = result.get("pm_agent_id")
    logger.info(
        f"[COMPOSER] Created project '{title}' ({project_slug}), "
        f"PM={pm_agent_id}, contributors={len(contributors)}, reason={reason}"
    )

    return [{
        "project_slug": project_slug,
        "title": title,
        "pm_agent_id": pm_agent_id,
        "contributors": len(contributors),
        "reason": reason,
        "action_type": "create_project",
    }]


async def _execute_promote_duty(
    client: Any, user_id: str, decision: dict, assessment: dict
) -> list[dict]:
    """ADR-117 Phase 3: Execute Composer's promote_duty decision.

    Validates against ROLE_PORTFOLIOS, writes duties JSONB, workspace file,
    and updates AGENT.md with new capabilities section.
    """
    from services.agent_framework import ROLE_PORTFOLIOS, get_promotion_duty
    from services.workspace import AgentWorkspace
    from services.workspace import get_agent_slug
    from services.activity_log import write_activity

    agent_id = decision.get("agent_id")
    new_duty = decision.get("new_duty")
    reason = decision.get("reason", "")

    if not agent_id or not new_duty:
        logger.warning("[COMPOSER] promote_duty missing agent_id or new_duty")
        return []

    # Fetch agent
    try:
        result = client.table("agents").select(
            "id, title, role, duties, user_id"
        ).eq("id", agent_id).single().execute()
        agent = result.data
    except Exception as e:
        logger.warning(f"[COMPOSER] promote_duty: agent fetch failed: {e}")
        return []

    role = agent.get("role", "custom")
    current_duties = agent.get("duties") or [{"duty": role, "trigger": "recurring", "status": "active"}]

    # Validate: new_duty must be in the role's portfolio for senior level
    portfolio = ROLE_PORTFOLIOS.get(role, {})
    senior_duties = portfolio.get("senior", [])
    valid_duty_names = {d["duty"] for d in senior_duties}

    if new_duty not in valid_duty_names:
        logger.warning(
            f"[COMPOSER] promote_duty rejected: {new_duty} not in {role} portfolio "
            f"(valid: {valid_duty_names})"
        )
        return []

    # Check not already held
    if any(d.get("duty") == new_duty for d in current_duties):
        logger.info(f"[COMPOSER] promote_duty: {agent['title']} already has {new_duty} duty")
        return []

    # Find the duty spec from portfolio
    duty_spec = next((d for d in senior_duties if d["duty"] == new_duty), None)
    if not duty_spec:
        return []

    # Build updated duties list
    new_duty_entry = {
        "duty": new_duty,
        "trigger": duty_spec.get("trigger", "reactive"),
        "status": "active",
        "added_at": datetime.now(timezone.utc).isoformat(),
        "added_by": "composer",
    }
    updated_duties = current_duties + [new_duty_entry]

    # Write to agents.duties JSONB
    try:
        client.table("agents").update(
            {"duties": updated_duties}
        ).eq("id", agent_id).execute()
    except Exception as e:
        logger.error(f"[COMPOSER] promote_duty: JSONB update failed: {e}")
        return []

    # Write workspace duty file
    try:
        slug = get_agent_slug(agent)
        ws = AgentWorkspace(client, user_id, slug)
        duty_content = (
            f"# Duty: {new_duty}\n\n"
            f"**Trigger:** {duty_spec.get('trigger', 'reactive')}\n"
            f"**Added:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
            f"**Reason:** {reason}\n\n"
            f"This duty expands your responsibilities. When this duty fires, "
            f"you operate as a {new_duty} agent within your domain.\n"
        )
        await ws.write_duty(new_duty, duty_content)

        # Update AGENT.md with duties section
        agent_md = await ws.read("AGENT.md") or ""
        duties_section = "\n\n## Duties & Capabilities\n"
        for d in updated_duties:
            marker = " (primary)" if d["duty"] == role else " (earned)"
            duties_section += f"- **{d['duty']}** — {d.get('trigger', 'recurring')}{marker}\n"
        # Replace existing section or append
        if "## Duties & Capabilities" in agent_md:
            import re as _re
            agent_md = _re.sub(
                r"## Duties & Capabilities.*?(?=\n## |\Z)",
                duties_section.strip() + "\n",
                agent_md,
                flags=_re.DOTALL,
            )
        else:
            agent_md = agent_md.rstrip() + duties_section
        await ws.write("AGENT.md", agent_md, summary="Updated duties after promotion")
    except Exception as e:
        logger.warning(f"[COMPOSER] promote_duty: workspace write failed (non-fatal): {e}")

    # Write activity event (Step 5 integration)
    try:
        await write_activity(
            client=client,
            user_id=user_id,
            event_type="duty_promoted",
            summary=f"{agent['title']} earned {new_duty} duty",
            event_ref=agent_id,
            metadata={
                "agent_id": agent_id,
                "role": role,
                "new_duty": new_duty,
                "seniority": "senior",
                "reason": reason,
            },
        )
    except Exception as e:
        logger.warning(f"[COMPOSER] promote_duty: activity write failed (non-fatal): {e}")

    logger.info(
        f"[COMPOSER] Duty promoted: {agent['title']} gained {new_duty} duty "
        f"(role={role}, reason={reason})"
    )

    return [{
        "action_type": "promote_duty",
        "agent_id": agent_id,
        "title": agent["title"],
        "new_duty": new_duty,
        "reason": reason,
    }]


def _infer_sources_for_role(role: str, assessment: dict) -> list:
    """Infer appropriate sources for a new agent based on role and available platforms."""
    # Synthesize/cross-platform: include all platform sources
    if role in ("synthesize", "custom"):
        all_sources = []
        for p in assessment["platform_details"]:
            all_sources.extend(p.get("selected_sources") or [])
        return all_sources

    # Platform-specific roles: use first platform's sources
    if role in ("digest", "monitor", "prepare"):
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

                # ADR-117: Write coaching feedback to agent workspace
                try:
                    from services.feedback_distillation import write_supervisor_notes
                    coaching = (
                        f"Your recent outputs have a {approval_rate:.0%} approval rate "
                        f"across {total_runs} runs. The user is frequently editing or "
                        f"not approving your outputs. Focus on:\n"
                        f"- Following the preferences in memory/preferences.md closely\n"
                        f"- Producing more concise, actionable content\n"
                        f"- Prioritizing what the user has explicitly asked for in AGENT.md"
                    )
                    await write_supervisor_notes(client, user_id, up, coaching)
                except Exception as e:
                    logger.warning(f"[COMPOSER] Supervisor notes failed for {title}: {e}")

    # Scope expansion: senior platform digest → scaffold cross-platform synthesis project (ADR-122)
    elif reason.startswith("lifecycle_expansion"):
        seniors = assessment.get("maturity", {}).get("senior_agents", [])
        expandable = [
            m for m in seniors
            if m.get("scope") == "platform" and m.get("role") == "digest"
            and m.get("total_runs", 0) >= 10
        ]
        if expandable and assessment["tier"]["can_create"]:
            from services.project_registry import scaffold_project
            scaffold_result = await scaffold_project(
                client, user_id, "cross_platform_synthesis",
            )
            if scaffold_result.get("success"):
                for ca in scaffold_result.get("contributors_created", []):
                    result["actions_taken"].append({
                        "action": "created",
                        "agent_id": ca["agent_id"],
                        "title": ca["title"],
                        "role": ca["role"],
                        "project_slug": scaffold_result["project_slug"],
                        "reason": f"Lifecycle expansion: {len(expandable)} senior digest agents warrant synthesis",
                    })
                logger.info(f"[COMPOSER] Lifecycle expansion: scaffolded synthesis project "
                            f"({scaffold_result['project_slug']})")
            elif scaffold_result.get("reason") == "duplicate":
                result["observations"].append("Cross-platform synthesis project already exists")
        else:
            result["observations"].append(
                f"{len(expandable)} senior digest agents detected but can't expand "
                f"(tier limit: {not assessment['tier']['can_create']})"
            )

    # ADR-117 Phase 3: Duty promotion — deterministic, no LLM needed
    elif reason.startswith("duty_promotion"):
        from services.agent_framework import get_promotion_duty, ROLE_PORTFOLIOS
        senior_agents = assessment.get("maturity", {}).get("senior_agents", [])
        for sa in senior_agents:
            agent_role = sa.get("role")
            if not agent_role or agent_role not in ROLE_PORTFOLIOS:
                continue
            current_duties = sa.get("duties") or [{"duty": agent_role}]
            promo = get_promotion_duty(agent_role, "senior", current_duties)
            if promo:
                promo_result = await _execute_promote_duty(
                    client, user_id,
                    {"agent_id": sa["agent_id"], "new_duty": promo["duty"],
                     "reason": f"Senior agent eligible for {promo['duty']} duty per role portfolio"},
                    assessment,
                )
                result["actions_taken"].extend(promo_result)
                break  # One promotion per heartbeat cycle

    # Cross-agent pattern: multiple digests → scaffold synthesis project (ADR-122)
    elif reason.startswith("cross_agent_pattern"):
        if assessment["tier"]["can_create"]:
            from services.project_registry import scaffold_project
            scaffold_result = await scaffold_project(
                client, user_id, "cross_platform_synthesis",
            )
            if scaffold_result.get("success"):
                for ca in scaffold_result.get("contributors_created", []):
                    result["actions_taken"].append({
                        "action": "created",
                        "agent_id": ca["agent_id"],
                        "title": ca["title"],
                        "role": ca["role"],
                        "project_slug": scaffold_result["project_slug"],
                        "reason": "Cross-agent pattern: consolidating multiple digests into synthesis project",
                    })

    return result


# =============================================================================
# Heartbeat Entry Point (called from unified_scheduler.py)
# =============================================================================
# NOTE: Per-agent supervisory review (ADR-111 Phase 4) has been absorbed into
# the Agent Pulse engine (ADR-126). The scheduler now dispatches pulses directly
# via run_agent_pulse() — Composer no longer owns per-agent review.

async def run_heartbeat(client: Any, user_id: str) -> dict:
    """
    Full heartbeat cycle for one user:
    1. Cheap data query (workforce assessment)
    2. Should Composer act? (create/adjust agents)
    3. If yes: run Composer assessment

    ADR-126: Per-agent pulse dispatch moved to the scheduler. Composer's
    heartbeat focuses purely on workforce composition (coverage gaps,
    lifecycle, expansion opportunities).

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
            "coverage_gaps": len(assessment["coverage"]["platforms_without_coverage"]),
            "stale_agents": len(assessment["health"]["stale_agents"]),
            "senior_agents": len(assessment.get("maturity", {}).get("senior_agents", [])),
            "underperformers": len(assessment.get("maturity", {}).get("underperformers", [])),
            "knowledge_files": assessment.get("knowledge", {}).get("total_files", 0),
            "workspace_density": assessment.get("workspace_density", "developing"),
            "total_agent_runs": assessment.get("total_agent_runs", 0),
        },
        "composer_result": None,
    }

    # Step 3: Composer assessment (LLM only when warranted)
    if should_act:
        logger.info(f"[COMPOSER] Heartbeat triggered Composer for {user_id}: {reason}")
        composer_result = await run_composer_assessment(client, user_id, assessment, reason)
        heartbeat_result["composer_result"] = composer_result

        # Activity log for created members
        if composer_result.get("contributors_created"):
            try:
                from services.activity_log import write_activity
                for created in composer_result["contributors_created"]:
                    await write_activity(
                        client=client,
                        user_id=user_id,
                        event_type="agent_bootstrapped",
                        summary=f"Composer created: {created.get('title', 'Unknown')}",
                        event_ref=created.get("agent_id"),
                        metadata={
                            "origin": "composer",
                            "role": created.get("role"),
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

    # NOTE: Per-agent pulse dispatch is now handled by the scheduler (ADR-126).
    # Composer's heartbeat focuses on workforce composition only.

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
            lifecycle_actions = composer_result.get("lifecycle_actions", [])
            created_count = len(composer_result.get("contributors_created", []))

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
                    "contributors_created": created_count,
                    "lifecycle_actions": len(lifecycle_actions),
                    **hb_result.get("assessment_summary", {}),
                },
            )
        except Exception:
            pass  # Non-fatal

        return hb_result
    except Exception as e:
        logger.warning(f"[COMPOSER] Event-driven heartbeat failed for {user_id}: {e}")
        return None
