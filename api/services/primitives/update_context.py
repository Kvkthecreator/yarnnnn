"""
UpdateContext Primitive — ADR-146: Primitive Hardening

Unified context mutation primitive. Replaces 4 separate primitives:
- UpdateSharedContext (identity/brand) → target="identity" | "brand"
- SaveMemory (user notes) → target="memory"
- WriteAgentFeedback (agent preferences) → target="agent"
- WriteTaskFeedback (task specs) → target="task"

Design principle P2 (Inference Over Classification): TP says "this is what I learned,"
infrastructure routes to the correct file. TP picks the target scope (simple enum),
not the destination file (complex classification).
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


UPDATE_CONTEXT_TOOL = {
    "name": "UpdateContext",
    "description": """Update workspace context — shared declarations, memory, agent feedback, task feedback, or the full first-act workspace scaffold.

Call this whenever you learn something worth persisting. Pick the right target:

**target="workspace"** — Rich first-act input (ADR-190). User just sent a doc,
URL, or description on a fresh/thin workspace. Runs ONE inference call that
produces identity + brand + named entities + work intent in one pass, then
writes IDENTITY.md, BRAND.md, and scaffolds entity subfolders across domains.
Returns a scaffold report with a `work_intent_proposal` you can act on
in the same turn via follow-up ManageAgent + ManageTask tool calls.
Use this when: identity is empty or sparse AND the user has submitted rich
source material (doc, URL, multi-sentence description).
  UpdateContext(target="workspace", text="I run a competitive intel
      shop tracking AI foundation models", document_ids=["<uuid>"])

**target="identity"** — User shares who they are (role, domain, background).
Use for targeted updates, not first-act. See "workspace" for first-act.
  UpdateContext(target="identity", text="I'm Sarah, VP Eng at Acme, building ML infrastructure")

**target="brand"** — User shares brand/voice/style (often from URLs or docs)
  UpdateContext(target="brand", text="...", url_contents=[{url, content}])

**target="mandate"** — User declares what this workspace is running
  UpdateContext(target="mandate", text="Run a systematic retail trading operation with explicit signal attribution")

**target="autonomy"** — User declares how much authority the AI may carry
on their behalf
  UpdateContext(target="autonomy", text="...")

**target="precedent"** — User resolves a recurring ambiguity or boundary case
that should compound across future decisions
  UpdateContext(target="precedent", text="If a signal family has fewer than 20 realized outcomes, recommend or clarify instead of auto-executing")

**target="memory"** — User states a fact, preference, or standing instruction
  UpdateContext(target="memory", text="Always include a TL;DR in reports")

**target="agent"** — User gives feedback about an agent's work quality
  UpdateContext(target="agent", agent_slug="research-agent", text="Reports are too long, be more concise")

**target="task"** — User gives feedback about a specific task's output
  UpdateContext(target="task", task_slug="weekly-briefing", text="Charts need better labels")
  UpdateContext(target="task", task_slug="weekly-briefing", text="Focus on pricing", feedback_target="criteria")

**target="awareness"** — Update your situational awareness notes (shift handoff)
  UpdateContext(target="awareness", text="User focused on competitive intel. Two tracking tasks active...")

**target="recurrence"** — Manage a recurrence declaration (ADR-231 D5).
The recurrence declaration is a YAML file at the natural-home substrate
location (e.g., `/workspace/reports/{slug}/_spec.yaml`,
`/workspace/context/{domain}/_recurring.yaml`,
`/workspace/operations/{slug}/_action.yaml`,
`/workspace/_shared/back-office.yaml`). One target, five actions:

  - "create" — write a new declaration (single-decl shapes) or append an
     entry to a multi-decl file (accumulation, maintenance)
  - "update" — merge `changes` into an existing declaration's body
  - "pause" — set `paused: true`
  - "resume" — set `paused: false`
  - "archive" — remove the declaration (delete file or remove entry)

  UpdateContext(target="recurrence", action="create", shape="deliverable",
      slug="market-weekly", body={schedule: "0 9 * * 1", display_name: "Weekly Market Report",
      output_path: "/workspace/reports/market-weekly/{date}/output.md", agents: ["analyst", "writer"]})

  UpdateContext(target="recurrence", action="create", shape="accumulation",
      slug="competitors-weekly-scan", domain="competitors",
      body={schedule: "0 9 * * 1", agent: "researcher", objective: "Weekly competitive moves"})

  UpdateContext(target="recurrence", action="pause", shape="deliverable", slug="market-weekly")
  UpdateContext(target="recurrence", action="resume", shape="deliverable", slug="market-weekly")
  UpdateContext(target="recurrence", action="update", shape="deliverable", slug="market-weekly",
      changes={schedule: "0 9 * * *"})  # change cadence to daily
  UpdateContext(target="recurrence", action="archive", shape="deliverable", slug="market-weekly")

For workspace: combined inference produces identity + brand + entities + work_intent in one call. Scaffolds identity/brand files + entity subfolders. Returns `work_intent_proposal` for you to materialize via ManageAgent + FireInvocation in the same turn.
For identity/brand: inference merges with existing content — nothing is lost.
For mandate/autonomy/precedent: writes the operator's declaration verbatim to the canonical shared substrate file.
For memory: appends (deduped). For agent/task: appends feedback entry.
For awareness: full replacement — write your current understanding as a living document.
For recurrence: read-modify-write of the YAML file via Authored Substrate.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "enum": ["workspace", "mandate", "identity", "brand", "autonomy", "precedent", "memory", "agent", "task", "awareness", "recurrence"],
                "description": "What to update: workspace (first-act scaffold — ADR-190), mandate (MANDATE.md), identity (IDENTITY.md), brand (BRAND.md), autonomy (AUTONOMY.md delegation ceiling), precedent (PRECEDENT.md durable interpretations), memory (notes), agent (agent feedback), task (task feedback), awareness (your situational notes), recurrence (recurrence declaration YAML — ADR-231)"
            },
            "text": {
                "type": "string",
                "description": "The content to persist — what you learned from the user. Required for non-workspace and non-recurrence targets."
            },
            "agent_slug": {
                "type": "string",
                "description": "Required for target='agent'. The agent's slug."
            },
            "task_slug": {
                "type": "string",
                "description": "Required for target='task'. The task's slug."
            },
            "feedback_target": {
                "type": "string",
                "enum": ["deliverable", "criteria", "objective", "output_spec", "run_log"],
                "description": "For target='task': where to route feedback. 'deliverable' (default) writes to feedback.md for DELIVERABLE.md inference. Others patch TASK.md sections directly."
            },
            "document_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "For target='workspace', 'identity', or 'brand': UUIDs of uploaded documents. Content is read server-side — TP does not need to relay document content."
            },
            "url_contents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "content": {"type": "string"}
                    }
                },
                "description": "For target='workspace', 'identity', or 'brand': content from web pages"
            },
            "action": {
                "type": "string",
                "enum": ["create", "update", "pause", "resume", "archive"],
                "description": "For target='recurrence': which lifecycle action to perform. Required for target='recurrence'."
            },
            "shape": {
                "type": "string",
                "enum": ["deliverable", "accumulation", "action", "maintenance"],
                "description": "For target='recurrence': the recurrence shape (drives natural-home path). Required for action='create'; recommended for other actions to avoid path ambiguity."
            },
            "slug": {
                "type": "string",
                "description": "For target='recurrence': the operator-legible nameplate. Required for all recurrence actions."
            },
            "domain": {
                "type": "string",
                "description": "For target='recurrence' + shape='accumulation': the context domain slug (e.g., 'competitors'). Required because accumulation declarations live at /workspace/context/{domain}/_recurring.yaml as multi-entry files."
            },
            "body": {
                "type": "object",
                "description": "For target='recurrence' + action='create': the declaration body. Keys depend on shape: deliverable expects {schedule, output_path, agents, ...}; accumulation expects {schedule, agent, objective, context_writes, ...}; action expects {schedule, target_capability, target_channel, ...}; maintenance expects {executor, schedule, ...}. The slug is added automatically."
            },
            "changes": {
                "type": "object",
                "description": "For target='recurrence' + action='update': partial dict of fields to merge into the existing declaration. e.g., {schedule: '0 9 * * *'} to change cadence."
            },
            "paused_until": {
                "type": "string",
                "description": "For target='recurrence' + action='pause': optional ISO-8601 timestamp. If provided, declaration auto-resumes after this date."
            },
        },
        "required": ["target"]
    }
}


async def handle_update_context(auth: Any, input: dict) -> dict:
    """
    Handle UpdateContext — route to appropriate handler by target.

    ADR-146: Single entry point for all context mutations.
    """
    target = input.get("target")
    text = input.get("text", "").strip()

    # ADR-190 "workspace" target added: rich-input first-act scaffold pass.
    # ADR-207 D2 "mandate" target added: workspace Primary Action declaration.
    # ADR-217 D2 "autonomy" target added: workspace delegation declaration.
    # Shared precedent target added: durable interpretations / boundary cases.
    # ADR-231 D5 "recurrence" target added: recurrence-declaration lifecycle.
    valid_targets = ("mandate", "identity", "brand", "autonomy", "precedent", "memory", "agent", "task", "awareness", "workspace", "recurrence")
    if target not in valid_targets:
        return {"success": False, "error": "invalid_target", "message": f"target must be one of: {', '.join(valid_targets)}"}

    # "workspace" and "recurrence" don't require `text` (recurrence carries `body` or `changes` instead).
    if target not in ("workspace", "recurrence") and not text:
        return {"success": False, "error": "empty_text", "message": "text is required"}

    if target == "workspace":
        return await _handle_workspace_scaffold(auth, input)
    elif target == "mandate":
        return await _handle_mandate(auth, text)
    elif target == "autonomy":
        return await _handle_autonomy(auth, text)
    elif target == "precedent":
        return await _handle_precedent(auth, text)
    elif target in ("identity", "brand"):
        return await _handle_shared_context(auth, target, input)
    elif target == "memory":
        return await _handle_memory(auth, text)
    elif target == "agent":
        return await _handle_agent_feedback(auth, input)
    elif target == "task":
        return await _handle_task_feedback(auth, input)
    elif target == "awareness":
        return await _handle_awareness(auth, text)
    elif target == "recurrence":
        return await _handle_recurrence(auth, input)

    return {"success": False, "error": "unknown_target", "message": f"Unhandled target: {target}"}


async def _handle_mandate(auth: Any, text: str) -> dict:
    """Write workspace MANDATE.md (ADR-207 D2).

    Accepts operator-declared operation content and writes verbatim to
    `/workspace/context/_shared/MANDATE.md`. This is the workspace's
    CLAUDE.md equivalent — declares Primary Action + success criteria +
    boundary conditions. No forced revision cadence; operator edits when
    operator decides. Versioning deferred to ADR-208 (git backend).

    Plain-text write (no inference pass). YARNNN passes the text as
    authored during first-turn operation elicitation or subsequent
    operator-driven revision.
    """
    from services.workspace import UserMemory
    from services.workspace_paths import SHARED_MANDATE_PATH

    um = UserMemory(auth.client, auth.user_id)
    ok = await um.write(
        SHARED_MANDATE_PATH,
        text,
        summary="Mandate authored",
        authored_by="operator",
        message="author mandate",
    )
    if not ok:
        return {"success": False, "error": "write_failed", "message": "Failed to write MANDATE.md"}

    # ADR-231 Phase 3.7: task_derivation registry-based derivation report is
    # dissolved. Per ADR-231 D2/D3, recurrences are operator-authored YAML
    # declarations at natural-home paths — there's no registry to derive from.
    # YARNNN proposes recurrences in conversation grounded in MANDATE.md +
    # context domains; the loop-role coverage check happens through chat
    # rather than a generated derivation report.
    return {
        "success": True,
        "target": "mandate",
        "filename": SHARED_MANDATE_PATH,
        "message": "Mandate authored. Recurrence creation is now unblocked. "
                   "Use UpdateContext(target='recurrence', action='create', ...) "
                   "to author each recurrence aligned with the mandate.",
    }


async def _handle_autonomy(auth: Any, text: str) -> dict:
    """Write workspace AUTONOMY.md (ADR-217 D2).

    Accepts operator-declared delegation content and writes verbatim to
    `/workspace/context/_shared/AUTONOMY.md`. This is the operator's
    standing intent about how autonomous the AI is allowed to be on their
    behalf. Read at reasoning time by the Reviewer dispatcher; read at
    execution time by the task pipeline capability gate.

    Plain-text write (no inference pass). YARNNN passes the text as
    authored during operator conversation about autonomy tuning.

    Revision-chained via ADR-209 Authored Substrate: every edit lands a
    `workspace_file_versions` row with `authored_by=operator`.
    """
    from services.workspace import UserMemory
    from services.workspace_paths import SHARED_AUTONOMY_PATH

    um = UserMemory(auth.client, auth.user_id)
    ok = await um.write(
        SHARED_AUTONOMY_PATH,
        text,
        summary="Autonomy authored",
        authored_by="operator",
        message="author autonomy",
    )
    if not ok:
        return {"success": False, "error": "write_failed", "message": "Failed to write AUTONOMY.md"}

    return {
        "success": True,
        "target": "autonomy",
        "filename": SHARED_AUTONOMY_PATH,
        "message": "Autonomy authored. The Reviewer dispatcher reads this on the "
                   "next proposal. Remember: principles in /workspace/review/principles.md "
                   "can narrow this delegation (add defer conditions) but never widen it — "
                   "the servant can be more conservative than you permit, never more "
                   "permissive. When tightening (e.g. before live-broker flip), edit this "
                   "file alone; the Reviewer will apply the new ceiling at the next verdict.",
    }


async def _handle_precedent(auth: Any, text: str) -> dict:
    """Write workspace PRECEDENT.md.

    Accepts operator-declared durable interpretations and boundary-case
    guidance and writes verbatim to `/workspace/context/_shared/PRECEDENT.md`.
    Use when a chat decision should compound across future runs without
    widening mandate or autonomy.
    """
    from services.workspace import UserMemory
    from services.workspace_paths import SHARED_PRECEDENT_PATH

    um = UserMemory(auth.client, auth.user_id)
    ok = await um.write(
        SHARED_PRECEDENT_PATH,
        text,
        summary="Precedent authored",
        authored_by="operator",
        message="author precedent",
    )
    if not ok:
        return {"success": False, "error": "write_failed", "message": "Failed to write PRECEDENT.md"}

    return {
        "success": True,
        "target": "precedent",
        "filename": SHARED_PRECEDENT_PATH,
        "message": "Precedent recorded. Use this file for durable interpretations "
                   "and boundary-case rules that should compound across future "
                   "decisions without rewriting mandate, autonomy, or reviewer principles.",
    }


async def _handle_workspace_scaffold(auth: Any, input: dict) -> dict:
    """Rich-input first-act scaffold pass (ADR-190).

    Calls `infer_first_act()` which produces identity + brand + entities +
    work_intent from the rich input in ONE LLM call. Writes IDENTITY.md and
    BRAND.md, delegates entity subfolder creation to ManageDomains(scaffold),
    and returns a structured scaffold report that includes a
    `work_intent_proposal` for YARNNN to act on in the same conversation turn
    (via follow-up ManageAgent + ManageTask tool calls).

    The orchestrator writes CONTEXT files; it does not create agents or tasks
    directly. This preserves primitive atomicity (ADR-168) and YARNNN's team
    composition judgment (ADR-176). YARNNN reads the scaffold report and
    decides whether/how to materialize the work_intent_proposal.
    """
    from services.context_inference import infer_first_act, read_uploaded_documents
    from services.workspace import UserMemory
    from services.primitives.scaffold import _handle_scaffold as _handle_domain_scaffold

    text = input.get("text", "") or ""
    document_ids = input.get("document_ids", []) or []
    url_contents = input.get("url_contents", []) or []

    # At least one input channel must have content.
    if not text.strip() and not document_ids and not url_contents:
        return {
            "success": False,
            "error": "empty_input",
            "message": "target='workspace' requires text, document_ids, or url_contents",
        }

    # Read uploaded document contents (TP passes IDs, we resolve here).
    document_contents = []
    if document_ids:
        try:
            document_contents = await read_uploaded_documents(
                auth.client, auth.user_id, document_ids
            )
        except Exception as e:
            logger.warning(f"[WORKSPACE_SCAFFOLD] Document read failed: {e}")

    # Run combined first-act inference.
    inference_result = await infer_first_act(
        text=text,
        document_contents=document_contents,
        url_contents=url_contents,
    )
    usage = inference_result.get("usage", {}) or {}

    # Record token usage (ADR-171).
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
        except Exception as _e:
            logger.warning(f"[TOKEN_USAGE] first-act inference record failed: {_e}")

    # If inference failed entirely, surface the error and stop.
    if inference_result.get("error") and not (
        inference_result.get("identity_md") or inference_result.get("brand_md") or inference_result.get("entities")
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

    # 1. Write IDENTITY.md if produced (ADR-206 relocation to context/_shared/).
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
            logger.info(f"[WORKSPACE_SCAFFOLD] Wrote {SHARED_IDENTITY_PATH} ({len(identity_md)} chars)")

    # 2. Write BRAND.md if produced.
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
            logger.info(f"[WORKSPACE_SCAFFOLD] Wrote {SHARED_BRAND_PATH} ({len(brand_md)} chars)")

    # 3. Scaffold entities into domains (delegate to ManageDomains scaffold).
    entities = inference_result.get("entities") or []
    if entities:
        # `_handle_domain_scaffold` expects entities in its own shape: {domain, slug, name, facts, url}.
        # `infer_first_act` emits {domain, name, slug, hints}. Translate hints → facts.
        translated = [
            {
                "domain": e["domain"],
                "slug": e["slug"],
                "name": e["name"],
                "facts": e.get("hints", []),
                "url": "",  # hints aren't URLs; URL enrichment is a separate concern
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
                f"[WORKSPACE_SCAFFOLD] Domain scaffold: "
                f"{scaffolded['entity_count']} entities / "
                f"{len(scaffolded['domains'])} domains"
            )
        except Exception as e:
            logger.error(f"[WORKSPACE_SCAFFOLD] Domain scaffold failed: {e}")
            scaffolded["domains_error"] = str(e)

    # 4. Package work_intent as a PROPOSAL for YARNNN to act on.
    #    We do NOT call ManageAgent / ManageTask here — that's YARNNN's judgment
    #    call in the same conversation turn. Orchestrator stays a context primitive.
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
        "work_intent_proposal": work_intent,  # None if inference couldn't infer intent
        "source_summary": source_summary,
        "message": (
            f"Scaffolded from {source_counts}: "
            f"identity={scaffolded['identity']}, "
            f"brand={scaffolded['brand']}, "
            f"entities={scaffolded['entity_count']} across {len(scaffolded['domains'])} domain(s)"
            + (f"; work intent: {work_intent.get('kind')}/{work_intent.get('deliverable_type')}" if work_intent else "")
        ),
    }


# ---------------------------------------------------------------------------
# Internal handlers — absorbed from deleted primitives
# ---------------------------------------------------------------------------

async def _handle_shared_context(auth: Any, target: str, input: dict) -> dict:
    """Identity/brand update via inference merge. Was: UpdateSharedContext.

    ADR-162 Sub-phase A: After inference completes, run deterministic gap
    detection on the result and include it in the response payload. TP reads
    `gaps.single_most_important_gap` and issues at most one targeted Clarify
    if severity is "high". This is the post-inference "what's missing" loop
    without introducing a shadow LLM call.
    """
    from services.context_inference import infer_shared_context, detect_inference_gaps, read_uploaded_documents
    from services.workspace import UserMemory

    from services.workspace_paths import SHARED_IDENTITY_PATH, SHARED_BRAND_PATH
    text = input.get("text", "")
    document_ids = input.get("document_ids", [])
    url_contents = input.get("url_contents", [])
    filename = SHARED_IDENTITY_PATH if target == "identity" else SHARED_BRAND_PATH

    try:
        um = UserMemory(auth.client, auth.user_id)
        existing = await um.read(filename)

        # Read document content server-side — TP passes IDs, not content
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

        # ADR-171: Record token spend for this inference call
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
            except Exception as _e:
                logger.warning(f"[TOKEN_USAGE] inference record failed: {_e}")

        if not new_content or not new_content.strip():
            return {"success": False, "error": "inference_empty", "message": "Inference produced no content — try providing more detail"}

        ok = await um.write(
            filename,
            new_content,
            summary=f"{target.capitalize()} updated via inference",
            authored_by="operator",
            message=f"infer {target}",
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"Failed to write {filename}"}

        logger.info(f"[UPDATE_CONTEXT] Updated {filename} ({len(new_content)} chars)")

        # ADR-162 Sub-phase A: Deterministic gap detection on the inference output.
        # Pure Python, zero LLM cost. TP reads `gaps.single_most_important_gap`
        # and decides whether to issue a Clarify in the next turn.
        gap_report = detect_inference_gaps(target=target, inferred_content=new_content)
        if gap_report.get("single_most_important_gap"):
            logger.info(
                f"[UPDATE_CONTEXT] Gap detected for {target}: "
                f"{gap_report['single_most_important_gap']['field']} "
                f"({gap_report['richness']})"
            )

        # ADR-155 revised: No backend inference cascade. TP decides what to scaffold
        # via ManageDomains primitive after processing identity/brand.

        return {
            "success": True,
            "target": target,
            "filename": filename,
            "content": new_content,
            "gaps": gap_report,
            "message": f"Updated {filename} successfully",
        }

    except Exception as e:
        logger.error(f"[UPDATE_CONTEXT] Failed to update {target}: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}


async def _handle_memory(auth: Any, text: str) -> dict:
    """Append user fact/preference/instruction to notes. Was: SaveMemory."""
    from services.workspace import UserMemory

    try:
        um = UserMemory(auth.client, auth.user_id)

        # Dedup check
        existing_notes = await um.get_notes()
        if any(n["content"].lower().strip() == text.lower().strip() for n in existing_notes):
            return {
                "success": True,
                "already_exists": True,
                "message": f"Already remembered: {text}",
            }

        # Infer entry type from content
        entry_type = "fact"
        text_lower = text.lower()
        if any(w in text_lower for w in ("prefer", "always", "never", "like", "don't like")):
            entry_type = "preference"
        if any(w in text_lower for w in ("always include", "never include", "make sure", "when you")):
            entry_type = "instruction"

        await um.add_note(entry_type, text)

        # Activity log
        try:
            from services.activity_log import write_activity
            preview = text[:60] + "..." if len(text) > 60 else text
            await write_activity(
                client=auth.client,
                user_id=auth.user_id,
                event_type="memory_written",
                summary=f"Noted: {preview}",
                metadata={"type": entry_type, "source": "user_stated"},
            )
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Remembered: {text}",
            "entry_type": entry_type,
        }

    except Exception as e:
        logger.error(f"[UPDATE_CONTEXT] Memory save failed: {e}")
        return {"success": False, "error": "save_failed", "message": str(e)}


async def _handle_awareness(auth: Any, text: str) -> dict:
    """Direct write to AWARENESS.md — TP's situational notes. Full replacement."""
    from services.workspace import UserMemory

    try:
        um = UserMemory(auth.client, auth.user_id)

        # Truncate to prevent unbounded growth (2000 chars ≈ 500 tokens)
        content = text.strip()
        if len(content) > 2000:
            content = content[:2000] + "\n\n(truncated — keep awareness notes concise)"

        from services.workspace_paths import MEMORY_AWARENESS_PATH
        ok = await um.write(
            MEMORY_AWARENESS_PATH,
            content,
            summary="YARNNN awareness updated",
            authored_by="yarnnn:chat",
            message="update awareness",
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": "Failed to write AWARENESS.md"}

        logger.info(f"[UPDATE_CONTEXT] AWARENESS.md updated ({len(content)} chars)")
        return {
            "success": True,
            "target": "awareness",
            "filename": "AWARENESS.md",
            "message": "Awareness notes updated",
        }

    except Exception as e:
        logger.error(f"[UPDATE_CONTEXT] Awareness update failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}


async def _handle_agent_feedback(auth: Any, input: dict) -> dict:
    """Write cross-task feedback to agent's workspace memory/feedback.md.

    Agent feedback is style/tone/preference corrections that apply to ALL
    tasks this agent works on. Written to /agents/{slug}/memory/feedback.md
    (agent workspace), not task-scoped feedback.
    """
    from datetime import datetime, timezone

    agent_slug = input.get("agent_slug", "")
    feedback_text = input.get("text", "")

    if not agent_slug:
        return {"success": False, "error": "missing_agent_slug", "message": "agent_slug is required for target='agent'"}

    client = auth.client if not isinstance(auth, dict) else auth["client"]
    user_id = auth.user_id if not isinstance(auth, dict) else auth["user_id"]

    try:
        from services.workspace import AgentWorkspace

        ws = AgentWorkspace(client, user_id, agent_slug)

        # Verify agent exists
        agent_md = await ws.read("AGENT.md")
        if not agent_md:
            return {"success": False, "error": "not_found", "message": f"Agent '{agent_slug}' not found"}

        # Append to agent's memory/feedback.md (cross-task, persistent)
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M")
        entry = f"## Feedback ({date_str}, source: user_conversation)\n- {feedback_text}\n"

        existing = await ws.read("memory/feedback.md") or ""
        if existing.startswith("# Agent Feedback"):
            header_lines = existing.split("\n", 2)
            rest = header_lines[2] if len(header_lines) > 2 else ""
            updated = f"{header_lines[0]}\n{header_lines[1] if len(header_lines) > 1 else ''}\n\n{entry}\n{rest}"
        else:
            updated = f"# Agent Feedback\n\n{entry}\n{existing}"

        ok = await ws.write("memory/feedback.md", updated,
                            summary=f"User feedback: {feedback_text[:50]}")

        if ok:
            # Activity log
            try:
                from services.activity_log import write_activity
                await write_activity(
                    client=client, user_id=user_id,
                    event_type="agent_feedback",
                    summary=f"Feedback for {agent_slug}: {feedback_text[:60]}",
                    metadata={"agent_slug": agent_slug, "source": "conversation"},
                )
            except Exception:
                pass
            return {"success": True, "message": f"Feedback written to {agent_slug} (applies to all tasks)"}
        else:
            return {"success": False, "error": "write_failed", "message": "Failed to write feedback"}

    except Exception as e:
        logger.warning(f"[UPDATE_CONTEXT] Agent feedback failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}


async def _handle_task_feedback(auth: Any, input: dict) -> dict:
    """Write task-specific feedback to feedback.md (default) or TASK.md sections.

    ADR-149/181: feedback_target="deliverable" (default) writes to feedback.md
    (task root) for DELIVERABLE.md inference. Other targets patch TASK.md directly.
    """
    # ADR-231 Phase 3.7: TaskWorkspace dissolved. Feedback flows through
    # natural-home substrate per D2 — declaration walker resolves the
    # feedback path; UpdateContext writes there with ADR-209 attribution.
    # Other feedback_targets (criteria/objective/output_spec) are dissolved:
    # those fields now live in the recurrence YAML's `deliverable:` block
    # and operator updates them via UpdateContext(target='recurrence',
    # action='update', changes={'deliverable': {...}}).
    from datetime import datetime, timezone
    from services.recurrence import walk_workspace_recurrences
    from services.recurrence_paths import resolve_paths
    from services.workspace import UserMemory

    task_slug = input.get("task_slug", "")
    feedback_text = input.get("text", "")
    feedback_target = input.get("feedback_target", "deliverable")

    if not task_slug:
        return {"success": False, "error": "missing_task_slug", "message": "task_slug is required for target='task'"}

    client = auth.client if not isinstance(auth, dict) else auth["client"]
    user_id = auth.user_id if not isinstance(auth, dict) else auth["user_id"]

    decls = walk_workspace_recurrences(client, user_id)
    decl = next((d for d in decls if d.slug == task_slug), None)
    if decl is None:
        return {
            "success": False,
            "error": "no_declaration",
            "message": f"No recurrence declaration for slug '{task_slug}'",
        }

    if feedback_target in ("criteria", "objective", "output_spec"):
        return {
            "success": False,
            "error": "deprecated_target",
            "message": (
                f"feedback_target='{feedback_target}' is dissolved per ADR-231 D5. "
                f"Update the recurrence's deliverable block via UpdateContext"
                f"(target='recurrence', action='update', shape='{decl.shape.value}', "
                f"slug='{task_slug}', changes={{'deliverable': {{...}}}})"
            ),
        }

    paths = resolve_paths(decl)
    if paths.feedback_path is None:
        return {
            "success": False,
            "error": "no_feedback_substrate",
            "message": f"Recurrence shape '{decl.shape.value}' has no feedback substrate",
        }

    relative = paths.feedback_path[len("/workspace/"):] if paths.feedback_path.startswith("/workspace/") else paths.feedback_path
    um = UserMemory(client, user_id)

    try:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M")
        entry = f"## User Feedback ({date_str}, source: user_conversation)\n- {feedback_text}\n"
        existing = await um.read(relative) or ""
        if existing.startswith("# Feedback") or existing.startswith("# Task Feedback"):
            header_lines = existing.split("\n", 2)
            rest = header_lines[2] if len(header_lines) > 2 else ""
            updated = f"{header_lines[0]}\n{header_lines[1] if len(header_lines) > 1 else ''}\n\n{entry}\n{rest}"
        else:
            updated = f"# Feedback\n<!-- Source-agnostic feedback layer. Newest first. ADR-181 + ADR-231 D2. -->\n\n{entry}\n{existing}"
        await um.write(
            relative,
            updated,
            summary=f"User feedback: {feedback_text[:50]}",
            authored_by="operator",
            message="user feedback via UpdateContext(target='task')",
        )
        return {
            "success": True,
            "message": f"Feedback recorded at {paths.feedback_path} (will inform next invocation)",
        }
    except Exception as e:
        logger.warning(f"[UPDATE_CONTEXT] Task feedback failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}


# ---------------------------------------------------------------------------
# ADR-231 D5 — Recurrence declaration lifecycle
# ---------------------------------------------------------------------------


_SHAPE_TO_FILENAME = {
    "deliverable": "_spec.yaml",
    "accumulation": "_recurring.yaml",
    "action": "_action.yaml",
    "maintenance": "back-office.yaml",
}

_SINGLE_DECL_SHAPES = {"deliverable", "action"}
_MULTI_DECL_SHAPES = {"accumulation", "maintenance"}


def _resolve_recurrence_path(shape: str, slug: str, domain: Optional[str]) -> str:
    """Compute the workspace-relative path (no /workspace/ prefix) for a recurrence file.

    UserMemory.write expects paths relative to /workspace/, so we return the
    relative form here.
    """
    if shape == "deliverable":
        return f"reports/{slug}/_spec.yaml"
    if shape == "action":
        return f"operations/{slug}/_action.yaml"
    if shape == "accumulation":
        if not domain:
            raise ValueError("domain required for shape='accumulation'")
        return f"context/{domain}/_recurring.yaml"
    if shape == "maintenance":
        return "_shared/back-office.yaml"
    raise ValueError(f"unknown shape: {shape}")


async def _handle_recurrence(auth: Any, input: dict) -> dict:
    """Manage a recurrence declaration (ADR-231 D5).

    One handler, five actions. Read-modify-write of YAML files via
    UserMemory.write → write_revision (ADR-209 Authored Substrate).

    All writes are attributed `authored_by="yarnnn:..."` because YARNNN
    is the calling Identity per FOUNDATIONS Axiom 2. The model identity
    is resolved via auth.metadata when available; otherwise we use a
    stable fallback marker.
    """
    import yaml as _yaml
    from services.workspace import UserMemory
    from services.recurrence import (
        RecurrenceShape,
        parse_recurrence_yaml,
        serialize_declaration_yaml,
        shape_for_path,
    )

    action = input.get("action")
    shape = input.get("shape")
    slug = input.get("slug")
    domain = input.get("domain")
    body = input.get("body") or {}
    changes = input.get("changes") or {}
    paused_until = input.get("paused_until")

    if action not in {"create", "update", "pause", "resume", "archive"}:
        return {
            "success": False,
            "error": "invalid_action",
            "message": "action must be one of: create, update, pause, resume, archive",
        }
    if not slug:
        return {"success": False, "error": "missing_slug", "message": "slug is required"}
    if shape and shape not in _SHAPE_TO_FILENAME:
        return {
            "success": False,
            "error": "invalid_shape",
            "message": "shape must be one of: deliverable, accumulation, action, maintenance",
        }
    if action == "create" and not shape:
        return {
            "success": False,
            "error": "missing_shape",
            "message": "shape is required for action='create'",
        }
    if shape == "accumulation" and not domain:
        return {
            "success": False,
            "error": "missing_domain",
            "message": "domain is required when shape='accumulation'",
        }

    # Resolve path (shape required for path resolution; if not provided on
    # update/pause/resume/archive, we error — operator-level explicitness wins).
    if not shape:
        return {
            "success": False,
            "error": "missing_shape",
            "message": "shape is required to resolve the declaration path",
        }
    try:
        rel_path = _resolve_recurrence_path(shape, slug, domain)
    except ValueError as e:
        return {"success": False, "error": "invalid_path", "message": str(e)}

    abs_path = f"/workspace/{rel_path}"
    um = UserMemory(auth.client, auth.user_id)
    authored_by = "yarnnn:adr-231"

    # Read current content (may be None for create)
    current = await um.read(rel_path)

    try:
        if shape in _SINGLE_DECL_SHAPES:
            result = await _handle_recurrence_single(
                um=um,
                rel_path=rel_path,
                abs_path=abs_path,
                shape=shape,
                slug=slug,
                action=action,
                body=body,
                changes=changes,
                paused_until=paused_until,
                current=current,
                authored_by=authored_by,
            )
        else:
            result = await _handle_recurrence_multi(
                um=um,
                rel_path=rel_path,
                abs_path=abs_path,
                shape=shape,
                slug=slug,
                action=action,
                body=body,
                changes=changes,
                paused_until=paused_until,
                current=current,
                authored_by=authored_by,
            )
    except Exception as e:
        logger.warning(f"[UPDATE_CONTEXT recurrence] {action} failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}

    # ADR-231 Phase 3.3 — materialize scheduling index after every successful
    # YAML write so the scheduler sees the change on its next tick. The index
    # is fully reconstructable from filesystem; this call is a fast-path
    # optimization, not a correctness requirement. Best-effort.
    if result.get("success"):
        try:
            from services.scheduling import materialize_scheduling_index
            await materialize_scheduling_index(auth.client, auth.user_id)
        except Exception as e:
            logger.warning(
                f"[UPDATE_CONTEXT recurrence] scheduling index materialization failed (non-fatal): {e}"
            )

    return result


async def _handle_recurrence_single(
    *,
    um,
    rel_path: str,
    abs_path: str,
    shape: str,
    slug: str,
    action: str,
    body: dict,
    changes: dict,
    paused_until: Optional[str],
    current: Optional[str],
    authored_by: str,
) -> dict:
    """Handle DELIVERABLE / ACTION shapes — one declaration per file."""
    import yaml as _yaml
    from services.recurrence import parse_recurrence_yaml, serialize_declaration_yaml, RecurrenceDeclaration, RecurrenceShape

    if action == "create":
        if current:
            return {
                "success": False,
                "error": "already_exists",
                "message": f"declaration already exists at {abs_path} (use action='update' to modify)",
            }
        # Ensure slug is in body for round-trip sanity
        body_with_slug = dict(body)
        body_with_slug.setdefault("slug", slug)
        decl = RecurrenceDeclaration.from_yaml_block(
            shape=RecurrenceShape(shape),
            slug=slug,
            declaration_path=abs_path,
            data=body_with_slug,
        )
        yaml_text = serialize_declaration_yaml(decl)
        ok = await um.write(
            rel_path,
            yaml_text,
            summary=f"recurrence:create {shape}/{slug}",
            authored_by=authored_by,
            message=f"create {shape} recurrence {slug}",
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
        return {
            "success": True,
            "action": "create",
            "shape": shape,
            "slug": slug,
            "path": abs_path,
            "message": f"created {shape} recurrence at {abs_path}",
        }

    if action == "archive":
        if not current:
            return {"success": False, "error": "not_found", "message": f"no declaration at {abs_path}"}
        # Soft archive: write empty file to drop the declaration. Actual
        # filesystem deletion is a separate concern (workspace_cleanup or
        # explicit delete primitive); for ADR-231 purposes, an empty YAML
        # parses to zero declarations.
        ok = await um.write(
            rel_path,
            "",
            summary=f"recurrence:archive {shape}/{slug}",
            authored_by=authored_by,
            message=f"archive {shape} recurrence {slug}",
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
        return {
            "success": True,
            "action": "archive",
            "shape": shape,
            "slug": slug,
            "path": abs_path,
            "message": f"archived {shape} recurrence {slug}",
        }

    # update / pause / resume require the file to exist
    if not current:
        return {"success": False, "error": "not_found", "message": f"no declaration at {abs_path}"}

    decls = parse_recurrence_yaml(current, abs_path)
    if not decls:
        return {
            "success": False,
            "error": "parse_failed",
            "message": f"could not parse existing declaration at {abs_path}",
        }
    decl = decls[0]
    new_data = dict(decl.data)

    if action == "pause":
        new_data["paused"] = True
        if paused_until:
            new_data["paused_until"] = paused_until
        msg = f"paused {shape} recurrence {slug}"
    elif action == "resume":
        new_data["paused"] = False
        new_data.pop("paused_until", None)
        msg = f"resumed {shape} recurrence {slug}"
    elif action == "update":
        # Recursive merge of `changes` over `new_data` (top-level dict merge;
        # nested objects are replaced wholesale to keep semantics predictable).
        for k, v in changes.items():
            new_data[k] = v
        msg = f"updated {shape} recurrence {slug}: {sorted(changes.keys())}"
    else:
        return {"success": False, "error": "unhandled_action", "message": action}

    decl.data = new_data
    yaml_text = serialize_declaration_yaml(decl)
    ok = await um.write(
        rel_path,
        yaml_text,
        summary=f"recurrence:{action} {shape}/{slug}",
        authored_by=authored_by,
        message=msg,
    )
    if not ok:
        return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
    return {
        "success": True,
        "action": action,
        "shape": shape,
        "slug": slug,
        "path": abs_path,
        "message": msg,
    }


async def _handle_recurrence_multi(
    *,
    um,
    rel_path: str,
    abs_path: str,
    shape: str,
    slug: str,
    action: str,
    body: dict,
    changes: dict,
    paused_until: Optional[str],
    current: Optional[str],
    authored_by: str,
) -> dict:
    """Handle ACCUMULATION / MAINTENANCE shapes — list-of-declarations file."""
    import yaml as _yaml

    list_key = "recurrences" if shape == "accumulation" else "back_office_jobs"

    parsed = {}
    if current:
        try:
            loaded = _yaml.safe_load(current)
            if isinstance(loaded, dict):
                parsed = loaded
        except _yaml.YAMLError as e:
            return {
                "success": False,
                "error": "parse_failed",
                "message": f"could not parse existing {abs_path}: {e}",
            }

    entries = parsed.get(list_key)
    if not isinstance(entries, list):
        entries = []

    # Find existing entry by slug (entries without explicit slug match by
    # derived slug for back-office; for accumulation, slug must be explicit).
    def _entry_slug(entry: dict) -> Optional[str]:
        if not isinstance(entry, dict):
            return None
        s = entry.get("slug")
        if s:
            return str(s)
        if shape == "maintenance":
            from services.recurrence import _slug_from_executor

            ex = entry.get("executor")
            if ex:
                return _slug_from_executor(str(ex))
        return None

    idx = next((i for i, e in enumerate(entries) if _entry_slug(e) == slug), -1)

    if action == "create":
        if idx >= 0:
            return {
                "success": False,
                "error": "already_exists",
                "message": f"entry slug='{slug}' already exists in {abs_path} (use action='update')",
            }
        new_entry = dict(body)
        # Ensure slug is recorded explicitly on multi-decl entries
        new_entry.setdefault("slug", slug)
        if shape == "maintenance" and not new_entry.get("executor"):
            return {
                "success": False,
                "error": "missing_executor",
                "message": "back-office entries require body.executor (dotted Python path)",
            }
        entries.append(new_entry)
        msg = f"created {shape} recurrence {slug}"
    elif action == "archive":
        if idx < 0:
            return {"success": False, "error": "not_found", "message": f"no entry slug='{slug}' in {abs_path}"}
        entries.pop(idx)
        msg = f"archived {shape} recurrence {slug}"
    else:
        if idx < 0:
            return {"success": False, "error": "not_found", "message": f"no entry slug='{slug}' in {abs_path}"}
        entry = dict(entries[idx])
        if action == "pause":
            entry["paused"] = True
            if paused_until:
                entry["paused_until"] = paused_until
            msg = f"paused {shape} recurrence {slug}"
        elif action == "resume":
            entry["paused"] = False
            entry.pop("paused_until", None)
            msg = f"resumed {shape} recurrence {slug}"
        elif action == "update":
            for k, v in changes.items():
                entry[k] = v
            msg = f"updated {shape} recurrence {slug}: {sorted(changes.keys())}"
        else:
            return {"success": False, "error": "unhandled_action", "message": action}
        entries[idx] = entry

    parsed[list_key] = entries
    yaml_text = _yaml.safe_dump(parsed, sort_keys=False, default_flow_style=False)
    ok = await um.write(
        rel_path,
        yaml_text,
        summary=f"recurrence:{action} {shape}/{slug}",
        authored_by=authored_by,
        message=msg,
    )
    if not ok:
        return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
    return {
        "success": True,
        "action": action,
        "shape": shape,
        "slug": slug,
        "path": abs_path,
        "message": msg,
    }
