"""
Feedback formatters — ADR-235 D1.b

Pure-Python formatters for the three feedback shapes that previously lived
inside UpdateContext._handle_memory / _handle_agent_feedback /
_handle_task_feedback. After ADR-235 dissolves UpdateContext, these
formatters are called server-side from the WriteFile handler when the
write target is a recognized feedback path. The formatter logic stays
unchanged — only its primitive entry point changes.

These helpers do NOT perform writes themselves. They:
  - Compute the canonical workspace-relative path
  - Format the new content (with dedup for memory, header pattern for
    feedback)
  - Return a directive shape `(path, content_or_None, mode)` the caller
    routes to UserMemory.write or AgentWorkspace.write

`None` content means "skip the write entirely" (dedup hit on memory entry).
"""

from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from services.workspace_paths import MEMORY_NOTES_PATH


# ---------------------------------------------------------------------------
# Memory entry formatter (operator-stated facts/preferences/instructions)
# ---------------------------------------------------------------------------


def infer_memory_entry_type(text: str) -> str:
    """Heuristic classification matching the prior _handle_memory logic."""
    text_lower = text.lower()
    entry_type = "fact"
    if any(w in text_lower for w in ("prefer", "always", "never", "like", "don't like")):
        entry_type = "preference"
    if any(w in text_lower for w in ("always include", "never include", "make sure", "when you")):
        entry_type = "instruction"
    return entry_type


async def format_memory_entry(
    db_client: Any,
    user_id: str,
    text: str,
) -> Tuple[Optional[str], str, str]:
    """Compute (content, path, entry_type) for a memory append.

    Returns (None, path, entry_type) on dedup hit — caller skips the write.

    Reads existing notes via UserMemory.get_notes() and rejects entries
    that match an existing note (case-insensitive, whitespace-stripped).
    """
    from services.workspace import UserMemory

    um = UserMemory(db_client, user_id)
    existing_notes = await um.get_notes()

    needle = text.lower().strip()
    if any(n["content"].lower().strip() == needle for n in existing_notes):
        return (None, MEMORY_NOTES_PATH, "duplicate")

    entry_type = infer_memory_entry_type(text)
    return (text, MEMORY_NOTES_PATH, entry_type)


# ---------------------------------------------------------------------------
# Agent feedback formatter (cross-task agent style/tone corrections)
# ---------------------------------------------------------------------------


def format_agent_feedback_entry(
    agent_slug: str,
    feedback_text: str,
    existing: str,
) -> str:
    """Build the new content for an agent's memory/feedback.md.

    Preserves the prior `## Feedback (date, source: ...)` header pattern
    and prepends the new entry (newest at the top, immediately after the
    file header).
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")
    entry = f"## Feedback ({date_str}, source: user_conversation)\n- {feedback_text}\n"

    if existing.startswith("# Agent Feedback"):
        header_lines = existing.split("\n", 2)
        rest = header_lines[2] if len(header_lines) > 2 else ""
        return f"{header_lines[0]}\n{header_lines[1] if len(header_lines) > 1 else ''}\n\n{entry}\n{rest}"

    return f"# Agent Feedback\n\n{entry}\n{existing}"


def agent_feedback_relative_path(agent_slug: str) -> str:
    """Compute the AgentWorkspace-relative path for an agent's feedback file."""
    return "memory/feedback.md"


# ---------------------------------------------------------------------------
# Task feedback formatter (task-scoped feedback driving DELIVERABLE inference)
# ---------------------------------------------------------------------------


def format_task_feedback_entry(
    feedback_text: str,
    existing: str,
) -> str:
    """Build the new content for a task's feedback.md.

    Preserves the prior `## User Feedback (date, source: ...)` header
    pattern. Newest at top, immediately after the file header.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")
    entry = f"## User Feedback ({date_str}, source: user_conversation)\n- {feedback_text}\n"

    if existing.startswith("# Feedback") or existing.startswith("# Task Feedback"):
        header_lines = existing.split("\n", 2)
        rest = header_lines[2] if len(header_lines) > 2 else ""
        return f"{header_lines[0]}\n{header_lines[1] if len(header_lines) > 1 else ''}\n\n{entry}\n{rest}"

    return (
        f"# Feedback\n"
        f"<!-- Source-agnostic feedback layer. Newest first. ADR-181 + ADR-231 D2. -->\n\n"
        f"{entry}\n"
        f"{existing}"
    )


async def resolve_task_feedback_path(
    db_client: Any,
    user_id: str,
    task_slug: str,
) -> Tuple[Optional[str], Optional[dict]]:
    """Resolve task feedback path via the recurrence walker.

    Returns (relative_path, error_payload). On success, error_payload is None.
    On failure, relative_path is None and error_payload describes the issue.
    """
    from services.recurrence import walk_workspace_recurrences
    from services.recurrence_paths import resolve_paths

    decls = walk_workspace_recurrences(db_client, user_id)
    decl = next((d for d in decls if d.slug == task_slug), None)
    if decl is None:
        return (
            None,
            {
                "success": False,
                "error": "no_declaration",
                "message": f"No recurrence declaration for slug '{task_slug}'",
            },
        )

    paths = resolve_paths(decl)
    if paths.feedback_path is None:
        return (
            None,
            {
                "success": False,
                "error": "no_feedback_substrate",
                "message": f"Recurrence shape '{decl.shape.value}' has no feedback substrate",
            },
        )

    relative = (
        paths.feedback_path[len("/workspace/"):]
        if paths.feedback_path.startswith("/workspace/")
        else paths.feedback_path
    )
    return (relative, None)
