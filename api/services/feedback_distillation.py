"""
Feedback Distillation — ADR-117 Phase 1.

Distills cumulative user feedback (edit patterns, feedback notes, approval signals)
into persistent workspace preferences. Replaces raw get_past_versions_context()
injection with structured, persistent preferences in memory/preferences.md.

Called from:
- agents.py PATCH version endpoint (after edit metrics are computed)
- Composer lifecycle events (supervisor coaching to supervisor-notes.md)

The workspace IS the unified feedback substrate. All feedback — user edits,
Composer coaching, agent self-reflection — converges to workspace files.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def distill_feedback_to_workspace(
    client: Any,
    user_id: str,
    agent: dict,
) -> bool:
    """
    Distill cumulative feedback from agent_runs into memory/preferences.md.

    Reads the last 10 delivered/approved runs, aggregates edit patterns and
    feedback notes, and writes a structured preferences file to the agent's
    workspace. This file is loaded by all strategies via load_context().

    preferences.md is overwritten each time — it represents the current best
    understanding of what the user wants, not an append log.

    Returns True if preferences were written, False otherwise.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    if not agent_id:
        return False

    try:
        # Fetch recent runs with feedback signals
        result = (
            client.table("agent_runs")
            .select("version_number, edit_categories, edit_distance_score, feedback_notes, status")
            .eq("agent_id", agent_id)
            .in_("status", ["approved", "delivered"])
            .order("version_number", desc=True)
            .limit(10)
            .execute()
        )

        runs = result.data or []
        if not runs:
            return False

        preferences = _build_preferences(runs)
        if not preferences:
            return False

        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        await ws.write(
            "memory/preferences.md",
            preferences,
            summary="Distilled user feedback preferences",
        )

        logger.info(
            f"[FEEDBACK] Distilled preferences for {agent.get('title', agent_id)} "
            f"from {len(runs)} runs"
        )
        return True

    except Exception as e:
        logger.warning(f"[FEEDBACK] Distillation failed for {agent_id}: {e}")
        return False


def _build_preferences(runs: list[dict]) -> str:
    """
    Build structured preferences from run feedback history.

    Converts raw edit signals into behavioral directives:
    - "User added action items in 4 of 5 runs" → "Always include an Action Items section"
    - "User removed meeting summaries in 3 runs" → "Omit detailed meeting-by-meeting summaries"
    - Feedback notes are included verbatim as explicit user guidance
    """
    addition_counts: dict[str, int] = {}
    deletion_counts: dict[str, int] = {}
    feedback_notes: list[str] = []
    total_with_edits = 0
    total_runs = len(runs)

    for run in runs:
        categories = run.get("edit_categories") or {}
        has_edits = False

        for addition in categories.get("additions", []):
            addition_counts[addition] = addition_counts.get(addition, 0) + 1
            has_edits = True
        for deletion in categories.get("deletions", []):
            deletion_counts[deletion] = deletion_counts.get(deletion, 0) + 1
            has_edits = True

        if has_edits:
            total_with_edits += 1

        note = (run.get("feedback_notes") or "").strip()
        if note and note not in feedback_notes:
            feedback_notes.append(note)

    # No feedback signals at all
    if not addition_counts and not deletion_counts and not feedback_notes:
        # Positive signal: runs delivered without edits
        if total_runs >= 3:
            return (
                "# User Preferences\n\n"
                f"The user has approved {total_runs} recent outputs without significant edits. "
                "Current format and content selection are working well. Maintain this approach."
            )
        return ""

    lines = ["# User Preferences\n"]

    # Recurring additions — things the user consistently adds
    if addition_counts:
        lines.append("## Content the user wants included")
        for item, count in sorted(addition_counts.items(), key=lambda x: -x[1])[:5]:
            if count >= 3:
                lines.append(f"- **Always include {item}** (added in {count}/{total_runs} runs)")
            elif count >= 2:
                lines.append(f"- Include {item} (added in {count}/{total_runs} runs)")
            else:
                lines.append(f"- Consider including {item}")

    # Recurring deletions — things the user consistently removes
    if deletion_counts:
        lines.append("\n## Content the user does NOT want")
        for item, count in sorted(deletion_counts.items(), key=lambda x: -x[1])[:5]:
            if count >= 3:
                lines.append(f"- **Never include {item}** (removed in {count}/{total_runs} runs)")
            elif count >= 2:
                lines.append(f"- Avoid {item} (removed in {count}/{total_runs} runs)")
            else:
                lines.append(f"- User removed {item} once — consider omitting")

    # Explicit feedback notes — highest signal, include verbatim
    if feedback_notes:
        lines.append("\n## Explicit feedback")
        for note in feedback_notes[:5]:
            lines.append(f"- \"{note}\"")

    # Quality signal
    if total_with_edits > 0:
        edit_rate = total_with_edits / total_runs
        if edit_rate > 0.6:
            lines.append(f"\n*Note: {total_with_edits}/{total_runs} recent outputs required edits. Pay close attention to the preferences above.*")
        elif edit_rate < 0.3:
            lines.append(f"\n*{total_runs - total_with_edits}/{total_runs} recent outputs accepted without edits. Preferences are mostly satisfied.*")

    return "\n".join(lines)


async def write_supervisor_notes(
    client: Any,
    user_id: str,
    agent: dict,
    coaching: str,
) -> bool:
    """
    Write Composer/TP coaching feedback to the agent's workspace.

    ADR-117 Phase 1c: Bridges Composer lifecycle assessment with agent intelligence.
    The agent sees supervisor notes on its next run via load_context().
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    if not agent_id or not coaching:
        return False

    try:
        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        await ws.write(
            "memory/supervisor-notes.md",
            f"# Supervisor Assessment\n\n{coaching}",
            summary="Composer coaching feedback",
        )

        logger.info(f"[FEEDBACK] Supervisor notes written for {agent.get('title', agent_id)}")
        return True

    except Exception as e:
        logger.warning(f"[FEEDBACK] Supervisor notes failed for {agent_id}: {e}")
        return False
