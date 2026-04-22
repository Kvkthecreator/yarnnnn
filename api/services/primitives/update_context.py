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
from typing import Any

logger = logging.getLogger(__name__)


UPDATE_CONTEXT_TOOL = {
    "name": "UpdateContext",
    "description": """Update workspace context — identity, brand, memory, agent feedback, task feedback, or the full first-act workspace scaffold.

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

**target="memory"** — User states a fact, preference, or standing instruction
  UpdateContext(target="memory", text="Always include a TL;DR in reports")

**target="agent"** — User gives feedback about an agent's work quality
  UpdateContext(target="agent", agent_slug="research-agent", text="Reports are too long, be more concise")

**target="task"** — User gives feedback about a specific task's output
  UpdateContext(target="task", task_slug="weekly-briefing", text="Charts need better labels")
  UpdateContext(target="task", task_slug="weekly-briefing", text="Focus on pricing", feedback_target="criteria")

**target="awareness"** — Update your situational awareness notes (shift handoff)
  UpdateContext(target="awareness", text="User focused on competitive intel. Two tracking tasks active...")

For workspace: combined inference produces identity + brand + entities + work_intent in one call. Scaffolds identity/brand files + entity subfolders. Returns `work_intent_proposal` for you to materialize via ManageAgent + ManageTask in the same turn.
For identity/brand: inference merges with existing content — nothing is lost.
For memory: appends (deduped). For agent/task: appends feedback entry.
For awareness: full replacement — write your current understanding as a living document.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "enum": ["workspace", "identity", "brand", "memory", "agent", "task", "awareness"],
                "description": "What to update: workspace (first-act scaffold — ADR-190), identity (IDENTITY.md), brand (BRAND.md), memory (notes), agent (agent feedback), task (task feedback), awareness (your situational notes)"
            },
            "text": {
                "type": "string",
                "description": "The content to persist — what you learned from the user. Required for all targets except 'workspace' when document_ids or url_contents are provided."
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
    valid_targets = ("identity", "brand", "memory", "agent", "task", "awareness", "workspace")
    if target not in valid_targets:
        return {"success": False, "error": "invalid_target", "message": f"target must be one of: {', '.join(valid_targets)}"}

    # "workspace" allows empty text if documents/URLs are present (rich input paths).
    if target != "workspace" and not text:
        return {"success": False, "error": "empty_text", "message": "text is required"}

    if target == "workspace":
        return await _handle_workspace_scaffold(auth, input)
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

    return {"success": False, "error": "unknown_target", "message": f"Unhandled target: {target}"}


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
        ok = await um.write(SHARED_IDENTITY_PATH, identity_md, summary="First-act identity inference")
        scaffolded["identity"] = "written" if ok else "failed"
        if ok:
            logger.info(f"[WORKSPACE_SCAFFOLD] Wrote {SHARED_IDENTITY_PATH} ({len(identity_md)} chars)")

    # 2. Write BRAND.md if produced.
    brand_md = inference_result.get("brand_md")
    if brand_md:
        ok = await um.write(SHARED_BRAND_PATH, brand_md, summary="First-act brand inference")
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

        ok = await um.write(filename, new_content, summary=f"{target.capitalize()} updated via inference")
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
        ok = await um.write(MEMORY_AWARENESS_PATH, content, summary="YARNNN awareness updated")
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
    from services.task_workspace import TaskWorkspace
    from datetime import datetime, timezone

    task_slug = input.get("task_slug", "")
    feedback_text = input.get("text", "")
    feedback_target = input.get("feedback_target", "deliverable")  # Default changed: ADR-149

    if not task_slug:
        return {"success": False, "error": "missing_task_slug", "message": "task_slug is required for target='task'"}

    client = auth.client if not isinstance(auth, dict) else auth["client"]
    user_id = auth.user_id if not isinstance(auth, dict) else auth["user_id"]

    try:
        tw = TaskWorkspace(client, user_id, task_slug)
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M")

        if feedback_target == "deliverable":
            # ADR-181: Primary path — write to feedback.md (task root) for DELIVERABLE.md inference
            entry = f"## User Feedback ({date_str}, source: user_conversation)\n- {feedback_text}\n"
            # ADR-181: Read from new path, fallback to old for migration
            existing = await tw.read("feedback.md") or await tw.read("memory/feedback.md") or ""
            # Prepend (newest first)
            if existing.startswith("# Task Feedback"):
                header_lines = existing.split("\n", 2)
                rest = header_lines[2] if len(header_lines) > 2 else ""
                updated = f"{header_lines[0]}\n{header_lines[1] if len(header_lines) > 1 else ''}\n\n{entry}\n{rest}"
            else:
                updated = f"# Task Feedback\n\n{entry}\n{existing}"
            # ADR-181: Write to task root
            await tw.write("feedback.md", updated,
                          summary=f"User feedback: {feedback_text[:50]}")
            return {"success": True, "message": f"Feedback recorded for {task_slug} (will inform next run via DELIVERABLE.md inference)"}

        elif feedback_target == "run_log":
            entry = f"\n## Feedback ({date_str})\n- {feedback_text}\n"
            existing = await tw.read("memory/_run_log.md") or ""
            await tw.write("memory/_run_log.md", existing + entry,
                          summary=f"Task feedback: {feedback_text[:50]}")
            return {"success": True, "message": f"Feedback recorded in run log for {task_slug}"}

        else:
            # Direct TASK.md section patching (criteria, objective, output_spec)
            task_md = await tw.read("TASK.md")
            if not task_md:
                return {"success": False, "error": "not_found", "message": f"TASK.md not found for {task_slug}"}

            section_map = {
                "criteria": "## Success Criteria",
                "objective": "## Objective",
                "output_spec": "## Output Specification",
            }
            section_header = section_map.get(feedback_target, "## Success Criteria")
            feedback_line = f"- {feedback_text} (updated {date_str})"

            if section_header in task_md:
                parts = task_md.split(section_header, 1)
                updated = parts[0] + section_header + "\n" + feedback_line + parts[1]
            else:
                updated = task_md + f"\n\n{section_header}\n{feedback_line}\n"

            await tw.write("TASK.md", updated, summary=f"Updated {feedback_target}: {feedback_text[:50]}")
            return {"success": True, "message": f"Updated {feedback_target} in {task_slug}"}

    except Exception as e:
        logger.warning(f"[UPDATE_CONTEXT] Task feedback failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}
