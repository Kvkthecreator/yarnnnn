"""
Context Inference — ADR-138/140

Workspace-level context enrichment. Reads user-provided documents and text,
infers identity, domain, industry, and work patterns.

This is NOT task creation. This enriches the workspace so TP and agents
have context to work from. Task creation is downstream — via TP conversation.

Two primitives:
  - enrich_context(): Sonnet reads docs + text → identity, brand, domain summary
  - suggest_tasks(): Sonnet reads enriched context → task recommendations (not created)
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-sonnet-4-20250514"


async def enrich_context(
    text_description: str = "",
    document_contents: Optional[list] = None,
) -> dict:
    """Infer workspace context from user-provided materials.

    Returns identity, brand, domain summary — NOT tasks.

    Args:
        text_description: What the user typed about their work
        document_contents: [{filename, content}] from uploaded docs

    Returns:
        {
            identity: {name, role, company, industry, context_summary},
            brand: {name, tone, voice},
            domains: ["domain1", "domain2"],
            work_patterns: ["pattern1", "pattern2"]
        }
    """
    from services.anthropic import chat_completion

    context_parts = []
    if text_description.strip():
        context_parts.append(f"User's description:\n{text_description.strip()}")
    if document_contents:
        for doc in (document_contents or [])[:5]:
            name = doc.get("filename", "document")
            content = doc.get("content", "")[:3000]
            if content:
                context_parts.append(f"--- Uploaded: {name} ---\n{content}")

    if not context_parts:
        return {"identity": {}, "brand": {}, "domains": [], "work_patterns": []}

    context = "\n\n".join(context_parts)

    prompt = f"""You are analyzing a user's work context to understand WHO they are and WHAT they care about.

Read their materials carefully. Extract identity, brand, and domain information.
Do NOT suggest tasks or actions — just understand the context.

USER MATERIALS:
{context}

Respond with ONLY a JSON object:
{{
  "identity": {{
    "name": "their name (if mentioned)",
    "role": "their role (e.g., 'Founder', 'CEO', 'Product Manager')",
    "company": "company name (if mentioned)",
    "industry": "industry or space (e.g., 'AI/ML', 'SaaS', 'E-commerce')",
    "context_summary": "2-3 sentence summary of who this person is and what they do"
  }},
  "brand": {{
    "name": "company or brand name",
    "tone": "communication tone (e.g., 'professional', 'casual', 'technical')",
    "voice": "brand voice description (1 sentence)"
  }},
  "domains": [
    "domain of attention (e.g., 'Competitive Intelligence', 'Team Communication', 'Product Development')"
  ],
  "work_patterns": [
    "recurring pattern (e.g., 'Weekly investor updates', 'Daily team standups', 'Monthly board reporting')"
  ]
}}

RULES:
- Extract REAL names, companies, industries from their documents
- domains = areas of sustained attention (2-5)
- work_patterns = recurring rhythms you can identify (1-5)
- If something isn't mentioned, use null or empty array
- Be specific — use their actual context, not generic labels"""

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": "Analyze the context."}],
            system=prompt,
            model=INFERENCE_MODEL,
            max_tokens=1024,
        )

        text = response.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            logger.info(f"[CONTEXT] Enriched: {len(result.get('domains', []))} domains, "
                        f"{len(result.get('work_patterns', []))} patterns")
            return result

        logger.warning("[CONTEXT] No JSON found in response")
    except Exception as e:
        logger.error(f"[CONTEXT] Enrichment failed: {e}")

    return {"identity": {}, "brand": {}, "domains": [], "work_patterns": []}


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
            logger.warning(f"[CONTEXT] Failed to read doc {doc_id}: {e}")

    return docs
