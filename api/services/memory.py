"""
User Memory Service — ADR-108 + ADR-156

Extracts stable personal facts and persists them as entries in
/memory/notes.md (workspace_files). Read-merge-write pattern ensures
deduplication and document-level coherence.

ADR-156: Nightly cron extraction REMOVED. Primary write path is now
TP calling UpdateContext(target="memory") during conversation.
This module is retained for:
  - extract_from_text_to_user_memory(): bulk import from user-provided text
  - process_conversation(): available for manual/test invocation
  - _extract_facts(): shared LLM extraction logic
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Extraction model — Haiku is sufficient for fact extraction from conversations
EXTRACTION_MODEL = os.getenv("MEMORY_EXTRACTION_MODEL", "claude-haiku-4-5-20251001")

# Minimum messages to trigger extraction
MIN_MESSAGES_FOR_EXTRACTION = 3


class UserMemoryService:
    """
    User memory extraction and persistence.

    ADR-108: Extracts stable personal facts from conversations and writes them
    to /memory/notes.md via read-merge-write. Deduplicates on content.
    """

    async def process_conversation(
        self,
        client,
        user_id: str,
        messages: list[dict],
        session_id: str,
    ) -> int:
        """
        Extract memories from a completed TP conversation.

        Called by the nightly cron job (unified_scheduler.py, midnight UTC)
        for all sessions from the previous day.
        Uses LLM to identify stable facts, then read-merge-writes to notes.md.

        Returns:
            Number of new memories written
        """
        user_messages = [m for m in messages if m.get("role") == "user"]
        if len(user_messages) < MIN_MESSAGES_FOR_EXTRACTION:
            logger.debug(f"[user_memory] Skipping extraction: only {len(user_messages)} user messages")
            return 0

        conversation_text = self._format_conversation(messages)
        facts = await self._extract_facts(conversation_text)

        if not facts:
            logger.debug(f"[user_memory] No facts extracted from session {session_id}")
            return 0

        # ADR-108: Read-merge-write to /memory/notes.md
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        existing_notes = await um.get_notes()
        existing_contents = {n["content"].lower().strip() for n in existing_notes}

        new_notes = []
        for fact in facts:
            value = fact.get("value", "").strip()
            if not value:
                continue
            # Deduplicate by content
            if value.lower().strip() in existing_contents:
                continue
            # Map key prefix to note type
            key = fact.get("key", "fact:unknown")
            note_type = key.split(":")[0] if ":" in key else "fact"
            if note_type not in ("fact", "instruction", "preference"):
                note_type = "fact"
            new_notes.append({"type": note_type, "content": value})
            existing_contents.add(value.lower().strip())

        if not new_notes:
            logger.debug(f"[user_memory] All extracted facts already exist in notes.md")
            return 0

        # Merge and write
        merged = existing_notes + new_notes
        await um.replace_notes(merged)

        # Log to activity_log
        try:
            from services.activity_log import write_activity
            for note in new_notes:
                preview = note["content"][:60] + "..." if len(note["content"]) > 60 else note["content"]
                await write_activity(
                    client=client,
                    user_id=user_id,
                    event_type="memory_written",
                    summary=f"Noted: {preview}",
                    metadata={"type": note["type"], "source": "tp_extracted"},
                )
        except Exception:
            pass  # Non-fatal

        logger.info(f"[user_memory] Extracted {len(new_notes)} new memories from session {session_id}")
        return len(new_notes)

    async def get_for_prompt(
        self,
        client,
        user_id: str,
        token_budget: int = 2000,
    ) -> str:
        """
        Format /memory/ files for system prompt injection.

        ADR-108: Reads MEMORY.md + preferences.md + notes.md and concatenates.
        """
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        files = await um.read_all()

        if not files:
            return ""

        sections = []
        for filename in ("MEMORY.md", "style.md", "notes.md"):
            content = files.get(filename, "").strip()
            if content:
                sections.append(content)

        return "\n\n".join(sections)

    # =========================================================================
    # Private methods
    # =========================================================================

    def _format_conversation(self, messages: list[dict]) -> str:
        """Format conversation for extraction prompt."""
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

    async def _extract_facts(self, conversation_text: str) -> list[dict]:
        """
        Use LLM to extract memorable facts from conversation.

        Returns list of {key, value, confidence}.
        """
        import anthropic

        prompt = """Analyze this conversation and extract facts about the user that would be useful to remember for future conversations.

Focus on:
- Stated preferences ("I prefer X over Y")
- Facts about their work ("I'm a product manager at Acme")
- Standing instructions ("Always include a TL;DR")
- Communication style preferences ("Keep responses brief")

Do NOT extract:
- Transient information (today's tasks, current project status)
- Information that changes frequently
- Opinions about specific topics

For each fact, provide:
- key: A short identifier (e.g., "preference:bullet_points", "fact:role", "instruction:tldr")
- value: The fact itself (concise, 1-2 sentences max)
- confidence: 0.0-1.0 how confident this is a stable, useful fact

Respond in JSON format:
{
  "facts": [
    {"key": "preference:format", "value": "Prefers bullet points over prose", "confidence": 0.9},
    ...
  ]
}

If no facts are worth remembering, return {"facts": []}.

CONVERSATION:
"""

        try:
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=EXTRACTION_MODEL,
                max_tokens=1024,
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
                messages=[
                    {"role": "user", "content": prompt + conversation_text}
                ],
            )

            text = response.content[0].text
            import json

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            return data.get("facts", [])

        except Exception as e:
            logger.error(f"[user_memory] Extraction LLM call failed: {e}")
            return []


# Module-level instance for convenience
_service = UserMemoryService()


async def process_conversation(client, user_id: str, messages: list[dict], session_id: str) -> int:
    """Extract stable personal facts from a completed conversation → /memory/notes.md."""
    return await _service.process_conversation(client, user_id, messages, session_id)


async def get_for_prompt(client, user_id: str, token_budget: int = 2000) -> str:
    """Format /memory/ files for system prompt injection."""
    return await _service.get_for_prompt(client, user_id, token_budget)


async def extract_from_text_to_user_memory(user_id: str, text: str, db_client) -> int:
    """
    Extract memories from user-provided text (bulk import).

    This is the entry point for the /context/bulk-import endpoint.
    Uses the same extraction logic as conversation extraction.
    """
    messages = [{"role": "user", "content": text}]
    return await _service.process_conversation(
        client=db_client,
        user_id=user_id,
        messages=messages,
        session_id="bulk_import",
    )
