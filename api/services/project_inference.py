"""
Work Inference — ADR-138

Single Sonnet call that reads user context (uploaded docs + text description)
and infers agents + tasks to create.

Agent = WHO (persistent domain expert with identity + capabilities)
Task = WHAT (work definition with objective, cadence, delivery)

Callers:
  - POST /api/memory/user/onboarding (onboarding submit)
  - Could also be called from TP CreateTask for conversation-driven creation
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

The system has two entities:
- **Agent** = WHO — a persistent domain expert (e.g., "Market Intelligence", "Team Observer")
- **Task** = WHAT — a defined unit of recurring work assigned to an agent

Read the user's context and infer what agents and tasks to create.

USER CONTEXT:
{context}

Identify 1-3 tasks the user needs. Each task gets ONE agent.

Respond with ONLY a JSON object:
{{
  "tasks": [
    {{
      "task_title": "specific task name (e.g., 'Weekly Competitive Intelligence Briefing')",
      "agent_title": "agent domain identity (e.g., 'Market Intelligence')",
      "agent_role": "monitor|researcher|producer|operator",
      "agent_instructions": "1-2 sentences describing the agent's domain expertise",
      "objective": {{
        "deliverable": "what gets produced",
        "audience": "who receives it",
        "format": "document|briefing|alert|report",
        "purpose": "why this matters — use the user's actual context"
      }},
      "success_criteria": ["specific criterion", "another criterion"],
      "output_spec": ["section 1", "section 2", "section 3"],
      "cadence": "daily|weekly|biweekly|monthly"
    }}
  ],
  "brand": {{
    "name": "company or brand name (if mentioned)",
    "tone": "communication tone (inferred from context)"
  }},
  "user_context": "1-sentence summary of what this user does"
}}

AGENT ROLES:
- **monitor**: Watches a domain, alerts on changes (Slack recaps, competitor tracking)
- **researcher**: Deep investigation, produces analysis (market research, due diligence)
- **producer**: Creates deliverables from context (reports, updates, presentations)
- **operator**: Takes actions on platforms (future — don't use yet)

RULES:
- Extract REAL names, competitors, topics from their documents
- Each task gets exactly 1 agent — the agent handles the full thinking chain
- If only 1 task is clear, return just 1 — don't invent work that isn't there
- Cadence should match the work rhythm (daily for monitoring, weekly for analysis)
- success_criteria should be SPECIFIC to their context, not generic"""

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
