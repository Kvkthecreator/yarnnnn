"""
Dashboard routes — Supervision Dashboard summary endpoint.

Provides the data for the frontend supervision dashboard:
- Agent health grid (status, maturity, last run)
- Recent Composer actions (from activity_log)
- Attention items (auto-paused agents, failed runs)
- Summary stats (counts, maturity distribution)

Zero LLM cost — pure DB queries. Reuses maturity logic from
composer.py heartbeat_data_query().

Mounted at /api/dashboard
"""

import logging

from fastapi import APIRouter
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

from services.supabase import UserClient

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(client: UserClient):
    """
    GET /api/dashboard/summary

    Returns supervision dashboard payload: agent health, Composer activity,
    attention items, and summary stats. Single call for the dashboard page.
    """
    now = datetime.now(timezone.utc)
    user_id = client.user_id
    db = client.client

    # 1. All non-archived agents with core fields
    agents_raw = []
    try:
        result = (
            db.table("agents")
            .select("id, title, status, origin, skill, scope, sources, created_at, last_run_at")
            .eq("user_id", user_id)
            .neq("status", "archived")
            .execute()
        )
        agents_raw = result.data or []
    except Exception as e:
        logger.warning(f"[DASHBOARD] Agent query failed: {e}")

    # 2. Per-agent maturity signals (same logic as composer.py heartbeat_data_query)
    active_agents = [a for a in agents_raw if a.get("status") == "active"]
    agent_health = []

    for agent in agents_raw:
        aid = agent["id"]
        maturity = "nascent"
        approval_rate = None
        edit_trend = None
        total_runs = 0

        if agent.get("status") != "archived":
            try:
                runs_result = (
                    db.table("agent_runs")
                    .select("status, edit_distance_score")
                    .eq("agent_id", aid)
                    .order("created_at", desc=True)
                    .limit(20)
                    .execute()
                )
                runs = runs_result.data or []
                total_runs = len(runs)

                if total_runs > 0:
                    completed = [r for r in runs if r.get("status") in ("approved", "delivered", "rejected")]
                    approved = [r for r in runs if r.get("status") in ("approved", "delivered")]
                    approval_rate = round(len(approved) / len(completed), 2) if completed else None

                    # Edit distance trend
                    distances = [
                        r["edit_distance_score"] for r in runs
                        if r.get("edit_distance_score") is not None
                    ]
                    if len(distances) >= 3:
                        recent_avg = sum(distances[:3]) / 3
                        older_count = min(3, len(distances) - 3)
                        if older_count > 0:
                            older_avg = sum(distances[3:3 + older_count]) / older_count
                            if older_avg > 0:
                                edit_trend = round((recent_avg - older_avg) / older_avg, 2)

                    # Classify maturity
                    rate = approval_rate or 0
                    if total_runs >= 10 and rate >= 0.8:
                        maturity = "mature"
                    elif total_runs >= 5 and rate >= 0.6:
                        maturity = "developing"
                    else:
                        maturity = "nascent"
            except Exception as e:
                logger.warning(f"[DASHBOARD] Maturity query failed for {aid}: {e}")

        agent_health.append({
            "id": aid,
            "title": agent["title"],
            "status": agent.get("status"),
            "origin": agent.get("origin"),
            "skill": agent.get("skill"),
            "scope": agent.get("scope"),
            "sources": agent.get("sources", []),
            "last_run_at": agent.get("last_run_at"),
            "maturity": maturity,
            "approval_rate": approval_rate,
            "edit_trend": edit_trend,
            "total_runs": total_runs,
        })

    # 3. Recent Composer actions (from activity_log, last 7 days)
    composer_actions = []
    try:
        week_ago = (now - timedelta(days=7)).isoformat()
        result = (
            db.table("activity_log")
            .select("id, event_type, summary, metadata, created_at")
            .eq("user_id", user_id)
            .in_("event_type", ["composer_heartbeat", "agent_bootstrapped"])
            .gte("created_at", week_ago)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        for row in (result.data or []):
            metadata = row.get("metadata") or {}
            # Extract lifecycle actions from heartbeat metadata
            lifecycle_actions = metadata.get("lifecycle_actions", [])
            if lifecycle_actions or row["event_type"] == "agent_bootstrapped":
                composer_actions.append({
                    "type": _classify_composer_action(row["event_type"], metadata),
                    "summary": row.get("summary", ""),
                    "agent_id": metadata.get("agent_id"),
                    "agent_title": metadata.get("agent_title"),
                    "created_at": row["created_at"],
                    "metadata": metadata,
                })
    except Exception as e:
        logger.warning(f"[DASHBOARD] Composer activity query failed: {e}")

    # 4. Attention items — things that need user review
    attention = []

    # Auto-paused agents (paused by lifecycle, not by user)
    for ah in agent_health:
        if ah["status"] == "paused" and ah["origin"] in ("composer", "system_bootstrap"):
            attention.append({
                "type": "auto_paused",
                "message": f"'{ah['title']}' was auto-paused — review or archive",
                "agent_id": ah["id"],
                "agent_title": ah["title"],
            })

    # Recent failed runs (last 3 days)
    try:
        three_days_ago = (now - timedelta(days=3)).isoformat()
        agent_ids = [a["id"] for a in agents_raw if a.get("status") == "active"]
        if agent_ids:
            result = (
                db.table("agent_runs")
                .select("agent_id, created_at")
                .in_("agent_id", agent_ids)
                .eq("status", "failed")
                .gte("created_at", three_days_ago)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            failed_agent_ids = set()
            for row in (result.data or []):
                faid = row["agent_id"]
                if faid not in failed_agent_ids:
                    failed_agent_ids.add(faid)
                    agent_match = next((a for a in agent_health if a["id"] == faid), None)
                    if agent_match:
                        attention.append({
                            "type": "failed",
                            "message": f"'{agent_match['title']}' had a failed run",
                            "agent_id": faid,
                            "agent_title": agent_match["title"],
                        })
    except Exception as e:
        logger.warning(f"[DASHBOARD] Failed runs query failed: {e}")

    # 5. Summary stats
    maturity_dist = {"nascent": 0, "developing": 0, "mature": 0}
    for ah in agent_health:
        if ah["status"] == "active":
            m = ah.get("maturity", "nascent")
            maturity_dist[m] = maturity_dist.get(m, 0) + 1

    # Runs this week
    runs_this_week = 0
    try:
        week_ago = (now - timedelta(days=7)).isoformat()
        agent_ids = [a["id"] for a in agents_raw]
        if agent_ids:
            result = (
                db.table("agent_runs")
                .select("id", count="exact")
                .in_("agent_id", agent_ids)
                .gte("created_at", week_ago)
                .execute()
            )
            runs_this_week = result.count or 0
    except Exception as e:
        logger.warning(f"[DASHBOARD] Weekly runs query failed: {e}")

    return {
        "agents": agent_health,
        "composer_actions": composer_actions,
        "attention": attention,
        "stats": {
            "total_agents": len(agents_raw),
            "active_agents": len(active_agents),
            "runs_this_week": runs_this_week,
            "maturity_distribution": maturity_dist,
        },
    }


def _classify_composer_action(event_type: str, metadata: dict) -> str:
    """Classify a composer event into a dashboard-friendly action type."""
    if event_type == "agent_bootstrapped":
        return "created"
    lifecycle = metadata.get("lifecycle_actions", [])
    for action in lifecycle:
        if "pause" in str(action).lower():
            return "paused"
        if "creat" in str(action).lower():
            return "created"
    if metadata.get("assessment_action") == "observed":
        return "observation"
    return "observation"
