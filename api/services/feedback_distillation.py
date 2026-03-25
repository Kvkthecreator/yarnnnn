"""
Feedback Distillation — ADR-143 Phase 2.

Consolidates all feedback signals into a single memory/feedback.md file.
Replaces the old preferences.md / supervisor-notes.md / observations.md split.

feedback.md is append-at-top with a rolling 10-entry cap (like self_assessment.md).
Each entry is a human-readable summary of what changed and why.

Two write paths:
  1. Edit-based (this module) — called from agents.py PATCH run endpoint
  2. Conversational (WriteAgentFeedback primitive) — called by TP

The agent reads feedback.md on every run via load_context(). The LLM
infers patterns from the entries — no classification logic needed.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Maximum feedback entries to keep (newest first)
_MAX_FEEDBACK_ENTRIES = 10


async def distill_feedback_to_workspace(
    client: Any,
    user_id: str,
    agent: dict,
) -> bool:
    """
    Append a feedback entry to memory/feedback.md from edit signals.

    Called after a user approves/edits/rejects an agent run. Reads the
    latest run's edit_categories and formats a human-readable entry.

    Returns True if feedback was written, False otherwise.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    if not agent_id:
        return False

    try:
        # Fetch the most recent run with feedback signals
        result = (
            client.table("agent_runs")
            .select("version_number, edit_categories, edit_distance_score, feedback_notes, status")
            .eq("agent_id", agent_id)
            .in_("status", ["approved", "delivered", "rejected"])
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )

        runs = result.data or []
        if not runs:
            return False

        run = runs[0]
        entry = _build_feedback_entry(run)
        if not entry:
            return False

        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        await _append_feedback(ws, entry)

        logger.info(
            f"[FEEDBACK] Wrote feedback for {agent.get('title', agent_id)} "
            f"run #{run.get('version_number')}"
        )
        return True

    except Exception as e:
        logger.warning(f"[FEEDBACK] Distillation failed for {agent_id}: {e}")
        return False


async def write_feedback_entry(
    client: Any,
    user_id: str,
    agent: dict,
    feedback_text: str,
    source: str = "conversation",
) -> bool:
    """
    Write a conversational feedback entry to an agent's feedback.md.

    Called by TP via WriteAgentFeedback primitive when the user gives
    feedback about an agent's work in conversation.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    if not agent_id or not feedback_text:
        return False

    try:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M")

        entry = f"## Feedback ({date_str}, {source})\n- {feedback_text}\n"

        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        await _append_feedback(ws, entry)

        logger.info(f"[FEEDBACK] Conversational feedback for {agent.get('title', agent_id)}")
        return True

    except Exception as e:
        logger.warning(f"[FEEDBACK] Write failed for {agent_id}: {e}")
        return False


def _build_feedback_entry(run: dict) -> str:
    """
    Build a human-readable feedback entry from a run's edit signals.

    Converts edit_categories + feedback_notes + status into a concise
    description of what happened, readable by the agent on next run.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")
    version = run.get("version_number", "?")
    status = run.get("status", "unknown")
    categories = run.get("edit_categories") or {}
    feedback_notes = (run.get("feedback_notes") or "").strip()
    edit_score = run.get("edit_distance_score")

    lines = []

    if status == "rejected":
        lines.append(f"## Run {version} ({date_str}, rejected)")
        lines.append("- Output was rejected by the user.")
        if feedback_notes:
            lines.append(f"- User said: \"{feedback_notes}\"")
        return "\n".join(lines) + "\n"

    # Approved/delivered
    additions = categories.get("additions", [])
    deletions = categories.get("deletions", [])
    restructures = categories.get("restructures", [])
    rewrites = categories.get("rewrites", [])

    has_edits = additions or deletions or restructures or rewrites

    if not has_edits and not feedback_notes:
        # Approved without changes — brief positive entry
        lines.append(f"## Run {version} ({date_str}, approved)")
        lines.append("- Approved without changes. Current approach is working.")
        return "\n".join(lines) + "\n"

    source = "edited" if has_edits else "approved"
    lines.append(f"## Run {version} ({date_str}, {source})")

    # Additions — user added content
    for item in additions[:3]:
        lines.append(f"- User added: {item}")

    # Deletions — user removed content
    for item in deletions[:3]:
        lines.append(f"- User removed: {item}")

    # Restructures — user moved sections
    for item in restructures[:2]:
        if isinstance(item, dict):
            lines.append(f"- User restructured: moved '{item.get('section', '?')}' {item.get('direction', '')}")
        else:
            lines.append(f"- User restructured: {item}")

    # Rewrites — user rephrased
    for item in rewrites[:2]:
        if isinstance(item, dict):
            orig = item.get("original", "")[:50]
            revised = item.get("revised", "")[:50]
            lines.append(f"- User rephrased: \"{orig}\" → \"{revised}\"")
        else:
            lines.append(f"- User rephrased content")

    # Explicit feedback notes
    if feedback_notes:
        lines.append(f"- User said: \"{feedback_notes}\"")

    # Edit intensity signal
    if edit_score is not None and edit_score > 0.5:
        lines.append(f"- Note: significant edits (distance: {edit_score:.1%})")

    return "\n".join(lines) + "\n"


async def _append_feedback(ws: Any, new_entry: str) -> None:
    """
    Append a feedback entry to memory/feedback.md (newest first, capped).

    Same pattern as _append_self_assessment in agent_execution.py.
    """
    existing = await ws.read("memory/feedback.md") or ""

    header = "# Feedback History\n<!-- Most recent first. Max 10 entries. TP writes, agent reads. -->\n\n"

    # Split on ## headers (each entry starts with ##)
    entries = re.split(r"(?=^## )", existing, flags=re.MULTILINE)
    entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("## ")]

    # Prepend new entry, cap at max
    entries = [new_entry.strip()] + entries[:_MAX_FEEDBACK_ENTRIES - 1]

    content = header + "\n\n".join(entries) + "\n"

    await ws.write(
        "memory/feedback.md",
        content,
        summary="ADR-143: feedback entry",
    )
