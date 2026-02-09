"""
Memory Extraction Service

ADR-005: Unified memory with embeddings.
Extracts memories from conversations and text using LLM.
Uses emergent structure (tags/entities) instead of forced categories.
"""

import json
import hashlib
import re
from datetime import datetime
from typing import Optional

from anthropic import Anthropic
from services.embeddings import get_embedding, get_embeddings_batch


# =============================================================================
# EXTRACTION PROMPT (ADR-005: Emergent Structure)
# =============================================================================

EXTRACTION_PROMPT = """Analyze this content and extract distinct memories (facts, insights, preferences, or important information).

For each memory:
1. content: The specific fact, insight, preference, or information (1-2 sentences, concise)
2. scope: "user" (true across all projects) or "project" (specific to this work)
3. tags: 2-5 descriptive tags (lowercase, no spaces, e.g., "deadline", "preference", "client")
4. entities: People, companies, or concepts mentioned
5. importance: 0.0-1.0 (how critical is this information?)

## SCOPE Classification Guide

USER scope (portable, about the person):
- Personal preferences: "Prefers bullet points over prose"
- Business facts: "Works at a B2B SaaS startup"
- Work patterns: "Usually writes reports on Fridays"
- Goals: "Raising Series A funding"
- Professional relationships: "Works closely with Alice on design"

PROJECT scope (task-specific):
- Deadlines: "Report due Tuesday"
- Requirements: "Must include executive summary"
- Client/stakeholder info: "Client is Acme Corp"
- Project facts: "Target audience is CTOs"
- Assumptions: "Assuming 3-week timeline"

## Rules
- Only extract genuinely useful, specific information
- Skip greetings, acknowledgments, and filler
- Be conservative with user scope - prefer project unless clearly user-level
- Tags should be descriptive and reusable (not unique identifiers)
- Return empty array if nothing worth extracting

Content to analyze:
---
{content}
---

Return JSON:
{{
  "memories": [
    {{
      "content": "Prefers bullet points over prose",
      "scope": "user",
      "tags": ["preference", "formatting", "style"],
      "entities": {{"people": [], "companies": [], "concepts": ["documentation"]}},
      "importance": 0.7
    }},
    {{
      "content": "Report must include executive summary",
      "scope": "project",
      "tags": ["requirement", "deliverable", "report"],
      "entities": {{"people": [], "companies": [], "concepts": ["executive-summary"]}},
      "importance": 0.9
    }}
  ]
}}

Extract:"""


def content_hash(content: str) -> str:
    """Generate hash for deduplication."""
    normalized = content.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


async def extract_memories_from_text(
    text: str,
    model: str = "claude-3-haiku-20240307"
) -> list[dict]:
    """
    Use LLM to extract memories from text.

    Returns list of dicts with: content, scope, tags, entities, importance
    """
    if not text or len(text.strip()) < 50:
        return []

    client = Anthropic()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(content=text[:8000])
            }]
        )

        response_text = response.content[0].text.strip()

        # Handle markdown code blocks (```json, ```, etc.)
        if "```" in response_text:
            # Find content between code blocks
            code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
            if code_block_match:
                response_text = code_block_match.group(1).strip()

        # Try to find JSON object if there's text before/after
        if not response_text.startswith("{"):
            start = response_text.find("{")
            if start != -1:
                # Find matching closing brace
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

        extracted = json.loads(response_text)
        memories = extracted.get("memories", [])

        # Validate and normalize
        validated = []
        for item in memories:
            if not isinstance(item, dict) or "content" not in item:
                continue

            # Normalize scope
            scope = item.get("scope", "project")
            if scope not in ("user", "project"):
                scope = "project"

            # Normalize tags
            tags = item.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            tags = [str(t).lower().strip() for t in tags if t][:5]

            # Normalize entities
            entities = item.get("entities", {})
            if not isinstance(entities, dict):
                entities = {}
            for key in ["people", "companies", "concepts"]:
                if key not in entities:
                    entities[key] = []
                elif not isinstance(entities[key], list):
                    entities[key] = []

            # Normalize importance
            importance = float(item.get("importance", 0.5))
            importance = max(0.0, min(1.0, importance))

            validated.append({
                "content": item["content"],
                "scope": scope,
                "tags": tags,
                "entities": entities,
                "importance": importance
            })

        return validated

    except json.JSONDecodeError as e:
        print(f"Failed to parse extraction response as JSON: {e}")
        try:
            print(f"Response text (first 500 chars): {response_text[:500]}")
        except NameError:
            pass
        return []
    except Exception as e:
        print(f"Extraction failed: {e}")
        return []


async def extract_from_conversation(
    user_id: str,
    messages: list[dict],
    db_client,
    project_id: Optional[str] = None,  # Deprecated: use domain_id
    source_type: str = "chat",
    source_ref: Optional[str] = None,
    domain_id: Optional[str] = None  # ADR-034: Domain for routing
) -> dict:
    """
    Extract memories from conversation and save to database.

    Args:
        user_id: User UUID
        messages: List of {role, content} message dicts
        db_client: Supabase client with auth
        project_id: Deprecated - kept for backwards compatibility
        source_type: Source identifier (chat, import)
        source_ref: Optional reference (session_id)
        domain_id: Domain UUID for routing (ADR-034)

    Returns:
        Dict with user_memories_inserted and domain_memories_inserted counts
    """
    # Format conversation for extraction
    formatted_messages = []
    for msg in messages[-20:]:  # Last 20 messages max
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        if content:
            formatted_messages.append(f"{role}: {content}")

    if not formatted_messages:
        return {"user_memories_inserted": 0, "project_memories_inserted": 0}

    text = "\n\n".join(formatted_messages)

    try:
        # Extract memories
        memories = await extract_memories_from_text(text)

        if not memories:
            return {"user_memories_inserted": 0, "project_memories_inserted": 0}

        # Get existing memories for deduplication
        existing_query = db_client.table("memories")\
            .select("content")\
            .eq("user_id", user_id)\
            .eq("is_active", True)

        # ADR-034: Include all memories for this user for deduplication
        existing_result = existing_query.execute()

        existing_hashes = {content_hash(m["content"]) for m in (existing_result.data or [])}

        # ADR-034: Get or create default domain for user-scoped memories
        default_domain_id = None
        if domain_id is None:
            try:
                default_result = db_client.rpc("get_or_create_default_domain", {
                    "p_user_id": user_id
                }).execute()
                default_domain_id = default_result.data
            except Exception:
                pass  # Will insert with NULL domain_id

        # Prepare memories for insertion
        default_inserted = 0
        domain_inserted = 0

        for mem in memories:
            mem_hash = content_hash(mem["content"])
            if mem_hash in existing_hashes:
                continue

            # ADR-034: Determine domain_id based on scope
            # "user" scope -> default domain (always accessible)
            # "project" scope -> active domain (if provided)
            if mem["scope"] == "user":
                mem_domain_id = default_domain_id
            else:
                mem_domain_id = domain_id if domain_id else default_domain_id

            # Generate embedding
            try:
                embedding = await get_embedding(mem["content"])
            except Exception as e:
                print(f"Failed to generate embedding: {e}")
                embedding = None

            # Build record
            record = {
                "user_id": user_id,
                "domain_id": mem_domain_id,
                "content": mem["content"],
                "tags": mem["tags"],
                "entities": mem["entities"],
                "importance": mem["importance"],
                "source_type": source_type,
                "source_ref": {"session_id": source_ref} if source_ref else None,
            }

            # Add embedding if available (format for pgvector)
            if embedding:
                record["embedding"] = embedding

            # Insert
            try:
                db_client.table("memories").insert(record).execute()
                existing_hashes.add(mem_hash)

                if mem_domain_id == default_domain_id:
                    default_inserted += 1
                else:
                    domain_inserted += 1
            except Exception as e:
                print(f"Failed to insert memory: {e}")

        return {
            "user_memories_inserted": default_inserted,  # Backwards compatible key
            "domain_memories_inserted": domain_inserted
        }

    except Exception as e:
        print(f"Extraction failed: {e}")
        return {"user_memories_inserted": 0, "project_memories_inserted": 0}


async def extract_from_bulk_text(
    user_id: str,
    project_id: str,
    text: str,
    db_client
) -> int:
    """
    Extract memories from bulk text input.

    Args:
        user_id: User UUID
        project_id: Project UUID
        text: Raw text to extract from
        db_client: Supabase client with auth

    Returns:
        Number of memories extracted
    """
    try:
        memories = await extract_memories_from_text(text)

        if not memories:
            return 0

        # Get existing for deduplication
        existing = db_client.table("memories")\
            .select("content")\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .execute()

        existing_hashes = {content_hash(m["content"]) for m in (existing.data or [])}

        inserted = 0
        for mem in memories:
            mem_hash = content_hash(mem["content"])
            if mem_hash in existing_hashes:
                continue

            # For bulk import, use the provided project_id for project-scoped
            mem_project_id = None if mem["scope"] == "user" else project_id

            # Generate embedding
            try:
                embedding = await get_embedding(mem["content"])
            except Exception as e:
                print(f"Failed to generate embedding: {e}")
                embedding = None

            record = {
                "user_id": user_id,
                "project_id": mem_project_id,
                "content": mem["content"],
                "tags": mem["tags"],
                "entities": mem["entities"],
                "importance": mem["importance"],
                "source_type": "bulk",
            }

            if embedding:
                record["embedding"] = embedding

            try:
                db_client.table("memories").insert(record).execute()
                existing_hashes.add(mem_hash)
                inserted += 1
            except Exception as e:
                print(f"Failed to insert memory: {e}")

        return inserted

    except Exception as e:
        print(f"Bulk extraction failed: {e}")
        return 0


async def create_memory_manual(
    user_id: str,
    content: str,
    db_client,
    project_id: Optional[str] = None,
    tags: list[str] = None,
    importance: float = 0.5
) -> dict:
    """
    Create a memory manually (user-entered).

    Args:
        user_id: User UUID
        content: Memory content
        db_client: Supabase client
        project_id: Optional project UUID (None = user-scoped)
        tags: Optional tags
        importance: Importance score (0-1)

    Returns:
        Created memory record
    """
    # Generate embedding
    try:
        embedding = await get_embedding(content)
    except Exception as e:
        print(f"Failed to generate embedding: {e}")
        embedding = None

    record = {
        "user_id": user_id,
        "project_id": project_id,
        "content": content,
        "tags": tags or [],
        "entities": {},
        "importance": importance,
        "source_type": "manual",
    }

    if embedding:
        record["embedding"] = embedding

    result = db_client.table("memories").insert(record).execute()
    return result.data[0] if result.data else None
