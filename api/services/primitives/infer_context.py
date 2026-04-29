"""
InferContext Primitive — ADR-235 D1.a

Identity/brand inference-merged write. Extracted from UpdateContext as part
of the UpdateContext dissolution (ADR-235): inference-merged writes deserve
an honest verb name, separate from substrate writes (which use WriteFile)
and lifecycle actions (which use ManageRecurrence).

Cognitive shape: LLM-merged write. The primitive runs Sonnet inference that
merges new operator text + uploaded documents + URL contents with existing
content, then writes the result via the Authored Substrate. Gap detection
(ADR-162 Sub-phase A) runs deterministically on the result, returned as
`gaps` for YARNNN to issue at most one targeted Clarify.

Chat-only (per ADR-235 D1.a — requires LLM-side inference path that lives
in chat dispatch).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


INFER_CONTEXT_TOOL = {
    "name": "InferContext",
    "description": """Run inference-merged write to IDENTITY.md or BRAND.md.

This primitive performs an LLM inference call (Sonnet) that merges new
operator input with existing content. Use when:
- The operator shares who they are (role, domain, background) → target='identity'
- The operator shares brand/voice/style (often from URLs or docs) → target='brand'

Inference merge preserves prior content — nothing is lost. After the merge
runs, deterministic gap detection runs on the result and is returned in
`gaps`. If gaps.severity is "high", consider issuing a Clarify in your
next turn.

For first-act scaffolding (combined identity + brand + entities + work_intent
in one pass), use InferWorkspace instead.

For direct substrate writes (mandate, autonomy, precedent, awareness,
operator-authored content with no inference) use WriteFile against the
canonical path.

Examples:
  InferContext(target='identity',
      text="I'm Sarah, VP Eng at Acme, building ML infrastructure")
  InferContext(target='brand', text="...", url_contents=[{url, content}])
  InferContext(target='identity', text="...", document_ids=["<uuid>"])""",
    "input_schema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "enum": ["identity", "brand"],
                "description": "Which shared-context file to update via inference merge."
            },
            "text": {
                "type": "string",
                "description": "Operator-supplied text to merge with existing content."
            },
            "document_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "UUIDs of uploaded documents. Content is read server-side."
            },
            "url_contents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
                "description": "Content from web pages.",
            },
        },
        "required": ["target", "text"],
    },
}


async def handle_infer_context(auth: Any, input: dict) -> dict:
    """Identity/brand inference-merged write (extracted from UpdateContext._handle_shared_context).

    ADR-162 Sub-phase A: After inference completes, deterministic gap
    detection runs on the result and is returned in `gaps`. Chat reads
    `gaps.single_most_important_gap` and issues at most one targeted Clarify
    if severity is "high".

    Token usage recorded under caller='inference' (ADR-171).
    """
    from services.context_inference import (
        infer_shared_context,
        detect_inference_gaps,
        read_uploaded_documents,
    )
    from services.workspace import UserMemory
    from services.workspace_paths import SHARED_IDENTITY_PATH, SHARED_BRAND_PATH

    target = input.get("target")
    text = input.get("text", "")
    document_ids = input.get("document_ids", []) or []
    url_contents = input.get("url_contents", []) or []

    if target not in ("identity", "brand"):
        return {
            "success": False,
            "error": "invalid_target",
            "message": "target must be 'identity' or 'brand'",
        }
    if not text or not text.strip():
        return {
            "success": False,
            "error": "empty_text",
            "message": "text is required",
        }

    filename = SHARED_IDENTITY_PATH if target == "identity" else SHARED_BRAND_PATH

    try:
        um = UserMemory(auth.client, auth.user_id)
        existing = await um.read(filename)

        document_contents = []
        if document_ids:
            document_contents = await read_uploaded_documents(
                auth.client, auth.user_id, document_ids
            )

        new_content, inference_usage = await infer_shared_context(
            target=target,
            text=text,
            document_contents=document_contents,
            url_contents=url_contents,
            existing_content=existing or "",
        )

        # ADR-171: record token spend.
        if inference_usage.get("input_tokens") or inference_usage.get("output_tokens"):
            try:
                from services.platform_limits import record_token_usage
                from services.supabase import get_service_client
                record_token_usage(
                    get_service_client(),
                    user_id=auth.user_id,
                    caller="inference",
                    model="claude-sonnet-4-6",
                    input_tokens=inference_usage.get("input_tokens", 0),
                    output_tokens=inference_usage.get("output_tokens", 0),
                    metadata={"target": target},
                )
            except Exception as e:
                logger.warning(f"[INFER_CONTEXT] token usage record failed: {e}")

        if not new_content or not new_content.strip():
            return {
                "success": False,
                "error": "inference_empty",
                "message": "Inference produced no content — try providing more detail",
            }

        ok = await um.write(
            filename,
            new_content,
            summary=f"{target.capitalize()} updated via inference",
            authored_by="operator",
            message=f"infer {target}",
        )
        if not ok:
            return {
                "success": False,
                "error": "write_failed",
                "message": f"Failed to write {filename}",
            }

        logger.info(f"[INFER_CONTEXT] Updated {filename} ({len(new_content)} chars)")

        # ADR-162 Sub-phase A: deterministic gap detection (zero LLM cost).
        gap_report = detect_inference_gaps(target=target, inferred_content=new_content)
        if gap_report.get("single_most_important_gap"):
            logger.info(
                f"[INFER_CONTEXT] Gap detected for {target}: "
                f"{gap_report['single_most_important_gap']['field']} "
                f"({gap_report['richness']})"
            )

        return {
            "success": True,
            "target": target,
            "filename": filename,
            "content": new_content,
            "gaps": gap_report,
            "message": f"Updated {filename} successfully",
        }

    except Exception as e:
        logger.error(f"[INFER_CONTEXT] Failed to update {target}: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}
