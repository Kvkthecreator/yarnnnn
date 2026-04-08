"""Back Office: Agent Hygiene — ADR-164.

Migrated from `unified_scheduler._pause_underperformers()` (ADR-156).

Reviews all active agents for the workspace. Pauses agents that meet the
underperformer criteria:
  - At least UNDERPERFORMER_MIN_RUNS runs completed
  - Approval rate below UNDERPERFORMER_MAX_APPROVAL
  - Origin is NOT 'user_configured' (respect explicit user choices)

Zero LLM cost — deterministic SQL rules only. Output is a markdown report
with the observed state and any actions taken. The report is written to
/tasks/back-office-agent-hygiene/outputs/{date}/output.md by the task
pipeline; this module only returns the result dict.

This is the ADR-164 pattern: system-facing maintenance work lives as a task
owned by TP, executed through the same pipeline as user work, producing
visible outputs the user can inspect.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# Thresholds inherited from ADR-156's _pause_underperformers.
# Kept as module constants so they can be referenced in the output report
# and adjusted via config without touching the scheduler or pipeline.
UNDERPERFORMER_MIN_RUNS = 8
UNDERPERFORMER_MAX_APPROVAL = 0.30


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Execute agent hygiene for the given workspace.

    Args:
        client: Supabase service client
        user_id: User UUID
        task_slug: The task slug being executed (used only for logging)

    Returns:
        {
            "summary": str,                 — one-line human summary
            "output_markdown": str,          — full markdown report
            "actions_taken": list[dict],     — structured action log
        }
    """
    started_at = datetime.now(timezone.utc)

    # Fetch active agents (excluding TP itself — TP is infrastructure,
    # not subject to hygiene review).
    try:
        agents_result = (
            client.table("agents")
            .select("id, title, role, origin, slug")
            .eq("user_id", user_id)
            .eq("status", "active")
            .neq("role", "thinking_partner")
            .execute()
        )
    except Exception as e:
        logger.error(f"[BACK_OFFICE:agent_hygiene] Agent query failed: {e}")
        return _empty_result(started_at, error=str(e))

    agents = agents_result.data or []
    if not agents:
        return {
            "summary": "No active agents to review.",
            "output_markdown": _format_empty_report(started_at),
            "actions_taken": [],
        }

    agent_ids = [a["id"] for a in agents]

    # Batch query: fetch all runs for these agents
    try:
        runs_result = (
            client.table("agent_runs")
            .select("agent_id, status")
            .in_("agent_id", agent_ids)
            .execute()
        )
    except Exception as e:
        logger.error(f"[BACK_OFFICE:agent_hygiene] Runs query failed: {e}")
        return _empty_result(started_at, error=str(e))

    runs = runs_result.data or []

    # Compute per-agent stats
    stats: dict[str, dict] = {}
    for run_row in runs:
        aid = run_row["agent_id"]
        if aid not in stats:
            stats[aid] = {"total": 0, "approved": 0}
        stats[aid]["total"] += 1
        if run_row.get("status") == "approved":
            stats[aid]["approved"] += 1

    # Apply hygiene rule to each agent
    observations: list[dict] = []
    actions_taken: list[dict] = []

    for agent in agents:
        aid = agent["id"]
        agent_stats = stats.get(aid, {"total": 0, "approved": 0})
        total = agent_stats["total"]
        approved = agent_stats["approved"]
        approval_rate = (approved / total) if total > 0 else 0.0

        observation = {
            "title": agent.get("title", "Untitled"),
            "slug": agent.get("slug", ""),
            "role": agent.get("role", "custom"),
            "origin": agent.get("origin", "user_configured"),
            "runs": total,
            "approved": approved,
            "approval_rate": round(approval_rate, 2),
            "decision": "no_action",
            "reason": "",
        }

        # Gate 1: respect user-configured agents
        if agent.get("origin") == "user_configured":
            observation["reason"] = "user_configured (exempt from auto-pause)"
            observations.append(observation)
            continue

        # Gate 2: minimum runs before review
        if total < UNDERPERFORMER_MIN_RUNS:
            observation["reason"] = f"below min runs ({total}/{UNDERPERFORMER_MIN_RUNS})"
            observations.append(observation)
            continue

        # Gate 3: approval rate threshold
        if approval_rate >= UNDERPERFORMER_MAX_APPROVAL:
            observation["reason"] = f"approval rate OK ({approval_rate:.0%})"
            observations.append(observation)
            continue

        # All gates failed — pause the agent
        try:
            client.table("agents").update(
                {"status": "paused"}
            ).eq("id", aid).execute()

            observation["decision"] = "paused"
            observation["reason"] = f"{approval_rate:.0%} approval over {total} runs"
            actions_taken.append({
                "action": "pause_agent",
                "agent_id": aid,
                "agent_title": agent.get("title", ""),
                "approval_rate": round(approval_rate, 2),
                "run_count": total,
            })

            # Write coaching feedback (same pattern as ADR-156)
            try:
                from services.feedback_distillation import write_feedback_entry
                await write_feedback_entry(
                    client=client,
                    user_id=user_id,
                    agent=agent,
                    feedback_text=(
                        f"Auto-paused by back office hygiene: {approval_rate:.0%} approval "
                        f"over {total} runs. Review output quality and deliverable spec."
                    ),
                    source="system_lifecycle",
                )
            except Exception as e:
                logger.warning(
                    f"[BACK_OFFICE:agent_hygiene] Feedback write failed for {aid}: {e}"
                )
        except Exception as e:
            logger.warning(
                f"[BACK_OFFICE:agent_hygiene] Failed to pause {agent.get('title')}: {e}"
            )
            observation["decision"] = "error"
            observation["reason"] = f"pause failed: {e}"

        observations.append(observation)

    # Format output
    paused_count = sum(1 for o in observations if o["decision"] == "paused")
    reviewed_count = len(observations)

    if paused_count == 0:
        summary = f"Reviewed {reviewed_count} agents. No action taken."
    else:
        summary = f"Reviewed {reviewed_count} agents. Paused {paused_count} underperformers."

    output_markdown = _format_report(started_at, observations, paused_count, reviewed_count)

    logger.info(f"[BACK_OFFICE:agent_hygiene] {summary}")

    return {
        "summary": summary,
        "output_markdown": output_markdown,
        "actions_taken": actions_taken,
    }


def _empty_result(started_at: datetime, error: str | None = None) -> dict:
    """Return an empty result (used when a query fails or there are no agents)."""
    return {
        "summary": f"Hygiene check failed: {error}" if error else "No agents reviewed.",
        "output_markdown": _format_empty_report(started_at, error=error),
        "actions_taken": [],
    }


def _format_empty_report(started_at: datetime, error: str | None = None) -> str:
    date_str = started_at.strftime("%Y-%m-%d %H:%M UTC")
    if error:
        return (
            f"# Agent Hygiene — {date_str}\n\n"
            f"**Status:** Error\n\n"
            f"Error during hygiene check: `{error}`\n\n"
            f"<!-- executor: services.back_office.agent_hygiene -->\n"
        )
    return (
        f"# Agent Hygiene — {date_str}\n\n"
        f"**Summary:** No active agents to review.\n\n"
        f"<!-- executor: services.back_office.agent_hygiene -->\n"
    )


def _format_report(
    started_at: datetime,
    observations: list[dict],
    paused_count: int,
    reviewed_count: int,
) -> str:
    """Format the hygiene observations as a markdown report."""
    date_str = started_at.strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Agent Hygiene — {date_str}",
        "",
        "## Summary",
        f"Reviewed **{reviewed_count}** active agents. Paused **{paused_count}** underperformers.",
        "",
        "## Thresholds",
        f"- Minimum runs before review: `{UNDERPERFORMER_MIN_RUNS}`",
        f"- Minimum approval rate: `{UNDERPERFORMER_MAX_APPROVAL:.0%}`",
        "- Exempt: agents with `origin='user_configured'` (respect explicit user choices)",
        "- Exempt: TP itself (meta-cognitive agent, infrastructure)",
        "",
        "## Observations",
        "",
        "| Agent | Role | Runs | Approval | Decision | Reason |",
        "|---|---|---:|---:|---|---|",
    ]

    for obs in observations:
        approval_display = f"{obs['approval_rate']:.0%}" if obs['runs'] > 0 else "—"
        decision_display = obs['decision']
        if decision_display == "paused":
            decision_display = "⚠ **paused**"
        elif decision_display == "error":
            decision_display = "❌ error"
        else:
            decision_display = "✓ ok"
        lines.append(
            f"| {obs['title']} | `{obs['role']}` | {obs['runs']} | "
            f"{approval_display} | {decision_display} | {obs['reason']} |"
        )

    lines.append("")
    lines.append(f"<!-- executor: services.back_office.agent_hygiene · version: 1 -->")

    return "\n".join(lines) + "\n"
