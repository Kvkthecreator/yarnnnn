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

from services.recurrence import Recurrence
from services.telemetry import (
    record_execution_event,
    get_daily_spend,
)

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
    Reviewer's context envelope). `wake_source="manual_fire"` ↔
    `trigger="addressed"`; `wake_source="cron_tick"` ↔ `trigger="reactive"`.
    The trigger axis itself is preserved as kernel-internal vocabulary
    per ADR-263 D2; only the public surface speaks wake_source.
    """
    if recurrence.paused:
        return _result_paused(recurrence, wake_source)

    started_at = datetime.now(timezone.utc)

    # ADR-296 v2 D1: wake-source comes from the caller. Derive the
    # legacy `trigger` value for downstream callers that still consume it.
    trigger = "addressed" if wake_source == "manual_fire" else "reactive"

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

    # ---- Compute-resource governance (ADR-293 D7) ----
    # Per-workspace `_token_budget.yaml` declares ceilings. Falls back to
    # kernel defaults (ADR-250 legacy) when absent. Reviewer cannot author
    # this file — it's governance (DEFAULT_REVIEWER_WRITE_LOCKS).
    from services.token_budget import (
        load_token_budget,
        count_judgment_fires_today,
        seconds_since_last_fire,
    )
    budget = load_token_budget(client, user_id)

    try:
        daily_spend = get_daily_spend(client, user_id)
    except Exception:
        daily_spend = 0.0

    # Gate 1: daily spend ceiling
    if daily_spend >= budget.daily_spend_ceiling_usd:
        warning = (
            f"Daily spend ceiling reached (${daily_spend:.2f} / "
            f"${budget.daily_spend_ceiling_usd:.2f} per _token_budget.yaml). "
            f"{recurrence.slug} skipped."
        )
        logger.warning("[DISPATCH] %s", warning)
        if trigger == "reactive":
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=f"Spend ceiling reached — {recurrence.slug} skipped",
                body=(
                    f"{recurrence.slug} was due but today's spend "
                    f"(${daily_spend:.2f}) has reached the workspace's "
                    f"daily ceiling (${budget.daily_spend_ceiling_usd:.2f}). "
                    f"Run skipped. Resets at midnight UTC. To adjust, "
                    f"edit /workspace/context/_shared/_token_budget.yaml."
                ),
                trigger=trigger,
                weight="material",
            )
            record_execution_event(
                client, user_id=user_id, slug=recurrence.slug,
                mode="judgment", trigger_type=trigger,
                status="skipped", error_reason="spend_ceiling",
                error_detail=warning,
                wake_source=wake_source,
                funnel_decision="skip",  # ADR-296 v2 D2: Tier 1 kernel gate
            )
            return _result_failed(recurrence, warning, trigger=trigger)
        else:
            await _emit_system_narrative(
                client, user_id, recurrence,
                summary=f"Spend ceiling warning — {recurrence.slug} running (manual)",
                body=f"Daily ceiling ${budget.daily_spend_ceiling_usd:.2f} reached, but running anyway (manual trigger). Today: ${daily_spend:.2f}.",
                trigger=trigger,
                weight="routine",
            )

    # Gate 2: max judgment recurrences per day (ADR-293 D7)
    judgment_count_today = count_judgment_fires_today(client, user_id)
    if judgment_count_today >= budget.max_judgment_recurrences_per_day:
        warning = (
            f"Daily judgment-recurrence cap reached "
            f"({judgment_count_today} / {budget.max_judgment_recurrences_per_day} "
            f"per _token_budget.yaml). {recurrence.slug} skipped."
        )
        logger.warning("[DISPATCH] %s", warning)
        if trigger == "reactive":
            record_execution_event(
                client, user_id=user_id, slug=recurrence.slug,
                mode="judgment", trigger_type=trigger,
                status="skipped", error_reason="judgment_cap",
                error_detail=warning,
                wake_source=wake_source,
                funnel_decision="skip",  # ADR-296 v2 D2: Tier 1 kernel gate
            )
            return _result_failed(recurrence, warning, trigger=trigger)
        # Manual: warn but proceed (operator at the keyboard).

    # Gate 3: per-slug min-interval (ADR-293 D7)
    min_iv = budget.min_interval_for(recurrence.slug)
    since_last = seconds_since_last_fire(client, user_id, recurrence.slug)
    if since_last is not None and since_last < min_iv:
        warning = (
            f"Min-interval floor: {recurrence.slug} fired {since_last}s ago "
            f"(floor: {min_iv}s per _token_budget.yaml). Skipping."
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
        # ADR-276 + ADR-301 D5: shared governance pre-load — full operator-
        # authored substrate (IDENTITY + principles + PRECEDENT + MANDATE +
        # AUTONOMY + _preferences.yaml + _pace.yaml + _operator_profile +
        # _risk + _performance + signal_files + occupant + standing_intent
        # + schedule_index + recent_execution + operating_context_block).
        # Same helper as the addressed-trigger envelope in routes/feed.py —
        # Singular Implementation: one envelope helper, one assembly point.
        # ADR-301 D5 consolidated operating_context_block composition into
        # the helper so the envelope dict carries all assembled content.
        from services.reviewer_envelope import load_reviewer_governance_envelope
        governance_envelope, envelope_load_ms = await load_reviewer_governance_envelope(
            client, user_id
        )

        reviewer_output = await invoke_reviewer(
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
    # accumulators (incl. cache breakdown) and model — written to execution_events
    # as the sole authoritative cost record per the unified-cost-ledger collapse.
    # NULL when Reviewer returned None (shape violation / pre-LLM exit).
    _ro = reviewer_output if isinstance(reviewer_output, dict) else {}
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
        from services.reviewer_audit import render_lineage_entry_if_material
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


async def _invoke_substrate_event_wake(
    client,
    user_id: str,
    *,
    hook: dict,
    path: str,
    field_change: dict,
    revision_id: Optional[str] = None,
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
        )
        return {
            "success": False, "slug": slug, "source": "substrate_event",
            "message": "balance exhausted",
        }

    try:
        from agents.reviewer_agent import (
            invoke_reviewer,
        )
        from services.reviewer_envelope import load_reviewer_governance_envelope
    except ImportError as e:
        logger.exception("[WAKE:substrate] reviewer_agent not importable: %s", e)
        return {
            "success": False, "slug": slug, "source": "substrate_event",
            "message": f"reviewer_agent unavailable: {e}",
        }

    try:
        # ADR-301 D5: envelope helper composes operating_context_block + all
        # other envelope content in one place. No separate build call here.
        governance_envelope, envelope_load_ms = await load_reviewer_governance_envelope(
            client, user_id
        )
        reviewer_output = await invoke_reviewer(
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
    )

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
      {"type": "progress", "event": <invoke_reviewer event dict>}
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
    from agents.reviewer_agent import (
        invoke_reviewer,
        REVIEWER_MODEL_IDENTITY,
    )
    from services.reviewer_envelope import load_reviewer_governance_envelope
    from services.reviewer_chat_surfacing import (
        REVIEWER_COGNITION_TOOLS as _COGNITION_ONLY,
        is_mirror_refresh_action,
        narrate_reviewer_action,
    )
    # ADR-298 Phase 3 (Option α): addressed turns enqueue + acquire the
    # single-in-flight lock before the Reviewer runs. While waiting for
    # another lane's mid-flight wake to complete, we emit "queued"
    # progress events so the operator sees the wait honestly. Lock
    # release happens after invoke_reviewer completes (mark_completed
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
    governance_envelope, _envelope_load_ms = await load_reviewer_governance_envelope(
        client, user_id
    )

    invoke_task = _asyncio.create_task(invoke_reviewer(
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
                # the Reviewer persona bubble (role='reviewer' per
                # ADR-247 + ADR-258 D1), not as System Agent narration.
                # Caller (routes/feed.py) reads event['role'].
                row_role = "reviewer" if tool_name == "Clarify" else "system_agent"
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
                # the Reviewer persona bubble (role='reviewer' per
                # ADR-247 + ADR-258 D1), not as System Agent narration.
                # Caller (routes/feed.py) reads event['role'].
                row_role = "reviewer" if tool_name == "Clarify" else "system_agent"
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
    # invoke_reviewer outcome — release the single-in-flight lock so
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
                "output": output,  # full ReviewerOutput for the route's telemetry write
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
