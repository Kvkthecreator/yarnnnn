"""
InferWorkspace Primitive — ADR-235 D1.a

First-act workspace scaffold via combined inference (ADR-190 path). Extracted
from UpdateContext as part of the UpdateContext dissolution (ADR-235).

Cognitive shape: LLM-merged write — runs ONE Sonnet call producing
identity + brand + named entities + work intent. Writes IDENTITY.md and
BRAND.md, delegates entity subfolder creation to ManageDomains(scaffold),
returns a structured scaffold report whose `work_intent_proposal` lets
YARNNN materialize follow-on ManageAgent + FireInvocation calls in the
same conversation turn.

Chat-only.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


INFER_WORKSPACE_TOOL = {
    "name": "InferWorkspace",
    "description": """First-act workspace scaffold (ADR-190).

User just sent rich first-act input — a doc, URL, or description on a
fresh/thin workspace. Runs ONE inference call that produces identity +
brand + named entities + work intent in one pass, writes IDENTITY.md and
BRAND.md, scaffolds entity subfolders across domains, and returns a
scaffold report with a `work_intent_proposal` you can act on in the same
turn via follow-up ManageAgent + FireInvocation tool calls.

Use this when: identity is empty or sparse AND the user has submitted
rich source material (doc, URL, multi-sentence description).

For targeted identity-only or brand-only updates, use InferContext.

At least one of `text`, `document_ids`, or `url_contents` is required.

  InferWorkspace(text="I run a competitive intel shop tracking AI foundation models",
                 document_ids=["<uuid>"])""",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Operator-supplied first-act description (free-form)."
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
        "required": [],
    },
}


async def handle_infer_workspace(auth: Any, input: dict) -> dict:
    """First-act scaffold via combined inference (extracted from UpdateContext._handle_workspace_scaffold).

    Combined inference produces identity + brand + entities + work_intent
    in one call. Writes IDENTITY.md and BRAND.md, delegates entity
    scaffolding to ManageDomains, returns work_intent as a proposal.
    Token usage recorded under caller='inference' (ADR-171).

    Orchestrator stays a context primitive — it does NOT create agents
    or tasks directly. YARNNN reads the returned `work_intent_proposal`
    and materializes via follow-up ManageAgent + FireInvocation calls.
    """
    from services.context_inference import infer_first_act, read_uploaded_documents
    from services.workspace import UserMemory
    from services.primitives.scaffold import _handle_scaffold as _handle_domain_scaffold

    text = input.get("text", "") or ""
    document_ids = input.get("document_ids", []) or []
    url_contents = input.get("url_contents", []) or []

    if not text.strip() and not document_ids and not url_contents:
        return {
            "success": False,
            "error": "empty_input",
            "message": "InferWorkspace requires text, document_ids, or url_contents",
        }

    # Read uploaded document contents (chat passes IDs, we resolve here).
    document_contents = []
    if document_ids:
        try:
            document_contents = await read_uploaded_documents(
                auth.client, auth.user_id, document_ids
            )
        except Exception as e:
            logger.warning(f"[INFER_WORKSPACE] document read failed: {e}")

    inference_result = await infer_first_act(
        text=text,
        document_contents=document_contents,
        url_contents=url_contents,
    )
    usage = inference_result.get("usage", {}) or {}

    # ADR-171: record token usage.
    if usage.get("input_tokens") or usage.get("output_tokens"):
        try:
            from services.platform_limits import record_token_usage
            from services.supabase import get_service_client
            record_token_usage(
                get_service_client(),
                user_id=auth.user_id,
                caller="inference",
                model="claude-sonnet-4-6",
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                metadata={"target": "workspace", "first_act": True},
            )
        except Exception as e:
            logger.warning(f"[INFER_WORKSPACE] token usage record failed: {e}")

    if inference_result.get("error") and not (
        inference_result.get("identity_md")
        or inference_result.get("brand_md")
        or inference_result.get("entities")
    ):
        return {
            "success": False,
            "error": inference_result.get("error"),
            "message": "First-act inference produced no usable content",
        }

    um = UserMemory(auth.client, auth.user_id)
    scaffolded: dict = {
        "identity": "skipped",
        "brand": "skipped",
        "domains": {},
        "entity_count": 0,
    }

    from services.workspace_paths import SHARED_IDENTITY_PATH, SHARED_BRAND_PATH

    identity_md = inference_result.get("identity_md")
    if identity_md:
        ok = await um.write(
            SHARED_IDENTITY_PATH,
            identity_md,
            summary="First-act identity inference",
            authored_by="operator",
            message="infer identity from first-act input",
        )
        scaffolded["identity"] = "written" if ok else "failed"
        if ok:
            logger.info(
                f"[INFER_WORKSPACE] Wrote {SHARED_IDENTITY_PATH} ({len(identity_md)} chars)"
            )

    brand_md = inference_result.get("brand_md")
    if brand_md:
        ok = await um.write(
            SHARED_BRAND_PATH,
            brand_md,
            summary="First-act brand inference",
            authored_by="operator",
            message="infer brand from first-act input",
        )
        scaffolded["brand"] = "written" if ok else "failed"
        if ok:
            logger.info(
                f"[INFER_WORKSPACE] Wrote {SHARED_BRAND_PATH} ({len(brand_md)} chars)"
            )

    entities = inference_result.get("entities") or []
    if entities:
        translated = [
            {
                "domain": e["domain"],
                "slug": e["slug"],
                "name": e["name"],
                "facts": e.get("hints", []),
                "url": "",
            }
            for e in entities
            if e.get("domain") and e.get("slug") and e.get("name")
        ]
        try:
            domain_result = await _handle_domain_scaffold(auth, {"entities": translated})
            scaffolded["domains"] = domain_result.get("scaffolded", {})
            scaffolded["entity_count"] = sum(len(v) for v in scaffolded["domains"].values())
            if domain_result.get("skipped"):
                scaffolded["skipped_entities"] = domain_result["skipped"]
            logger.info(
                f"[INFER_WORKSPACE] domain scaffold: "
                f"{scaffolded['entity_count']} entities / "
                f"{len(scaffolded['domains'])} domains"
            )
        except Exception as e:
            logger.error(f"[INFER_WORKSPACE] domain scaffold failed: {e}")
            scaffolded["domains_error"] = str(e)

    work_intent = inference_result.get("work_intent")
    source_summary = inference_result.get("source_summary", {}) or {}
    source_counts = (
        f"{source_summary.get('doc_count', 0)} doc(s) + "
        f"{source_summary.get('url_count', 0)} URL(s) + "
        f"{'text' if source_summary.get('has_text') else 'no text'}"
    )

    return {
        "success": True,
        "target": "workspace",
        "scaffolded": scaffolded,
        "work_intent_proposal": work_intent,
        "source_summary": source_summary,
        "message": (
            f"Scaffolded from {source_counts}: "
            f"identity={scaffolded['identity']}, "
            f"brand={scaffolded['brand']}, "
            f"entities={scaffolded['entity_count']} across {len(scaffolded['domains'])} domain(s)"
            + (
                f"; work intent: {work_intent.get('kind')}/{work_intent.get('deliverable_type')}"
                if work_intent
                else ""
            )
        ),
    }
