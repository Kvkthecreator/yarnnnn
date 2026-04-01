"""
Context Inference — ADR-144: Inference-First Shared Context

Single inference function for workspace shared context. Reads any combination
of sources (text, documents, URLs, platform content) and produces rich markdown
for IDENTITY.md or BRAND.md.

Replaces enrich_context() from ADR-138/140 onboarding flow.
"""

import json
import logging
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-sonnet-4-20250514"


IDENTITY_SYSTEM = """You are updating a user's workspace identity file (IDENTITY.md).
Read all provided sources carefully. Produce a rich markdown identity document.

OUTPUT FORMAT (use exactly this structure):
# Identity

## Who
[Name], [Role] at [Company]
[Industry/space]. [2-3 sentence context summary of who this person is and what they work on.]

## Domains of Attention
- [Domain 1]: [why this matters to them]
- [Domain 2]: [why this matters to them]

## Work Patterns
- [Pattern 1]: [cadence, what it involves]
- [Pattern 2]: [cadence, what it involves]

## Timezone
[Inferred or stated, e.g., "US Pacific (UTC-8)"]

RULES:
- Extract REAL names, companies, industries from their materials — never fabricate
- Domains = areas of sustained attention (2-5)
- Work patterns = recurring rhythms you can identify (1-5)
- If something isn't mentioned, omit that section entirely
- Be specific — use their actual context, not generic labels
- If existing content is provided, MERGE: preserve information from both old and new sources"""


BRAND_SYSTEM = """You are updating a user's workspace brand file (BRAND.md).
Read all provided sources carefully. Produce a rich markdown brand guide.

OUTPUT FORMAT (use exactly this structure):
# Brand

## Voice
[1-2 sentences describing the communication style — how they sound]

## Tone
[Professional/casual/technical/etc. with nuance and examples]

## Terminology
- [Term]: [how they use it, what it means in their context]
- [Term]: [how they use it]

## Audience
[Who they typically communicate with — investors, engineers, customers, etc.]

## Style Notes
- [Specific observation from their materials about how they write]
- [Another observation]

RULES:
- Extract real voice/tone from their actual writing, not generic descriptions
- Terminology should capture their specific vocabulary
- If they have a company, capture company brand voice (not just personal style)
- If something isn't mentioned, omit that section entirely
- If existing content is provided, MERGE: preserve information from both old and new sources"""


async def infer_shared_context(
    target: Literal["identity", "brand"],
    text: str = "",
    document_contents: Optional[list] = None,
    url_contents: Optional[list] = None,
    existing_content: str = "",
) -> str:
    """Infer workspace shared context from provided sources.

    Returns markdown content for the target workspace file.

    Args:
        target: "identity" or "brand"
        text: Direct text from user (chat message, description)
        document_contents: [{filename, content}] from uploaded documents
        url_contents: [{url, content}] from web search/fetch
        existing_content: Current file content (for merge, not overwrite)

    Returns:
        Markdown string for IDENTITY.md or BRAND.md
    """
    from services.anthropic import chat_completion

    # Assemble source material
    parts = []
    if text.strip():
        parts.append(f"User says:\n{text.strip()}")
    if document_contents:
        for doc in (document_contents or [])[:5]:
            name = doc.get("filename", "document")
            content = doc.get("content", "")[:5000]
            if content:
                parts.append(f"--- Document: {name} ---\n{content}")
    if url_contents:
        for item in (url_contents or [])[:3]:
            url = item.get("url", "")
            content = item.get("content", "")[:3000]
            if content:
                parts.append(f"--- URL: {url} ---\n{content}")
    if not parts:
        logger.warning("[INFERENCE] No source material provided")
        return existing_content or ""

    # Include existing content for merge
    if existing_content and existing_content.strip():
        parts.append(f"--- Existing {target.upper()}.md (merge with this) ---\n{existing_content.strip()}")

    source_material = "\n\n".join(parts)
    system = IDENTITY_SYSTEM if target == "identity" else BRAND_SYSTEM

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": f"Update the {target} file from these sources:\n\n{source_material}"}],
            system=system,
            model=INFERENCE_MODEL,
            max_tokens=2048,
        )
        result = response.strip()
        if result:
            logger.info(f"[INFERENCE] Generated {target} ({len(result)} chars)")
            return result
    except Exception as e:
        logger.error(f"[INFERENCE] Failed for {target}: {e}")

    return existing_content or ""


async def read_uploaded_documents(
    client: Any,
    user_id: str,
    document_ids: list,
) -> list:
    """Read content from uploaded documents by ID.

    Returns [{filename, content}] for inference input.
    """
    docs = []
    for doc_id in (document_ids or [])[:5]:
        try:
            result = client.table("filesystem_documents").select(
                "filename, file_type"
            ).eq("id", doc_id).eq("user_id", user_id).single().execute()
            if not result.data:
                continue

            chunks_result = client.table("filesystem_chunks").select(
                "content"
            ).eq("document_id", doc_id).order("chunk_index").execute()

            content = "\n".join(
                c["content"] for c in (chunks_result.data or []) if c.get("content")
            )
            if content:
                docs.append({
                    "filename": result.data.get("filename", "document"),
                    "content": content,
                })
        except Exception as e:
            logger.warning(f"[INFERENCE] Failed to read doc {doc_id}: {e}")

    return docs
