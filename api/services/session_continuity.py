"""
Session Continuity Service — ADR-067, ADR-087 Phase 2

Chat-layer feature for cross-session conversational continuity.
YARNNN equivalent of Claude Code's auto memory (MEMORY.md).

This is NOT backend orchestration — it's a chat-specific feature that
generates prose summaries of completed sessions for context in future sessions.

Write:
  - generate_session_summary(): LLM-generated summary of a session.
    Written to chat_sessions.summary. Called by nightly cron for prior day's sessions.

Read:
  - Summaries read by working_memory._get_recent_sessions() for global sessions.
  - For agent-scoped sessions, read via chat_sessions.agent_id FK
    in working_memory._extract_agent_scope().
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Model for summarization
SUMMARY_MODEL = os.getenv("MEMORY_EXTRACTION_MODEL", "claude-sonnet-4-20250514")

# Minimum user messages for a session to be worth summarizing
MIN_MESSAGES_FOR_SUMMARY = 3


def _format_conversation(messages: list[dict]) -> str:
    """Format conversation messages for the summarization prompt."""
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = [
                p.get("text", "") for p in content if p.get("type") == "text"
            ]
            content = " ".join(text_parts)
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


async def generate_session_summary(
    messages: list[dict],
    session_date: str,
) -> Optional[str]:
    """
    Generate a prose summary of a completed session for cross-session continuity.

    ADR-067 Phase 1: YARNNN equivalent of Claude Code's auto memory (MEMORY.md).
    Called by nightly cron after user_memory extraction for each session.
    Written to chat_sessions.summary; read by working_memory._get_recent_sessions().

    Args:
        messages: Conversation messages (role, content)
        session_date: ISO date string (YYYY-MM-DD) for prefix in summary

    Returns:
        Prose summary string, or None if session too short/empty
    """
    import anthropic

    user_messages = [m for m in messages if m.get("role") == "user"]
    if len(user_messages) < MIN_MESSAGES_FOR_SUMMARY:
        return None

    conversation_text = _format_conversation(messages)

    prompt = """Summarise this conversation in 2-4 sentences for use as context in a future session.

Focus on:
- Decisions made or agreed on
- Work in progress or left unfinished
- Actions taken (agents set up, platform actions executed)
- Anything the user explicitly asked to continue or follow up on

Do NOT include:
- Questions that were fully answered and closed
- General small talk
- Information that won't be relevant next session

Write in past tense, third-person neutral. Be specific and concrete — prefer "settled on 4-section board update format" over "discussed document structure."

CONVERSATION:
"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=256,
            messages=[
                {"role": "user", "content": prompt + conversation_text}
            ],
        )
        summary_text = response.content[0].text.strip()
        if not summary_text:
            return None
        # Prefix with date for working memory rendering
        return f"[{session_date}] {summary_text}"

    except Exception as e:
        logger.error(f"[session_continuity] Session summary LLM call failed: {e}")
        return None
