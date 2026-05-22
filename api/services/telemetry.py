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
# Billing rates — ADR-291 single source of truth (2x Anthropic markup).
# Any future Anthropic-cost optimization (cache discount changes, prompt
# compression, model tier changes) flows through this table only; the
# multiplier rule is durable. Per ADR-291 D2: cost math lives here, in
# exactly one place, in compute_cost_usd_inclusive().
# ---------------------------------------------------------------------------

_BILLING_RATES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":          {"input_per_mtok": 6.00,  "output_per_mtok": 30.00},
    "claude-opus-4-6":            {"input_per_mtok": 30.00, "output_per_mtok": 150.00},
    "claude-haiku-4-5-20251001":  {"input_per_mtok": 1.60,  "output_per_mtok": 8.00},
}
_DEFAULT_RATE = _BILLING_RATES["claude-sonnet-4-6"]

# ADR-293 (2026-05-19): DAILY_SPEND_CEILING_USD export DELETED.
# Compute-resource governance is now per-workspace via
# `services/token_budget.py` reading `/workspace/context/_shared/_token_budget.yaml`.
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
    """Cache-inclusive cost at user-facing 2× Anthropic billing rates.

    ADR-291: this is the sole canonical cost function. Accounts for
    cache_read (10% of input rate) and cache_creation (125% of input rate),
    matching Anthropic's actual invoice shape with 2x platform multiplier.
    """
    rate = _BILLING_RATES.get(model, _DEFAULT_RATE)
    ir = rate["input_per_mtok"]
    or_ = rate["output_per_mtok"]
    cost = (
        (input_tokens        / 1_000_000) * ir
        + (cache_read_tokens   / 1_000_000) * ir * 0.10
        + (cache_create_tokens / 1_000_000) * ir * 1.25
        + (output_tokens       / 1_000_000) * or_
    )
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Daily spend query (Phase 3 spend guard)
# ---------------------------------------------------------------------------

def get_daily_spend(client, user_id: str) -> float:
    """Return today's total cost_usd for user from execution_events (UTC day).

    Used by the spend guard before dispatching generative invocations.
    Returns 0.0 on any error (fail-open: prefer running over blocking on DB error).
    """
    try:
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        result = (
            client.table("execution_events")
            .select("cost_usd")
            .eq("user_id", user_id)
            .gte("created_at", today_utc)
            .execute()
        )
        rows = result.data or []
        return round(sum(float(r.get("cost_usd") or 0) for r in rows), 6)
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
) -> Optional[str]:
    """Write one row to execution_events. Never raises. Returns the row id on
    success, None on insert failure.

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
        envelope_load_ms:   ms spent in load_reviewer_governance_envelope() for
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
        if input_tokens is not None and output_tokens is not None:
            cost_usd = compute_cost_usd_inclusive(
                model=model or "claude-sonnet-4-6",
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
        if duration_ms is not None:
            row["duration_ms"] = duration_ms
        if envelope_load_ms is not None:
            row["envelope_load_ms"] = envelope_load_ms
        if wake_source is not None:
            row["wake_source"] = wake_source
        if funnel_decision is not None:
            row["funnel_decision"] = funnel_decision
        if agent_run_id is not None:
            row["agent_run_id"] = agent_run_id

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
        logger.warning("[TELEMETRY] record_execution_event failed (non-fatal): %s", e)
        return None
