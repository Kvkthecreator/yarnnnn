"""
PM Coordination — ADR-135: Chat as Coordination Substrate

Unified helper for PM and contributor communication. All significant
autonomous actions write to the project chat session (visible to user)
+ PM decision log (workspace continuity) + activity events (audit trail).

Callers:
  - agent_pulse.py (Tier 3 PM coordination decisions)
  - agent_execution.py (PM headless decisions, contributor completions)
  - agent_execution.py (assembly delivery)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


async def pm_announce(
    client,
    user_id: str,
    project_slug: str,
    agent: dict,
    message: str,
    decision_type: str = "coordination",
    metadata: Optional[dict] = None,
) -> None:
    """Write PM decision to chat session + pm_log.md + activity event.

    This is the single communication path for all PM autonomous decisions.
    The chat message appears in the meeting room timeline attributed to the PM.
    """
    from routes.chat import get_or_create_project_session, append_message
    from services.workspace import ProjectWorkspace, get_agent_slug
    from services.activity_log import write_activity

    agent_slug = get_agent_slug(agent)
    now = datetime.now(timezone.utc)

    # 1. Write to project chat session (user-visible)
    try:
        session = await get_or_create_project_session(client, user_id, project_slug)
        if session and session.get("id"):
            await append_message(
                client,
                session["id"],
                "assistant",
                message,
                metadata={
                    "author_agent_id": agent.get("id"),
                    "author_agent_slug": agent_slug,
                    "author_role": "pm",
                    "autonomous": True,
                    "decision_type": decision_type,
                    **(metadata or {}),
                },
            )
    except Exception as e:
        logger.warning(f"[PM-COORD] Chat message failed (non-fatal): {e}")

    # 2. Append to memory/pm_log.md (workspace continuity)
    try:
        pw = ProjectWorkspace(client, user_id, project_slug)
        log_entry = f"## {now.strftime('%Y-%m-%d %H:%M')} — {decision_type}\n{message}\n\n"
        existing = await pw.read("memory/pm_log.md") or ""
        # Prepend new entry, cap at 10 entries
        entries = [log_entry] + existing.split("\n## ")[1:9] if existing else [log_entry]
        updated = entries[0] + "".join(f"\n## {e}" for e in entries[1:]) if len(entries) > 1 else entries[0]
        await pw.write("memory/pm_log.md", updated, summary=f"PM: {decision_type}")
    except Exception as e:
        logger.warning(f"[PM-COORD] Decision log failed (non-fatal): {e}")

    # 3. Activity event (audit trail)
    try:
        await write_activity(
            client=client,
            user_id=user_id,
            event_type="pm_coordination",
            summary=message[:200],
            event_ref=agent.get("id"),
            metadata={
                "project_slug": project_slug,
                "decision_type": decision_type,
                "agent_slug": agent_slug,
                **(metadata or {}),
            },
        )
    except Exception:
        pass  # Non-fatal


async def contributor_report(
    client,
    user_id: str,
    project_slug: str,
    agent: dict,
    message: str,
    metadata: Optional[dict] = None,
) -> None:
    """Write contributor completion message to chat session.

    Appears in the meeting room timeline attributed to the contributor agent.
    """
    from routes.chat import get_or_create_project_session, append_message
    from services.workspace import get_agent_slug

    agent_slug = get_agent_slug(agent)

    try:
        session = await get_or_create_project_session(client, user_id, project_slug)
        if session and session.get("id"):
            await append_message(
                client,
                session["id"],
                "assistant",
                message,
                metadata={
                    "author_agent_id": agent.get("id"),
                    "author_agent_slug": agent_slug,
                    "author_role": agent.get("role", "briefer"),
                    "autonomous": True,
                    "event": "run_complete",
                    **(metadata or {}),
                },
            )
    except Exception as e:
        logger.warning(f"[CONTRIB-COORD] Chat message failed (non-fatal): {e}")


async def read_pm_log(client, user_id: str, project_slug: str, max_entries: int = 5) -> str:
    """Read last N PM decisions from pm_log.md for context injection."""
    from services.workspace import ProjectWorkspace

    try:
        pw = ProjectWorkspace(client, user_id, project_slug)
        log = await pw.read("memory/pm_log.md")
        if not log:
            return ""
        # Return last N entries
        entries = log.split("\n## ")
        return "\n## ".join(entries[:max_entries + 1])  # +1 for first entry without ##
    except Exception:
        return ""
