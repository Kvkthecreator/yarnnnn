"""
Session Continuity Service — ADR-067, ADR-087, ADR-125

Chat-layer feature for cross-session conversational continuity.
YARNNN equivalent of Claude Code's auto memory (MEMORY.md).

This is NOT backend orchestration — it's a chat-specific feature that
generates prose summaries of completed sessions for context in future sessions.

Write:
  - generate_session_summary(): LLM-generated summary of a session.
    Written to chat_sessions.summary. Called by nightly cron for prior day's sessions.
  - generate_project_session_summary(): Author-aware summary for project sessions (ADR-125).

Read:
  - Summaries read by working_memory._get_recent_sessions() for global sessions.
  - ADR-125: Project session summaries read by working_memory for global TP awareness.
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


def _format_conversation_author_aware(messages: list[dict]) -> str:
    """Format conversation with author attribution for project session summaries.

    ADR-125: Project sessions have multiple agent participants.
    Messages carry author_agent_slug in metadata for assistant messages.
    """
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        metadata = msg.get("metadata") or {}

        if isinstance(content, list):
            text_parts = [
                p.get("text", "") for p in content if p.get("type") == "text"
            ]
            content = " ".join(text_parts)

        # Attribute assistant messages to specific agents when available
        if role == "assistant" and metadata.get("author_agent_slug"):
            speaker = metadata["author_agent_slug"]
            agent_role = metadata.get("author_role", "")
            if agent_role:
                speaker = f"{speaker} ({agent_role})"
        elif role == "assistant":
            speaker = "ASSISTANT"
        else:
            speaker = role.upper()

        lines.append(f"{speaker}: {content}")
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


async def generate_project_session_summary(
    messages: list[dict],
    session_date: str,
    project_slug: str,
) -> Optional[str]:
    """
    ADR-125: Generate an author-aware summary for a project session.

    Preserves WHO said/decided what across multiple agent participants.
    Written to chat_sessions.summary for cross-session continuity.

    Args:
        messages: Conversation messages with metadata (author attribution)
        session_date: ISO date string (YYYY-MM-DD)
        project_slug: Project slug for context

    Returns:
        Author-attributed prose summary, or None if too short
    """
    import anthropic

    user_messages = [m for m in messages if m.get("role") == "user"]
    if len(user_messages) < MIN_MESSAGES_FOR_SUMMARY:
        return None

    conversation_text = _format_conversation_author_aware(messages)

    prompt = f"""Summarise this project meeting room conversation in 2-4 sentences.
Project: {project_slug}

This is a multi-participant conversation — the user talks with different agents.
Attribute decisions and actions to the specific participant who made/took them.

Focus on:
- Decisions made and WHO made or agreed on them
- Directives given by user to specific agents
- Work assigned, in progress, or left unfinished
- Quality assessments or steering from PM
- Anything explicitly asked to continue or follow up on

Do NOT include:
- Questions that were fully answered and closed
- General small talk

Write in past tense, third-person. Name participants explicitly — e.g., "User directed slack-agent to focus on action items; PM assessed quality as sufficient and triggered assembly."

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
        return f"[{session_date}] ({project_slug}) {summary_text}"

    except Exception as e:
        logger.error(f"[session_continuity] Project session summary failed: {e}")
        return None
