"""
Project Inference — ADR-136

Single Haiku call that enriches generic project templates with specific,
actionable content based on user input (text description + uploaded docs).

Called between user input and scaffold_project(). Produces:
- Specific objective (not template interpolation)
- Success criteria (measurable, PM can evaluate against)
- Output specification (components, quality bar)
- Team recommendation (which agent types and why)
- Suggested cadence

Input: user's scope name + optional text description + optional document content
Output: enriched overrides for scaffold_project()
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-haiku-4-5-20251001"
INFERENCE_MAX_TOKENS = 1024


async def infer_project_spec(
    scope_name: str,
    description: str = "",
    document_context: str = "",
) -> dict:
    """Infer specific project specification from user input.

    Returns overrides for scaffold_project():
        {
            objective: {deliverable, audience, format, purpose},
            success_criteria: [str, ...],
            output_spec: {layout_mode, components: [{name, producer, description}], quality_bar: [str, ...]},
            team: [{role, reason}],
            cadence: str,
            assembly_spec: str,
        }

    Falls back to generic defaults if inference fails.
    """
    from services.anthropic import chat_completion

    context_section = ""
    if description:
        context_section += f"\nUser's description: {description}"
    if document_context:
        context_section += f"\nFrom uploaded documents:\n{document_context[:2000]}"

    prompt = f"""You are helping set up a recurring work project for a solo founder.

The user wants to track: "{scope_name}"
{context_section}

Based on this, define a specific, actionable project specification. Be concrete — use real names, numbers, and formats.

Respond with ONLY a JSON object:
{{
  "objective": {{
    "deliverable": "specific deliverable name (e.g., 'Weekly AI Competitive Intelligence Briefing')",
    "audience": "who receives this (e.g., 'Founder', 'Board', 'Team')",
    "format": "output format (e.g., 'Document with charts', 'Email summary', 'Dashboard')",
    "purpose": "why this matters — 1 sentence"
  }},
  "success_criteria": [
    "specific measurable criterion 1",
    "specific measurable criterion 2",
    "specific measurable criterion 3"
  ],
  "output_spec": {{
    "layout_mode": "document or dashboard or presentation",
    "components": [
      {{"name": "section name", "description": "what this section contains"}}
    ],
    "quality_bar": [
      "minimum quality requirement 1",
      "minimum quality requirement 2"
    ]
  }},
  "team": [
    {{"role": "briefer or scout or researcher or analyst or drafter or writer or planner", "reason": "why this type"}}
  ],
  "cadence": "daily or weekly or biweekly or monthly",
  "assembly_spec": "1-2 sentence instruction for how to combine contributor outputs"
}}"""

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": "Generate the project specification."}],
            system=prompt,
            model=INFERENCE_MODEL,
            max_tokens=INFERENCE_MAX_TOKENS,
        )

        # Parse JSON from response
        text = response.strip()
        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            spec = json.loads(text[start:end])
            logger.info(f"[INFERENCE] Inferred project spec for '{scope_name}': {list(spec.keys())}")
            return spec
        else:
            logger.warning(f"[INFERENCE] No JSON found in response for '{scope_name}'")
    except Exception as e:
        logger.warning(f"[INFERENCE] Failed for '{scope_name}': {e}")

    # Fallback: return empty (scaffold_project will use registry defaults)
    return {}


async def enrich_scaffold_params(
    client: Any,
    user_id: str,
    scope_name: str,
    description: str = "",
    document_ids: list[str] = None,
) -> dict:
    """Enrich scaffold_project() parameters with inferred spec.

    Reads uploaded documents if provided, runs inference, returns
    overrides that scaffold_project() accepts.
    """
    # Gather document context if provided
    doc_context = ""
    if document_ids:
        try:
            for doc_id in document_ids[:3]:  # Cap at 3 docs
                result = client.table("filesystem_documents").select(
                    "filename, content"
                ).eq("id", doc_id).eq("user_id", user_id).single().execute()
                if result.data and result.data.get("content"):
                    doc_context += f"\n--- {result.data['filename']} ---\n{result.data['content'][:1000]}\n"
        except Exception as e:
            logger.warning(f"[INFERENCE] Document read failed: {e}")

    spec = await infer_project_spec(scope_name, description, doc_context)
    if not spec:
        return {}

    overrides = {}

    if spec.get("objective"):
        overrides["objective_override"] = spec["objective"]

    if spec.get("cadence"):
        overrides["frequency"] = spec["cadence"]

    if spec.get("assembly_spec"):
        overrides["assembly_spec_override"] = spec["assembly_spec"]

    # Build enriched team from spec
    if spec.get("team"):
        from services.agent_framework import AGENT_TYPES
        contributors = []
        for t in spec["team"]:
            role = t.get("role", "briefer")
            if role not in AGENT_TYPES:
                role = "briefer"
            contributors.append({
                "title_template": f"{scope_name} {AGENT_TYPES[role]['display_name']}",
                "role": role,
                "scope": "cross_platform",
                "frequency": spec.get("cadence", "weekly"),
                "expected_contribution": t.get("reason", f"{role} output"),
            })
        if contributors:
            overrides["contributors_override"] = contributors

    # Store success criteria and output spec for write_project to use
    overrides["_success_criteria"] = spec.get("success_criteria", [])
    overrides["_output_spec"] = spec.get("output_spec", {})

    return overrides
