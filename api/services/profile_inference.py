"""
Profile Inference Service - ADR-058 Knowledge Base Architecture

Infers user profile information from their filesystem content:
- Name and role from email signatures, Slack profiles
- Company from email domains, Slack workspace names
- Timezone from calendar events, message timestamps
- Summary from overall communication patterns

This is triggered:
- After platform sync completes
- Periodically via scheduled job
- On user request ("Refresh" button)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


# =============================================================================
# Profile Inference Prompt
# =============================================================================

PROFILE_INFERENCE_PROMPT = """Analyze the following content samples from a user's work platforms to infer their professional profile.

## Content Samples

{content}

## Instructions

Based on these samples, extract:
1. **name**: Their full name (look for signatures, mentions, "I am", etc.)
2. **role**: Their job title or role (look for signatures, context clues)
3. **company**: Their company or organization (look for email domains, workspace names)
4. **timezone**: Their timezone if determinable (look for calendar events, work hours patterns)
5. **summary**: A 1-2 sentence professional summary describing who they are

## Rules
- Only extract information you're confident about
- Return null for fields you can't determine
- For timezone, use IANA format (e.g., "America/New_York")
- Be conservative - it's better to return null than guess incorrectly

Return JSON:
{{
  "name": "string or null",
  "role": "string or null",
  "company": "string or null",
  "timezone": "string or null",
  "summary": "string or null",
  "confidence": 0.0-1.0
}}

Extract:"""


async def infer_profile_from_filesystem(
    user_id: str,
    client: Any,
    force: bool = False
) -> dict:
    """
    Infer user profile from their filesystem content.

    Args:
        user_id: User UUID
        client: Supabase client
        force: If True, re-infer even if profile was recently inferred

    Returns:
        Dict with inferred profile fields and metadata
    """
    # Check if we should skip (recently inferred)
    if not force:
        existing = client.table("knowledge_profile").select(
            "last_inferred_at"
        ).eq("user_id", user_id).maybe_single().execute()

        if existing.data and existing.data.get("last_inferred_at"):
            last_inferred = datetime.fromisoformat(
                existing.data["last_inferred_at"].replace("Z", "+00:00")
            )
            hours_since = (datetime.now(timezone.utc) - last_inferred).total_seconds() / 3600
            if hours_since < 24:  # Skip if inferred within 24 hours
                logger.info(f"[PROFILE_INFERENCE] Skipping - inferred {hours_since:.1f}h ago")
                return {"skipped": True, "reason": "recently_inferred"}

    # Gather content samples from filesystem
    samples = await _gather_profile_samples(user_id, client)

    if not samples:
        logger.info(f"[PROFILE_INFERENCE] No samples found for user {user_id[:8]}")
        return {"skipped": True, "reason": "no_samples"}

    # Call LLM to infer profile
    inferred = await _infer_profile_llm(samples)

    if not inferred:
        return {"skipped": True, "reason": "inference_failed"}

    # Update knowledge_profile with inferred values
    await _update_profile(user_id, client, inferred)

    logger.info(
        f"[PROFILE_INFERENCE] Updated profile for {user_id[:8]}: "
        f"name={inferred.get('name')}, role={inferred.get('role')}, "
        f"confidence={inferred.get('confidence', 0):.2f}"
    )

    return {
        "success": True,
        "inferred": inferred
    }


async def _gather_profile_samples(user_id: str, client: Any) -> str:
    """
    Gather content samples that might contain profile information.

    Sources:
    - Email signatures (from user-authored sent emails)
    - Slack messages with self-identification
    - Calendar event descriptions (organizer info)
    """
    samples = []

    # Get user-authored emails (sent messages often have signatures)
    try:
        email_result = client.table("filesystem_items").select(
            "content, metadata"
        ).eq(
            "user_id", user_id
        ).eq(
            "platform", "gmail"
        ).eq(
            "is_user_authored", True
        ).order(
            "source_timestamp", desc=True
        ).limit(20).execute()

        for item in email_result.data or []:
            content = item.get("content", "")
            if len(content) > 50:
                samples.append(f"[EMAIL]\n{content[:1000]}")
    except Exception as e:
        logger.warning(f"Failed to fetch emails: {e}")

    # Get user-authored Slack messages
    try:
        slack_result = client.table("filesystem_items").select(
            "content, metadata"
        ).eq(
            "user_id", user_id
        ).eq(
            "platform", "slack"
        ).eq(
            "is_user_authored", True
        ).order(
            "source_timestamp", desc=True
        ).limit(30).execute()

        for item in slack_result.data or []:
            content = item.get("content", "")
            if len(content) > 20:
                samples.append(f"[SLACK]\n{content[:500]}")
    except Exception as e:
        logger.warning(f"Failed to fetch Slack messages: {e}")

    # Get calendar events (may have organizer info)
    try:
        calendar_result = client.table("filesystem_items").select(
            "content, metadata"
        ).eq(
            "user_id", user_id
        ).eq(
            "platform", "calendar"
        ).order(
            "source_timestamp", desc=True
        ).limit(10).execute()

        for item in calendar_result.data or []:
            content = item.get("content", "")
            metadata = item.get("metadata", {})
            if metadata:
                samples.append(f"[CALENDAR]\n{content[:500]}\nMetadata: {metadata}")
    except Exception as e:
        logger.warning(f"Failed to fetch calendar: {e}")

    # Get platform connection metadata (workspace names, email)
    try:
        conn_result = client.table("platform_connections").select(
            "platform, metadata, settings"
        ).eq("user_id", user_id).execute()

        for conn in conn_result.data or []:
            metadata = conn.get("metadata", {})
            settings = conn.get("settings", {})
            if metadata or settings:
                platform = conn.get("platform", "unknown")
                samples.append(f"[PLATFORM: {platform}]\nMetadata: {metadata}\nSettings: {settings}")
    except Exception as e:
        logger.warning(f"Failed to fetch platform connections: {e}")

    return "\n\n---\n\n".join(samples[:30])  # Cap at 30 samples


async def _infer_profile_llm(content: str) -> Optional[dict]:
    """
    Use LLM to infer profile from content samples.
    """
    if not content or len(content) < 100:
        return None

    try:
        anthropic = Anthropic()

        response = anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": PROFILE_INFERENCE_PROMPT.format(content=content[:8000])
            }]
        )

        response_text = response.content[0].text.strip()

        # Parse JSON response
        import json
        import re

        # Handle markdown code blocks
        if "```" in response_text:
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
            if match:
                response_text = match.group(1).strip()

        # Find JSON object
        if not response_text.startswith("{"):
            start = response_text.find("{")
            if start != -1:
                depth = 0
                end = start
                for i, c in enumerate(response_text[start:], start):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                response_text = response_text[start:end]

        return json.loads(response_text)

    except Exception as e:
        logger.error(f"Profile inference LLM failed: {e}")
        return None


async def _update_profile(user_id: str, client: Any, inferred: dict) -> None:
    """
    Update knowledge_profile with inferred values.
    Does not overwrite stated values.
    """
    update_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_inferred_at": datetime.now(timezone.utc).isoformat(),
        "inference_confidence": inferred.get("confidence", 0.5),
    }

    # Only update inferred fields (don't touch stated)
    if inferred.get("name"):
        update_data["inferred_name"] = inferred["name"]
    if inferred.get("role"):
        update_data["inferred_role"] = inferred["role"]
    if inferred.get("company"):
        update_data["inferred_company"] = inferred["company"]
    if inferred.get("timezone"):
        update_data["inferred_timezone"] = inferred["timezone"]
    if inferred.get("summary"):
        update_data["inferred_summary"] = inferred["summary"]

    # Check if profile exists
    existing = client.table("knowledge_profile").select(
        "id"
    ).eq("user_id", user_id).maybe_single().execute()

    if existing.data:
        # Update existing
        client.table("knowledge_profile").update(
            update_data
        ).eq("user_id", user_id).execute()
    else:
        # Create new profile
        update_data["user_id"] = user_id
        client.table("knowledge_profile").insert(update_data).execute()


# =============================================================================
# Trigger Functions
# =============================================================================

async def trigger_profile_inference_after_sync(
    user_id: str,
    platform: str,
    client: Any
) -> None:
    """
    Trigger profile inference after a platform sync completes.
    Called from sync jobs.
    """
    # Only trigger for platforms likely to have profile info
    if platform not in ["gmail", "slack", "calendar"]:
        return

    try:
        await infer_profile_from_filesystem(user_id, client, force=False)
    except Exception as e:
        logger.error(f"Post-sync profile inference failed: {e}")


async def run_profile_inference_batch(client: Any, max_users: int = 50) -> dict:
    """
    Run profile inference for users who haven't been inferred recently.
    Called from scheduled job.
    """
    from datetime import timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Find users with filesystem content but no recent inference
    try:
        # Get users with filesystem items
        users_result = client.table("filesystem_items").select(
            "user_id"
        ).limit(max_users * 2).execute()

        user_ids = list(set(item["user_id"] for item in users_result.data or []))

        processed = 0
        updated = 0

        for user_id in user_ids[:max_users]:
            try:
                result = await infer_profile_from_filesystem(user_id, client, force=False)
                processed += 1
                if result.get("success"):
                    updated += 1
            except Exception as e:
                logger.error(f"Batch inference failed for {user_id[:8]}: {e}")

        return {
            "processed": processed,
            "updated": updated
        }

    except Exception as e:
        logger.error(f"Batch profile inference failed: {e}")
        return {"error": str(e)}
