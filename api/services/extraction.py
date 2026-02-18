"""
Memory Extraction Service

ADR-059: LLM-based inference removed.
extract_from_conversation and extract_from_bulk_text are no-ops.
create_memory_manual writes to user_context table.
"""

from typing import Optional


async def extract_from_conversation(
    user_id: str,
    messages: list[dict],
    db_client,
    project_id: Optional[str] = None,
    source_type: str = "chat",
    source_ref: Optional[str] = None,
    domain_id: Optional[str] = None
) -> dict:
    """
    ADR-059: LLM-based conversation extraction removed.
    TP only knows what the user explicitly states or TP writes via tools.
    """
    return {"user_memories_inserted": 0, "domain_memories_inserted": 0}


async def extract_from_bulk_text(
    user_id: str,
    project_id: str,
    text: str,
    db_client
) -> int:
    """
    ADR-059: LLM-based bulk extraction removed.
    Returns 0 — no auto-inference from text.
    """
    return 0


async def create_memory_manual(
    user_id: str,
    content: str,
    db_client,
    project_id: Optional[str] = None,
    tags: list[str] = None,
    importance: float = 0.5,
    domain_id: Optional[str] = None
) -> dict:
    """
    ADR-059: Write a user-stated memory to user_context.

    Stores under key "fact:{content[:60]}" with source="user_stated".
    """
    import re as _re
    from datetime import datetime as _dt

    safe = _re.sub(r'[^a-zA-Z0-9_ -]', '', content)[:60].strip()
    key = f"fact:{safe}"
    now = _dt.utcnow().isoformat()
    record = {
        "user_id": user_id,
        "key": key,
        "value": content,
        "source": "user_stated",
        "confidence": importance,
        "created_at": now,
        "updated_at": now,
    }
    result = db_client.table("user_context").upsert(record, on_conflict="user_id,key").execute()
    return result.data[0] if result.data else None
