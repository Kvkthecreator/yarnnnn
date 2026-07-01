"""
services/wake.py — Singular invocation gateway (ADR-296 v2).

Per ADR-296 v2 D1, wake is the irreducible architectural unit of YARNNN's
autonomy: something changed in the world or worldview, and under the
operator's standing intent that change warrants a moment of judgment.
This module is THE entry point for every Reviewer wake — there is no
parallel path.

`submit_wake_proposal(client, user_id, source, payload)` is the singular
public API. Five wake sources contribute proposals to one evaluation
funnel; the Reviewer's full cycle fires only when the funnel escalates:

  - cron_tick         scheduler walked a due recurrence
  - addressed         operator addressed the Reviewer via chat (streaming)
  - proposal_arrival  proposal creation woke Reviewer for judgment
  - substrate_event   /workspace/_hooks.yaml match — substrate transition
                       operator/Reviewer declared interest in
  - manual_fire       operator explicitly fired via FireInvocation in chat

Evaluation (per ADR-296 v2 D2) is two tiers, both inside `submit_wake_proposal`:

  - Tier 1 deterministic (zero LLM) — given source + payload + budget +
    standing intent + recent-fire history: skip | tier_2 | escalate.
  - Tier 2 cheap Haiku — when Tier 1 returns "tier_2", a minimal-envelope
    LLM call decides wait | observe | escalate.

Only on `escalate` does the Reviewer's full real-time loop run. The
funnel decision stamps every execution_events row via the wake_source +
funnel_decision columns (migration 177).

Per ADR-296 v2 D3 the Reviewer's authority is over cadence preference +
standing intent. It does not invoke itself by name. FireInvocation lives
in CHAT_PRIMITIVES (operator manual fire path); it routes through the
`manual_fire` wake source. The Reviewer's mid-loop primitives are
Schedule + WriteFile + ProposeAction + DispatchSpecialist + Compose +
reads + Clarify + ReturnVerdict.

Per ADR-263, the recurrence's `mode` field declares whether a fire wakes
the Reviewer. Mechanical-mode recurrences bypass Reviewer invocation via
the `mechanical` funnel decision (deterministic Python primitive
execution; no LLM); judgment-mode recurrences flow through the Reviewer-
invocation path on `escalate`.

Cost gating (Tier 1 deterministic — these are kernel pre-conditions that
short-circuit the funnel to "skip"):
  - Balance check (ADR-172)
  - Daily spend ceiling (ADR-293 D7 / ADR-250 Phase 3)
  - Daily judgment-recurrence cap (ADR-293 D7)
  - Per-slug min-interval (ADR-293 D7)

Fire-frequency gate partition (ADR-313): the gates above are the
TOKEN-BUDGET half — COST (daily $ + daily fire count) + PER-SLUG FLOOR
(min_interval_for(slug)). They are sequential with, not redundant to, the
PACE drain-lane-rate gate in `services/wake_drainer.py` (ADR-298/301). A
wake must satisfy the pace lane to be pulled, then satisfy token-budget to
fire. `pace.min_interval_seconds` is a workspace-wide drain interval;
`token_budget.min_interval_for(slug)` is a per-recurrence floor — same
word, different layer, different scope. See ADR-313 for the canonical
partition statement.

Failure discipline: every public entry returns `{success: bool, ...}`.
Reviewer exceptions emit a system-role narrative entry; the scheduler
index advances next_run_at so on-demand recurrences don't get stuck.

Streaming: the `addressed` wake source has its own SSE-streaming
entry point `stream_addressed_wake(...)` (async generator) because the
operator's HTTP response is the consumer; events yield as the Reviewer
runs. Same funnel semantics — operator presence is itself a wake-warrant
(Tier 1 auto-escalates).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Literal, Optional

try:
    import sentry_sdk as _sentry
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

from agents.occupant_contract import FREDDIE_MODEL_IDENTITY  # ADR-315: single canonical occupant identity
from services.recurrence import Recurrence
from services.telemetry import record_execution_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wake-source + funnel-decision taxonomies (ADR-296 v2 D1 + D2)
# ---------------------------------------------------------------------------

WakeSource = Literal[
    "cron_tick",
    "addressed",
    "proposal_arrival",
    "substrate_event",
    "manual_fire",
]

FunnelDecision = Literal[
    "skip",
    "tier_2_wait",
    "tier_2_observe",
    "escalate",
    "mechanical",
]


# ---------------------------------------------------------------------------
# Public entry point — Singular invocation gateway (ADR-296 v2 D1)
# ---------------------------------------------------------------------------


async def submit_wake_proposal(
    client,
    user_id: str,
    *,
    source: WakeSource,
    payload: dict,
) -> dict:
    """Singular wake-proposal entry point per ADR-296 v2 D1 + ADR-298 D2.

    Post-ADR-298 Phase 3 cutover (2026-05-22):
    This function enqueues a wake on `wake_queue` and returns immediately.
    The Reviewer is NOT invoked synchronously by this call. Execution
    happens later when the drainer (`services.wake_drainer.drain_*`)
    pulls the pending row, acquires the single-in-flight lock per ADR-298
    D1, and dispatches to the source-specific Reviewer-invocation body.

    Per ADR-298 D6: per-source dedup_key is derived here from the payload.
    UNIQUE (user_id, wake_source, dedup_key) on wake_queue enforces
    cross-source dedup at insert time. Silent dedup-hit returns
    {success: True, dedup: True} so callers can treat duplicate
    submission as a no-op.

    Args:
        client: Supabase service client.
        user_id: Workspace owner UUID.
        source: WakeSource taxonomy value naming what proposed the wake.
        payload: source-specific dict.
          - cron_tick / manual_fire: {"recurrence": Recurrence,
                                       "context": Optional[str]}
          - proposal_arrival: {"proposal_row": dict, "context_domain": str}
          - substrate_event: {"hook": dict, "path": str,
                               "field_change": dict, "revision_id": str}
          - addressed: NOT this entry point — use stream_addressed_wake()
                       (SSE generator with Option-α lock-acquire).

    Returns dict with at least `{success, source, queue_id|dedup, lane}`.
    Recurrence-shaped payloads include `slug` for telemetry continuity.
    """
    if source == "addressed":
        # Architectural invariant: addressed routes through the SSE
        # generator with Option-α lock-acquire (ADR-298 D3 + addressed-
        # turn coordination decision). Caller error to come through here.
        raise ValueError(
            "submit_wake_proposal does not serve source='addressed' — "
            "use stream_addressed_wake() for the SSE path."
        )

    # ADR-375 §6 chokepoint #2 — steward-presence gate (belt-and-suspenders).
    # When AGENT_ENABLED is off, no wake is ever enqueued: the singular
    # wake-proposal gateway no-ops. Chokepoint #1 (scheduler) alone suffices
    # to stop the steward firing, but gating here makes the off-state airtight
    # — and covers the MCP→wake adapter, which reaches the queue ONLY via this
    # function and "never raises" (the foreign write already committed +
    # attributed per ADR-307/209; it simply is not placed/judged — ADR-375 D3).
    from services.agent_gating import is_agent_enabled
    if not is_agent_enabled(workspace_id=user_id):
        return {"success": True, "source": source, "skipped": "agent_disabled"}

    from services.wake_queue import enqueue, resolve_lane

    # Per-source payload normalization + dedup_key derivation. The
    # Recurrence object is not JSON-serializable directly; we project
    # it to a dict here so the drainer can reconstruct it without
    # needing live recurrence YAML at drain time.
    if source in ("cron_tick", "manual_fire"):
        recurrence = payload.get("recurrence")
        if not isinstance(recurrence, Recurrence):
            raise ValueError(
                f"wake source {source!r} requires payload['recurrence'] "
                f"as a Recurrence object; got {type(recurrence).__name__}"
            )
        slug = recurrence.slug
        # ADR-298 D6: dedup key for cron_tick is `<slug>:<scheduled_minute>`
        # to drop concurrent enqueues of the same recurrence in the same
        # minute. manual_fire intentionally has no dedup (operator
        # explicitly bypasses idempotency by clicking "run now" twice).
        if source == "cron_tick":
            now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            dedup_key = f"{slug}:{now.isoformat()}"
        else:
            dedup_key = None
        queue_payload = {
            "recurrence_data": {
                "slug": recurrence.slug,
                "schedule": recurrence.schedule,
                "prompt": recurrence.prompt,
                "mode": getattr(recurrence, "mode", "judgment"),
                "paused": getattr(recurrence, "paused", False),
                "options": dict(getattr(recurrence, "options", {}) or {}),
            },
            "context": payload.get("context"),
        }
        queue_id = enqueue(
            client,
            user_id=user_id,
            wake_source=source,
            payload=queue_payload,
            dedup_key=dedup_key,
            slug=slug,
        )

    elif source == "proposal_arrival":
        proposal_row = payload.get("proposal_row") or {}
        proposal_id = proposal_row.get("id") or payload.get("proposal_id") or ""
        # ADR-298 D6: proposal_arrival dedup key = proposal_id.
        queue_payload = {
            "proposal_row": proposal_row,
            "proposal_id": proposal_id,
            "context_domain": payload.get("context_domain"),
        }
        queue_id = enqueue(
            client,
            user_id=user_id,
            wake_source="proposal_arrival",
            payload=queue_payload,
            dedup_key=str(proposal_id) if proposal_id else None,
            slug=None,
        )

    elif source == "substrate_event":
        # ADR-298 D6: substrate_event dedup key = revision_id (the
        # workspace_file_versions.id that matched the hook). Replaces
        # ADR-272's execution_events.wake_dedup_key for this source.
        revision_id = payload.get("revision_id")
        queue_payload = {
            "hook": payload.get("hook") or {},
            "path": payload.get("path") or "",
            "field_change": payload.get("field_change") or {},
            "revision_id": revision_id,
        }
        hook_slug = (payload.get("hook") or {}).get("slug") or "substrate-event"
        queue_id = enqueue(
            client,
            user_id=user_id,
            wake_source="substrate_event",
            payload=queue_payload,
            dedup_key=str(revision_id) if revision_id else None,
            slug=hook_slug,
        )

    else:
        raise ValueError(f"unknown wake source: {source!r}")

    if queue_id is None:
        # UNIQUE constraint hit — wake already enqueued for this dedup key.
        # Silent dedup per ADR-298 D6.
        return {
            "success": True,
            "source": source,
            "dedup": True,
            "lane": resolve_lane(source),
            "message": "duplicate wake suppressed by queue dedup",
        }

    return {
        "success": True,
        "source": source,
        "queue_id": queue_id,
        "lane": resolve_lane(source),
        "message": "wake enqueued for drainer",
    }


# ---------------------------------------------------------------------------
# Recurrence-fire wake body (cron_tick + manual_fire)
# ---------------------------------------------------------------------------


async def _invoke_recurrence_wake(
    client,
    user_id: str,
    *,
    recurrence: Recurrence,
    wake_source: WakeSource,  # "cron_tick" | "manual_fire"
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

    ADR-296 v2: the legacy `trigger` parameter is computed here from
    `wake_source` for backwards compatibility with downstream functions
    (record_execution_event's trigger_type column, narrative pulse,
    Reviewer's context envelope). This function handles RECURRENCE fires
    only (cron_tick + manual_fire of a recurrence) — both carry the
    recurrence-fire context shape, so `trigger="reactive"` for both (fixed
    2026-06-04 — the prior manual_fire→addressed mapping was the silent-wake
    root cause; see the trigger-derivation comment below). The manual-vs-cron
    distinction is carried by the `wake_source` field on the context, not the
    trigger axis. Genuine operator chat turns are `addressed` and reach the
    Reviewer through the feed/stream_addressed path, not this function. The
    trigger axis is kernel-internal vocabulary per ADR-263 D2; only the public
    surface speaks wake_source.
    """
    if recurrence.paused:
        return _result_paused(recurrence, wake_source)

    started_at = datetime.now(timezone.utc)

    # ADR-296 v2 D1: wake-source comes from the caller. Derive the legacy
    # `trigger` value for downstream callers that still consume it.
    #
    # SILENT-WAKE ROOT CAUSE (2026-06-04): this function handles RECURRENCE
    # fires only — both cron_tick AND manual_fire of a recurrence. Both build
    # the recurrence-fire context shape (recurrence_prompt + recurrence_slug, NO
    # user_message). The prior `"addressed" if manual_fire else "reactive"`
    # mapping was WRONG: it tagged a manual_fire recurrence wake as trigger=
    # "addressed", but addressed requires a non-empty user_message — so
    # invoke_freddie's _validate_context_shape rejected the contradictory
    # (trigger=addressed, recurrence-context) pair, returned None, and the wake
    # silently produced nothing. This is why every eval that fired a recurrence
    # via manual_fire (the {fire: <slug>} path) saw the Reviewer "never run".
    # A recurrence fire is `reactive` regardless of manual-vs-cron — the
    # wake_source field (already on the context) carries the manual/cron
    # distinction for the Reviewer to perceive; the trigger axis follows the
    # CONTEXT SHAPE, which is recurrence-fire either way. Genuine operator chat
    # turns are `addressed` and never reach this function (they go through the
    # feed/stream_addressed path with a real user_message).
    trigger = "reactive"

    # ADR-289 D2 + D3: pre-generate the invocation atom id. This UUID is the
    # canonical execution_events.id for the cycle; every narrative row produced
    # during the cycle stamps metadata.invocation_id with this value so the FE
    # can group them into one invocation card on the Feed surface.
    import uuid as _uuid
    invocation_id = str(_uuid.uuid4())

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
            started_at=started_at, wake_source=wake_source,
        )

    # ---- Balance gate (ADR-172) ----
    try:
        from services.platform_limits import check_balance
        balance_ok, _balance = check_balance(client, user_id)
    except Exception as e:
        logger.warning("[DISPATCH] balance check failed (proceeding): %s", e)
        balance_ok = True

    if not balance_ok:
        # ADR-291 Phase 2 (Flaw 3 cleanup): suppress repeat material-weight
        # feed emissions when balance has been zero across multiple scheduler
        # ticks. Without this, a user with $0 balance and a recurrence on
        # */15 cadence would generate ~96 feed entries per day per recurrence
        # — feed noise that drowns out actionable signal.
        #
        # Rule: feed entry is the *transition* into balance-exhausted state,
        # not the repeat. We always write the forensic execution_events row
        # (operator can still see the full skip history under /admin); we
        # only suppress the operator-facing feed emission on consecutive
        # balance-exhausted failures for the same recurrence.
        is_repeat = False
        try:
            prev = (
                client.table("execution_events")
                .select("status, error_reason")
                .eq("user_id", user_id)
                .eq("slug", recurrence.slug)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if prev.data:
                prev_row = prev.data[0]
                is_repeat = (
                    prev_row.get("status") == "failed"
                    and prev_row.get("error_reason") == "balance_exhausted"
                )
        except Exception as e:
            # Fail open — emit the narrative if we can't determine repeat
            # state. Operator visibility wins over silence on uncertainty.
            logger.warning("[DISPATCH] balance-exhausted repeat check failed: %s", e)

        if not is_repeat:
            # ADR-277: material weight — hard stop, operator must see this.
            # Distinct from the substrate-row execution_events entry (which
            # carries forensic status); the feed entry carries the operator-
            # actionable "you're out of budget" framing.
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=f"{recurrence.slug} skipped: balance exhausted",
                trigger=trigger,
                weight="material",
            )
        # Always record the execution_events row (forensic ledger) regardless
        # of feed suppression — admin dashboard analytics depend on it.
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            mode="judgment",  # ADR-265: mode replaces dead shape discriminator
            trigger_type=trigger,
            status="failed", error_reason="balance_exhausted",
            wake_source=wake_source,
            funnel_decision="skip",  # ADR-296 v2 D2: Tier 1 kernel gate
        )
        return _result_failed(recurrence, "balance exhausted", trigger=trigger)

    # ---- Cost governance (ADR-327) ----
    # Per-workspace `_budget.yaml` declares the spend envelope (dollar budget
    # over a timeframe) + per-slug fire floor. Falls back to kernel defaults
    # ($50/monthly) when absent. Reviewer cannot author this file — it's
    # governance (DEFAULT_FREDDIE_WRITE_LOCKS). Collapses the retired
    # _pace.yaml + _token_budget.yaml.
    #
    # D4 priority rule: trigger=="reactive" here is the SCHEDULED (cron_tick)
    # lane — hard-gated on budget exhaustion (scheduled work goes quiet
    # rather than over-spend). trigger=="manual" (operator FireInvocation)
    # warns-but-proceeds (operator presence is warrant).
    from services.budget import load_budget, window_spend, seconds_since_last_fire
    budget = load_budget(client, user_id)

    try:
        spent = window_spend(client, user_id, budget.window)
    except Exception:
        spent = 0.0

    # Gate 1: window budget (ADR-327 D3/D4)
    if spent >= budget.amount_usd:
        warning = (
            f"Budget reached (${spent:.2f} / ${budget.amount_usd:.2f} "
            f"per {budget.window} _budget.yaml). {recurrence.slug} skipped."
        )
        logger.warning("[DISPATCH] %s", warning)
        if trigger == "reactive":
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=f"Budget reached — {recurrence.slug} skipped",
                body=(
                    f"{recurrence.slug} was due but this {budget.window}'s spend "
                    f"(${spent:.2f}) has reached the operation's budget "
                    f"(${budget.amount_usd:.2f}). Scheduled run skipped — the "
                    f"operation goes quiet rather than over-spend. Resets at the "
                    f"start of the next {budget.window} window. To adjust, edit "
                    f"/workspace/governance/_budget.yaml."
                ),
                trigger=trigger,
                weight="material",
            )
            record_execution_event(
                client, user_id=user_id, slug=recurrence.slug,
                mode="judgment", trigger_type=trigger,
                status="skipped", error_reason="budget_exhausted",
                error_detail=warning,
                wake_source=wake_source,
                funnel_decision="skip",  # ADR-296 v2 D2: Tier 1 kernel gate
            )
            return _result_failed(recurrence, warning, trigger=trigger)
        else:
            # Manual FireInvocation — operator presence is warrant (D4
            # reactive-warn). Surface the overage, then proceed.
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=f"Budget warning — {recurrence.slug} running (manual)",
                body=f"{budget.window.capitalize()} budget ${budget.amount_usd:.2f} reached, but running anyway (manual fire). This {budget.window}: ${spent:.2f}.",
                trigger=trigger,
                weight="routine",
            )

    # Gate 2 (judgment-recurrence cap) DELETED per ADR-327 D2 — fire-count
    # was a cost proxy; the dollar budget (Gate 1) governs cost directly.

    # Gate 3: per-slug min-interval floor (ADR-313 Gate 3, preserved by ADR-327)
    min_iv = budget.min_interval_for(recurrence.slug)
    since_last = seconds_since_last_fire(client, user_id, recurrence.slug)
    if since_last is not None and since_last < min_iv:
        warning = (
            f"Min-interval floor: {recurrence.slug} fired {since_last}s ago "
            f"(floor: {min_iv}s per _budget.yaml). Skipping."
        )
        logger.warning("[DISPATCH] %s", warning)
        if trigger == "reactive":
            record_execution_event(
                client, user_id=user_id, slug=recurrence.slug,
                mode="judgment", trigger_type=trigger,
                status="skipped", error_reason="min_interval",
                error_detail=warning,
                wake_source=wake_source,
                funnel_decision="skip",  # ADR-296 v2 D2: Tier 1 kernel gate
            )
            return _result_failed(recurrence, warning, trigger=trigger)
        # Manual: warn but proceed.

    # ---- Mechanical pre-fold for platform-attested ground-truth loops ----
    # A platform-attested outcome loop (ADR-330 `attestation: "platform"` —
    # the trader's broker fills, the commerce LS orders) reaches the agent only
    # after an external oracle is POLLED and matched deterministically (FIFO,
    # client_order_id attribution) — work an LLM judgment wake structurally
    # cannot do. The `outcome-reconciliation` prompt for those programs reads
    # ("the reconciler has folded yesterday's fills … read the reconciled
    # outcomes"); this pre-step is the fold it reads. Runs mechanically (zero
    # LLM) before envelope assembly so the freshly-reconciled `_money_truth.md`
    # is in the substrate the envelope loads.
    #
    # ADR-260/261 fallout repair (2026-06-26): the historical caller — the
    # `back-office-outcome-reconciliation` task — was dissolved when back-office
    # tasks collapsed into recurrences, orphaning this fold. Workspaces that
    # never got the one-time bootstrap (kvk-trader) never materialized the
    # organ; the prompt's "has folded" precondition was silently false. See
    # 2026-06-25-trader-money-truth-orphaned-reconciler-AUDIT.md.
    #
    # Gated tight on `has_platform_attested_provider`: the alpha-author program
    # is operator-attested (its judgment wake folds its OWN events — no
    # mechanical pre-step), and an ungated call would write a spurious empty
    # `trading` _money_truth.md stub into the author's workspace
    # (fold_outcome_candidates stubs unconditionally on empty candidates). The
    # gate makes this a true no-op (never called) for operator/agent-attested
    # programs. Best-effort: a reconcile failure must not break the wake.
    if recurrence.slug == "outcome-reconciliation":
        try:
            from services.outcomes import (
                has_platform_attested_provider,
                reconcile_user,
            )
            if has_platform_attested_provider(client, user_id):
                summary = await reconcile_user(client, user_id)
                logger.info(
                    "[DISPATCH] %s/%s pre-fold: platform-attested reconcile ran "
                    "(appended=%s)",
                    user_id[:8], recurrence.slug,
                    summary.get("total_appended"),
                )
        except Exception as exc:  # noqa: BLE001 — pre-fold must not break dispatch
            logger.warning(
                "[DISPATCH] %s/%s pre-fold reconcile failed: %s",
                user_id[:8], recurrence.slug, exc,
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
        from agents.freddie_agent import invoke_freddie
    except ImportError as e:
        logger.exception("[DISPATCH] freddie_agent not importable: %s", e)
        return _result_failed(recurrence, f"freddie_agent unavailable: {e}", trigger=trigger)

    try:
        # Context keys must match what invoke_freddie reads at
        # `freddie_agent.py::_build_user_message`. The Reviewer's
        # `is_recurrence_fire` detection (freddie_agent.py:573) keys
        # on `recurrence_prompt` / `recurrence_slug` — passing bare
        # `prompt` / `slug` here would silently drop the recurrence
        # context, causing every cron-fired Reviewer wake to fall into
        # the proposal-arrival shape (Sonnet/3-rounds with empty user
        # message → universal stand_down). Bug surfaced 2026-05-13 in
        # the post-ADR-267 audit.
        # ADR-276 + ADR-301 D5: shared governance pre-load — full operator-
        # authored substrate (IDENTITY + principles + PRECEDENT + MANDATE +
        # AUTONOMY + _preferences.yaml + _pace.yaml + _operator_profile +
        # _risk + _performance + signal_files + occupant + standing_intent
        # + schedule_index + recent_execution + operating_context_block).
        # Same helper as the addressed-trigger envelope in routes/feed.py —
        # Singular Implementation: one envelope helper, one assembly point.
        # ADR-301 D5 consolidated operating_context_block composition into
        # the helper so the envelope dict carries all assembled content.
        from services.freddie_envelope import load_freddie_governance_envelope
        governance_envelope, envelope_load_ms = await load_freddie_governance_envelope(
            client, user_id
        )

        # ADR-360 D2: the ask-builder. For a declared owed-output producer
        # recurrence, the schedule must fire an IMPERATIVE ("produce X now"),
        # not the stored situation-framing prompt ("assess the operation") —
        # the six-probe arc proved framing defers and imperatives produce
        # (docs/evaluations/2026-06-24-step3-cron-imperative-VALIDATION.md).
        # Opt-in + program-agnostic: the recurrence flags itself via
        # options.produces_owed_output; the kernel reads the declared
        # kind/cadence from _expected_output.yaml (already in the envelope) +
        # the produced-count, and composes a category-neutral imperative. When
        # the recurrence is not a producer (or no contract is declared, or the
        # count read fails), build_owed_output_ask returns None and the
        # recurrence's own prompt stands unchanged.
        try:
            from services.ask_builder import build_owed_output_ask

            _produces_owed = bool(
                (recurrence.options or {}).get("produces_owed_output")
            )
            owed_ask = await build_owed_output_ask(
                client, user_id,
                produces_owed_output=_produces_owed,
                expected_output_yaml=governance_envelope.get("expected_output_yaml"),
            )
            if owed_ask:
                # The imperative replaces the stored prompt; one-shot steering
                # (if any) is still appended.
                prompt = owed_ask
                if context and context.strip():
                    prompt = (
                        f"{prompt}\n\n"
                        f"## One-shot steering (this firing only)\n{context.strip()}"
                    )
                logger.info(
                    "[DISPATCH] %s/%s ask-builder delivered owed-output imperative "
                    "(ADR-360 D2)", user_id[:8], recurrence.slug,
                )
        except Exception as exc:
            # The ask-builder is an enhancement, not a gate — a failure degrades
            # to the recurrence's stored prompt rather than dropping the wake.
            logger.warning(
                "[DISPATCH] %s/%s ask-builder failed (using stored prompt): %s",
                user_id[:8], recurrence.slug, exc,
            )

        reviewer_output = await invoke_freddie(
            client=client,
            user_id=user_id,
            trigger=trigger,
            invocation_id=invocation_id,
            context={
                "recurrence_prompt": prompt,
                "recurrence_slug": recurrence.slug,
                # ADR-269: capability flow — recurrence declares the
                # program-specific capabilities its dispatched specialists
                # need. Reviewer reads this from context envelope and
                # passes through (or extends) when calling DispatchSpecialist.
                "recurrence_required_capabilities": list(recurrence.required_capabilities),
                "options": dict(recurrence.options) if recurrence.options else {},
                # 2026-05-27 Hat-A parity fix: pre-load fine-grained wake_source
                # so the Reviewer can disambiguate cron_tick vs manual_fire
                # within the coarse trigger=reactive class. Empty triggering
                # path/revision for recurrence-fire wakes (the recurrence.slug
                # already names the wake's anchor).
                "wake_source": wake_source,
                "triggering_path": "",
                "triggering_revision_id": "",
                **governance_envelope,  # ADR-276 + ADR-301: full envelope pre-load
            },
        )
    except Exception as exc:
        logger.exception("[DISPATCH] %s/%s reviewer raised: %s", user_id[:8], recurrence.slug, exc)
        if _SENTRY_AVAILABLE:
            _sentry.capture_exception(exc)
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        # `envelope_load_ms` is defined iff the envelope load completed before the
        # Reviewer raised. If the gather itself threw, the local is unbound — guard.
        _env_ms = locals().get("envelope_load_ms")
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            id=invocation_id,  # ADR-289 D2: canonical invocation atom id
            mode="judgment", trigger_type=trigger,
            status="failed", error_reason="exception",
            error_detail=str(exc), duration_ms=duration_ms,
            envelope_load_ms=_env_ms,
            wake_source=wake_source,
            funnel_decision="escalate",  # ADR-296 v2 D2: Reviewer was invoked
        )
        # ADR-277: material weight — Reviewer invocation raised an
        # exception. Real failure; operator should see. The execution_events
        # row carries status=failed + error_reason for the audit log;
        # the feed entry carries the operator-facing acknowledgment.
        await _emit_system_narrative(
            client, user_id, recurrence,
            summary=f"{recurrence.slug} failed",
            body=f"Reviewer invocation raised: {exc}",
            trigger=trigger,
            weight="material",
        )
        return _result_failed(recurrence, str(exc), trigger=trigger)

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    # ADR-291 cost ledger write. reviewer_output carries the loop's token
    # accumulators (incl. cache breakdown) and model.
    #
    # SILENT-WAKE FIX (2026-06-04): a `None` return from invoke_freddie means
    # the Reviewer did NOT close a cycle — a context-shape violation, a pre-LLM
    # exit, or a swallowed exception inside the round loop (freddie_agent.py
    # outer try/except → return None). Previously this was recorded as
    # status="success" with NULL tokens — making a FAILED judgment wake
    # indistinguishable from a successful no-op stand-down. That ambiguity is
    # the recurring "the agent silently produces nothing" trap across every
    # alpha-trader autonomy run: a wake escalates, the LLM never runs (or
    # raises), and telemetry says success. A judgment wake that escalated but
    # returned None did NOT judge — record it as a failure so it is visible.
    _ro = reviewer_output if isinstance(reviewer_output, dict) else None
    if _ro is None:
        logger.error(
            "[DISPATCH] %s/%s SILENT WAKE — invoke_freddie returned None "
            "(escalated, envelope loaded in %sms, but no verdict/output). "
            "Recording as failed.",
            user_id[:8], recurrence.slug, envelope_load_ms,
        )
        record_execution_event(
            client, user_id=user_id, slug=recurrence.slug,
            id=invocation_id,
            mode="judgment", trigger_type=trigger,
            status="failed", error_reason="reviewer_returned_none",
            error_detail="invoke_freddie returned None — context-shape violation, "
                         "pre-LLM exit, or swallowed exception in the round loop "
                         "(see freddie_agent.py logs for the captured cause)",
            duration_ms=duration_ms,
            envelope_load_ms=envelope_load_ms,
            wake_source=wake_source,
            funnel_decision="escalate",
        )
        await _emit_system_narrative(
            client, user_id, recurrence,
            summary=f"{recurrence.slug} produced no judgment",
            body="The Reviewer wake escalated but returned no verdict (silent "
                 "exit). This is a system fault, not a stand-down — see logs.",
            trigger=trigger,
            weight="material",
        )
        return _result_failed(recurrence, "reviewer returned None (silent wake)", trigger=trigger)

    record_execution_event(
        client, user_id=user_id, slug=recurrence.slug,
        id=invocation_id,  # ADR-289 D2: canonical invocation atom id
        mode="judgment", trigger_type=trigger,
        status="success", duration_ms=duration_ms,
        envelope_load_ms=envelope_load_ms,
        input_tokens=_ro.get("input_tokens"),
        output_tokens=_ro.get("output_tokens"),
        cache_read_tokens=_ro.get("cache_read_tokens"),
        cache_create_tokens=_ro.get("cache_create_tokens"),
        model=_ro.get("model"),
        tool_rounds=_ro.get("tool_rounds"),
        wake_source=wake_source,
        funnel_decision="escalate",  # ADR-296 v2 D2: Reviewer was invoked
    )

    actions_taken = []
    proposals = []
    verdict_summary = ""
    # ADR-315 occupant contract: the occupant identity is the single canonical
    # constant FREDDIE_MODEL_IDENTITY — NOT a hardcoded literal. The prior
    # default "ai:reviewer" drifted from the constant and leaked into
    # judgment_log attribution as `reviewer:ai:reviewer` whenever the
    # FreddieOutput dict carried no reviewer_identity field (which is always —
    # FreddieOutput has no such field; line below was a dead overwrite). One
    # occupant, one slug: `reviewer:ai:freddie-sonnet-v8` (2026-06-08 eval
    # finding — three attribution strings for one occupant broke the
    # revision-chain audit). Imported at module top per ADR-315 contract.
    reviewer_identity = FREDDIE_MODEL_IDENTITY
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
            # exit at freddie_agent.py:864 already rejects empty
            # reasoning before this code runs).
            verdict_summary = reviewer_output.get("verdict") or ""
        # NOTE: FreddieOutput (occupant_contract) carries NO per-output occupant
        # identity field — the occupant identity is the canonical
        # FREDDIE_MODEL_IDENTITY constant set above, not an output value. A prior
        # dead read of a non-existent output key only made the identity look
        # dynamic and leaked the stale "ai:reviewer" default into attribution;
        # deleted per ADR-315 (one occupant, one slug) + Singular Implementation.

    # ADR-281 §5.D2 + §5.D4 single-writer contract: judgment_log.md is the
    # Reviewer's operation-shaping judgment lineage, NOT a wake-audit log.
    # The wake's existence is recorded in execution_events (kernel-side
    # forensic substrate per ADR-265) + the feed narrative entry below
    # (per ADR-258 revised). The judgment_log only gets an entry if the
    # wake produced a material outcome per the §5.D3 deterministic
    # 5-condition gate (ProposeAction, Schedule create/update/archive,
    # WriteFile to operator-canon, Clarify alert, or meta-level verdict).
    # Routine stand-downs correctly produce no lineage entry — they are
    # not operation-shaping moments.
    #
    # Replaces the deleted append_recurrence_fire blanket-write
    # (pre-ADR-281 every wake produced an entry; this was the same
    # duplication pattern ADR-277 named at the feed-emission layer,
    # applied at the substrate-write layer).
    #
    # Pass the full reviewer_output dict (carries actions_taken + verdict)
    # so the gate can inspect tool calls. Best-effort; never raises.
    try:
        from services.freddie_audit import render_lineage_entry_if_material
        await render_lineage_entry_if_material(
            client, user_id,
            reviewer_output=reviewer_output if isinstance(reviewer_output, dict) else {},
            slug=recurrence.slug,
            trigger=trigger,
            reviewer_identity=reviewer_identity,
        )
    except Exception as exc:  # noqa: BLE001 — judgment-log writes must not break dispatch
        logger.warning(
            "[DISPATCH] %s/%s judgment-log lineage render failed: %s",
            user_id[:8], recurrence.slug, exc,
        )

    # FOUNDATIONS Axiom 9 + Derived Principle 12 (channel legibility gates
    # autonomy): emit one narrative entry per System Agent invocation the
    # Reviewer fired during the Loop wake-up. Same per-action narration the
    # proposal-arrival path uses (review_proposal_dispatch.py:373); cron-
    # fired reactive wakes were silent prior to FOUNDATIONS v8.4. Best-effort.
    try:
        from services.freddie_chat_surfacing import surface_freddie_actions
        await surface_freddie_actions(
            client, user_id,
            actions_taken=actions_taken,
        )
    except Exception as exc:  # noqa: BLE001 — narration is legibility, not control-flow
        logger.warning(
            "[DISPATCH] %s/%s narration emission failed: %s",
            user_id[:8], recurrence.slug, exc,
        )

    # ADR-317: post-judgment operator-addressing dispatcher. After the
    # outcome-reconciliation judgment completes (the Reviewer folded fills
    # into _money_truth.md + closed with a verdict), send the daily P&L
    # email IF the operator opted in. The Reviewer cannot send this itself
    # (platform_email_send_to_operator is deliberately excluded from
    # FREDDIE_PRIMITIVES — verdict-quality regression); the dispatcher is
    # the send half. Same post-judgment best-effort shape as the lineage +
    # narration hooks above. Gated on the trigger slug so it costs nothing
    # for any other recurrence.
    if recurrence.slug == "outcome-reconciliation":
        try:
            from services.daily_pnl_email import maybe_send_daily_pnl_email
            await maybe_send_daily_pnl_email(client, user_id)
        except Exception as exc:  # noqa: BLE001 — notification must not break dispatch
            logger.warning(
                "[DISPATCH] %s/%s daily-pnl dispatch failed: %s",
                user_id[:8], recurrence.slug, exc,
            )

    # ADR-333 D2: session-close persists substrate only — the Reviewer has
    # already written section partials + manifest. Composition is a lazy
    # projection pulled at the consumption boundary (a surface opening the
    # artifact, an export, an email send), never pushed eagerly here. The
    # render service is not driven at session-close. (Retires ADR-262 D4's
    # eager auto-compose, which contradicted ADR-213's own surface-pull
    # principle and drove the Docker render service on every fire for
    # artifacts most of which are never opened.)

    logger.info(
        "[DISPATCH] %s/%s done (%dms) — actions=%d proposals=%d",
        user_id[:8], recurrence.slug, duration_ms,
        len(actions_taken), len(proposals),
    )

    return {
        "success": True,
        "slug": recurrence.slug,
        "trigger": trigger,
        "duration_ms": duration_ms,
        "actions_taken": actions_taken,
        "proposals": proposals,
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
#     write_to="operation/portfolio/positions/{symbol}.yaml"
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
    wake_source: str,
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
            wake_source=wake_source,
            funnel_decision="mechanical",  # ADR-296 v2 D2
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
            wake_source=wake_source,
            funnel_decision="mechanical",  # ADR-296 v2 D2
        )
        if is_transition:
            # ADR-277: material weight — first-detection of capability
            # loss. Operator-actionable (go reconnect). The transition
            # guard above keeps this firing at most once per disconnect
            # event (not per per-minute fire), so material weight is
            # safe — no flood risk.
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
                weight="material",
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
            wake_source=wake_source,
            funnel_decision="mechanical",  # ADR-296 v2 D2
        )
        return _result_failed(recurrence, msg, trigger=trigger)

    # Build a minimal auth-shaped object for the primitive handler.
    # Mechanical dispatch runs as the system actor under the workspace owner's
    # user_id. Per ADR-288 D1, caller_identity carries the canonical
    # attribution string — the recurrence slug names the system actor
    # responsible for the write (e.g., system:sync-platform-state). Primitives
    # that need attribution default authored_by from auth.caller_identity
    # (ADR-288 D2). Explicit per-primitive authored_by="system:<actor>" still
    # wins where the primitive asserts its own specific actor name (e.g.,
    # SyncPlatformState passes its primitive name as the actor).
    class _MechanicalAuth:
        def __init__(self, user_id: str, client, caller_identity: str):
            self.user_id = user_id
            self.client = client
            self.caller_identity = caller_identity
    auth = _MechanicalAuth(
        user_id=user_id,
        client=client,
        caller_identity=f"system:{recurrence.slug}",
    )

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
            wake_source=wake_source,
            funnel_decision="mechanical",  # ADR-296 v2 D2
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
        wake_source=wake_source,
        funnel_decision="mechanical",  # ADR-296 v2 D2
    )

    # FOUNDATIONS Axiom 9: every invocation emits a narrative entry. Mechanical
    # recurrences ARE invocations (Axiom 9 + ADR-263) and emit ONE housekeeping-
    # weight entry per successful fire. The narrative_digest rolls these up
    # into daily roll-ups; per-fire entries stay weight-gated out of
    # material/routine FE rendering by default.
    #
    # ADR-277 (2026-05-15) emission policy: per-fire success narrative
    # DELETED. The 478 "SyncPlatformState: 0 written, 1 unchanged" rows
    # per 24h were pure duplication — execution_events already records
    # every fire with status + duration + cost; workspace_file_versions
    # records what got written. The feed is for events whose canonical
    # home is conversation, not for events the system happened to do.
    # Mechanical-mirror success carries no operator-relevant judgment
    # the substrate rows don't already have.
    #
    # What stays:
    #   - The transition guard above emits ONCE per capability-loss
    #     event (operator-actionable; weight=material).
    #   - Failure suppression (ADR-263 amendment 2026-05-12) preserved —
    #     execution_events carries forensic failure detail.
    #   - execution_events records every fire (visible at /activity).
    #
    # The original ADR-219 D5 design intended housekeeping rows to roll
    # into a daily narrative_digest; that digest job was deleted by the
    # ADR-260/261/262 back-office package cleanup. Rather than rebuild
    # the roll-up, ADR-277 makes the emission intentional at source.

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
    narration of judgment-mode work happens inside surface_freddie_actions,
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
# Result helpers
# ---------------------------------------------------------------------------


def _result_paused(recurrence: Recurrence, trigger_or_source: str) -> dict:
    return {
        "success": True,
        "slug": recurrence.slug,
        "trigger": trigger_or_source,
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


# ---------------------------------------------------------------------------
# Substrate-event wake body (Phase 1C will wire _hooks.yaml walking;
# this body assembles the Reviewer envelope when a hook match fires)
# ---------------------------------------------------------------------------


async def _embed_derived_files(client, user_id: str, *, since_iso: str) -> int:
    """Mechanically embed eligible files the Reviewer DERIVED during this wake (ADR-379 follow-on).

    The embedding gap (2026-06-29 finding, docs/evaluations/2026-06-29-recall-
    empty-embedding-gap.md): the seat derives understanding into operation/ from a
    foreign `remember` (and from any derivation), but nothing made those files
    AI-ready — workspace embeddings were 0/N, so semantic `recall` matched nothing.

    Why a mechanical post-step, NOT a Reviewer tool call: embedding is the
    make-AI-ready MECHANICS, not judgment — the seat's judgment is *what* to derive
    and *where*. Adding `Embed` to FREDDIE_PRIMITIVES is the corrosive move the
    registry comment (registry.py ~485) warns against (the 2026-05-25 canary: one
    extra tool collapsed Reviewer output ~74%). So `Embed` is NOT in the seat's
    hands; instead, after the wake completes, we deterministically embed the
    eligible files the seat just authored. This preserves ADR-325's properties
    (eligibility-checked via is_embed_eligible, cost-ceilinged below) while keeping
    the Reviewer tool surface untouched. Zero LLM.

    Targeted, not a blind sweep: only files (a) authored by the reviewer occupant
    (b) since this wake started (c) embed-eligible per ADR-325 D5. Idempotent and
    best-effort — never raises (an embed failure must not fail the wake, which has
    already done its judgment work).
    """
    try:
        from services.primitives.embed import (
            is_embed_eligible,
            _EMBED_DAILY_CAP,
            _embed_calls_today,
        )
        from services.primitives.workspace import _embed_workspace_file

        # The reviewer occupant's authored_by prefix (ADR-315 single identity).
        # Match any reviewer:* authorship (occupant id may vary by model).
        rows = (
            client.table("workspace_file_versions")
            .select("path, authored_by, created_at")
            .eq("user_id", user_id)
            .gte("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.debug("[WAKE:embed] derived-file query failed (non-fatal): %s", exc)
        return 0

    # Distinct reviewer-authored eligible paths (newest revision per path).
    seen: set[str] = set()
    embedded = 0
    for r in rows:
        path = r.get("path") or ""
        authored_by = (r.get("authored_by") or "").lower()
        if not path or path in seen:
            continue
        if not authored_by.startswith("freddie:"):
            continue
        rel = path[len("/workspace/"):] if path.startswith("/workspace/") else path.lstrip("/")
        eligible, _reason = is_embed_eligible(rel)
        if not eligible:
            continue
        seen.add(path)
        # Cost ceiling (ADR-325 D4) — additive backstop, same as the Embed primitive.
        try:
            if _embed_calls_today(client, user_id) >= _EMBED_DAILY_CAP:
                logger.info("[WAKE:embed] daily embed cap reached; stopping derived-embed sweep")
                break
        except Exception:  # noqa: BLE001
            pass
        try:
            # Read current content (the helper needs it; also confirms eligibility on length).
            res = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            content = (res.data or [{}])[0].get("content") or ""
            ok_len, _ = is_embed_eligible(rel, content)
            if not ok_len:
                continue
            await _embed_workspace_file(client, user_id, path, content)
            embedded += 1
            # Cost-ledger marker so _embed_calls_today + cost reporting see it.
            try:
                from services.telemetry import record_execution_event
                from services.supabase import get_service_client
                record_execution_event(
                    get_service_client(), user_id=user_id, slug="embed",
                    mode="mechanical", trigger_type="reactive", status="success",
                )
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("[WAKE:embed] embed of %s failed (non-fatal): %s", path, exc)
    if embedded:
        logger.info("[WAKE:embed] embedded %d derived file(s) for user=%s", embedded, user_id[:8])
    return embedded


async def _invoke_substrate_event_wake(
    client,
    user_id: str,
    *,
    hook: dict,
    path: str,
    field_change: dict,
    revision_id: Optional[str] = None,
    principal_id: Optional[str] = None,
) -> dict:
    """Invoke the Reviewer with a substrate-event hook's prompt as envelope.

    Per ADR-296 v2 D2, substrate-event wakes are gated identically to
    cron-tick wakes — kernel gates apply (balance / spend / cap), then
    the Reviewer's full real-time loop runs with the hook's prompt as
    the addressed-equivalent envelope.

    The hook declaration carries the prompt; the path + field_change
    payload identify which substrate transition fired the hook. Both
    are passed into the Reviewer's user-message context as
    `substrate_event_*` fields so the Reviewer can read the transition
    that woke it.

    ADR-298 Phase 5 cleanup (2026-05-22): the per-record wake_dedup_key
    stamping on execution_events is DELETED. Cross-source dedup
    migrated to the wake_queue.dedup_key UNIQUE constraint enforced at
    enqueue time per ADR-298 D6. Migration 180 drops the column from
    execution_events.
    """
    started_at = datetime.now(timezone.utc)
    import uuid as _uuid
    invocation_id = str(_uuid.uuid4())

    slug = hook.get("slug") or "substrate-event"
    prompt = hook.get("prompt") or ""

    if not prompt.strip():
        record_execution_event(
            client, user_id=user_id, slug=slug,
            id=invocation_id,
            mode="judgment", trigger_type="reactive",
            status="failed", error_reason="empty_hook_prompt",
            wake_source="substrate_event",
            funnel_decision="skip",
            principal_id=principal_id,
        )
        return {
            "success": False,
            "slug": slug,
            "source": "substrate_event",
            "message": f"hook {slug!r} has empty prompt",
        }

    # ---- Balance gate (ADR-172) ----
    try:
        from services.platform_limits import check_balance
        balance_ok, _balance = check_balance(client, user_id)
    except Exception as e:
        logger.warning("[WAKE:substrate] balance check failed (proceeding): %s", e)
        balance_ok = True

    if not balance_ok:
        record_execution_event(
            client, user_id=user_id, slug=slug,
            id=invocation_id,
            mode="judgment", trigger_type="reactive",
            status="failed", error_reason="balance_exhausted",
            wake_source="substrate_event",
            funnel_decision="skip",
            principal_id=principal_id,
        )
        return {
            "success": False, "slug": slug, "source": "substrate_event",
            "message": "balance exhausted",
        }

    try:
        from agents.freddie_agent import (
            invoke_freddie,
        )
        from services.freddie_envelope import load_freddie_governance_envelope
    except ImportError as e:
        logger.exception("[WAKE:substrate] freddie_agent not importable: %s", e)
        return {
            "success": False, "slug": slug, "source": "substrate_event",
            "message": f"freddie_agent unavailable: {e}",
        }

    try:
        # ADR-301 D5: envelope helper composes operating_context_block + all
        # other envelope content in one place. No separate build call here.
        governance_envelope, envelope_load_ms = await load_freddie_governance_envelope(
            client, user_id
        )
        reviewer_output = await invoke_freddie(
            client=client,
            user_id=user_id,
            trigger="reactive",
            invocation_id=invocation_id,
            context={
                "recurrence_prompt": prompt,
                "recurrence_slug": slug,
                "recurrence_required_capabilities": [],
                "options": {},
                "substrate_event_path": path,
                "substrate_event_field_change": field_change,
                # 2026-05-27 Hat-A parity fix: pre-load wake_source + triggering
                # anchor so the Reviewer perceives "the operator just transitioned
                # THIS file" rather than inferring it from substrate reads. Empty
                # triggering_revision_id if the caller didn't pass one (the wake
                # body still works without it; only the envelope display is
                # affected — operator-visibility regresses to "wake was substrate-
                # event but anchor unknown" which is itself honest).
                "wake_source": "substrate_event",
                "triggering_path": path or "",
                "triggering_revision_id": revision_id or "",
                **governance_envelope,  # ADR-276 + ADR-301
            },
        )
    except Exception as exc:
        logger.exception("[WAKE:substrate] reviewer raised: %s", exc)
        if _SENTRY_AVAILABLE:
            _sentry.capture_exception(exc)
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        _env_ms = locals().get("envelope_load_ms")
        record_execution_event(
            client, user_id=user_id, slug=slug,
            id=invocation_id,
            mode="judgment", trigger_type="reactive",
            status="failed", error_reason="exception",
            error_detail=str(exc), duration_ms=duration_ms,
            envelope_load_ms=_env_ms,
            wake_source="substrate_event",
            funnel_decision="escalate",
            principal_id=principal_id,
        )
        return {
            "success": False, "slug": slug, "source": "substrate_event",
            "message": str(exc),
        }

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    _ro = reviewer_output if isinstance(reviewer_output, dict) else {}
    record_execution_event(
        client, user_id=user_id, slug=slug,
        id=invocation_id,
        mode="judgment", trigger_type="reactive",
        status="success", duration_ms=duration_ms,
        envelope_load_ms=envelope_load_ms,
        input_tokens=_ro.get("input_tokens"),
        output_tokens=_ro.get("output_tokens"),
        cache_read_tokens=_ro.get("cache_read_tokens"),
        cache_create_tokens=_ro.get("cache_create_tokens"),
        model=_ro.get("model"),
        tool_rounds=_ro.get("tool_rounds"),
        wake_source="substrate_event",
        funnel_decision="escalate",
        principal_id=principal_id,
    )

    # ADR-325 follow-on (2026-06-29 finding): mechanically embed any eligible files
    # the seat DERIVED during this wake, so semantic `recall` can rank them. This is
    # make-AI-ready MECHANICS, not judgment — deliberately NOT a Reviewer tool call
    # (Embed stays out of FREDDIE_PRIMITIVES; see registry.py ~485). Best-effort.
    try:
        await _embed_derived_files(client, user_id, since_iso=started_at.isoformat())
    except Exception as exc:  # noqa: BLE001 — embed must never fail the wake
        logger.debug("[WAKE:substrate] derived-embed post-step failed (non-fatal): %s", exc)

    return {
        "success": True,
        "slug": slug,
        "source": "substrate_event",
        "duration_ms": duration_ms,
        "actions_taken": _ro.get("actions_taken", []) or [],
        "proposals": _ro.get("proposals", []) or [],
        "message": (_ro.get("reasoning") or "").strip() or f"{slug} completed",
    }


# ---------------------------------------------------------------------------
# Addressed-stream entry — SSE async generator (ADR-296 v2 D1)
# ---------------------------------------------------------------------------


async def stream_addressed_wake(
    client,
    user_id: str,
    *,
    session_id: str,
    invocation_id: str,
    user_message: str,
    conversation_window: str,
    workspace_state_text: str,
) -> AsyncGenerator[dict, None]:
    """Addressed wake source — SSE-streaming entry point.

    Per ADR-296 v2 D1, operator-addressed wakes pass the funnel by default
    (operator presence is itself a wake-warrant). This async generator
    runs the Reviewer's real-time loop and yields progress events as
    they fire, so routes/feed.py can stream them as SSE to the operator.

    Yields dicts shaped for SSE consumption — caller is responsible for
    formatting + writing to the HTTP response. Each yield is one of:
      {"type": "progress", "event": <invoke_freddie event dict>}
      {"type": "agent_narration", "tool": str, "summary": str, "narration": str}
      {"type": "reviewer_response", "text": str, "actions": list}
      {"type": "done", "actions": list}
      {"type": "error", "error": str}

    The funnel decision is always "escalate" for addressed wakes — the
    telemetry row is finalized via record_execution_event at the route
    layer (routes/feed.py owns the addressed_started_at + duration_ms
    accounting because the SSE response is structured around it).
    """
    import asyncio as _asyncio
    from agents.freddie_agent import invoke_freddie
    from services.freddie_envelope import load_freddie_governance_envelope
    from services.freddie_chat_surfacing import (
        REVIEWER_COGNITION_TOOLS as _COGNITION_ONLY,
        is_mirror_refresh_action,
        narrate_reviewer_action,
    )
    # ADR-298 Phase 3 (Option α): addressed turns enqueue + acquire the
    # single-in-flight lock before the Reviewer runs. While waiting for
    # another lane's mid-flight wake to complete, we emit "queued"
    # progress events so the operator sees the wait honestly. Lock
    # release happens after invoke_freddie completes (mark_completed
    # transitions wake_queue row pending→completed).
    from services.wake_queue import (
        enqueue as _wq_enqueue,
        try_lock as _wq_try_lock,
        mark_completed as _wq_mark_completed,
        mark_failed as _wq_mark_failed,
    )
    from services.wake_drainer import (
        drain_can_acquire_for_user as _wq_can_acquire,
        instance_id as _wq_instance_id,
    )

    progress_queue: _asyncio.Queue = _asyncio.Queue()

    async def _emit_progress(event: dict) -> None:
        await progress_queue.put(event)

    # ADR-298 D1 + D3 (Option α) — enqueue this addressed wake into the
    # live lane, then wait for the single-in-flight lock. Per ADR-298 D6
    # the dedup_key is the invocation_id (callers pass a unique uuid per
    # turn; double-submit of the same id is intentionally suppressed).
    addressed_payload = {
        "session_id": session_id,
        "user_message": user_message[:200],  # truncated — full text held by caller
        "invocation_id": invocation_id,
    }
    queue_id = _wq_enqueue(
        client,
        user_id=user_id,
        wake_source="addressed",
        payload=addressed_payload,
        dedup_key=invocation_id,
        slug=None,
    )
    if queue_id is None:
        # Dedup hit — same invocation_id already in flight. Treat as
        # caller error; surface an error event.
        yield {
            "type": "error",
            "error": "duplicate_invocation_id",
            "message": "Addressed wake with this invocation_id already enqueued.",
        }
        return

    # Wait for the in-flight lock. Poll every 500ms; emit a single
    # "queued" event the first time we observe contention so the operator
    # sees the explanation. Bounded waits — after ~5 min of contention
    # something is wrong (cron wake should not run that long).
    wait_emitted = False
    wait_seconds_max = 300
    wait_poll_seconds = 0.5
    waited = 0.0
    inst = _wq_instance_id()
    while True:
        if _wq_can_acquire(client, user_id):
            if _wq_try_lock(client, queue_id=queue_id, instance_id=inst):
                break
            # Lost the CAS — fall through to poll again.
        if not wait_emitted:
            yield {
                "type": "progress",
                "event": {
                    "phase": "queued",
                    "summary": (
                        "Reviewer is mid-flight on another wake; "
                        "your turn will start as soon as it completes."
                    ),
                },
            }
            wait_emitted = True
        await _asyncio.sleep(wait_poll_seconds)
        waited += wait_poll_seconds
        if waited >= wait_seconds_max:
            _wq_mark_failed(client, queue_id=queue_id)
            yield {
                "type": "error",
                "error": "lock_wait_timeout",
                "message": (
                    f"Waited {wait_seconds_max}s for in-flight wake to "
                    "complete; aborting addressed turn."
                ),
            }
            return

    # ADR-301 D5: envelope helper composes operating_context_block alongside
    # all other envelope content. Singular envelope assembly point.
    governance_envelope, _envelope_load_ms = await load_freddie_governance_envelope(
        client, user_id
    )

    invoke_task = _asyncio.create_task(invoke_freddie(
        client, user_id,
        trigger="addressed",
        invocation_id=invocation_id,
        context={
            **governance_envelope,  # ADR-276 + ADR-301 — full envelope incl. operating_context_block
            "user_message": user_message,
            "conversation_window": conversation_window,
            "workspace_state": workspace_state_text or "",
            # 2026-05-27 Hat-A parity fix: explicit wake_source so the Reviewer
            # perceives "operator directly addressed me" as a first-class envelope
            # input (was previously implicit via the user_message field's presence).
            "wake_source": "addressed",
            "triggering_path": "",
            "triggering_revision_id": "",
        },
        event_callback=_emit_progress,
    ))

    # Drain progress events while invoke_task runs.
    while not invoke_task.done():
        try:
            event = await _asyncio.wait_for(progress_queue.get(), timeout=0.5)
        except _asyncio.TimeoutError:
            continue

        phase = event.get("phase")
        tool_name = event.get("tool", "?")

        # ADR-351 Phase 1: reasoning tokens stream as their own SSE event so
        # the frontend appends them to the live Reviewer bubble as they arrive
        # (not buffered to the terminal reviewer_response). Distinct type so
        # the consumer never has to demux text out of generic progress frames.
        if phase == "text_delta":
            yield {"type": "text_delta", "text": event.get("text", ""), "round": event.get("round")}
            continue

        yield {"type": "progress", "event": event}

        if phase == "tool_end":
            summary = event.get("summary", "")
            success = event.get("success", True)
            _action_synth = {"tool": tool_name, "input": event.get("input") or {}}
            if (
                success
                and tool_name not in _COGNITION_ONLY
                and not is_mirror_refresh_action(_action_synth, client, user_id)
            ):
                narration = narrate_reviewer_action(tool_name, summary)
                # 2026-05-25 clarify-silenced-from-feed: per-tool role.
                # Clarify is the Reviewer asking the operator — render in
                # the Reviewer persona bubble (role='freddie' per
                # ADR-247 + ADR-258 D1), not as System Agent narration.
                # Caller (routes/feed.py) reads event['role'].
                row_role = "freddie" if tool_name == "Clarify" else "system_agent"
                event_out: dict = {
                    "type": "agent_narration",
                    "tool": tool_name,
                    "summary": summary,
                    "narration": narration,
                    "role": row_role,
                }
                if tool_name == "Clarify":
                    cinp = _action_synth.get("input") or {}
                    if isinstance(cinp, dict):
                        cq = cinp.get("question")
                        co = cinp.get("options")
                        if cq:
                            event_out["clarify_question"] = cq
                        if isinstance(co, list) and co:
                            event_out["clarify_options"] = list(co)
                yield event_out

    # Drain any remaining queued events.
    while not progress_queue.empty():
        try:
            event = progress_queue.get_nowait()
        except Exception:
            break
        phase = event.get("phase")
        tool_name = event.get("tool", "?")
        if phase == "text_delta":
            yield {"type": "text_delta", "text": event.get("text", ""), "round": event.get("round")}
            continue
        yield {"type": "progress", "event": event}
        if phase == "tool_end":
            summary = event.get("summary", "")
            success = event.get("success", True)
            _action_synth = {"tool": tool_name, "input": event.get("input") or {}}
            if (
                success
                and tool_name not in _COGNITION_ONLY
                and not is_mirror_refresh_action(_action_synth, client, user_id)
            ):
                narration = narrate_reviewer_action(tool_name, summary)
                # 2026-05-25 clarify-silenced-from-feed: per-tool role.
                # Clarify is the Reviewer asking the operator — render in
                # the Reviewer persona bubble (role='freddie' per
                # ADR-247 + ADR-258 D1), not as System Agent narration.
                # Caller (routes/feed.py) reads event['role'].
                row_role = "freddie" if tool_name == "Clarify" else "system_agent"
                event_out: dict = {
                    "type": "agent_narration",
                    "tool": tool_name,
                    "summary": summary,
                    "narration": narration,
                    "role": row_role,
                }
                if tool_name == "Clarify":
                    cinp = _action_synth.get("input") or {}
                    if isinstance(cinp, dict):
                        cq = cinp.get("question")
                        co = cinp.get("options")
                        if cq:
                            event_out["clarify_question"] = cq
                        if isinstance(co, list) and co:
                            event_out["clarify_options"] = list(co)
                yield event_out

    # ADR-298 Phase 3: queue lifecycle terminates here regardless of
    # invoke_freddie outcome — release the single-in-flight lock so
    # the next pending wake (or addressed turn) can drain.
    output: Optional[dict] = None
    wake_failed = False
    try:
        output = await invoke_task
        if not output or not output.get("reasoning"):
            yield {"type": "error", "error": "Reviewer returned no response"}
            wake_failed = True
        else:
            response_text = output["reasoning"]
            actions = output.get("actions_taken") or []
            yield {
                "type": "reviewer_response",
                "text": response_text,
                "actions": actions,
                "output": output,  # full FreddieOutput for the route's telemetry write
            }
            yield {"type": "done", "actions": actions}
    except Exception as exc:
        wake_failed = True
        yield {"type": "error", "error": str(exc)}
    finally:
        try:
            if wake_failed:
                _wq_mark_failed(client, queue_id=queue_id)
            else:
                _wq_mark_completed(client, queue_id=queue_id)
        except Exception as exc:
            logger.warning(
                "[stream_addressed_wake] queue release failed for %s: %s",
                queue_id, exc,
            )


__all__ = [
    "submit_wake_proposal",
    "stream_addressed_wake",
    "WakeSource",
    "FunnelDecision",
]
