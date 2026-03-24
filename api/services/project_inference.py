"""
Project Inference — ADR-132/136

Single Sonnet call that reads user context (uploaded docs + text description)
and infers complete project scaffolding: multiple scopes, objectives,
success criteria, team composition, output specs.

This is the brain of onboarding. One call extracts everything needed to
scaffold N projects with rich, specific charter content.

Callers:
  - POST /api/memory/user/onboarding (onboarding submit)
  - Could also be called from TP CreateProject for conversation-driven creation
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Use Sonnet for onboarding inference — quality matters more than speed here
INFERENCE_MODEL = "claude-sonnet-4-20250514"
INFERENCE_MAX_TOKENS = 2048


async def infer_work_scopes(
    text_description: str = "",
    document_contents: list[dict] = None,
) -> dict:
    """Infer complete project scaffolding from user context.

    Single Sonnet call. Reads text + document contents → produces
    multiple work scopes with rich specifications.

    Args:
        text_description: What the user typed about their work
        document_contents: [{filename, content}] from uploaded docs

    Returns:
        {
            scopes: [{name, objective, success_criteria, output_spec, team, cadence, assembly_spec}],
            brand: {name, tone},
            user_context: str (1-sentence summary of what user does)
        }
    """
    from services.anthropic import chat_completion

    # Build context from all inputs
    context_parts = []
    if text_description.strip():
        context_parts.append(f"User's description:\n{text_description.strip()}")
    if document_contents:
        for doc in document_contents[:5]:  # Cap at 5 docs
            name = doc.get("filename", "document")
            content = doc.get("content", "")[:3000]  # Cap per doc
            if content:
                context_parts.append(f"--- Uploaded: {name} ---\n{content}")

    if not context_parts:
        return {"scopes": [], "brand": {}, "user_context": ""}

    context = "\n\n".join(context_parts)

    prompt = f"""You are helping a solo founder set up their autonomous work management system.

Read their context carefully and extract the distinct workstreams they need to track.

USER CONTEXT:
{context}

Based on this, identify 1-5 distinct work scopes (projects). Each scope is a recurring area of attention that needs its own team of AI agents.

For each scope, provide a SPECIFIC, ACTIONABLE specification. Use real names, numbers, and formats from the user's context.

Respond with ONLY a JSON object:
{{
  "scopes": [
    {{
      "name": "short project name",
      "objective": {{
        "deliverable": "specific deliverable (e.g., 'Weekly AI Competitive Intelligence Briefing')",
        "audience": "who receives this",
        "format": "document or dashboard or presentation",
        "purpose": "why this matters — 1 sentence using user's actual context"
      }},
      "success_criteria": [
        "specific measurable criterion from their context",
        "another criterion",
        "quality bar statement"
      ],
      "output_spec": {{
        "layout_mode": "document or dashboard or presentation",
        "components": [
          {{"name": "section name", "description": "what this contains"}}
        ]
      }},
      "team": [
        {{"role": "briefer|scout|researcher|analyst|drafter|writer|planner", "reason": "why this type fits"}}
      ],
      "pipeline": [
        {{"step": "step_name", "agent_type": "role", "description": "what this step does"}},
        {{"step": "evaluate", "agent_type": "pm", "mode": "evaluate", "description": "check quality"}},
        {{"step": "deliver", "agent_type": "pm", "mode": "compose", "description": "assemble and deliver"}}
      ],
      "cadence": "daily or weekly or biweekly or monthly",
      "assembly_spec": "1-2 sentence instruction for how to combine outputs"
    }}
  ],
  "brand": {{
    "name": "company or brand name (if mentioned)",
    "tone": "communication tone (inferred from context)"
  }},
  "user_context": "1-sentence summary of what this user does"
}}

IMPORTANT:
- Extract REAL names, competitors, projects, metrics from their documents
- Each scope should have 2-4 success criteria that are SPECIFIC to their context
- Choose agent types that match the work: scout for external tracking, briefer for platform monitoring, researcher for deep investigation, analyst for data tracking, drafter for deliverable production, writer for communications
- If only 1 scope is clear, return just 1 — don't invent scopes that aren't in the context
- Cadence should match the work rhythm (daily for platform monitoring, weekly for analysis, etc.)"""

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": "Analyze the context and extract work scopes."}],
            system=prompt,
            model=INFERENCE_MODEL,
            max_tokens=INFERENCE_MAX_TOKENS,
        )

        # Parse JSON
        text = response.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            logger.info(f"[INFERENCE] Extracted {len(result.get('scopes', []))} scopes")
            return result

        logger.warning("[INFERENCE] No JSON found in response")
    except Exception as e:
        logger.error(f"[INFERENCE] Failed: {e}")

    return {"scopes": [], "brand": {}, "user_context": ""}


async def read_uploaded_documents(
    client: Any,
    user_id: str,
    document_ids: list[str],
) -> list[dict]:
    """Read content from uploaded documents by ID.

    Returns [{filename, content}] for inference input.
    """
    docs = []
    for doc_id in document_ids[:5]:  # Cap at 5
        try:
            result = client.table("filesystem_documents").select(
                "filename, file_type"
            ).eq("id", doc_id).eq("user_id", user_id).single().execute()
            if not result.data:
                continue

            # Read content from chunks (documents are chunked on upload)
            chunks_result = client.table("filesystem_chunks").select(
                "content"
            ).eq("document_id", doc_id).order("chunk_index").execute()

            content = "\n".join(c["content"] for c in (chunks_result.data or []) if c.get("content"))
            if content:
                docs.append({
                    "filename": result.data.get("filename", "document"),
                    "content": content,
                })
        except Exception as e:
            logger.warning(f"[INFERENCE] Failed to read doc {doc_id}: {e}")

    return docs
