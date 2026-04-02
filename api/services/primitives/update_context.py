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
    "description": """Update workspace context — identity, brand, memory, agent feedback, or task feedback.

Call this whenever you learn something worth persisting. Pick the right target:

**target="identity"** — User shares who they are (role, domain, background)
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

For identity/brand: inference merges with existing content — nothing is lost.
For memory: appends (deduped). For agent/task: appends feedback entry.
For awareness: full replacement — write your current understanding as a living document.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "enum": ["identity", "brand", "memory", "agent", "task", "awareness"],
                "description": "What to update: identity (IDENTITY.md), brand (BRAND.md), memory (notes), agent (agent feedback), task (task feedback), awareness (your situational notes)"
            },
            "text": {
                "type": "string",
                "description": "The content to persist — what you learned from the user"
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
                "description": "For target='task': where to route feedback. 'deliverable' (default) writes to memory/feedback.md for DELIVERABLE.md inference. Others patch TASK.md sections directly."
            },
            "document_contents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "content": {"type": "string"}
                    }
                },
                "description": "For identity/brand: content from uploaded documents"
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
                "description": "For identity/brand: content from web pages"
            },
        },
        "required": ["target", "text"]
    }
}


async def handle_update_context(auth: Any, input: dict) -> dict:
    """
    Handle UpdateContext — route to appropriate handler by target.

    ADR-146: Single entry point for all context mutations.
    """
    target = input.get("target")
    text = input.get("text", "").strip()

    if target not in ("identity", "brand", "memory", "agent", "task", "awareness"):
        return {"success": False, "error": "invalid_target", "message": "target must be one of: identity, brand, memory, agent, task, awareness"}

    if not text:
        return {"success": False, "error": "empty_text", "message": "text is required"}

    if target in ("identity", "brand"):
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


# ---------------------------------------------------------------------------
# Internal handlers — absorbed from deleted primitives
# ---------------------------------------------------------------------------

async def _handle_shared_context(auth: Any, target: str, input: dict) -> dict:
    """Identity/brand update via inference merge. Was: UpdateSharedContext."""
    from services.context_inference import infer_shared_context
    from services.workspace import UserMemory

    text = input.get("text", "")
    document_contents = input.get("document_contents", [])
    url_contents = input.get("url_contents", [])
    filename = "IDENTITY.md" if target == "identity" else "BRAND.md"

    try:
        um = UserMemory(auth.client, auth.user_id)
        existing = await um.read(filename)

        new_content = await infer_shared_context(
            target=target,
            text=text,
            document_contents=document_contents,
            url_contents=url_contents,
            existing_content=existing or "",
        )

        if not new_content or not new_content.strip():
            return {"success": False, "error": "inference_empty", "message": "Inference produced no content — try providing more detail"}

        ok = await um.write(filename, new_content, summary=f"{target.capitalize()} updated via inference")
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"Failed to write {filename}"}

        logger.info(f"[UPDATE_CONTEXT] Updated {filename} ({len(new_content)} chars)")

        # ADR-155: Trigger workspace-wide inference after identity update.
        # Scaffolds entity stubs across all context domains from identity.
        inference_result = None
        if target == "identity":
            try:
                from services.workspace_inference import run_workspace_inference
                inference_result = await run_workspace_inference(auth.client, auth.user_id)
                if inference_result.get("success"):
                    total = inference_result.get("total_files", 0)
                    domains = len(inference_result.get("scaffolded", {}))
                    logger.info(f"[UPDATE_CONTEXT] Workspace inference: {total} files across {domains} domains")
            except Exception as e:
                logger.warning(f"[UPDATE_CONTEXT] Workspace inference failed (non-fatal): {e}")

        return {
            "success": True,
            "target": target,
            "filename": filename,
            "content": new_content,
            "message": f"Updated {filename} successfully",
            "inference": inference_result if inference_result and inference_result.get("success") else None,
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

        ok = await um.write("AWARENESS.md", content, summary="TP awareness updated")
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
    """Write feedback to agent's memory/feedback.md. Was: WriteAgentFeedback."""
    agent_slug = input.get("agent_slug", "")
    feedback_text = input.get("text", "")

    if not agent_slug:
        return {"success": False, "error": "missing_agent_slug", "message": "agent_slug is required for target='agent'"}

    client = auth.client if not isinstance(auth, dict) else auth["client"]
    user_id = auth.user_id if not isinstance(auth, dict) else auth["user_id"]

    try:
        result = client.table("agents").select("id, title, role").eq("user_id", user_id).execute()
        agents = result.data or []

        from services.workspace import get_agent_slug
        target_agent = None
        for a in agents:
            if get_agent_slug(a) == agent_slug:
                target_agent = a
                break

        if not target_agent:
            return {"success": False, "error": "not_found", "message": f"Agent '{agent_slug}' not found"}

        from services.feedback_distillation import write_feedback_entry
        success = await write_feedback_entry(
            client, user_id, target_agent, feedback_text, source="conversation"
        )

        if success:
            return {"success": True, "message": f"Feedback written to {target_agent.get('title', agent_slug)}"}
        else:
            return {"success": False, "error": "write_failed", "message": "Failed to write feedback"}

    except Exception as e:
        logger.warning(f"[UPDATE_CONTEXT] Agent feedback failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}


async def _handle_task_feedback(auth: Any, input: dict) -> dict:
    """Write task-specific feedback to memory/feedback.md (default) or TASK.md sections.

    ADR-149/151: feedback_target="deliverable" (default) writes to memory/feedback.md
    for DELIVERABLE.md inference. Other targets patch TASK.md sections directly.
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
            # ADR-149: Primary path — write to memory/feedback.md for DELIVERABLE.md inference
            entry = f"## User Feedback ({date_str}, source: user_conversation)\n- {feedback_text}\n"
            existing = await tw.read("memory/feedback.md") or ""
            # Prepend (newest first)
            if existing.startswith("# Task Feedback"):
                header_lines = existing.split("\n", 2)
                rest = header_lines[2] if len(header_lines) > 2 else ""
                updated = f"{header_lines[0]}\n{header_lines[1] if len(header_lines) > 1 else ''}\n\n{entry}\n{rest}"
            else:
                updated = f"# Task Feedback\n\n{entry}\n{existing}"
            await tw.write("memory/feedback.md", updated,
                          summary=f"User feedback: {feedback_text[:50]}")
            return {"success": True, "message": f"Feedback recorded for {task_slug} (will inform next run via DELIVERABLE.md inference)"}

        elif feedback_target == "run_log":
            entry = f"\n## Feedback ({date_str})\n- {feedback_text}\n"
            existing = await tw.read("memory/run_log.md") or ""
            await tw.write("memory/run_log.md", existing + entry,
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
