"""
Invocation Dispatcher — ADR-260 + ADR-261 unified path.

ONE dispatch path. Per ADR-261 D3, the scheduler walks recurrences in
``/workspace/_recurrences.yaml`` and for each due (and not paused) entry
calls ``dispatch(client, user_id, recurrence)``. Per ADR-260 D1, this
function invokes the Reviewer with the recurrence's ``prompt`` as the
addressed-equivalent envelope; the Reviewer's real-time loop then runs.

There is no shape branching. There is no agent resolution at the
dispatcher level. There is no per-shape substrate writer. The Reviewer's
loop directs work via tool calls — including specialist sub-LLM-calls
through DispatchSpecialist (per ADR-261 D7, landing in Phase C.2) and
self-scheduling through Schedule (per ADR-261 §3 / Phase A.3).

Per ADR-260 D2 amended by ADR-263 D2 there are two Reviewer triggers:
  - "addressed"  operator addressed the Reviewer (chat path, not the
                  scheduler).
  - "reactive"   substrate event requires Reviewer judgment. Two sub-shapes
                  internally to invoke_reviewer (differentiated by context-bag
                  contents): proposal arrival (proposal_row in context) and
                  judgment-mode recurrence fire (recurrence_prompt in context).
                  Cron-fired Reviewer wakes use "reactive" — the recurrence
                  is the substrate event.

Per ADR-263, the recurrence's `mode` field declares whether a fire wakes the
Reviewer. Mechanical-mode recurrences are dispatched via `_dispatch_mechanical`
(no Reviewer, no LLM, deterministic Python primitive execution); judgment-mode
recurrences flow through the Reviewer-invocation path with trigger="reactive".

Per ADR-260 D3 cron has one use: fire recurrences. The recurrence's `mode`
determines whether the fire involves the Reviewer at all.

Cost gating:
  - Balance check (ADR-172) at dispatch entry; exit early on exhaustion.
  - Daily spend ceiling (ADR-250 Phase 3); exit early on scheduled
    triggers when ceiling reached, warn-but-proceed on manual triggers.

Failure discipline:
  Returns ``{success: bool, ...}`` always. On failure: narrative entry
  emits with a system-role bubble describing the failure; the scheduler
  index advances next_run_at so on-demand recurrences don't get stuck.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import sentry_sdk as _sentry
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

from services.recurrence import Recurrence
from services.telemetry import (
    record_execution_event,
    get_daily_spend,
    DAILY_SPEND_CEILING_USD,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def dispatch(
    client,
    user_id: str,
    recurrence: Recurrence,
    *,
    trigger: str = "reactive",
    context: Optional[str] = None,
) -> dict:
    """Fire one recurrence (mode=judgment → Reviewer; mode=mechanical → primitive).

    Per ADR-260 D1 + ADR-261 D3 + ADR-263:
    - Judgment-mode recurrences invoke the Reviewer with ``recurrence.prompt``
      as the addressed-equivalent envelope. The Reviewer's real-time loop runs
      synchronously to completion.
    - Mechanical-mode recurrences route to `_dispatch_mechanical` which parses
      the prompt's `@primitive: ...` directive and executes deterministically.
      No Reviewer, no LLM.

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        recurrence: parsed Recurrence to fire
        trigger: per ADR-260 D2 amended by ADR-263 D2 — one of "reactive"
                 (default; substrate event including cron-fired recurrences)
                 or "addressed" (operator addressed the Reviewer; rarely used
                 here — chat surfaces invoke the Reviewer directly).
        context: optional one-shot steering for this firing (appended to
                 the prompt). Does not mutate the recurrence record.

    Returns:
        ``{success: bool, slug, trigger, message, ...}`` — at minimum.
        ``actions_taken`` and ``proposals`` populated when the Reviewer's
        loop produced them.
    """
    if recurrence.paused:
        return _result_paused(recurrence, trigger)

    started_at = datetime.now(timezone.utc)

    # ADR-250: tag Sentry scope so any exception carries context
    if _SENTRY_AVAILABLE:
        with _sentry.configure_scope() as scope:
            scope.set_user({"id": user_id})
            scope.set_tag("recurrence_slug", recurrence.slug)
            scope.set_tag("trigger", trigger)
            scope.set_tag("recurrence_mode", recurrence.mode)

    logger.info(
        "[DISPATCH] %s/%s start (trigger=%s, mode=%s)",
        user_id[:8], recurrence.slug, trigger, recurrence.mode,
    )

    # ADR-263 D5 + ADR-264 D2: mechanical-mode recurrences run as deterministic
    # Python primitive invocations. The recurrence's prompt is expected to name
    # a primitive call via the @primitive: <Name>(<args>) convention. The
    # dispatcher parses the directive, looks up the handler, and executes it.
    # NO Reviewer invocation, NO LLM session, NO balance gate (mechanical work
    # has zero LLM cost so the balance check would be theatre).
    if recurrence.mode == "mechanical":
        return await _dispatch_mechanical(
            client, user_id, recurrence, trigger=trigger, context=context,
            started_at=started_at,
        )

    # ---- Balance gate (ADR-172) ----
    try:
        from services.platform_limits import check_balance
        balance_ok, _balance = check_balance(client, user_id)
    except Exception as e:
        logger.warning("[DISPATCH] balance check failed (proceeding): %s", e)
        balance_ok = True

    if not balance_ok:
        await _emit_system_narrative(
            client, user_id, recurrence,
            summary=f"{recurrence.slug} skipped: balance exhausted",
            trigger=trigger,
        )
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            mode="judgment",  # ADR-265: mode replaces dead shape discriminator
            trigger_type=trigger,
            status="failed", error_reason="balance_exhausted",
        )
        return _result_failed(recurrence, "balance exhausted", trigger=trigger)

    # ---- Daily spend ceiling (ADR-250 Phase 3) ----
    try:
        daily_spend = get_daily_spend(client, user_id)
    except Exception:
        daily_spend = 0.0

    if daily_spend >= DAILY_SPEND_CEILING_USD:
        warning = (
            f"Daily spend ceiling reached (${daily_spend:.2f} / "
            f"${DAILY_SPEND_CEILING_USD:.2f}). {recurrence.slug} skipped."
        )
        logger.warning("[DISPATCH] %s", warning)
        # ADR-263: cron-fired recurrences (the prior `scheduled` trigger value)
        # now flow as `reactive`. Both reactive sub-shapes get the silent-skip
        # treatment when the ceiling is reached; only true `addressed` (operator
        # at the keyboard) gets the warn-but-proceed override.
        if trigger == "reactive":
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=f"Spend ceiling reached — {recurrence.slug} skipped",
                body=(
                    f"{recurrence.slug} was due but today's spend "
                    f"(${daily_spend:.2f}) has reached the daily ceiling "
                    f"(${DAILY_SPEND_CEILING_USD:.2f}). Run skipped. "
                    f"Resets at midnight UTC."
                ),
                trigger=trigger,
            )
            record_execution_event(
                client, user_id=user_id, slug=recurrence.slug,
                mode="judgment", trigger_type=trigger,
                status="skipped", error_reason="spend_ceiling",
                error_detail=warning,
            )
            return _result_failed(recurrence, warning, trigger=trigger)
        else:
            # Manual trigger: warn but proceed
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=f"Spend ceiling warning — {recurrence.slug} running (manual)",
                body=f"Daily ceiling ${DAILY_SPEND_CEILING_USD:.2f} reached, but running anyway (manual trigger). Today: ${daily_spend:.2f}.",
                trigger=trigger,
            )

    # ---- Build the Reviewer prompt envelope ----
    # Per ADR-261 D1: the recurrence's prompt IS what reaches the Reviewer.
    # We add only optional one-shot context (FireInvocation steering).
    prompt = recurrence.prompt
    if context and context.strip():
        prompt = (
            f"{prompt}\n\n"
            f"## One-shot steering (this firing only)\n{context.strip()}"
        )

    # ---- Invoke the Reviewer ----
    # Per ADR-260 D1: synchronous real-time tool-use loop. The Reviewer's
    # loop blocks until ReturnVerdict (or round bound).
    try:
        from agents.reviewer_agent import invoke_reviewer
    except ImportError as e:
        logger.exception("[DISPATCH] reviewer_agent not importable: %s", e)
        return _result_failed(recurrence, f"reviewer_agent unavailable: {e}", trigger=trigger)

    try:
        # Context keys must match what invoke_reviewer reads at
        # `reviewer_agent.py::_build_user_message`. The Reviewer's
        # `is_recurrence_fire` detection (reviewer_agent.py:573) keys
        # on `recurrence_prompt` / `recurrence_slug` — passing bare
        # `prompt` / `slug` here would silently drop the recurrence
        # context, causing every cron-fired Reviewer wake to fall into
        # the proposal-arrival shape (Sonnet/3-rounds with empty user
        # message → universal stand_down). Bug surfaced 2026-05-13 in
        # the post-ADR-267 audit.
        # ADR-274 / FOUNDATIONS v8.5: assemble Operating Context block —
        # time + market state + workspace tenure. Reviewer perceives `now`
        # on every wake (time is envelope, not substrate per Axiom 4 amendment).
        from agents.reviewer_agent import build_operating_context_block
        operating_context = build_operating_context_block(client, user_id)

        reviewer_output = await invoke_reviewer(
            client=client,
            user_id=user_id,
            trigger=trigger,
            context={
                "recurrence_prompt": prompt,
                "recurrence_slug": recurrence.slug,
                # ADR-269: capability flow — recurrence declares the
                # program-specific capabilities its dispatched specialists
                # need. Reviewer reads this from context envelope and
                # passes through (or extends) when calling DispatchSpecialist.
                "recurrence_required_capabilities": list(recurrence.required_capabilities),
                "options": dict(recurrence.options) if recurrence.options else {},
                "operating_context_block": operating_context,
            },
        )
    except Exception as exc:
        logger.exception("[DISPATCH] %s/%s reviewer raised: %s", user_id[:8], recurrence.slug, exc)
        if _SENTRY_AVAILABLE:
            _sentry.capture_exception(exc)
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            mode="judgment", trigger_type=trigger,
            status="failed", error_reason="exception",
            error_detail=str(exc), duration_ms=duration_ms,
        )
        await _emit_system_narrative(
            client, user_id, recurrence,
            summary=f"{recurrence.slug} failed",
            body=f"Reviewer invocation raised: {exc}",
            trigger=trigger,
        )
        return _result_failed(recurrence, str(exc), trigger=trigger)

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    record_execution_event(
        client, user_id=user_id, slug=recurrence.slug,
        mode="judgment", trigger_type=trigger,
        status="success", duration_ms=duration_ms,
    )

    actions_taken = []
    proposals = []
    verdict_summary = ""
    reviewer_identity = "ai:reviewer"
    if isinstance(reviewer_output, dict):
        actions_taken = reviewer_output.get("actions_taken", []) or []
        proposals = reviewer_output.get("proposals", []) or []
        # The Reviewer's tool schema requires `reasoning` ("2-5 sentences in
        # your persona's voice ... Written verbatim to decisions.md") for
        # every verdict. Reading `evidence_summary or verdict` here (prior
        # behavior) discarded the prose for non-reflection verdicts and
        # wrote only the enum string ("stand_down") to decisions.md —
        # making every recurrence-fire entry indistinguishable regardless
        # of the actual reasoning. Bug surfaced 2026-05-13 in the post-
        # ADR-267 verdict-quality audit (Problem A).
        #
        # Read order: `reasoning` is the primary audit text. When the
        # Reviewer additionally returned `evidence_summary` (reflection-
        # shape output per ADR-263), append it as a citations block —
        # both fields end up in decisions.md, not one substituted for
        # the other.
        reasoning_text = (reviewer_output.get("reasoning") or "").strip()
        evidence_text = (reviewer_output.get("evidence_summary") or "").strip()
        if reasoning_text and evidence_text:
            verdict_summary = f"{reasoning_text}\n\n**Evidence summary:**\n{evidence_text}"
        elif reasoning_text:
            verdict_summary = reasoning_text
        elif evidence_text:
            verdict_summary = evidence_text
        else:
            # Fallback to the verdict enum string only when the Reviewer
            # somehow returned neither prose field (should never happen —
            # reasoning is `required` in the tool schema, and the early-
            # exit at reviewer_agent.py:864 already rejects empty
            # reasoning before this code runs).
            verdict_summary = reviewer_output.get("verdict") or ""
        reviewer_identity = reviewer_output.get("reviewer_identity") or reviewer_identity

    # FOUNDATIONS v8.4 Axiom 1 (substrate-as-bus): persist Reviewer's verdict +
    # reasoning to /workspace/review/decisions.md so a later Reviewer
    # read-from-substrate (the next Loop wake) can recover what was decided.
    # Without this, the Reviewer's reasoning lives only in the tool-result
    # dict returned to the caller — a parallel control-flow channel that
    # violates the substrate-as-bus invariant. Best-effort; never raises.
    try:
        from services.reviewer_audit import append_recurrence_fire
        await append_recurrence_fire(
            client, user_id,
            slug=recurrence.slug,
            trigger=trigger,
            reviewer_identity=reviewer_identity,
            reasoning=verdict_summary,
            duration_ms=duration_ms,
            actions_count=len(actions_taken),
            proposals_count=len(proposals),
        )
    except Exception as exc:  # noqa: BLE001 — substrate audit must not break dispatch
        logger.warning(
            "[DISPATCH] %s/%s recurrence-fire substrate write failed: %s",
            user_id[:8], recurrence.slug, exc,
        )

    # FOUNDATIONS Axiom 9 + Derived Principle 12 (channel legibility gates
    # autonomy): emit one narrative entry per System Agent invocation the
    # Reviewer fired during the Loop wake-up. Same per-action narration the
    # proposal-arrival path uses (review_proposal_dispatch.py:373); cron-
    # fired reactive wakes were silent prior to FOUNDATIONS v8.4. Best-effort.
    try:
        from services.reviewer_chat_surfacing import surface_reviewer_actions
        await surface_reviewer_actions(
            client, user_id,
            actions_taken=actions_taken,
        )
    except Exception as exc:  # noqa: BLE001 — narration is legibility, not control-flow
        logger.warning(
            "[DISPATCH] %s/%s narration emission failed: %s",
            user_id[:8], recurrence.slug, exc,
        )

    # ADR-262 D4: opt-out structural auto-compose at session-close.
    # When the Reviewer wrote section partials matching the deliverable
    # convention, auto-run Compose unless the recurrence opted out via
    # options.skip_compose: true. Failure is logged + non-fatal — the
    # session result is preserved.
    composed_path = await _maybe_auto_compose(client, user_id, recurrence)

    logger.info(
        "[DISPATCH] %s/%s done (%dms) — actions=%d proposals=%d compose=%s",
        user_id[:8], recurrence.slug, duration_ms,
        len(actions_taken), len(proposals),
        composed_path or "—",
    )

    return {
        "success": True,
        "slug": recurrence.slug,
        "trigger": trigger,
        "duration_ms": duration_ms,
        "actions_taken": actions_taken,
        "proposals": proposals,
        "composed_html_path": composed_path,
        "summary": verdict_summary or f"{recurrence.slug} completed",
        "message": verdict_summary or f"{recurrence.slug} completed",
    }


# ---------------------------------------------------------------------------
# Mechanical recurrence dispatch (ADR-263 D5 + ADR-264 D2)
# ---------------------------------------------------------------------------

import re as _re

# Match: @primitive: <Name>(<args>) — args parsed as a Python literal-ish
# kwarg expression (yaml.safe_load on the args body for type fidelity).
# Example match: @primitive: SyncPlatformState(
#     tool="platform_trading_get_positions",
#     write_to="context/portfolio/positions/{symbol}.yaml"
# )
_PRIMITIVE_DIRECTIVE_RE = _re.compile(
    r"@primitive:\s*(\w+)\s*\((.*?)\)\s*$",
    _re.DOTALL,
)


def _parse_primitive_directive(prompt: str) -> Optional[tuple[str, dict]]:
    """Parse a `@primitive: <Name>(<args>)` directive from a mechanical
    recurrence's prompt body. Returns (primitive_name, kwargs_dict) or None
    if the prompt doesn't contain a parseable directive.

    Args body is parsed by wrapping the kwarg expression in YAML mapping
    syntax — operators write Python-flavored kwargs (`tool="...", write_to="..."`),
    which we coerce to YAML by replacing `=` with `:` at top level. This
    keeps the operator syntax close to LLM tool-call vocabulary while
    sidestepping a custom parser.
    """
    if not prompt:
        return None
    text = prompt.strip()
    m = _PRIMITIVE_DIRECTIVE_RE.search(text)
    if not m:
        return None
    primitive_name = m.group(1)
    args_body = m.group(2).strip()
    if not args_body:
        return (primitive_name, {})

    # Coerce Python-style kwargs to YAML mapping body. Naive transform:
    # `key="value"` → `key: "value"`. Conservative — only operates on
    # top-level `=` adjacent to identifier characters.
    yaml_body = _re.sub(r"(\b\w+)\s*=\s*", r"\1: ", args_body)
    try:
        import yaml as _yaml
        # Wrap in braces to ensure flow-style mapping parse
        parsed = _yaml.safe_load("{" + yaml_body + "}")
    except Exception as e:
        logger.warning(
            "[DISPATCH:mechanical] failed to parse @primitive args: %s | body=%r",
            e, args_body,
        )
        return None
    if not isinstance(parsed, dict):
        logger.warning(
            "[DISPATCH:mechanical] @primitive args did not parse to a dict: %r", parsed,
        )
        return None
    return (primitive_name, parsed)


# ---------------------------------------------------------------------------
# Capability gate helpers (ADR-263 amendment 2026-05-12)
#
# Mechanical primitives that wrap platform APIs (SyncPlatformState today;
# others later) can be derived to a required platform_connections.platform
# value from their args. The dispatcher checks the connection before firing
# and skips with capability_missing when absent — preventing per-minute
# credential-failure feed spam on workspaces that have a recurrence
# scheduled but no platform connected.
#
# Detection is convention-based (no schema bump): every platform tool name
# is `platform_<name>_<verb>` and `platform_connections.platform` stores
# `<name>` (slack | notion | github | commerce | trading). One-line parser.
# ---------------------------------------------------------------------------


def _required_platform_for_primitive(
    primitive_name: str, primitive_args: dict
) -> Optional[str]:
    """Derive the required platform_connections.platform value (e.g. "trading")
    from a mechanical primitive's args, or None if the primitive doesn't
    depend on a platform connection.

    Today only SyncPlatformState (ADR-264) needs this — its `tool` arg names
    a platform tool 1:1 with the connection record. Future platform-bound
    primitives can be added here without changing the dispatcher gate
    structure.
    """
    if primitive_name != "SyncPlatformState":
        return None
    tool = (primitive_args or {}).get("tool")
    if not isinstance(tool, str) or not tool.startswith("platform_"):
        return None
    # platform_<name>_<verb> → <name>
    parts = tool.split("_", 2)
    if len(parts) < 3:
        return None
    return parts[1]


def _platform_connection_active(
    client, user_id: str, platform: str
) -> bool:
    """True iff the user has an active platform_connections row for `platform`.
    Fail-closed: any DB error returns False (treat as missing — better to
    skip than to fire-and-fail on broken auth)."""
    try:
        result = (
            client.table("platform_connections")
            .select("id")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning(
            "[DISPATCH:cap-gate] platform_connections lookup failed for %s/%s: %s",
            user_id[:8], platform, e,
        )
        return False


def _last_skip_reason(client, user_id: str, slug: str) -> Optional[str]:
    """Most-recent execution_events.error_reason for this slug — used by the
    capability gate to emit a narrative entry only on transition (first
    detection of capability_missing) and stay silent on subsequent firings.
    Returns None on no-history or DB error (treat as transition — emit once)."""
    try:
        result = (
            client.table("execution_events")
            .select("error_reason")
            .eq("user_id", user_id)
            .eq("slug", slug)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        return rows[0].get("error_reason")
    except Exception as e:
        logger.warning(
            "[DISPATCH:cap-gate] last_skip_reason lookup failed for %s/%s: %s",
            user_id[:8], slug, e,
        )
        return None


async def _dispatch_mechanical(
    client,
    user_id: str,
    recurrence: Recurrence,
    *,
    trigger: str,
    context: Optional[str],
    started_at: datetime,
) -> dict:
    """Execute a mechanical-mode recurrence (ADR-263 + ADR-264).

    The recurrence's `prompt` is expected to name a primitive invocation
    via `@primitive: <Name>(<args>)`. The dispatcher parses, looks up the
    handler in HANDLERS, and executes it.

    No Reviewer involvement. No LLM session. Substrate writes happen via
    the primitive's normal write path with the primitive's authoring
    attribution (e.g., `system:sync-platform-state`).
    """
    parsed = _parse_primitive_directive(recurrence.prompt)
    if parsed is None:
        msg = (
            f"mechanical recurrence {recurrence.slug!r} has no parseable "
            f"@primitive: directive in its prompt"
        )
        logger.warning("[DISPATCH:mechanical] %s", msg)
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            mode="mechanical", trigger_type=trigger,
            status="failed", error_reason="no_primitive_directive",
            error_detail=msg,
        )
        return _result_failed(recurrence, msg, trigger=trigger)

    primitive_name, primitive_args = parsed

    # Capability gate (ADR-263 amendment 2026-05-12): when a mechanical primitive
    # depends on a platform connection that isn't active, skip without firing
    # the primitive. Detection is derived from primitive args (no schema bump):
    # SyncPlatformState's `tool="platform_<name>_..."` argument names the
    # required platform 1:1 with platform_connections.platform.
    #
    # Suppression rule: emit ONE narrative entry on the transition firing
    # (prior status was anything other than capability_missing); subsequent
    # firings remain silent until the operator either connects the platform
    # or pauses the recurrence. Eliminates per-minute feed spam without
    # losing first-detection signal.
    required_platform = _required_platform_for_primitive(primitive_name, primitive_args)
    if required_platform and not _platform_connection_active(client, user_id, required_platform):
        prior_reason = _last_skip_reason(client, user_id, recurrence.slug)
        is_transition = prior_reason != "capability_missing"
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            mode="mechanical", trigger_type=trigger,
            status="skipped", error_reason="capability_missing",
            error_detail=f"required platform {required_platform!r} not connected",
        )
        if is_transition:
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=(
                    f"{recurrence.slug} paused — {required_platform.title()} not connected"
                ),
                body=(
                    f"`{recurrence.slug}` requires the {required_platform.title()} platform "
                    f"to be connected. Reconnect at /settings?tab=connectors, or pause this "
                    f"recurrence in /workspace/_recurrences.yaml. Subsequent firings will "
                    f"stay silent until either action is taken."
                ),
                trigger=trigger,
            )
        else:
            logger.info(
                "[DISPATCH:mechanical] %s/%s skipped (capability_missing, silent — repeat)",
                user_id[:8], recurrence.slug,
            )
        return _result_failed(
            recurrence,
            f"capability_missing: {required_platform}",
            trigger=trigger,
            error_reason="capability_missing",
        )

    # Look up the handler in the central HANDLERS dict.
    try:
        from services.primitives.registry import HANDLERS
    except ImportError as e:
        logger.exception("[DISPATCH:mechanical] HANDLERS import failed: %s", e)
        return _result_failed(recurrence, f"registry import failed: {e}", trigger=trigger)

    handler = HANDLERS.get(primitive_name)
    if handler is None:
        msg = (
            f"mechanical recurrence {recurrence.slug!r} names unknown primitive "
            f"{primitive_name!r}"
        )
        logger.warning("[DISPATCH:mechanical] %s", msg)
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            mode="mechanical", trigger_type=trigger,
            status="failed", error_reason="unknown_primitive",
            error_detail=msg,
        )
        return _result_failed(recurrence, msg, trigger=trigger)

    # Build a minimal auth-shaped object for the primitive handler.
    # Mechanical dispatch runs as the system actor under the workspace owner's
    # user_id; the handler's writes will be attributed by the primitive itself
    # (e.g., SyncPlatformState writes `authored_by="system:sync-platform-state"`).
    class _MechanicalAuth:
        def __init__(self, user_id: str, client):
            self.user_id = user_id
            self.client = client
    auth = _MechanicalAuth(user_id=user_id, client=client)

    try:
        result = await handler(auth, primitive_args)
    except Exception as e:
        logger.exception(
            "[DISPATCH:mechanical] %s/%s primitive %s raised: %s",
            user_id[:8], recurrence.slug, primitive_name, e,
        )
        if _SENTRY_AVAILABLE:
            _sentry.capture_exception(e)
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            mode="mechanical", trigger_type=trigger,
            status="failed", error_reason="primitive_raised",
            error_detail=str(e), duration_ms=duration_ms,
        )
        return _result_failed(recurrence, str(e), trigger=trigger)

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    success = bool(result.get("success", False)) if isinstance(result, dict) else False
    status = "success" if success else "failed"

    record_execution_event(
        client, user_id=user_id, slug=recurrence.slug,
        mode="mechanical", trigger_type=trigger,
        status=status, duration_ms=duration_ms,
        error_reason=None if success else (result.get("error") if isinstance(result, dict) else None),
    )

    # FOUNDATIONS Axiom 9: every invocation emits a narrative entry. Mechanical
    # recurrences ARE invocations (Axiom 9 + ADR-263) and emit ONE housekeeping-
    # weight entry per successful fire. The narrative_digest rolls these up
    # into daily roll-ups; per-fire entries stay weight-gated out of
    # material/routine FE rendering by default.
    #
    # Failure suppression (ADR-263 amendment 2026-05-12): per-fire narrative
    # is success-only. Failed runs already land an execution_events row;
    # emitting a per-fire feed entry every failure produced the
    # ~1 entry/minute "background:" spam from credentialled-but-broken
    # mirrors. The capability gate above handles transition emission for
    # the common missing-credentials case; transient/unexpected failures
    # remain visible via execution_events without flooding the feed.
    if success:
        summary = _summarize_mechanical_result(primitive_name, result)
        await _emit_system_narrative(
            client, user_id, recurrence,
            summary=summary,
            trigger=trigger,
            weight="housekeeping",
        )

    logger.info(
        "[DISPATCH:mechanical] %s/%s done (status=%s duration_ms=%d primitive=%s)",
        user_id[:8], recurrence.slug, status, duration_ms, primitive_name,
    )

    # Propagate inner-result `error` field as `error_reason` so the
    # scheduler's record_task_run can recognize capability_missing and
    # preserve fire_on_activation arming (cold-start ordering fix). The
    # dispatcher's capability gate only covers SyncPlatformState; primitives
    # like TrackUniverse/TrackRegime that self-load credentials report
    # capability_missing from inside the handler and would otherwise be
    # invisible to record_task_run.
    error_reason = None
    if not success and isinstance(result, dict):
        error_reason = result.get("error")
    return {
        "success": success,
        "slug": recurrence.slug,
        "trigger": trigger,
        "mode": "mechanical",
        "primitive": primitive_name,
        "result": result,
        "duration_ms": duration_ms,
        "error_reason": error_reason,
    }


def _summarize_mechanical_result(primitive_name: str, result) -> str:
    """One-line summary of a mechanical-fire result for the housekeeping
    narrative entry. Falls back to a generic summary when the primitive's
    result shape isn't recognized.
    """
    if not isinstance(result, dict):
        return f"{primitive_name} completed"
    success = bool(result.get("success", False))
    if not success:
        err = result.get("error") or "unknown error"
        return f"{primitive_name} failed: {err}"
    # SyncPlatformState returns paths_written + paths_skipped + items_processed
    paths_written = result.get("paths_written")
    paths_skipped = result.get("paths_skipped")
    if isinstance(paths_written, list) and isinstance(paths_skipped, list):
        return (
            f"{primitive_name}: {len(paths_written)} written, "
            f"{len(paths_skipped)} unchanged"
        )
    items = result.get("items_processed")
    if isinstance(items, int):
        return f"{primitive_name}: {items} items processed"
    return f"{primitive_name} completed"


# ---------------------------------------------------------------------------
# Narrative emission — shared system-role surface
# ---------------------------------------------------------------------------


async def _emit_system_narrative(
    client,
    user_id: str,
    recurrence: Recurrence,
    *,
    summary: str,
    body: str = "",
    trigger: str,
    weight: Optional[str] = None,
) -> None:
    """Emit a system-role narrative entry for dispatcher-level events
    (skip / failure / spend-ceiling / mechanical-fire). Reviewer-bubble
    narration of judgment-mode work happens inside surface_reviewer_actions,
    not here.

    2026-05-11 audit-pass-2 fix: the prior implementation called
    write_narrative_entry with kwargs that didn't match the signature
    (user_id, authored_by, metadata vs the real session_id, extra_metadata,
    weight). Every call silently failed under the broad except — including
    skip/failure events the audit assumed were emitting. Fixed: resolve
    session_id via find_active_workspace_session and call with correct
    kwargs.
    """
    try:
        from services.narrative import (
            find_active_workspace_session,
            write_narrative_entry,
        )
    except ImportError:
        logger.warning("[DISPATCH] narrative module unavailable; skipping entry")
        return

    try:
        session_id = find_active_workspace_session(client, user_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("[DISPATCH] session lookup failed: %s", e)
        return
    if not session_id:
        # No active session — no operator-facing surface to write to.
        return

    try:
        write_narrative_entry(
            client,
            session_id,
            role="system",
            summary=summary,
            body=body or summary,
            pulse="reactive" if trigger == "reactive" else "addressed",
            weight=weight,  # type: ignore[arg-type]
            extra_metadata={
                "recurrence_slug": recurrence.slug,
                "trigger": trigger,
            },
        )
    except Exception as e:
        logger.warning("[DISPATCH] narrative emit failed: %s", e)


# ---------------------------------------------------------------------------
# Auto-compose at session-close (ADR-262 D4 opt-out structural default)
# ---------------------------------------------------------------------------


async def _maybe_auto_compose(
    client,
    user_id: str,
    recurrence: Recurrence,
) -> Optional[str]:
    """Auto-run Compose when section partials exist and the recurrence
    didn't opt out. Returns the composed HTML's absolute path on success,
    None when the auto-trigger didn't fire (no partials, opt-out,
    already composed) or on failure.

    Per ADR-262 D4 the trigger is structural (substrate-shape based),
    not LLM-judged. Failure modes:
      - section partials absent → no-op (None)
      - options.skip_compose: true → no-op (None)
      - output.html already present + newer than the latest partial →
        no-op (idempotency: don't recompose unchanged substrate)
      - render service errors → log + return None (Reviewer's session
        success is preserved; operator can re-trigger composition manually
        via the Compose primitive)
    """
    from services.conventions import (
        report_dated_folder,
        report_output_html_path,
        report_root,
        report_sections_dir,
    )

    if (recurrence.options or {}).get("skip_compose"):
        return None

    substrate_root = report_root(recurrence.slug)

    # Find the most recent dated folder containing section partials.
    try:
        rows = (
            client.table("workspace_files")
            .select("path,updated_at")
            .eq("user_id", user_id)
            .like("path", f"{substrate_root}/%/sections/%.md")
            .order("updated_at", desc=True)
            .limit(50)
            .execute()
        ).data or []
    except Exception as e:
        logger.warning(
            "[AUTO_COMPOSE] section scan failed for %s: %s",
            recurrence.slug, e,
        )
        return None

    if not rows:
        return None

    # Group by dated folder; pick the most-recent folder (by latest section update)
    dated_folders: dict[str, str] = {}  # date_token → most recent updated_at
    prefix = f"{substrate_root}/"
    for row in rows:
        path = row.get("path") or ""
        if not path.startswith(prefix):
            continue
        rel = path[len(prefix):]
        date_token = rel.split("/", 1)[0]
        if date_token not in dated_folders:
            dated_folders[date_token] = row.get("updated_at") or ""

    if not dated_folders:
        return None

    # Newest folder wins
    date_token = max(dated_folders.keys(), key=lambda k: dated_folders[k])
    sections_dir = f"{report_root(recurrence.slug)}/{date_token}/sections"
    output_html_path = f"{report_root(recurrence.slug)}/{date_token}/output.html"
    latest_section_at = dated_folders[date_token]

    # Idempotency: skip when output.html already exists AND is newer than
    # the latest section partial.
    try:
        existing = (
            client.table("workspace_files")
            .select("updated_at")
            .eq("user_id", user_id)
            .eq("path", output_html_path)
            .limit(1)
            .execute()
        ).data or []
        if existing:
            existing_at = existing[0].get("updated_at") or ""
            if existing_at and existing_at >= latest_section_at:
                logger.info(
                    "[AUTO_COMPOSE] %s/%s output.html newer than partials — skip",
                    user_id[:8], recurrence.slug,
                )
                return output_html_path
    except Exception as e:
        logger.warning(
            "[AUTO_COMPOSE] idempotency probe failed for %s: %s",
            recurrence.slug, e,
        )

    # Compose
    try:
        from services.compose.task_html import compose_task_output_html
        html = await compose_task_output_html(
            client, user_id,
            task_slug=recurrence.slug,
            date_folder=date_token,
        )
    except Exception as e:
        logger.warning(
            "[AUTO_COMPOSE] %s/%s compose failed: %s",
            user_id[:8], recurrence.slug, e,
        )
        return None

    if not html:
        return None

    # Write output.html via authored substrate
    try:
        from services.authored_substrate import write_revision
        write_revision(
            client,
            user_id=user_id,
            path=output_html_path,
            content=html,
            authored_by="system:auto-compose",
            message=(
                f"auto-compose {recurrence.slug}/{date_token} "
                f"({len(html)} bytes) per ADR-262 D4"
            ),
            content_type="text/html",
        )
    except Exception as e:
        logger.warning(
            "[AUTO_COMPOSE] %s/%s write_revision failed: %s",
            user_id[:8], recurrence.slug, e,
        )
        return None

    logger.info(
        "[AUTO_COMPOSE] %s/%s wrote %s (%d bytes)",
        user_id[:8], recurrence.slug, output_html_path, len(html),
    )
    return output_html_path


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _result_paused(recurrence: Recurrence, trigger: str) -> dict:
    return {
        "success": True,
        "slug": recurrence.slug,
        "trigger": trigger,
        "skipped": True,
        "message": f"recurrence {recurrence.slug} is paused",
    }


def _result_failed(
    recurrence: Recurrence,
    message: str,
    *,
    trigger: str,
    error_reason: Optional[str] = None,
) -> dict:
    """Build a failed-result envelope.

    error_reason is a structured tag the scheduler reads to decide
    whether to preserve `fire_on_activation` arming. Default None means
    "ordinary failure — consume the activation flag as usual."
    `"capability_missing"` means "platform connection unavailable — the
    work didn't happen, so don't consume the activation flag" (per the
    cold-start ordering fix).
    """
    return {
        "success": False,
        "slug": recurrence.slug,
        "trigger": trigger,
        "message": message,
        "error_reason": error_reason,
    }


__all__ = ["dispatch"]
