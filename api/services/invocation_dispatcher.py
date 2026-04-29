"""
Invocation Dispatcher — ADR-231 Phase 3.2.b YAML-native pipeline.

The canonical execution path for one invocation against a recurrence
declaration. Replaces the Phase 2 thin adapter that delegated to
`task_pipeline.execute_task` by slug.

Architectural posture (chat-as-layer per FOUNDATIONS Axiom 9):

  Every invocation emits a narrative entry first. Substrate writes are
  a property of the work, not the legibility surface. The chat scroll
  is the workspace's stream of consciousness — system outputs land with
  `authored_by: system:dispatcher`, agent work with `authored_by:
  agent:<slug>` / `reviewer:<identity>`. Filtering by Identity works
  uniformly for systemic + custom Agents (per ADR-231 D11).

Four shape branches:

  DELIVERABLE  ─┐
                ├── _dispatch_generative  (Sonnet generation; output to
  ACCUMULATION ─┘                          natural-home substrate;
                                           agent writes entity files via tools)

  ACTION       ─── _dispatch_action       (platform side-effect via
                                           target_capability tool;
                                           narrative is the surface)

  MAINTENANCE  ─── _dispatch_maintenance  (dotted-path executor; appends
                                           to /workspace/_shared/back-
                                           office-audit.md per ADR-231 D2)

Substrate writes:

  All paths resolved via services.recurrence_paths.resolve_paths(decl).
  No slug-rooted I/O. No /tasks/{slug}/ filesystem touched.

  Output substrate per shape:
    DELIVERABLE   → /workspace/reports/{slug}/{date}/output.md (+ manifest.json)
    ACCUMULATION  → agent writes entity files inside /workspace/context/{domain}/
                    via tool rounds; dispatcher does NOT write a per-firing
                    output file — there isn't one.
    ACTION        → no filesystem output (platform write IS the work);
                    outcome reconciliation per ADR-195 writes to domain
                    _performance.md asynchronously.
    MAINTENANCE   → append entry to /workspace/_shared/back-office-audit.md.

Run-log discipline (per ADR-231 D10):
  - DELIVERABLE → /workspace/reports/{slug}/_run_log.md (per-decl)
  - ACCUMULATION → /workspace/context/{domain}/_run_log.md (per-domain shared)
  - ACTION → /workspace/operations/{slug}/_run_log.md (per-decl)
  - MAINTENANCE → audit log doubles as run log.

Failure discipline:

  Returns `{success: bool, ...}` always — the contract from Phase 2 is
  preserved. On failure: narrative entry still emits (with weight=routine,
  failure summary), substrate is left clean, scheduler index is updated
  to reflect last_run_at.

Cost gating:

  Balance check (ADR-172) at dispatch entry — exits early on exhaustion.
  Capability gate (ADR-207 P3) at dispatch entry — exits early on missing
  required capabilities. Both emit narrative entries explaining the skip
  so the operator sees them in chat.
"""

from __future__ import annotations

import importlib
import json as _json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.recurrence import RecurrenceDeclaration, RecurrenceShape
from services.recurrence_paths import resolve_paths, ResolvedPaths

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def dispatch(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    *,
    context: Optional[str] = None,
) -> dict:
    """Fire one invocation against a recurrence declaration.

    Args:
        client: Supabase service client
        user_id: User UUID
        decl: parsed RecurrenceDeclaration to fire
        context: optional one-shot steering for this firing (does NOT
                 mutate the declaration; informs only this invocation)

    Returns:
        Result dict with at minimum `{success: bool, shape, slug,
        declaration_path, ...}`.
    """
    if decl.paused:
        return _result_paused(decl)

    started_at = datetime.now(timezone.utc)
    paths = resolve_paths(decl, started_at=started_at)

    logger.info(
        "[DISPATCH] %s/%s start (decl=%s)",
        decl.shape.value,
        decl.slug,
        decl.declaration_path,
    )

    # Capability gate (ADR-207 P3) — applies to every shape.
    capability_check = _check_capabilities(client, user_id, decl)
    if capability_check is not None:
        await _emit_narrative(
            client,
            user_id,
            decl,
            role="system",
            summary=f"{decl.slug} skipped: capability unavailable",
            body=capability_check,
            pulse=_pulse_for_decl(decl),
            weight="routine",
            paths=paths,
        )
        return _result_failed(decl, capability_check, paths=paths)

    try:
        if decl.shape == RecurrenceShape.MAINTENANCE:
            return await _dispatch_maintenance(
                client, user_id, decl, paths, started_at=started_at
            )
        if decl.shape == RecurrenceShape.ACTION:
            return await _dispatch_action(
                client, user_id, decl, paths,
                started_at=started_at, context=context,
            )
        # DELIVERABLE + ACCUMULATION share the same generation path
        return await _dispatch_generative(
            client, user_id, decl, paths,
            started_at=started_at, context=context,
        )
    except Exception as exc:
        logger.exception(
            "[DISPATCH] %s/%s failed: %s", decl.shape.value, decl.slug, exc
        )
        await _emit_narrative(
            client,
            user_id,
            decl,
            role="system",
            summary=f"{decl.slug} failed",
            body=f"Unhandled dispatcher error: {exc}",
            pulse=_pulse_for_decl(decl),
            weight="routine",
            paths=paths,
        )
        return _result_failed(decl, str(exc), paths=paths)


# ---------------------------------------------------------------------------
# Branch: generative (DELIVERABLE + ACCUMULATION)
# ---------------------------------------------------------------------------


async def _dispatch_generative(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    paths: ResolvedPaths,
    *,
    started_at: datetime,
    context: Optional[str],
) -> dict:
    """Run Sonnet generation against the declaration.

    DELIVERABLE: writes one cohesive output.md to /workspace/reports/{slug}/{date}/.
    ACCUMULATION: agent writes entity files inside the domain via tool rounds;
                  no per-firing output file (the entities ARE the output).

    Both shapes share:
      - context gathering from declaration's context_reads
      - mandate gate
      - balance gate
      - Sonnet generation via existing _generate
      - narrative emission
      - run log append
    """
    from services.platform_limits import check_balance, record_token_usage
    from services.task_pipeline import (
        _load_user_context,
        _generate,
        build_task_execution_prompt,
        gather_task_context,
        get_user_timezone,
    )
    from services.agent_creation import (
        ensure_infrastructure_agent,
        resolve_infra_role_from_ref,
    )
    from services.agent_execution import (
        SONNET_MODEL,
        _extract_agent_reflection,
        create_version_record,
        get_next_run_number,
        update_version_for_delivery,
    )
    from services.workspace import AgentWorkspace, UserMemory

    # ---- Empty-state special cases (ADR-161 / ADR-204) ----
    # daily-update + maintain-overview short-circuit when the workspace has
    # no other accumulated substrate. Operator gets a deterministic artifact;
    # zero LLM cost.
    if decl.slug in ("daily-update", "maintain-overview"):
        empty_result = await _maybe_empty_state(
            client, user_id, decl, paths, started_at=started_at
        )
        if empty_result is not None:
            return empty_result

    # ---- Balance gate (ADR-172) ----
    try:
        balance_ok, balance = check_balance(client, user_id)
    except Exception as e:
        logger.warning("[DISPATCH] balance check failed (proceeding): %s", e)
        balance_ok = True
    if not balance_ok:
        await _emit_narrative(
            client, user_id, decl,
            role="system",
            summary=f"{decl.slug} skipped: balance exhausted",
            pulse=_pulse_for_decl(decl),
            weight="routine",
            paths=paths,
        )
        return _result_failed(decl, "balance exhausted", paths=paths)

    # ---- Resolve agent ----
    # Declaration's `agents:` is the assignment list. First entry is the
    # generation lead. Universal-role agents lazy-create on first dispatch.
    agent_ref = decl.agents[0] if decl.agents else None
    if not agent_ref:
        msg = f"declaration {decl.slug} has no agent assigned"
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=msg,
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    agent = await _resolve_agent(client, user_id, agent_ref)
    if agent is None:
        msg = f"agent '{agent_ref}' not found and could not be ensured"
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=f"{decl.slug} failed: {msg}",
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    agent_id = agent["id"]
    agent_slug = agent["slug"]
    role = agent.get("role", "custom")
    scope = agent.get("scope", "cross_platform")

    # ---- Maintenance early-out: TP-class agents route through dotted executor.
    # In the generative branch we should never see thinking_partner. If we do,
    # the declaration is mis-classified — surface and fail.
    if role == "thinking_partner":
        msg = (
            f"{decl.slug}: TP-class agent assigned to non-MAINTENANCE shape "
            f"({decl.shape.value}); declaration is mis-classified"
        )
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=msg,
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    user_timezone = get_user_timezone(client, user_id)

    # ---- Build task_info shape from declaration ----
    # Existing helpers (gather_task_context, build_task_execution_prompt,
    # _generate) take a `task_info` dict. We synthesize that dict from the
    # declaration's data + paths so we can reuse the helpers without
    # rewriting them. This is the bridge between YAML-native declarations
    # and the survivor pipeline functions, which dies with task_pipeline.py
    # in 3.7 — at which point those helpers live in this dispatcher and the
    # bridge becomes inline.
    task_info = _decl_to_task_info(decl)

    # ---- Read declaration substrate (feedback, steering, intent) ----
    um = UserMemory(client, user_id)

    deliverable_spec = ""  # ADR-231 D5: deliverable spec for produces_deliverable
    # comes from the decl YAML's `deliverable:` block, surfaced through task_info
    if decl.shape == RecurrenceShape.DELIVERABLE:
        deliverable = decl.data.get("deliverable") or {}
        if deliverable:
            deliverable_spec = _format_deliverable_spec(deliverable)

    steering_notes = ""
    if paths.steering_path:
        steering_notes = await _read_workspace_path(um, paths.steering_path) or ""

    feedback_raw = ""
    if paths.feedback_path:
        feedback_raw = await _read_workspace_path(um, paths.feedback_path) or ""
    task_feedback = _extract_recent_feedback(feedback_raw, max_entries=3)

    # ADR-231 D2: optional operator-prose context
    intent_prose = ""
    if paths.intent_path:
        intent_prose = await _read_workspace_path(um, paths.intent_path) or ""

    # Optional: one-shot steering passed in this firing (FireInvocation
    # context= argument). Layered on top of authored steering.
    if context:
        steering_notes = (
            (steering_notes + "\n\n" if steering_notes else "")
            + f"## One-shot steering (this firing only)\n{context.strip()}"
        )

    # ---- Mandate gate (ADR-207) — non-fatal but surfaced ----
    # Reading the mandate is part of every invocation so the operator-
    # authored standing intent is in scope. Empty mandate is allowed
    # post-ADR-205; missing mandate is a system smell but doesn't block.

    # ---- Gather context ----
    try:
        context_text, _context_meta = await gather_task_context(
            client, user_id, agent, agent_slug,
            task_info=task_info,
            task_slug=decl.slug,  # label only — gather_task_context uses it for awareness reads
        )
    except Exception as e:
        logger.warning("[DISPATCH] gather_task_context failed (continuing with empty): %s", e)
        context_text = "(No context available)"

    user_context = _load_user_context(client, user_id)

    # Agent workspace identity (AGENT.md)
    ws = AgentWorkspace(client, user_id, agent_slug)
    await ws.ensure_seeded(agent)
    ws_instructions = await ws.read("AGENT.md") or ""

    # ---- Audit: create agent_runs row (run number + reservation) ----
    next_version = await get_next_run_number(client, agent_id)
    version = await create_version_record(client, agent_id, next_version)
    version_id = version["id"]

    # ---- Build prompt ----
    # Note: prior_output / prior_state_brief / generation_brief / revision_scope
    # are 3.2.b deferred — they require the slug-rooted /tasks/{slug}/outputs/latest/
    # substrate that dies in 3.7. Post-cutover, prior-state injection reads
    # from natural-home (/workspace/reports/{slug}/...). Stub for now;
    # 3.6.b.2 reshapes the compose/assembly module to consume natural-home paths.
    system_prompt, user_message = build_task_execution_prompt(
        task_info=task_info,
        agent=agent,
        agent_instructions=ws_instructions,
        context=context_text,
        user_context=user_context,
        deliverable_spec=deliverable_spec,
        steering_notes=steering_notes,
        task_feedback=task_feedback,
        task_mode=task_info.get("mode", "recurring"),
        prior_output="",
        prior_state_brief=intent_prose,  # operator prose stands in for prior-state for 3.2.b
        task_phase="steady",
        generation_brief="",
    )

    # ---- Tool surface (ADR-182) ----
    tool_overrides = None
    max_rounds_override = None
    output_kind = task_info.get("output_kind", "")
    if output_kind == "produces_deliverable":
        from services.primitives.workspace import WRITE_FILE_TOOL
        from services.primitives.runtime_dispatch import RUNTIME_DISPATCH_TOOL
        tool_overrides = [WRITE_FILE_TOOL, RUNTIME_DISPATCH_TOOL]
        max_rounds_override = 2

    # ---- Generate ----
    required_caps = decl.required_capabilities or []
    draft, usage, pending_renders, tools_used, tool_rounds = await _generate(
        client, user_id, agent, system_prompt, user_message, scope,
        task_phase="steady",
        task_slug=decl.slug,  # telemetry label
        output_kind=output_kind,
        tool_overrides=tool_overrides,
        max_rounds_override=max_rounds_override,
        task_required_capabilities=required_caps,
    )

    # Strip agent reflection (ADR-128/149)
    draft, agent_reflection = _extract_agent_reflection(draft)

    # ---- Render inline assets (ADR-148) ----
    rendered_assets = []
    try:
        from services.render_assets import render_inline_assets
        draft, rendered_assets = await render_inline_assets(draft, user_id)
    except Exception as e:
        logger.warning("[DISPATCH] inline asset rendering failed (non-fatal): %s", e)

    # ---- Update agent_runs ----
    version_metadata = {
        "input_tokens": _total_input_tokens(usage),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "model": SONNET_MODEL,
        "task_slug": decl.slug,  # label
        "trigger_type": "scheduled" if decl.schedule else "manual",
        "tool_rounds": tool_rounds,
        "tools_used": tools_used,
    }
    await update_version_for_delivery(client, version_id, draft, metadata=version_metadata)

    # ---- Write output to natural-home substrate ----
    # DELIVERABLE: write output.md + manifest.json to natural-home folder.
    # ACCUMULATION: do not write — agent already wrote entity files via tool rounds.
    if decl.shape == RecurrenceShape.DELIVERABLE and paths.output_path and paths.output_folder:
        await _write_deliverable_output(
            um=um,
            decl=decl,
            paths=paths,
            draft=draft,
            agent_slug=agent_slug,
            version_id=str(version_id),
            version_number=next_version,
            usage=usage,
            started_at=started_at,
        )

    # ---- Run log ----
    run_log_msg = f"v{next_version} delivered ({tool_rounds} tool rounds)"
    if agent_reflection:
        confidence = (agent_reflection.get("output_confidence") or "")
        level = confidence.split("—")[0].split("–")[0].strip().lower() if confidence else ""
        if level:
            run_log_msg += f" | confidence={level}"
    await _append_run_log(
        um=um, paths=paths,
        slug=decl.slug,
        author=f"agent:{agent_slug}",
        message=run_log_msg,
    )

    # ---- Token accounting (ADR-171) ----
    try:
        record_token_usage(
            client, user_id,
            caller="invocation_dispatcher",
            model=SONNET_MODEL,
            input_tokens=version_metadata["input_tokens"],
            output_tokens=version_metadata["output_tokens"],
            ref_id=str(version_id),
            metadata={"slug": decl.slug, "shape": decl.shape.value},
        )
    except Exception as e:
        logger.warning("[DISPATCH] token accounting failed (non-fatal): %s", e)

    # ---- Mark agent_runs delivered ----
    try:
        client.table("agent_runs").update({
            "status": "delivered",
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", version_id).execute()
    except Exception as e:
        logger.warning("[DISPATCH] agent_runs delivered-mark failed: %s", e)

    # ---- Narrative emission (ADR-219) ----
    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    output_pointer = paths.output_path or paths.substrate_root
    summary = _generative_summary(decl, agent, version=next_version)
    body = (
        f"Output at {output_pointer}.\n"
        f"Run log at {paths.run_log_path}.\n"
        f"Duration: {duration_ms}ms · Tool rounds: {tool_rounds}."
    )
    await _emit_narrative(
        client, user_id, decl,
        role="agent",
        summary=summary,
        body=body,
        pulse=_pulse_for_decl(decl),
        weight="material",
        paths=paths,
        invocation_id=str(version_id),
        extra_metadata={
            "agent_slug": agent_slug,
            "agent_role": role,
            "tool_rounds": tool_rounds,
            "tools_used": tools_used,
            "duration_ms": duration_ms,
            "input_tokens": version_metadata["input_tokens"],
            "output_tokens": version_metadata["output_tokens"],
        },
    )

    logger.info(
        "[DISPATCH] %s/%s complete v%d (%dms)",
        decl.shape.value, decl.slug, next_version, duration_ms,
    )

    return {
        "success": True,
        "shape": decl.shape.value,
        "slug": decl.slug,
        "declaration_path": decl.declaration_path,
        "agent_slug": agent_slug,
        "run_id": version_id,
        "version_number": next_version,
        "status": "delivered",
        "duration_ms": duration_ms,
        "output_path": paths.output_path,
        "message": f"v{next_version} delivered",
    }


# ---------------------------------------------------------------------------
# Branch: action (external_action)
# ---------------------------------------------------------------------------


async def _dispatch_action(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    paths: ResolvedPaths,
    *,
    started_at: datetime,
    context: Optional[str],
) -> dict:
    """Fire an external-action declaration.

    Routes through the generative branch (Sonnet plans the action message
    + emits the platform write tool call). The platform side-effect IS
    the work; outcome reconciliation per ADR-195 writes to the relevant
    domain's `_performance.md` asynchronously via the back-office
    outcome reconciliation job.

    For 3.2.b, this delegates to _dispatch_generative because the agent
    needs Sonnet to compose the message + invoke the platform tool. The
    distinguishing characteristic of ACTION at the dispatch layer is
    substrate semantics (no filesystem output), which the generative
    branch already honors via paths.output_path is None.
    """
    return await _dispatch_generative(
        client, user_id, decl, paths,
        started_at=started_at, context=context,
    )


# ---------------------------------------------------------------------------
# Branch: maintenance (back-office)
# ---------------------------------------------------------------------------


async def _dispatch_maintenance(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    paths: ResolvedPaths,
    *,
    started_at: datetime,
) -> dict:
    """Fire a back-office maintenance declaration.

    The declaration's `executor:` field names a dotted Python module path.
    The module's `run(client, user_id, slug)` async function is invoked;
    its returned dict is appended as one entry to the shared audit log
    `/workspace/_shared/back-office-audit.md` per ADR-231 D2.

    Back-office work does NOT consume balance, does NOT create agent_runs
    rows, and does NOT go through Sonnet generation. It's deterministic
    Python.
    """
    from services.workspace import UserMemory

    executor_path = decl.executor
    if not executor_path:
        msg = f"maintenance declaration {decl.slug} missing executor:"
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=msg,
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    try:
        module = importlib.import_module(executor_path)
    except ImportError as e:
        msg = f"executor module not importable: {executor_path} ({e})"
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=f"{decl.slug} failed: {msg}",
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    if not hasattr(module, "run") or not callable(module.run):
        msg = f"executor {executor_path} missing async run(client, user_id, slug)"
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=f"{decl.slug} failed: {msg}",
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    logger.info("[DISPATCH:MAINT] %s → %s", decl.slug, executor_path)

    try:
        result = await module.run(client, user_id, decl.slug)
    except Exception as e:
        msg = f"executor {executor_path} raised: {e}"
        logger.exception("[DISPATCH:MAINT] executor raised")
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=f"{decl.slug} failed",
            body=msg,
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    if not isinstance(result, dict) or "output_markdown" not in result:
        msg = (
            f"executor {executor_path} returned invalid shape "
            "(expected dict with 'output_markdown')"
        )
        await _emit_narrative(
            client, user_id, decl,
            role="system", summary=f"{decl.slug} failed: invalid result",
            body=msg,
            pulse=_pulse_for_decl(decl), weight="routine", paths=paths,
        )
        return _result_failed(decl, msg, paths=paths)

    summary = result.get("summary", "Back office task completed")
    output_markdown = result["output_markdown"]
    actions_taken = result.get("actions_taken", []) or []

    # Append to shared audit log (the audit log doubles as run log per D10)
    um = UserMemory(client, user_id)
    audit_entry = _format_audit_entry(
        slug=decl.slug,
        executor=executor_path,
        summary=summary,
        actions_taken=actions_taken,
        output_markdown=output_markdown,
        started_at=started_at,
    )
    await _append_audit_log(um, paths.run_log_path, audit_entry)

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    # Narrative — routine weight (back-office is housekeeping)
    await _emit_narrative(
        client, user_id, decl,
        role="system",
        summary=f"back-office: {summary}",
        body=(
            f"Executor: {executor_path}\n"
            f"Actions: {len(actions_taken)}\n"
            f"Audit log: {paths.run_log_path}"
        ),
        pulse=_pulse_for_decl(decl),
        weight="housekeeping",
        paths=paths,
        extra_metadata={
            "executor": executor_path,
            "actions_taken_count": len(actions_taken),
            "duration_ms": duration_ms,
        },
    )

    logger.info("[DISPATCH:MAINT] %s done (%dms) — %s", decl.slug, duration_ms, summary)

    return {
        "success": True,
        "shape": decl.shape.value,
        "slug": decl.slug,
        "declaration_path": decl.declaration_path,
        "executor": executor_path,
        "summary": summary,
        "actions_taken": actions_taken,
        "duration_ms": duration_ms,
        "message": summary,
    }


# ---------------------------------------------------------------------------
# Empty-state special cases (ADR-161 / ADR-204)
# ---------------------------------------------------------------------------


async def _maybe_empty_state(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    paths: ResolvedPaths,
    *,
    started_at: datetime,
) -> Optional[dict]:
    """If the workspace is empty, short-circuit with a deterministic template.

    Only daily-update + maintain-overview have empty-state branches. Returns
    None for all other slugs (caller proceeds with normal generation) or
    when the workspace has accumulated substrate.
    """
    if decl.slug not in ("daily-update", "maintain-overview"):
        return None

    try:
        from services.task_pipeline import _is_workspace_empty_for_daily_update
        is_empty = await _is_workspace_empty_for_daily_update(client, user_id)
    except Exception as e:
        logger.warning("[DISPATCH] empty-state check failed (proceeding): %s", e)
        return None

    if not is_empty:
        return None

    from services.task_pipeline import (
        _execute_daily_update_empty_state,
        _execute_maintain_overview_empty_state,
        get_user_timezone,
    )

    user_timezone = get_user_timezone(client, user_id)
    if decl.slug == "daily-update":
        legacy_result = await _execute_daily_update_empty_state(
            client, user_id, started_at, user_timezone=user_timezone
        )
    else:  # maintain-overview
        legacy_result = await _execute_maintain_overview_empty_state(
            client, user_id, started_at
        )

    # Empty-state writers append their own narrative entry; do not double-emit.
    return {
        "success": True,
        "shape": decl.shape.value,
        "slug": decl.slug,
        "declaration_path": decl.declaration_path,
        "status": "delivered_empty_state",
        "message": legacy_result.get("message", "empty-state template delivered"),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decl_to_task_info(decl: RecurrenceDeclaration) -> dict:
    """Synthesize the legacy task_info dict shape from a RecurrenceDeclaration.

    Bridge for survivor helpers (gather_task_context, build_task_execution_prompt,
    _generate) that take a `task_info` dict. Dies in 3.7 when those helpers
    are absorbed inline.
    """
    output_kind = _output_kind_for_shape(decl.shape)
    return {
        "title": decl.display_name or decl.slug,
        "slug": decl.slug,
        "objective": {"prose": decl.objective or ""},
        "agent_slug": decl.agents[0] if decl.agents else "",
        "context_reads": decl.context_reads,
        "context_writes": decl.context_writes,
        "required_capabilities": decl.required_capabilities,
        "schedule": decl.schedule or "",
        "mode": decl.data.get("mode") or _default_mode_for_shape(decl.shape),
        "output_kind": output_kind,
        "page_structure": decl.data.get("page_structure"),
        "surface_type": decl.data.get("surface_type"),
        "delivery": decl.data.get("delivery", ""),
        "sources": decl.data.get("sources") or {},
        "process_steps": [
            {
                "agent_ref": decl.agents[0] if decl.agents else "",
                "instruction": decl.data.get("instruction") or decl.objective or "",
            }
        ],
        "commerce": decl.data.get("commerce") or {},
    }


def _output_kind_for_shape(shape: RecurrenceShape) -> str:
    """Map RecurrenceShape → legacy output_kind enum value."""
    return {
        RecurrenceShape.DELIVERABLE: "produces_deliverable",
        RecurrenceShape.ACCUMULATION: "accumulates_context",
        RecurrenceShape.ACTION: "external_action",
        RecurrenceShape.MAINTENANCE: "system_maintenance",
    }[shape]


def _default_mode_for_shape(shape: RecurrenceShape) -> str:
    """Default mode when declaration doesn't specify."""
    if shape == RecurrenceShape.ACTION:
        return "reactive"
    return "recurring"


def _pulse_for_decl(decl: RecurrenceDeclaration) -> str:
    """Map declaration to narrative pulse type per Axiom 4 / ADR-219."""
    if decl.shape == RecurrenceShape.ACTION:
        return "reactive"
    if decl.schedule:
        return "periodic"
    return "addressed"


def _format_deliverable_spec(deliverable: dict) -> str:
    """Render the YAML deliverable: block as prompt-friendly markdown."""
    lines = ["## Deliverable Specification"]
    if deliverable.get("audience"):
        lines.append(f"**Audience**: {deliverable['audience']}")
    if deliverable.get("page_structure"):
        ps = deliverable["page_structure"]
        if isinstance(ps, list):
            lines.append("**Page structure**: " + ", ".join(str(s) for s in ps))
    if deliverable.get("quality_criteria"):
        qc = deliverable["quality_criteria"]
        if isinstance(qc, list):
            lines.append("**Quality criteria**:")
            for c in qc:
                lines.append(f"- {c}")
    return "\n".join(lines)


def _check_capabilities(client, user_id: str, decl: RecurrenceDeclaration) -> Optional[str]:
    """Return None if all required capabilities are available, else a
    human-readable error message."""
    required = decl.required_capabilities
    if not required:
        return None
    try:
        from services.orchestration import unavailable_capabilities
        missing = unavailable_capabilities(user_id, required, client)
    except Exception as e:
        logger.warning("[DISPATCH] capability check raised (proceeding): %s", e)
        return None
    if not missing:
        return None
    parts = []
    for m in missing:
        if m["reason"] == "unknown_capability":
            parts.append(f"'{m['capability']}' (unknown)")
        else:
            parts.append(
                f"'{m['capability']}' (connect {m['required_platform']} first)"
            )
    return "Required capability unavailable: " + "; ".join(parts)


def find_declaration_for_agent(
    client, user_id: str, agent_slug: str
) -> Optional[RecurrenceDeclaration]:
    """Find the recurrence declaration that assigns this agent.

    Walks all of the user's recurrence declarations and returns the first
    one whose `agents:` list (or `agent:` singular) contains the given
    slug. Returns None when no declaration assigns this agent.

    Used by routes/agents.py POST /agents/{id}/run and
    services.trigger_dispatch._dispatch_high to map agent → declaration
    before dispatching. Replaces the legacy task_pipeline.execute_agent_run
    which scanned `tasks` rows + parsed every TASK.md to find the
    agent-task assignment.
    """
    from services.recurrence import walk_workspace_recurrences

    decls = walk_workspace_recurrences(client, user_id)
    for d in decls:
        # Match against either 'agents' (list) or 'agent' (singular)
        agents_list = d.agents
        if agent_slug in agents_list:
            return d
    return None


async def _resolve_agent(client, user_id: str, agent_ref: str) -> Optional[dict]:
    """Resolve an agent_ref (slug or role) to an agents row.

    Mirrors the resolution shape from `task_pipeline.execute_task` step 2:
    1. If ref names an infrastructure role, ensure_infrastructure_agent.
    2. Otherwise, look up by slug or role in the user's roster.
    """
    from services.agent_creation import (
        ensure_infrastructure_agent,
        resolve_infra_role_from_ref,
    )

    infra_role = resolve_infra_role_from_ref(agent_ref)
    if infra_role:
        ensured = await ensure_infrastructure_agent(client, user_id, infra_role)
        if ensured:
            return ensured

    try:
        roster = (
            client.table("agents")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as e:
        logger.warning("[DISPATCH] agent roster query failed: %s", e)
        return None
    for a in (roster.data or []):
        if a.get("slug") == agent_ref or a.get("role") == agent_ref:
            return a
    return None


async def _read_workspace_path(um, absolute_path: str) -> Optional[str]:
    """Read a workspace_files entry given an absolute /workspace/-prefixed path
    via the UserMemory abstraction. Returns None on miss or error."""
    if not absolute_path or not absolute_path.startswith("/workspace/"):
        return None
    relative = absolute_path[len("/workspace/"):]
    try:
        return await um.read(relative)
    except Exception:
        return None


async def _write_workspace_path(
    um,
    absolute_path: str,
    content: str,
    *,
    authored_by: str,
    message: str,
    summary: Optional[str] = None,
) -> bool:
    """Write a workspace_files entry given an absolute /workspace/-prefixed path
    via the UserMemory abstraction (which routes through ADR-209 write_revision)."""
    if not absolute_path or not absolute_path.startswith("/workspace/"):
        logger.warning("[DISPATCH] refusing to write non-/workspace/ path: %s", absolute_path)
        return False
    relative = absolute_path[len("/workspace/"):]
    try:
        return await um.write(
            relative,
            content,
            summary=summary,
            authored_by=authored_by,
            message=message,
        )
    except Exception as e:
        logger.error("[DISPATCH] write failed %s: %s", absolute_path, e)
        return False


async def _write_deliverable_output(
    *,
    um,
    decl: RecurrenceDeclaration,
    paths: ResolvedPaths,
    draft: str,
    agent_slug: str,
    version_id: str,
    version_number: int,
    usage: dict,
    started_at: datetime,
) -> None:
    """Write output.md + manifest.json to the natural-home output folder."""
    if not paths.output_path or not paths.output_folder:
        return

    # output.md
    await _write_workspace_path(
        um,
        paths.output_path,
        draft,
        authored_by=f"agent:{agent_slug}",
        message=f"produce v{version_number} for {decl.slug}",
        summary=f"{decl.slug} v{version_number}",
    )

    # manifest.json — natural-home substrate's per-firing metadata
    manifest = {
        "shape": decl.shape.value,
        "slug": decl.slug,
        "agent_slug": agent_slug,
        "version_id": version_id,
        "version_number": version_number,
        "created_at": started_at.isoformat(),
        "declaration_path": decl.declaration_path,
        "tokens": usage,
        "files": [
            {"path": "output.md", "type": "text/markdown", "role": "primary"},
        ],
    }
    manifest_path = f"{paths.output_folder}/manifest.json"
    await _write_workspace_path(
        um,
        manifest_path,
        _json.dumps(manifest, indent=2),
        authored_by="system:dispatcher",
        message=f"manifest for {decl.slug} v{version_number}",
        summary=f"manifest {decl.slug} v{version_number}",
    )


async def _append_run_log(
    *,
    um,
    paths: ResolvedPaths,
    slug: str,
    author: str,
    message: str,
) -> None:
    """Append a single line to the declaration's run log per ADR-231 D10."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = f"- [{timestamp}] [{slug}] {message}"
    existing = await _read_workspace_path(um, paths.run_log_path) or ""
    if existing:
        new_content = existing.rstrip() + "\n" + line + "\n"
    else:
        new_content = f"# Run Log\n\n{line}\n"
    await _write_workspace_path(
        um, paths.run_log_path, new_content,
        authored_by=author,
        message="append run log entry",
        summary="run log",
    )


async def _append_audit_log(um, audit_path: str, entry: str) -> None:
    """Append one entry to the shared back-office audit log per ADR-231 D2."""
    existing = await _read_workspace_path(um, audit_path) or ""
    if existing:
        new_content = existing.rstrip() + "\n\n" + entry + "\n"
    else:
        new_content = f"# Back Office Audit Log\n\n{entry}\n"
    await _write_workspace_path(
        um, audit_path, new_content,
        authored_by="system:dispatcher",
        message="back-office audit entry",
        summary="back-office audit",
    )


def _format_audit_entry(
    *,
    slug: str,
    executor: str,
    summary: str,
    actions_taken: list,
    output_markdown: str,
    started_at: datetime,
) -> str:
    """Render one back-office firing as an audit-log entry."""
    timestamp = started_at.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"## [{timestamp}] {slug}",
        f"- Executor: `{executor}`",
        f"- Summary: {summary}",
    ]
    if actions_taken:
        lines.append(f"- Actions: {len(actions_taken)}")
        for a in actions_taken[:5]:
            lines.append(f"  - {a}")
        if len(actions_taken) > 5:
            lines.append(f"  - ... and {len(actions_taken) - 5} more")
    if output_markdown:
        # Inline body trimmed to keep audit log readable; full output discarded
        # for back-office (the audit log IS the canonical surface per D10).
        excerpt = output_markdown.strip()
        if len(excerpt) > 1000:
            excerpt = excerpt[:1000] + "\n... [truncated]"
        lines.append("")
        lines.append(excerpt)
    return "\n".join(lines)


async def _emit_narrative(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    *,
    role: str,
    summary: str,
    body: Optional[str] = None,
    pulse: str,
    weight: str,
    paths: ResolvedPaths,
    invocation_id: Optional[str] = None,
    extra_metadata: Optional[dict] = None,
) -> None:
    """Emit one narrative entry per ADR-219.

    Identity rules per ADR-231 D11:
      - role='system' for dispatcher / scheduler / cost-gate messages
      - role='agent' for persona-bearing agent generation
      - role='reviewer' for Reviewer judgments
      - role='external' for MCP-driven invocations

    Provenance entries link operator-clickable substrate paths.
    """
    from services.narrative import write_narrative_entry, find_active_workspace_session

    session_id = find_active_workspace_session(client, user_id)
    if not session_id:
        logger.warning(
            "[DISPATCH] no active workspace session for user %s — narrative skipped",
            user_id[:8] if user_id else "?",
        )
        return

    provenance = []
    if paths.output_path:
        provenance.append({"path": paths.output_path, "kind": "output"})
    elif paths.substrate_root:
        provenance.append({"path": paths.substrate_root, "kind": "substrate_root"})
    if paths.run_log_path:
        provenance.append({"path": paths.run_log_path, "kind": "run_log"})
    if paths.feedback_path:
        provenance.append({"path": paths.feedback_path, "kind": "feedback"})
    provenance.append({"path": decl.declaration_path, "kind": "declaration"})

    extra = {"shape": decl.shape.value, "declaration_path": decl.declaration_path}
    if extra_metadata:
        extra.update(extra_metadata)

    try:
        write_narrative_entry(
            client,
            session_id,
            role=role,
            summary=summary,
            body=body,
            pulse=pulse,
            weight=weight,
            invocation_id=invocation_id,
            task_slug=decl.slug,  # ADR-219 D4: declaration slug serves as task_slug label
            provenance=provenance,
            extra_metadata=extra,
        )
    except Exception as e:
        logger.warning("[DISPATCH] narrative emission failed (non-fatal): %s", e)


def _generative_summary(decl: RecurrenceDeclaration, agent: dict, *, version: int) -> str:
    """One-line narrative summary for a generative invocation."""
    title = decl.display_name or decl.slug
    agent_slug = agent.get("slug", "agent")
    if decl.shape == RecurrenceShape.DELIVERABLE:
        return f"{title} delivered v{version} (by {agent_slug})"
    if decl.shape == RecurrenceShape.ACCUMULATION:
        return f"{title} accumulated v{version} (by {agent_slug})"
    if decl.shape == RecurrenceShape.ACTION:
        return f"{title} fired v{version} (by {agent_slug})"
    return f"{title} v{version}"


def _extract_recent_feedback(feedback_md: str, max_entries: int = 3) -> str:
    """Extract the last N feedback entries from feedback.md.

    Mirrors task_pipeline._extract_recent_feedback shape; ports here so
    the dispatcher is self-contained when task_pipeline.py dies in 3.7.
    """
    if not feedback_md:
        return ""
    blocks = []
    current: list[str] = []
    for line in feedback_md.splitlines():
        if line.startswith("## "):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        else:
            if current:
                current.append(line)
    if current:
        blocks.append("\n".join(current))
    if not blocks:
        return feedback_md.strip()
    return "\n\n".join(blocks[-max_entries:])


def _total_input_tokens(usage: dict) -> int:
    """Sum input + cache tokens for accounting parity with task_pipeline."""
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


def _result_paused(decl: RecurrenceDeclaration) -> dict:
    return {
        "success": False,
        "error": "paused",
        "message": (
            f"declaration '{decl.slug}' is paused; cannot dispatch. "
            f"Use UpdateContext(target='recurrence', action='resume', ...) to resume."
        ),
        "shape": decl.shape.value,
        "slug": decl.slug,
        "declaration_path": decl.declaration_path,
    }


def _result_failed(
    decl: RecurrenceDeclaration,
    message: str,
    *,
    paths: Optional[ResolvedPaths] = None,
) -> dict:
    return {
        "success": False,
        "error": "dispatch_failed",
        "message": message,
        "shape": decl.shape.value,
        "slug": decl.slug,
        "declaration_path": decl.declaration_path,
        "output_path": paths.output_path if paths else None,
    }


__all__ = ["dispatch", "find_declaration_for_agent"]
