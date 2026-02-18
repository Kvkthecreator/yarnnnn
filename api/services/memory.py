"""
Unified Memory Service — ADR-064

Backend service for implicit memory extraction from multiple sources.
Replaces explicit TP memory tools with boundary-triggered extraction.

Write sources:
  - Conversation: extracted at session end via process_conversation()
  - Deliverable feedback: extracted when user approves edited version
  - Activity patterns: extracted by daily background job

Read:
  - get_for_prompt(): formats memories for TP system prompt injection
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Extraction model — use fast model for cost efficiency
EXTRACTION_MODEL = os.getenv("MEMORY_EXTRACTION_MODEL", "claude-3-haiku-20240307")

# Minimum messages to trigger extraction
MIN_MESSAGES_FOR_EXTRACTION = 3


class MemoryService:
    """
    Unified memory extraction and persistence.

    Replaces explicit TP memory tools with implicit extraction
    at pipeline boundaries.
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

        Called at session end (timeout or explicit close).
        Uses LLM to identify facts worth remembering.

        Args:
            client: Supabase client (service role)
            user_id: User ID
            messages: Conversation messages (role, content)
            session_id: Session ID for logging

        Returns:
            Number of memories written
        """
        # Skip if too few messages
        user_messages = [m for m in messages if m.get("role") == "user"]
        if len(user_messages) < MIN_MESSAGES_FOR_EXTRACTION:
            logger.debug(f"[memory] Skipping extraction: only {len(user_messages)} user messages")
            return 0

        # Build conversation text for extraction
        conversation_text = self._format_conversation(messages)

        # Extract facts via LLM
        facts = await self._extract_facts(conversation_text)

        if not facts:
            logger.debug(f"[memory] No facts extracted from session {session_id}")
            return 0

        # Write to user_context
        written = 0
        for fact in facts:
            success = await self._write_memory(
                client=client,
                user_id=user_id,
                key=fact["key"],
                value=fact["value"],
                source="conversation",
                confidence=fact.get("confidence", 0.8),
            )
            if success:
                written += 1

        logger.info(f"[memory] Extracted {written} memories from session {session_id}")
        return written

    async def process_feedback(
        self,
        client,
        user_id: str,
        deliverable_id: str,
        original: str,
        edited: str,
    ) -> int:
        """
        Learn from user edits to deliverable output.

        Called when user approves an edited version.
        Analyzes diff to identify consistent patterns.

        Args:
            client: Supabase client
            user_id: User ID
            deliverable_id: Deliverable ID
            original: Original generated content
            edited: User-edited content

        Returns:
            Number of memories written
        """
        # Skip if no meaningful edits
        if not original or not edited:
            return 0

        if original.strip() == edited.strip():
            return 0

        # For v1, use simple heuristics
        # Future: LLM-based diff analysis
        patterns = self._analyze_edit_patterns(original, edited)

        if not patterns:
            return 0

        written = 0
        for pattern in patterns:
            success = await self._write_memory(
                client=client,
                user_id=user_id,
                key=pattern["key"],
                value=pattern["value"],
                source="feedback",
                confidence=0.7,
            )
            if success:
                written += 1

        logger.info(f"[memory] Extracted {written} patterns from deliverable {deliverable_id}")
        return written

    async def process_patterns(
        self,
        client,
        user_id: str,
    ) -> int:
        """
        Analyze activity_log for behavioral patterns.

        Called by unified_scheduler (daily job).
        Rule-based pattern detection.

        Args:
            client: Supabase client
            user_id: User ID

        Returns:
            Number of memories written
        """
        # Query recent activity
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        try:
            result = (
                client.table("activity_log")
                .select("event_type, summary, metadata, created_at")
                .eq("user_id", user_id)
                .gte("created_at", since)
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )
            events = result.data or []
        except Exception as e:
            logger.error(f"[memory] Failed to query activity_log: {e}")
            return 0

        if not events:
            return 0

        # Detect patterns
        patterns = self._detect_activity_patterns(events)

        if not patterns:
            return 0

        written = 0
        for pattern in patterns:
            success = await self._write_memory(
                client=client,
                user_id=user_id,
                key=pattern["key"],
                value=pattern["value"],
                source="pattern",
                confidence=0.6,
            )
            if success:
                written += 1

        logger.info(f"[memory] Detected {written} activity patterns for user {user_id}")
        return written

    async def get_for_prompt(
        self,
        client,
        user_id: str,
        token_budget: int = 2000,
    ) -> str:
        """
        Format memories for system prompt injection.

        Called by working_memory.py at session start.

        Args:
            client: Supabase client
            user_id: User ID
            token_budget: Approximate token limit (not strictly enforced)

        Returns:
            Formatted string for TP system prompt
        """
        try:
            result = (
                client.table("user_context")
                .select("key, value, source, confidence")
                .eq("user_id", user_id)
                .order("confidence", desc=True)
                .execute()
            )
            entries = result.data or []
        except Exception as e:
            logger.error(f"[memory] Failed to read user_context: {e}")
            return ""

        if not entries:
            return ""

        return self._format_for_prompt(entries)

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
                # Handle multimodal content
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
                messages=[
                    {"role": "user", "content": prompt + conversation_text}
                ],
            )

            # Parse response
            text = response.content[0].text
            import json

            # Handle potential markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            return data.get("facts", [])

        except Exception as e:
            logger.error(f"[memory] Extraction LLM call failed: {e}")
            return []

    def _analyze_edit_patterns(self, original: str, edited: str) -> list[dict]:
        """
        Simple heuristic analysis of edit patterns.

        For v1, detect basic patterns without LLM.
        """
        patterns = []

        # Length change
        orig_len = len(original)
        edit_len = len(edited)

        if edit_len < orig_len * 0.7:
            patterns.append({
                "key": "preference:length",
                "value": "Tends to shorten generated content significantly",
            })
        elif edit_len > orig_len * 1.3:
            patterns.append({
                "key": "preference:length",
                "value": "Tends to expand generated content with more detail",
            })

        # Bullet points added
        orig_bullets = original.count("- ") + original.count("* ")
        edit_bullets = edited.count("- ") + edited.count("* ")

        if edit_bullets > orig_bullets + 3:
            patterns.append({
                "key": "preference:format",
                "value": "Prefers bullet points over prose paragraphs",
            })

        return patterns

    def _detect_activity_patterns(self, events: list[dict]) -> list[dict]:
        """
        Rule-based detection of behavioral patterns from activity log.
        """
        patterns = []

        # Count deliverable runs by day of week
        from collections import Counter

        day_counts = Counter()
        for event in events:
            if event.get("event_type") == "deliverable_run":
                created_at = event.get("created_at", "")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        day_counts[dt.strftime("%A")] += 1
                    except ValueError:
                        pass

        # If clear pattern (one day has 3x more than others)
        if day_counts:
            most_common_day, count = day_counts.most_common(1)[0]
            total = sum(day_counts.values())
            if count > total * 0.5 and count >= 3:
                patterns.append({
                    "key": f"pattern:deliverable_day",
                    "value": f"Typically runs deliverables on {most_common_day}s",
                })

        return patterns

    async def _write_memory(
        self,
        client,
        user_id: str,
        key: str,
        value: str,
        source: str,
        confidence: float,
    ) -> bool:
        """
        Write a memory to user_context with upsert.

        Returns True on success, False on failure.
        """
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "user_id": user_id,
            "key": key,
            "value": value,
            "source": source,
            "confidence": confidence,
            "updated_at": now,
        }

        try:
            # Check if exists
            existing = (
                client.table("user_context")
                .select("id, source, confidence")
                .eq("user_id", user_id)
                .eq("key", key)
                .execute()
            )

            if existing.data:
                # Only update if new confidence is higher or source is more authoritative
                old = existing.data[0]
                source_priority = {"user_stated": 10, "conversation": 5, "feedback": 3, "pattern": 1}
                old_priority = source_priority.get(old["source"], 0)
                new_priority = source_priority.get(source, 0)

                # Don't overwrite user_stated with lower priority
                if old_priority > new_priority:
                    logger.debug(f"[memory] Skipping update: {key} (user_stated takes priority)")
                    return False

                client.table("user_context").update({
                    "value": value,
                    "source": source,
                    "confidence": confidence,
                    "updated_at": now,
                }).eq("id", old["id"]).execute()
            else:
                record["created_at"] = now
                client.table("user_context").insert(record).execute()

            # Log to activity_log
            try:
                from services.activity_log import write_activity

                preview = value[:60] + "..." if len(value) > 60 else value
                await write_activity(
                    client=client,
                    user_id=user_id,
                    event_type="memory_written",
                    summary=f"Noted: {preview}",
                    metadata={"key": key, "source": source},
                )
            except Exception:
                pass  # Non-fatal

            return True

        except Exception as e:
            logger.error(f"[memory] Failed to write {key}: {e}")
            return False

    def _format_for_prompt(self, entries: list[dict]) -> str:
        """
        Format user_context entries for system prompt injection.

        Groups by type and formats readably.
        """
        # Categorize entries
        profile = {}
        styles = {}
        facts = []
        instructions = []
        preferences = []

        for entry in entries:
            key = entry["key"]
            value = entry["value"]

            if key in ("name", "role", "company", "timezone", "summary"):
                profile[key] = value
            elif key.startswith("tone_"):
                platform = key.replace("tone_", "")
                styles.setdefault(platform, {})["tone"] = value
            elif key.startswith("verbosity_"):
                platform = key.replace("verbosity_", "")
                styles.setdefault(platform, {})["verbosity"] = value
            elif key.startswith("fact:"):
                facts.append(value)
            elif key.startswith("instruction:"):
                instructions.append(value)
            elif key.startswith("preference:"):
                preferences.append(value)
            elif key.startswith("pattern:"):
                facts.append(value)  # Patterns are facts about behavior

        # Build output
        sections = []

        # About you
        if profile:
            lines = []
            if profile.get("name") or profile.get("role"):
                name_role = f"{profile.get('name', 'User')}"
                if profile.get("role"):
                    name_role += f" ({profile['role']})"
                if profile.get("company"):
                    name_role += f" at {profile['company']}"
                lines.append(name_role)
            if profile.get("timezone"):
                lines.append(f"Timezone: {profile['timezone']}")
            if profile.get("summary"):
                lines.append(profile["summary"])
            if lines:
                sections.append("### About you\n" + "\n".join(lines))

        # Preferences (styles)
        if styles:
            lines = []
            for platform, settings in styles.items():
                parts = []
                if settings.get("tone"):
                    parts.append(f"tone: {settings['tone']}")
                if settings.get("verbosity"):
                    parts.append(f"verbosity: {settings['verbosity']}")
                if parts:
                    lines.append(f"- {platform}: {', '.join(parts)}")
            if lines:
                sections.append("### Your preferences\n" + "\n".join(lines))

        # What you've told me (facts + instructions + preferences)
        noted = []
        for inst in instructions:
            noted.append(f"- Instruction: {inst}")
        for pref in preferences:
            noted.append(f"- Preference: {pref}")
        for fact in facts:
            noted.append(f"- Note: {fact}")

        if noted:
            sections.append("### What you've told me\n" + "\n".join(noted))

        return "\n\n".join(sections)


# Module-level instance for convenience
_service = MemoryService()


async def process_conversation(client, user_id: str, messages: list[dict], session_id: str) -> int:
    """Extract memories from a completed conversation."""
    return await _service.process_conversation(client, user_id, messages, session_id)


async def process_feedback(client, user_id: str, deliverable_id: str, original: str, edited: str) -> int:
    """Learn from user edits to deliverable output."""
    return await _service.process_feedback(client, user_id, deliverable_id, original, edited)


async def process_patterns(client, user_id: str) -> int:
    """Analyze activity patterns for a user."""
    return await _service.process_patterns(client, user_id)


async def get_for_prompt(client, user_id: str, token_budget: int = 2000) -> str:
    """Format memories for system prompt injection."""
    return await _service.get_for_prompt(client, user_id, token_budget)


async def extract_from_text_to_user_context(user_id: str, text: str, db_client) -> int:
    """
    Extract memories from user-provided text (bulk import).

    This is the entry point for the /context/bulk-import endpoint.
    Uses the same extraction logic as conversation extraction.

    Args:
        user_id: User ID
        text: Text to extract from
        db_client: Supabase client

    Returns:
        Number of memories written
    """
    # Treat the text as a single "user" message for extraction
    messages = [{"role": "user", "content": text}]
    return await _service.process_conversation(
        client=db_client,
        user_id=user_id,
        messages=messages,
        session_id="bulk_import",
    )
