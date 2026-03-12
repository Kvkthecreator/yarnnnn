"""
SaveMemory Primitive — ADR-108

Chat-mode-only primitive that lets TP persist a user-stated fact,
preference, or instruction to /memory/notes.md in real time.

Add-only (no update/delete from chat). Users manage existing entries
via the Memory page. Nightly cron still runs for implicit extraction.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


SAVE_MEMORY_TOOL = {
    "name": "SaveMemory",
    "description": """Save a fact, preference, or instruction to the user's memory.

Use this when the user explicitly asks you to remember something, or states
a stable personal fact worth persisting (name, role, preference, standing instruction).

Examples of when to use:
- "Remember that I prefer bullet points"
- "Note that my timezone is Asia/Seoul"
- "Always include a TL;DR in my reports"
- "I'm the CTO at Acme Corp"

Do NOT use for:
- Transient information (today's tasks, current project status)
- Information already in memory (check working memory first)
- Opinions about specific topics

The memory will be available in all future sessions.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The fact, preference, or instruction to remember (concise, 1-2 sentences)"
            },
            "entry_type": {
                "type": "string",
                "enum": ["fact", "preference", "instruction"],
                "description": "Type of memory: 'fact' (about the user), 'preference' (how they like things), 'instruction' (standing directive). Default: fact"
            }
        },
        "required": ["content"]
    }
}


async def handle_save_memory(auth: Any, input: dict) -> dict:
    """Handle SaveMemory primitive — appends a note to /memory/notes.md."""
    from services.workspace import UserMemory

    content = input.get("content", "").strip()
    if not content:
        return {"success": False, "error": "empty_content", "message": "Content cannot be empty"}

    entry_type = input.get("entry_type", "fact")
    if entry_type not in ("fact", "preference", "instruction"):
        entry_type = "fact"

    try:
        um = UserMemory(auth.client, auth.user_id)

        # Dedup check: don't add if already exists
        existing_notes = await um.get_notes()
        if any(n["content"].lower().strip() == content.lower().strip() for n in existing_notes):
            return {
                "success": True,
                "already_exists": True,
                "message": f"Already remembered: {content}",
            }

        await um.add_note(entry_type, content)

        # Log to activity_log
        try:
            from services.activity_log import write_activity
            preview = content[:60] + "..." if len(content) > 60 else content
            await write_activity(
                client=auth.client,
                user_id=auth.user_id,
                event_type="memory_written",
                summary=f"Noted: {preview}",
                metadata={"type": entry_type, "source": "user_stated"},
            )
        except Exception:
            pass  # Non-fatal

        return {
            "success": True,
            "message": f"Remembered: {content}",
            "entry_type": entry_type,
        }

    except Exception as e:
        logger.error(f"[SaveMemory] Failed for user {auth.user_id[:8]}: {e}")
        return {"success": False, "error": "save_failed", "message": str(e)}
