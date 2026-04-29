"""
Feedback Distillation — ADR-143 Phase 2, updated ADR-154, ADR-181.

Routes user feedback signals to the appropriate task's feedback.md.
ADR-154: Feedback is per-task (HOW), not per-agent (WHO).
ADR-181: feedback.md promoted to task root (peer of TASK.md, DELIVERABLE.md).

Two write paths:
  1. Edit-based — called from agents.py PATCH run endpoint. Resolves task_slug
     from the run's metadata, writes to /tasks/{slug}/feedback.md.
  2. Conversational — called by TP via UpdateContext(target="agent" or "deliverable").
     For agent-targeted feedback with no task context, writes to the agent's
     most recent task's feedback file.

The task pipeline reads feedback.md on every run via build_task_execution_prompt().
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Maximum feedback entries to keep (newest first)
_MAX_FEEDBACK_ENTRIES = 10


async def _resolve_task_slug_for_agent(client: Any, agent_id: str) -> Optional[str]:
    """Find the most recent task_slug for an agent from agent_runs metadata."""
    try:
        result = (
            client.table("agent_runs")
            .select("metadata")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        for row in (result.data or []):
            meta = row.get("metadata") or {}
            task_slug = meta.get("task_slug")
            if task_slug:
                return task_slug
    except Exception as e:
        logger.warning(f"[FEEDBACK] Could not resolve task_slug for agent {agent_id}: {e}")
    return None


async def distill_feedback_to_workspace(
    client: Any,
    user_id: str,
    agent: dict,
) -> bool:
    """
    Append a feedback entry from edit signals to the task's feedback.md.

    ADR-154: Routes to task-level feedback, not agent-level.
    Resolves task_slug from the run's metadata.
    """
    agent_id = agent.get("id")
    if not agent_id:
        return False

    try:
        # Fetch the most recent run with feedback signals
        result = (
            client.table("agent_runs")
            .select("version_number, edit_categories, edit_distance_score, feedback_notes, status, metadata")
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

        # ADR-154: Resolve task_slug from run metadata
        task_slug = (run.get("metadata") or {}).get("task_slug")
        if not task_slug:
            task_slug = await _resolve_task_slug_for_agent(client, agent_id)

        if task_slug:
            await _append_feedback_for_slug(client, user_id, task_slug, entry)
            logger.info(
                f"[FEEDBACK] Wrote feedback to task {task_slug} for "
                f"{agent.get('title', agent_id)} run #{run.get('version_number')}"
            )
        else:
            logger.warning(f"[FEEDBACK] No task_slug found for agent {agent_id} — feedback dropped")
            return False

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
    task_slug: Optional[str] = None,
) -> bool:
    """
    Write a conversational feedback entry to the task's feedback.md.

    ADR-154: Routes to task-level feedback. If task_slug not provided,
    resolves from the agent's most recent run metadata.
    """
    agent_id = agent.get("id")
    if not agent_id or not feedback_text:
        return False

    try:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M")
        entry = f"## Feedback ({date_str}, {source})\n- {feedback_text}\n"

        # Resolve task_slug
        if not task_slug:
            task_slug = await _resolve_task_slug_for_agent(client, agent_id)

        if task_slug:
            await _append_feedback_for_slug(client, user_id, task_slug, entry)
            logger.info(f"[FEEDBACK] Conversational feedback → task {task_slug}")
        else:
            logger.warning(f"[FEEDBACK] No task_slug for agent {agent_id} — feedback dropped")
            return False

        return True

    except Exception as e:
        logger.warning(f"[FEEDBACK] Write failed for {agent_id}: {e}")
        return False


def _build_feedback_entry(run: dict) -> str:
    """
    Build a human-readable feedback entry from a run's edit signals.

    Converts edit_categories + feedback_notes + status into a concise
    description of what changed and why, readable by the agent on next run.
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
        lines.append(f"## Run {version} ({date_str}, approved)")
        lines.append("- Approved without changes. Current approach is working.")
        return "\n".join(lines) + "\n"

    source = "edited" if has_edits else "approved"
    lines.append(f"## Run {version} ({date_str}, {source})")

    for item in additions[:3]:
        lines.append(f"- User added: {item}")
    for item in deletions[:3]:
        lines.append(f"- User removed: {item}")
    for item in restructures[:2]:
        if isinstance(item, dict):
            lines.append(f"- User restructured: moved '{item.get('section', '?')}' {item.get('direction', '')}")
        else:
            lines.append(f"- User restructured: {item}")
    for item in rewrites[:2]:
        if isinstance(item, dict):
            orig = item.get("original", "")[:50]
            revised = item.get("revised", "")[:50]
            lines.append(f"- User rephrased: \"{orig}\" → \"{revised}\"")
        else:
            lines.append(f"- User rephrased content")

    if feedback_notes:
        lines.append(f"- User said: \"{feedback_notes}\"")
    if edit_score is not None and edit_score > 0.5:
        lines.append(f"- Note: significant edits (distance: {edit_score:.1%})")

    return "\n".join(lines) + "\n"


async def _append_feedback_for_slug(
    client: Any,
    user_id: str,
    slug: str,
    new_entry: str,
) -> None:
    """Append a feedback entry to the natural-home _feedback.md for a slug.

    ADR-231 Phase 3.6.b: writes to the recurrence's feedback path (DELIVERABLE
    → /workspace/reports/{slug}/_feedback.md, ACCUMULATION → /workspace/context/
    {domain}/_feedback.md per ADR-181). Resolves the path via the declaration
    walker; logs + skips silently when the slug has no declaration or the
    shape has no canonical feedback substrate (ACTION + MAINTENANCE).

    Newest entry first, capped at _MAX_FEEDBACK_ENTRIES.
    """
    from services.recurrence_paths import resolve_paths_for_slug
    from services.workspace import UserMemory

    paths = resolve_paths_for_slug(client, user_id, slug)
    if paths is None or paths.feedback_path is None:
        logger.warning(
            f"[FEEDBACK] no feedback path for slug={slug} (no decl or shape "
            f"has no feedback substrate); entry dropped"
        )
        return

    relative = paths.feedback_path[len("/workspace/"):] if paths.feedback_path.startswith("/workspace/") else paths.feedback_path
    um = UserMemory(client, user_id)
    existing = await um.read(relative) or ""

    header = "# Feedback\n<!-- Source-agnostic feedback layer. Newest first. ADR-181 + ADR-231 D2. -->\n\n"
    entries = re.split(r"(?=^## )", existing, flags=re.MULTILINE)
    entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("## ")]
    entries = [new_entry.strip()] + entries[:_MAX_FEEDBACK_ENTRIES - 1]
    content = header + "\n\n".join(entries) + "\n"

    await um.write(
        relative,
        content,
        summary="ADR-181: feedback entry (natural-home substrate)",
        authored_by="system:feedback-distillation",
        message=f"append feedback for {slug}",
    )
