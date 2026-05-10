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
            shape="recurrence",  # ADR-261: shape is no longer a discriminator
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
                shape="recurrence", trigger_type=trigger,
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
        reviewer_output = await invoke_reviewer(
            client=client,
            user_id=user_id,
            trigger=trigger,
            context={
                "prompt": prompt,
                "slug": recurrence.slug,
                "options": dict(recurrence.options) if recurrence.options else {},
            },
        )
    except Exception as exc:
        logger.exception("[DISPATCH] %s/%s reviewer raised: %s", user_id[:8], recurrence.slug, exc)
        if _SENTRY_AVAILABLE:
            _sentry.capture_exception(exc)
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            shape="recurrence", trigger_type=trigger,
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
        shape="recurrence", trigger_type=trigger,
        status="success", duration_ms=duration_ms,
    )

    # ADR-262 D4: opt-out structural auto-compose at session-close.
    # When the Reviewer wrote section partials matching the deliverable
    # convention, auto-run Compose unless the recurrence opted out via
    # options.skip_compose: true. Failure is logged + non-fatal — the
    # session result is preserved.
    composed_path = await _maybe_auto_compose(client, user_id, recurrence)

    actions_taken = []
    proposals = []
    verdict_summary = ""
    if isinstance(reviewer_output, dict):
        actions_taken = reviewer_output.get("actions_taken", []) or []
        proposals = reviewer_output.get("proposals", []) or []
        verdict_summary = reviewer_output.get("evidence_summary") or reviewer_output.get("verdict") or ""

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
            shape="recurrence", trigger_type=trigger,
            status="failed", error_reason="no_primitive_directive",
            error_detail=msg,
        )
        return _result_failed(recurrence, msg, trigger=trigger)

    primitive_name, primitive_args = parsed

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
            shape="recurrence", trigger_type=trigger,
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
            shape="recurrence", trigger_type=trigger,
            status="failed", error_reason="primitive_raised",
            error_detail=str(e), duration_ms=duration_ms,
        )
        return _result_failed(recurrence, str(e), trigger=trigger)

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    success = bool(result.get("success", False)) if isinstance(result, dict) else False
    status = "success" if success else "failed"

    record_execution_event(
        client, user_id=user_id, slug=recurrence.slug,
        shape="recurrence", trigger_type=trigger,
        status=status, duration_ms=duration_ms,
        error_reason=None if success else (result.get("error") if isinstance(result, dict) else None),
    )

    logger.info(
        "[DISPATCH:mechanical] %s/%s done (status=%s duration_ms=%d primitive=%s)",
        user_id[:8], recurrence.slug, status, duration_ms, primitive_name,
    )

    return {
        "success": success,
        "slug": recurrence.slug,
        "trigger": trigger,
        "mode": "mechanical",
        "primitive": primitive_name,
        "result": result,
        "duration_ms": duration_ms,
    }


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
) -> None:
    """Emit a system-role narrative entry for dispatcher-level events
    (skip / failure / spend-ceiling). Reviewer-bubble narration of the
    actual work happens inside the Reviewer's loop, not here."""
    try:
        from services.narrative import write_narrative_entry
    except ImportError:
        logger.warning("[DISPATCH] narrative module unavailable; skipping entry")
        return

    try:
        await write_narrative_entry(
            client,
            user_id=user_id,
            role="system",
            summary=summary,
            body=body or summary,
            authored_by="system:dispatcher",
            metadata={
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


def _result_failed(recurrence: Recurrence, message: str, *, trigger: str) -> dict:
    return {
        "success": False,
        "slug": recurrence.slug,
        "trigger": trigger,
        "message": message,
    }


__all__ = ["dispatch"]
