"""
Context Extraction Service

Extracts semantic blocks from conversations and text using LLM.
Implements ADR-004 dual-stream extraction: User Context + Project Blocks.
Designed for fire-and-forget async execution.
"""

import json
import hashlib
from datetime import datetime
from typing import Optional
from uuid import UUID

from anthropic import Anthropic

# =============================================================================
# DUAL-STREAM EXTRACTION PROMPT (ADR-004)
# =============================================================================

DUAL_EXTRACTION_PROMPT = """Analyze this conversation and extract TWO types of context:

1. USER CONTEXT - Things about the USER that would be true across any project:
   - preference: How they like things done (format, style, presentation)
   - business_fact: About their company/domain (industry, scale, stage)
   - work_pattern: How they work (timing, rhythm, behavior)
   - communication_style: Tone/format preferences (voice, audience-aware)
   - goal: What they're trying to achieve (aspirations, strategy)
   - constraint: Persistent limitations (scarcity, boundaries)
   - relationship: People in their professional orbit (colleagues, mentors)

2. PROJECT CONTEXT - Things specific to THIS task/project:
   - requirement: Must-have for this deliverable
   - fact: Project-specific information
   - guideline: Rules for this project
   - insight: Conclusions about this project
   - question: Open questions/ambiguities
   - assumption: Beliefs to be validated (things taken as true without evidence)

For each item, specify:
- layer: "user" or "project"
- category: the specific classification from above
- key: a unique identifier for user context (for deduplication, e.g., "format_preference", "company_type")
- content: the actual information (1-2 concise sentences)
- importance: 0.0-1.0 (how important; 0.8+ for critical items)
- confidence: 0.0-1.0 (how confident in this extraction; 0.9+ for explicit statements)

Rules:
- Only extract genuinely useful, specific information
- Skip greetings, acknowledgments, and filler
- USER items should be portable truths about the person
- PROJECT items should be task-specific details
- Be conservative with user extraction - prefer project unless clearly user-level
- For user items, generate stable keys that allow deduplication across sessions
- Return empty arrays if nothing worth extracting

Content to analyze:
---
{content}
---

Return JSON with two arrays:
{{
  "user_items": [
    {{"category": "preference", "key": "format_preference", "content": "Prefers bullet points over prose", "importance": 0.8, "confidence": 0.9}}
  ],
  "project_items": [
    {{"category": "requirement", "content": "Report must include executive summary", "importance": 0.9}}
  ]
}}

Extract:"""

# Legacy single-stream prompt (for bulk text import)
EXTRACTION_PROMPT = """Analyze the following content and extract important context items that would be useful to remember for future work on this project.

For each item, provide:
- type: One of [fact, guideline, requirement, insight, question, assumption]
  - fact: Verified information about the project, people, or domain
  - guideline: Rules, principles, or preferences to follow
  - requirement: Must-have constraints or specifications
  - insight: Derived understanding or conclusions
  - question: Open questions that need answers
  - assumption: Beliefs to be validated (taken as true without evidence)
- content: The actual information (1-2 concise sentences)
- importance: 0.0-1.0 (how important to remember; 0.8+ for critical items)

Rules:
- Only extract genuinely useful, specific information
- Skip greetings, acknowledgments, and filler
- Combine related points into single items
- Be concise but preserve key details
- Return empty array if nothing worth extracting

Content to analyze:
---
{content}
---

Return a JSON array of extracted items. Example:
[
  {"type": "requirement", "content": "Report must include executive summary", "importance": 0.9},
  {"type": "fact", "content": "Target audience is C-level executives", "importance": 0.7}
]

Extract:"""


def content_hash(content: str) -> str:
    """Generate hash for deduplication."""
    normalized = content.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


# Valid categories for each layer
USER_CATEGORIES = {"preference", "business_fact", "work_pattern", "communication_style", "goal", "constraint", "relationship"}
PROJECT_TYPES = {"fact", "guideline", "requirement", "insight", "note", "question", "assumption"}


async def extract_dual_stream(
    text: str,
    model: str = "claude-3-haiku-20240307"
) -> dict:
    """
    Use LLM to extract both user context and project blocks from text.

    Returns dict with:
    - user_items: list of user context items
    - project_items: list of project block items
    """
    if not text or len(text.strip()) < 50:
        return {"user_items": [], "project_items": []}

    client = Anthropic()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": DUAL_EXTRACTION_PROMPT.format(content=text[:8000])
            }]
        )

        response_text = response.content[0].text.strip()

        # Handle markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        extracted = json.loads(response_text)

        # Validate user items
        validated_user = []
        for item in extracted.get("user_items", []):
            if isinstance(item, dict) and "category" in item and "content" in item and "key" in item:
                item["category"] = item["category"] if item["category"] in USER_CATEGORIES else "preference"
                item["importance"] = float(item.get("importance", 0.5))
                item["importance"] = max(0.0, min(1.0, item["importance"]))
                item["confidence"] = float(item.get("confidence", 0.8))
                item["confidence"] = max(0.0, min(1.0, item["confidence"]))
                validated_user.append(item)

        # Validate project items
        validated_project = []
        for item in extracted.get("project_items", []):
            if isinstance(item, dict) and "category" in item and "content" in item:
                # Map "category" to "type" for consistency with existing code
                item["type"] = item["category"] if item["category"] in PROJECT_TYPES else "note"
                item["importance"] = float(item.get("importance", 0.5))
                item["importance"] = max(0.0, min(1.0, item["importance"]))
                validated_project.append(item)

        return {
            "user_items": validated_user,
            "project_items": validated_project
        }

    except json.JSONDecodeError:
        print(f"Failed to parse dual extraction response as JSON")
        return {"user_items": [], "project_items": []}
    except Exception as e:
        print(f"Dual extraction failed: {e}")
        return {"user_items": [], "project_items": []}


async def extract_blocks_from_text(
    text: str,
    model: str = "claude-3-haiku-20240307"
) -> list[dict]:
    """
    Use LLM to extract semantic blocks from text (single-stream, project-only).
    Used for bulk text import where user context isn't relevant.

    Returns list of dicts with: type, content, importance
    """
    if not text or len(text.strip()) < 50:
        return []

    client = Anthropic()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(content=text[:8000])  # Limit input
            }]
        )

        # Parse JSON response
        response_text = response.content[0].text.strip()

        # Handle markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        extracted = json.loads(response_text)

        # Validate structure
        validated = []
        for item in extracted:
            if isinstance(item, dict) and "type" in item and "content" in item:
                item["type"] = item["type"] if item["type"] in PROJECT_TYPES else "note"
                item["importance"] = float(item.get("importance", 0.5))
                item["importance"] = max(0.0, min(1.0, item["importance"]))
                validated.append(item)

        return validated

    except json.JSONDecodeError:
        print(f"Failed to parse extraction response as JSON")
        return []
    except Exception as e:
        print(f"Extraction failed: {e}")
        return []


async def extract_from_conversation(
    project_id: str,
    user_id: str,
    messages: list[dict],
    db_client,
    source_type: str = "chat",
    source_ref: Optional[str] = None
) -> dict:
    """
    Extract context from conversation using dual-stream (ADR-004).
    Saves to both user_context and blocks tables.

    Args:
        project_id: Project UUID
        user_id: User UUID (for user_context)
        messages: List of {role, content} message dicts
        db_client: Supabase client with auth
        source_type: Source identifier (chat, import)
        source_ref: Optional reference UUID (session_id, import_id)

    Returns:
        Dict with user_items_inserted and project_items_inserted counts
    """
    start_time = datetime.utcnow()

    # Format conversation for extraction
    formatted_messages = []
    for msg in messages[-20:]:  # Last 20 messages max
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        if content:
            formatted_messages.append(f"{role}: {content}")

    if not formatted_messages:
        return {"user_items_inserted": 0, "project_items_inserted": 0}

    text = "\n\n".join(formatted_messages)

    try:
        # Dual-stream extraction
        extracted = await extract_dual_stream(text)

        user_items = extracted.get("user_items", [])
        project_items = extracted.get("project_items", [])

        if not user_items and not project_items:
            await log_extraction(
                db_client, project_id, source_type, source_ref,
                "completed", 0, 0, None, start_time
            )
            return {"user_items_inserted": 0, "project_items_inserted": 0}

        # ============================================================
        # Save USER CONTEXT items (with upsert on user_id + category + key)
        # ============================================================
        user_inserted = 0
        for item in user_items:
            try:
                # Upsert: if (user_id, category, key) exists, update; else insert
                db_client.table("user_context").upsert({
                    "user_id": user_id,
                    "category": item["category"],
                    "key": item["key"],
                    "content": item["content"],
                    "importance": item["importance"],
                    "confidence": item["confidence"],
                    "source_type": "extracted",
                    "source_project_id": project_id,
                    "updated_at": datetime.utcnow().isoformat()
                }, on_conflict="user_id,category,key").execute()
                user_inserted += 1
            except Exception as e:
                print(f"Failed to upsert user context item: {e}")

        # ============================================================
        # Save PROJECT BLOCKS (with hash deduplication)
        # ============================================================
        existing = db_client.table("blocks")\
            .select("content")\
            .eq("project_id", project_id)\
            .execute()

        existing_hashes = {content_hash(b["content"]) for b in (existing.data or [])}

        project_inserted = 0
        for item in project_items:
            item_hash = content_hash(item["content"])
            if item_hash in existing_hashes:
                continue

            db_client.table("blocks").insert({
                "project_id": project_id,
                "content": item["content"],
                "block_type": "extracted",
                "semantic_type": item["type"],
                "source_type": source_type,
                "source_ref": source_ref,
                "importance": item["importance"],
                "metadata": {"extraction_model": "claude-3-haiku-20240307"}
            }).execute()

            existing_hashes.add(item_hash)
            project_inserted += 1

        # Log successful extraction
        await log_extraction(
            db_client, project_id, source_type, source_ref,
            "completed", project_inserted, user_inserted, None, start_time
        )

        return {
            "user_items_inserted": user_inserted,
            "project_items_inserted": project_inserted
        }

    except Exception as e:
        await log_extraction(
            db_client, project_id, source_type, source_ref,
            "failed", 0, 0, str(e), start_time
        )
        raise


async def extract_from_bulk_text(
    project_id: str,
    text: str,
    db_client
) -> int:
    """
    Extract context blocks from bulk text input (project-only, no user context).

    Args:
        project_id: Project UUID
        text: Raw text to extract from
        db_client: Supabase client with auth

    Returns:
        Number of blocks extracted
    """
    start_time = datetime.utcnow()

    try:
        # Extract blocks (single-stream, project-only)
        extracted = await extract_blocks_from_text(text)

        if not extracted:
            await log_extraction(
                db_client, project_id, "bulk", None,
                "completed", 0, 0, None, start_time
            )
            return 0

        # Get existing blocks for deduplication
        existing = db_client.table("blocks")\
            .select("content")\
            .eq("project_id", project_id)\
            .execute()

        existing_hashes = {content_hash(b["content"]) for b in (existing.data or [])}

        # Insert new blocks
        inserted = 0
        for item in extracted:
            item_hash = content_hash(item["content"])
            if item_hash in existing_hashes:
                continue

            db_client.table("blocks").insert({
                "project_id": project_id,
                "content": item["content"],
                "block_type": "extracted",
                "semantic_type": item["type"],
                "source_type": "bulk",
                "importance": item["importance"],
                "metadata": {"extraction_model": "claude-3-haiku-20240307"}
            }).execute()

            existing_hashes.add(item_hash)
            inserted += 1

        await log_extraction(
            db_client, project_id, "bulk", None,
            "completed", inserted, 0, None, start_time
        )

        return inserted

    except Exception as e:
        await log_extraction(
            db_client, project_id, "bulk", None,
            "failed", 0, 0, str(e), start_time
        )
        raise


# =============================================================================
# USER-ONLY EXTRACTION PROMPT (for global chat without project)
# =============================================================================

USER_ONLY_EXTRACTION_PROMPT = """Analyze this conversation and extract USER CONTEXT - things about the USER that would be true across any project:

Categories:
- preference: How they like things done (format, style, presentation)
- business_fact: About their company/domain (industry, scale, stage)
- work_pattern: How they work (timing, rhythm, behavior)
- communication_style: Tone/format preferences (voice, audience-aware)
- goal: What they're trying to achieve (aspirations, strategy)
- constraint: Persistent limitations (scarcity, boundaries)
- relationship: People in their professional orbit (colleagues, mentors)

For each item, specify:
- category: the specific classification from above
- key: a unique identifier (for deduplication, e.g., "format_preference", "company_type")
- content: the actual information (1-2 concise sentences)
- importance: 0.0-1.0 (how important; 0.8+ for critical items)
- confidence: 0.0-1.0 (how confident in this extraction; 0.9+ for explicit statements)

Rules:
- Only extract genuinely useful, specific information about the USER
- Skip greetings, acknowledgments, and filler
- Items should be portable truths about the person (not task-specific)
- Be conservative - only extract what's clearly about the user themselves
- Generate stable keys that allow deduplication across sessions
- Return empty array if nothing worth extracting

Content to analyze:
---
{content}
---

Return JSON array:
[
  {{"category": "preference", "key": "format_preference", "content": "Prefers bullet points over prose", "importance": 0.8, "confidence": 0.9}}
]

Extract:"""


async def extract_user_only(
    text: str,
    model: str = "claude-3-haiku-20240307"
) -> list[dict]:
    """
    Use LLM to extract user context only from text (no project blocks).
    Used for global chat where there's no project context.

    Returns list of dicts with: category, key, content, importance, confidence
    """
    if not text or len(text.strip()) < 50:
        return []

    client = Anthropic()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": USER_ONLY_EXTRACTION_PROMPT.format(content=text[:8000])
            }]
        )

        response_text = response.content[0].text.strip()

        # Handle markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        extracted = json.loads(response_text)

        # Validate items
        validated = []
        for item in extracted:
            if isinstance(item, dict) and "category" in item and "content" in item and "key" in item:
                item["category"] = item["category"] if item["category"] in USER_CATEGORIES else "preference"
                item["importance"] = float(item.get("importance", 0.5))
                item["importance"] = max(0.0, min(1.0, item["importance"]))
                item["confidence"] = float(item.get("confidence", 0.8))
                item["confidence"] = max(0.0, min(1.0, item["confidence"]))
                validated.append(item)

        return validated

    except json.JSONDecodeError:
        print(f"Failed to parse user-only extraction response as JSON")
        return []
    except Exception as e:
        print(f"User-only extraction failed: {e}")
        return []


async def extract_user_context_only(
    user_id: str,
    messages: list[dict],
    db_client,
    source_type: str = "global_chat",
    source_ref: Optional[str] = None
) -> int:
    """
    Extract user context from conversation (no project blocks).
    Used for global chat where there's no project.

    Args:
        user_id: User UUID
        messages: List of {role, content} message dicts
        db_client: Supabase client with auth
        source_type: Source identifier (global_chat, onboarding)
        source_ref: Optional reference UUID

    Returns:
        Number of user context items inserted/updated
    """
    start_time = datetime.utcnow()

    # Format conversation for extraction
    formatted_messages = []
    for msg in messages[-20:]:  # Last 20 messages max
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        if content:
            formatted_messages.append(f"{role}: {content}")

    if not formatted_messages:
        return 0

    text = "\n\n".join(formatted_messages)

    try:
        # User-only extraction
        user_items = await extract_user_only(text)

        if not user_items:
            # Log with null project_id
            await log_extraction_user_only(
                db_client, user_id, source_type, source_ref,
                "completed", 0, None, start_time
            )
            return 0

        # Save USER CONTEXT items (with upsert on user_id + category + key)
        user_inserted = 0
        for item in user_items:
            try:
                db_client.table("user_context").upsert({
                    "user_id": user_id,
                    "category": item["category"],
                    "key": item["key"],
                    "content": item["content"],
                    "importance": item["importance"],
                    "confidence": item["confidence"],
                    "source_type": "extracted",
                    "source_project_id": None,  # No project for global chat
                    "updated_at": datetime.utcnow().isoformat()
                }, on_conflict="user_id,category,key").execute()
                user_inserted += 1
            except Exception as e:
                print(f"Failed to upsert user context item: {e}")

        # Log successful extraction
        await log_extraction_user_only(
            db_client, user_id, source_type, source_ref,
            "completed", user_inserted, None, start_time
        )

        return user_inserted

    except Exception as e:
        await log_extraction_user_only(
            db_client, user_id, source_type, source_ref,
            "failed", 0, str(e), start_time
        )
        raise


async def log_extraction_user_only(
    db_client,
    user_id: str,
    source_type: str,
    source_ref: Optional[str],
    status: str,
    user_items_extracted: int,
    error_message: Optional[str],
    start_time: datetime
):
    """Log user-only extraction attempt for observability."""
    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    try:
        db_client.table("extraction_logs").insert({
            "project_id": None,  # No project for global chat
            "user_id": user_id,
            "source_type": source_type,
            "source_ref": source_ref,
            "status": status,
            "items_extracted": 0,
            "user_items_extracted": user_items_extracted,
            "error_message": error_message,
            "duration_ms": duration_ms
        }).execute()
    except Exception as e:
        # Don't fail the main operation if logging fails
        print(f"Failed to log user-only extraction: {e}")


async def log_extraction(
    db_client,
    project_id: str,
    source_type: str,
    source_ref: Optional[str],
    status: str,
    items_extracted: int,
    user_items_extracted: int,
    error_message: Optional[str],
    start_time: datetime
):
    """Log extraction attempt for observability."""
    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    try:
        db_client.table("extraction_logs").insert({
            "project_id": project_id,
            "source_type": source_type,
            "source_ref": source_ref,
            "status": status,
            "items_extracted": items_extracted,
            "user_items_extracted": user_items_extracted,
            "error_message": error_message,
            "duration_ms": duration_ms
        }).execute()
    except Exception as e:
        # Don't fail the main operation if logging fails
        print(f"Failed to log extraction: {e}")
