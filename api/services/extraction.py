"""
Context Extraction Service

Extracts semantic blocks from conversations and text using LLM.
Designed for fire-and-forget async execution.
"""

import json
import hashlib
from datetime import datetime
from typing import Optional
from uuid import UUID

from anthropic import Anthropic

# Extraction prompt - tuned for precision over recall
EXTRACTION_PROMPT = """Analyze the following content and extract important context items that would be useful to remember for future work on this project.

For each item, provide:
- type: One of [fact, guideline, requirement, insight, question]
  - fact: Verified information about the project, people, or domain
  - guideline: Rules, principles, or preferences to follow
  - requirement: Must-have constraints or specifications
  - insight: Derived understanding or conclusions
  - question: Open questions that need answers
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


async def extract_blocks_from_text(
    text: str,
    model: str = "claude-3-haiku-20240307"
) -> list[dict]:
    """
    Use LLM to extract semantic blocks from text.

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
        valid_types = {"fact", "guideline", "requirement", "insight", "question", "note"}
        validated = []
        for item in extracted:
            if isinstance(item, dict) and "type" in item and "content" in item:
                item["type"] = item["type"] if item["type"] in valid_types else "note"
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
    messages: list[dict],
    db_client,
    source_type: str = "chat",
    source_ref: Optional[str] = None
) -> int:
    """
    Extract context blocks from a conversation and save to database.

    Args:
        project_id: Project UUID
        messages: List of {role, content} message dicts
        db_client: Supabase client with auth
        source_type: Source identifier (chat, import)
        source_ref: Optional reference UUID (session_id, import_id)

    Returns:
        Number of blocks extracted
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
        # Extract blocks
        extracted = await extract_blocks_from_text(text)

        if not extracted:
            # Log empty extraction
            await log_extraction(
                db_client, project_id, source_type, source_ref,
                "completed", 0, None, start_time
            )
            return 0

        # Get existing blocks for deduplication
        existing = db_client.table("blocks")\
            .select("content")\
            .eq("project_id", project_id)\
            .execute()

        existing_hashes = {content_hash(b["content"]) for b in (existing.data or [])}

        # Insert new blocks (skip duplicates)
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
                "source_type": source_type,
                "source_ref": source_ref,
                "importance": item["importance"],
                "metadata": {"extraction_model": "claude-3-haiku-20240307"}
            }).execute()

            existing_hashes.add(item_hash)
            inserted += 1

        # Log successful extraction
        await log_extraction(
            db_client, project_id, source_type, source_ref,
            "completed", inserted, None, start_time
        )

        return inserted

    except Exception as e:
        # Log failed extraction
        await log_extraction(
            db_client, project_id, source_type, source_ref,
            "failed", 0, str(e), start_time
        )
        raise


async def extract_from_bulk_text(
    project_id: str,
    text: str,
    db_client
) -> int:
    """
    Extract context blocks from bulk text input.

    Args:
        project_id: Project UUID
        text: Raw text to extract from
        db_client: Supabase client with auth

    Returns:
        Number of blocks extracted
    """
    start_time = datetime.utcnow()

    try:
        # Extract blocks
        extracted = await extract_blocks_from_text(text)

        if not extracted:
            await log_extraction(
                db_client, project_id, "bulk", None,
                "completed", 0, None, start_time
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
            "completed", inserted, None, start_time
        )

        return inserted

    except Exception as e:
        await log_extraction(
            db_client, project_id, "bulk", None,
            "failed", 0, str(e), start_time
        )
        raise


async def log_extraction(
    db_client,
    project_id: str,
    source_type: str,
    source_ref: Optional[str],
    status: str,
    items_extracted: int,
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
            "error_message": error_message,
            "duration_ms": duration_ms
        }).execute()
    except Exception as e:
        # Don't fail the main operation if logging fails
        print(f"Failed to log extraction: {e}")
