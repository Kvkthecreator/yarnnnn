"""
Execution Telemetry — ADR-250 Phase 2 + ADR-291 unified cost ledger.

Single write path for execution_events table: one row per invocation attempt,
always written regardless of outcome (success, failed, skipped). Per ADR-291,
this is the sole canonical cost ledger — token_usage was sunset.

Also provides:
  - cache-inclusive cost computation (accurate Anthropic billing model)
  - daily spend query for the Phase 3 spend guard

Design rules (from observability.md):
  - record_execution_event() never raises — non-fatal, logs on failure
  - cost_usd uses cache-inclusive formula (compute_cost_usd_inclusive)
  - agent_run_id is NULL for failures that produce no agent_runs row
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Billing rates — ADR-291 single source of truth, at TRUE PROVIDER LIST
# PRICES (operator ruling 2026-07-06, recorded as an ADR-291 amendment).
# The legacy 2x platform markup is RETIRED: cost_usd records what the
# invocation actually costs at the provider. The platform margin lives in
# ADR-490's `billed_usd` (cost × billing_tiers.USAGE_BILLING_MULTIPLIER,
# stamped alongside cost_usd at the single write site) — the pool draws
# billed_usd; cost_usd stays truthful for the D4 cost-mirror + margin
# analytics. Any provider price change flows through this table only; per
# ADR-291 D2 cost math lives here, in exactly one place, in
# compute_cost_usd_inclusive().
#
# The prior table was drifted twice over: it carried 2x of STALE list
# prices (opus at 2x $15/$75 — the pre-4.5 Opus price; haiku at 2x
# $0.80/$4.00 — haiku 4.5 lists $1/$5). The D4 router's cost mirror
# surfaced the drift.
# ---------------------------------------------------------------------------

_BILLING_RATES: dict[str, dict[str, float]] = {
    # ── Anthropic (ADR-559 D1, list prices verified 2026-08-12) ──────────
    "claude-opus-5":              {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    # ⚠️ THE RULE (operator ruling, 2026-08-12): THIS TABLE CARRIES STANDING
    # LIST PRICE. Never an introductory, promotional, or otherwise time-boxed
    # rate — for any engine, any provider.
    #
    # A promo rate has to be un-entered on a date nobody is watching for. Enter
    # one and the table silently under-charges the day it lapses, with no
    # failing gate and no alert; the error surfaces as a slow margin leak, which
    # is the hardest kind to notice. A standing rate is wrong by a known,
    # bounded amount for the promo window and correct forever after — and the
    # over-charge is VISIBLE in the ADR-408 D4 rate mirror rather than silent.
    #
    # Consequence on Sonnet 5 today: Anthropic runs an intro $2/$10 and LiteLLM
    # prices at it, so the mirror reads x1.50 on this row (probe, 2026-08-12) —
    # the only row not mirroring ~1.00. **That is the rule working, not a
    # defect.** It resolves itself when the promo lapses; do not "fix" it by
    # entering the promo rate.
    "claude-sonnet-5":            {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5":           {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
    # RETIRED engines keep their rate rows. `unpriced_lane_model` gates EVERY
    # turn, so dropping a retired model's rate would refuse the lanes the
    # retired state exists to keep running (ADR-559 D2).
    "claude-sonnet-4-6":          {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5-20251001":  {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
    # `claude-opus-4-6` REMOVED (ADR-559 D1): priced here but absent from
    # LANE_MODELS, SYSTEM_CALLS and DEFAULT_ROUTES — nothing could route to it.
    # A rate row for an unroutable engine is a claim about what we run that is
    # not true, and it read as "we offer an Opus tier" when we did not.
    # ADR-408 D4 / ADR-411 D5: routed Altitude-2 models. A model the router
    # may route MUST have a row here — an unknown model silently prices at
    # the Sonnet default (model_router warns).
    # OpenAI bills cached input at 50% of the input rate and has no cache
    # write premium (automatic prompt cache) — per-model multipliers here;
    # absent keys fall to Anthropic's shape (10% read / 125% write).
    "gpt-4o-mini":                {"input_per_mtok": 0.15, "output_per_mtok": 0.60,
                                   "cache_read_mult": 0.50, "cache_create_mult": 0.0},
    # ADR-420 §10 seed lanes (verified against provider docs, 2026-07). Keys are
    # BARE model names (ledger_model_name strips the LiteLLM provider prefix).
    # Cache multipliers per provider invoice shape; absent → Anthropic default
    # (10% read / 125% write). OpenAI/Gemini/DeepSeek have no cache-WRITE premium.
    "gpt-5":                      {"input_per_mtok": 1.25, "output_per_mtok": 10.00,
                                   "cache_read_mult": 0.50, "cache_create_mult": 0.0},
    # Gemini 3.5 Flash-Lite supersedes 2.5 Flash at the SAME list price
    # ($0.30/$2.50, verified against Google's pricing page 2026-08-13) with
    # higher measured intelligence and throughput. Cached input is $0.03/MTok
    # = 10% of base (the 0.25 on the 2.5 rows below is left as-is: correcting
    # those is a separate claim about a different era's invoice, and a rate row
    # is only as good as the day it was verified).
    "gemini-3.5-flash-lite":      {"input_per_mtok": 0.30, "output_per_mtok": 2.50,
                                   "cache_read_mult": 0.10, "cache_create_mult": 0.0},
    # RETIRED from the door, still routable for lanes pinned to it (ADR-559 D2).
    "gemini-2.5-flash":           {"input_per_mtok": 0.30, "output_per_mtok": 2.50,
                                   "cache_read_mult": 0.25, "cache_create_mult": 0.0},
    "gemini-2.5-pro":             {"input_per_mtok": 1.25, "output_per_mtok": 10.00,
                                   "cache_read_mult": 0.25, "cache_create_mult": 0.0},
    # DeepSeek cache-hit input is ~2% of the base rate (98% discount, V4 Flash).
    "deepseek-chat":              {"input_per_mtok": 0.14, "output_per_mtok": 0.28,
                                   "cache_read_mult": 0.02, "cache_create_mult": 0.0},
    # ⚠️ xAI prices by PROMPT LENGTH, and this table is flat (one pair per model,
    # no length branch in `compute_cost_usd_inclusive`). grok-4.6 is $2/$6 under
    # 200k prompt tokens and $4/$12 at or above it; the row carries the **≥200k
    # tier** on purpose. Same reasoning as the standing-list-price rule above:
    # the high tier over-charges short calls by a KNOWN, bounded amount that is
    # visible in the ADR-408 D4 rate mirror, whereas the low tier would silently
    # UNDER-charge every long-context call — the invisible failure this table's
    # discipline exists to prevent. Revisit only if `compute_cost_usd_inclusive`
    # learns prompt-length tiers.
    # Cached input is 25% of base at both tiers ($0.50/$2.00); no cache-write premium.
    "grok-4.6":                   {"input_per_mtok": 4.00, "output_per_mtok": 12.00,
                                   "cache_read_mult": 0.25, "cache_create_mult": 0.0},
}
#: Per-IMAGE list price (ADR-568 D2.a). A rented generation call has no token
#: count, so it prices per image rather than per MTok — a different unit, hence
#: a different table, but the SAME rule as `_BILLING_RATES` above: STANDING list
#: price, never promotional, and an unpriced model is a refusal rather than a
#: guess.
#:
#: This replaces a hardcoded `0.08` default read from `IMAGES_GENERATION_COST_USD`
#: inside the driver. That figure was the promo-rate hazard in miniature: an env
#: var nobody re-reads, defaulting to a number nobody re-derives, sitting outside
#: the one rule that exists to keep cost honest. One home for "what a call costs".
_IMAGE_RATES: dict[str, float] = {
    # Google list price for image output, verified 2026-08-13.
    "gemini-2.5-flash-image": 0.04,
}


def image_generation_cost_usd(model: str) -> Optional[float]:
    """Standing list price for one generated image, or None when unpriced.

    None is a REFUSAL signal, not a default (the ADR-548 lesson: a plausible
    fallback hides the bug it should surface). `generation_availability()`
    reads this and darkens an unpriced engine with `unpriced`, exactly as
    `unpriced_lane_model` does for a text lane.
    """
    return _IMAGE_RATES.get(model)


# The fall-through rate for a model with no row. Points at the CURRENT Sonnet,
# not the retired 4.6 — same figures ($3/$15), but a default anchored to a
# retired engine would silently outlive the row it names.
_DEFAULT_RATE = _BILLING_RATES["claude-sonnet-5"]


def has_billing_rate(model: str) -> bool:
    """True when the model has an explicit rate row (ADR-408 D4: the model
    router warns before letting an unpriced model fall to the default)."""
    return model in _BILLING_RATES

# ADR-293 (2026-05-19): DAILY_SPEND_CEILING_USD export DELETED.
# Compute-resource governance is now per-workspace via
# `services/token_budget.py` reading `/workspace/governance/_token_budget.yaml`.
# Kernel default (env var) still applies as the fall-through value when
# no per-workspace governance file exists — read directly by token_budget.py.
# Singular Implementation: one canonical source for the ceiling value.


# ---------------------------------------------------------------------------
# Cost computation — cache-inclusive (accurate)
# ---------------------------------------------------------------------------

def compute_cost_usd_inclusive(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_create_tokens: int = 0,
) -> float:
    """Cache-inclusive cost at true provider list rates.

    ADR-291: this is the sole canonical cost function. Cache multipliers are
    per-model rate data: Anthropic's invoice shape (10% read / 125% write,
    the 5-minute-TTL premium) is the default; OpenAI rows override (50% read,
    no write premium). The legacy 2x platform multiplier is retired
    (2026-07-06 operator ruling) — cost_usd records actual provider cost.
    """
    rate = _BILLING_RATES.get(model, _DEFAULT_RATE)
    ir = rate["input_per_mtok"]
    or_ = rate["output_per_mtok"]
    cost = (
        (input_tokens        / 1_000_000) * ir
        + (cache_read_tokens   / 1_000_000) * ir * rate.get("cache_read_mult", 0.10)
        + (cache_create_tokens / 1_000_000) * ir * rate.get("cache_create_mult", 1.25)
        + (output_tokens       / 1_000_000) * or_
    )
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Daily spend query (Phase 3 spend guard)
# ---------------------------------------------------------------------------

def get_daily_spend(client, user_id: str) -> float:
    """Return today's total billed spend from execution_events (UTC day),
    scoped to the acting WORKSPACE (ADR-407 Phase 0 — the spend guard draws
    the shared pool, so every principal's spend counts). Falls back to the
    legacy user_id scope only when no workspace resolves (byte-identical N=1).
    ADR-490: sums billed_usd (the pool debit), falling back to cost_usd on
    pre-migration rows.

    Used by the spend guard before dispatching generative invocations.
    Returns 0.0 on any error (fail-open: prefer running over blocking on DB error).
    """
    try:
        from services.workspace_context import effective_workspace_id
        ws = effective_workspace_id(user_id)
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        query = client.table("execution_events").select("cost_usd, billed_usd")
        query = query.eq("workspace_id", ws) if ws else query.eq("user_id", user_id)
        result = query.gte("created_at", today_utc).execute()
        rows = result.data or []
        return round(
            sum(float(r.get("billed_usd") or r.get("cost_usd") or 0) for r in rows), 6
        )
    except Exception as e:
        logger.warning("[TELEMETRY] get_daily_spend failed (fail-open): %s", e)
        return 0.0


# ---------------------------------------------------------------------------
# Event recording — the single write path
# ---------------------------------------------------------------------------

def record_execution_event(
    client,
    *,
    user_id: str,
    slug: str,
    mode: str,
    trigger_type: str,
    status: str,
    id: Optional[str] = None,
    error_reason: Optional[str] = None,
    error_detail: Optional[str] = None,
    tool_rounds: Optional[int] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cache_read_tokens: Optional[int] = None,
    cache_create_tokens: Optional[int] = None,
    model: Optional[str] = None,
    duration_ms: Optional[int] = None,
    envelope_load_ms: Optional[int] = None,
    wake_source: Optional[str] = None,
    funnel_decision: Optional[str] = None,
    agent_run_id: Optional[str] = None,
    principal_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    cost_override_usd: Optional[float] = None,
    session_id: Optional[str] = None,
) -> Optional[str]:
    """Write one row to execution_events. Never raises. Returns the row id on
    success, None on insert failure.

    ADR-439 — `cost_override_usd`: when provided, the row's `cost_usd` is set to
    this value INSTEAD of computing it from tokens. Two legitimate uses, both
    consistent with the ADR-396 one-ledger invariant: (1) a BYOK lane round paid
    on the customer's own key costs US nothing, so the lane passes 0.0 and the
    pool draw sees $0 (ADR-409 D2); (2) a rented NON-TOKEN call (ADR-475 image
    generation — priced per image, no token count exists) passes its real
    per-call figure. Never to fudge a cost that tokens can compute. When None
    (the default), cost is computed from tokens exactly as before — every
    token-priced call is byte-identical.

    Args:
        client:             Supabase service client
        user_id:            User UUID
        slug:               Recurrence slug (or 'addressed' for chat-fired cycles
                            per ADR-289)
        mode:               judgment | mechanical (ADR-263 — wakes Reviewer or runs deterministic Python)
        trigger_type:       scheduled | manual | back_office | addressed (ADR-289)
        status:             success | failed | skipped
        id:                 Caller-supplied UUID for the row. ADR-289 callers
                            pre-generate the UUID so the invocation_id can be
                            stamped on narrative rows produced during the cycle
                            before the audit row finalizes. Omit for legacy
                            single-shot writes; Postgres generates the UUID.
        error_reason:       taxonomy key (see observability.md Error Reason Taxonomy)
        error_detail:       exception message, truncated to 2000 chars
        tool_rounds:        number of LLM tool rounds executed
        input_tokens:       fresh input tokens (excludes cache)
        output_tokens:      output tokens
        cache_read_tokens:  cache read tokens
        cache_create_tokens: cache creation tokens
        model:              model name for cost rate lookup
        duration_ms:        wall-clock duration of the invocation
        envelope_load_ms:   ms spent in load_freddie_governance_envelope() for
                            Reviewer wakes (ADR-276); NULL for mechanical-mode
                            recurrences and non-Reviewer paths (migration 175)
        wake_source:        ADR-296 v2 D1 wake-source taxonomy. One of
                            cron_tick | addressed | proposal_arrival |
                            substrate_event | manual_fire. NULL for rows
                            predating migration 177 + Session B (telemetry
                            accepts the kwarg as no-op; population wired in
                            Session C/D when wake.submit_wake_proposal becomes
                            the singular invocation gateway).
        funnel_decision:    ADR-296 v2 D2 funnel decision taxonomy. One of
                            skip | tier_2_wait | tier_2_observe | escalate |
                            mechanical. NULL for rows predating migration 177
                            + Session B. Population wired in Session C/D when
                            wake_evaluation.evaluate() produces the decision.
        agent_run_id:       agent_runs.id if a row was created (NULL for early exits)
        principal_id:       the PRINCIPAL that caused this invocation (ADR-373
                            resolve_principal_id: owner user_id | foreign-LLM
                            provider host-id | agent slug). NULL = unattributed
                            (existing rows + sites without principal context).
                            Capture-first Layer-1 (migration 192) — attributes
                            the cost so the Cost & Activity Surface can answer
                            "who spent what" per principal. N=1 safe: owner rows
                            carry the owner user_id, byte-identical rollup.
        workspace_id:       the workspace this invocation ran FOR — the ledger's
                            SCOPE key (ADR-407 Phase 0; migration 200). Spend
                            rolls up by workspace; user_id/principal_id stay as
                            attribution. Omit and it resolves via
                            effective_workspace_id(user_id) (explicit → request
                            contextvar → owner resolution), so no legacy call
                            site changes. NULL only if resolution fails
                            (fail-open — the row still lands, unscoped).

        ADR-298 Phase 5 cleanup (2026-05-22): the `wake_dedup_key` kwarg
        was DELETED. Cross-source dedup migrated to wake_queue.dedup_key
        with the UNIQUE constraint enforced at INSERT time per ADR-298 D6;
        execution_events is no longer the dedup surface for wakes.
        Migration 180 drops the column from execution_events. Callers in
        services/wake.py stopped passing wake_dedup_key in the same Phase
        5 commit.

    Returns:
        The execution_events.id of the inserted row, or None on insert failure.
        Per ADR-289 D2, this is the canonical substrate row for the invocation
        atom — every narrative entry produced during the cycle stamps
        metadata.invocation_id with this value.
    """
    try:
        cost_usd = None
        if cost_override_usd is not None:
            # ADR-439 BYOK — the customer's own key paid for this call, so it
            # costs US nothing; record the override (0.0) instead of computing.
            # The single intentional exception to at-cost recording (ADR-396).
            cost_usd = cost_override_usd
        elif input_tokens is not None and output_tokens is not None:
            cost_usd = compute_cost_usd_inclusive(
                model=model or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens or 0,
                cache_create_tokens=cache_create_tokens or 0,
            )

        row: dict[str, Any] = {
            "user_id": user_id,
            "slug": slug,
            "mode": mode,
            "trigger_type": trigger_type,
            "status": status,
        }
        if id is not None:
            row["id"] = id
        if error_reason is not None:
            row["error_reason"] = error_reason
        if error_detail is not None:
            row["error_detail"] = str(error_detail)[:2000]
        if tool_rounds is not None:
            row["tool_rounds"] = tool_rounds
        if input_tokens is not None:
            row["input_tokens"] = input_tokens
        if output_tokens is not None:
            row["output_tokens"] = output_tokens
        if cache_read_tokens is not None:
            row["cache_read_tokens"] = cache_read_tokens
        if cache_create_tokens is not None:
            row["cache_create_tokens"] = cache_create_tokens
        if cost_usd is not None:
            row["cost_usd"] = cost_usd
            # ADR-490 §2 — the pool debit: provider cost × the platform margin,
            # stamped at THIS single write site (never at read time, never into
            # cost_usd — which stays actual provider cost for the ADR-408 D4
            # cost-mirror). Every balance/spend reader draws billed_usd.
            from services.billing_tiers import billed_usd_for_cost
            row["billed_usd"] = billed_usd_for_cost(cost_usd)
        # Migration 204 (2026-07-06): the ledger records WHICH model ran —
        # previously `model` fed only the rate lookup and was discarded.
        # Per-model spend legibility for routed lanes (ADR-408 D4 / ADR-411).
        if model is not None:
            row["model"] = model
        if duration_ms is not None:
            row["duration_ms"] = duration_ms
        if envelope_load_ms is not None:
            row["envelope_load_ms"] = envelope_load_ms
        if wake_source is not None:
            row["wake_source"] = wake_source
        if funnel_decision is not None:
            row["funnel_decision"] = funnel_decision
        # `agent_run_id` REMOVED 2026-08-26 — migration 248 dropped the column
        # (execution_events.agent_run_id, 0 non-null of 571 rows) with the
        # retired agent model. The kwarg stays on the signature so any stale
        # caller is a no-op rather than a TypeError; it was already unreachable
        # (no caller in api/ ever passed it), which is why the column was null.
        # W0 / ADR-457 D8 (migration 216): the session this metered turn served.
        # The falsifier JOIN KEY — the surface class (think/make/derive) is
        # DERIVED from the joined session's lane binding at read time (DP29),
        # never stored here. NULL for non-session invocations (recurrences,
        # sweeps, capture) and for pre-216 rows; never backfilled, never guessed.
        if session_id is not None:
            row["session_id"] = session_id
        # Capture-first (migration 192): attribute the row to the causing
        # PRINCIPAL. Explicit principal_id wins (the interop path passes the
        # foreign provider host-id); otherwise default to user_id — correct for
        # every owner/reviewer/recurrence site (ADR-373 resolve_principal_id maps
        # reviewer→user_id), so no owner-attributed call site needs to change.
        # New rows are therefore always attributed; only rows written before this
        # migration stay NULL.
        row["principal_id"] = principal_id if principal_id is not None else user_id

        # ADR-407 Phase 0 (migration 200): scope the ledger row to the acting
        # WORKSPACE — the pool spend draws from. Resolution mirrors the ADR-373
        # sweep spine (explicit → request contextvar → owner resolution) so the
        # ~15 legacy call sites need no change; a member's or agent's spend in
        # a granted workspace lands on that workspace, not their own singleton.
        try:
            from services.workspace_context import effective_workspace_id
            ws = effective_workspace_id(user_id, workspace_id)
            if ws:
                row["workspace_id"] = ws
        except Exception:  # fail-open: never lose the ledger row over scoping
            pass

        result = client.table("execution_events").insert(row).execute()
        # Supabase returns the inserted row(s) in result.data when the client
        # is configured with default representation. ADR-289 callers rely on
        # this id to stamp metadata.invocation_id on narrative rows.
        inserted_id: Optional[str] = id
        if not inserted_id and getattr(result, "data", None):
            try:
                inserted_id = result.data[0].get("id")
            except (IndexError, KeyError, AttributeError, TypeError):
                inserted_id = None

        logger.info(
            "[TELEMETRY] %s/%s %s%s",
            mode, slug, status,
            f" cost=${cost_usd:.4f}" if cost_usd else "",
        )
        return inserted_id
    except Exception as e:
        # ADR-439 §4 (F2) — a DROPPED ledger row. Fail-open is deliberate (a
        # transient DB blip must never break a user's turn), but a dropped row
        # means a REAL cost went unrecorded and undrawn from the pool. Emit a
        # distinct, high-signal [LEDGER-DROP] ERROR (was a silent warning) so a
        # log-based monitor can alert on a SYSTEMATIC drop — with the lost cost +
        # attribution so the gap is quantifiable, not just "something failed".
        lost = None
        try:
            if cost_override_usd is not None:
                lost = cost_override_usd
            elif input_tokens is not None and output_tokens is not None:
                lost = compute_cost_usd_inclusive(
                    model=model or "",
                    input_tokens=input_tokens, output_tokens=output_tokens,
                    cache_read_tokens=cache_read_tokens or 0,
                    cache_create_tokens=cache_create_tokens or 0,
                )
        except Exception:  # pragma: no cover — cost estimate is best-effort
            pass
        logger.error(
            "[LEDGER-DROP] execution_events insert failed — UNRECORDED spend "
            "(slug=%s principal=%s workspace=%s model=%s lost_cost=%s): %s",
            slug, principal_id or user_id, workspace_id, model,
            f"${lost:.6f}" if lost is not None else "unknown", e,
        )
        return None
