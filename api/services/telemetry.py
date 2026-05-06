"""
Execution Telemetry — ADR-250 Phase 2.

Single write path for execution_events table: one row per invocation attempt,
always written regardless of outcome (success, failed, skipped).

Also provides:
  - cache-inclusive cost computation (accurate Anthropic billing model)
  - daily spend query for the Phase 3 spend guard

Design rules (from observability.md):
  - record_execution_event() never raises — non-fatal, logs on failure
  - cost_usd uses cache-inclusive formula, NOT the legacy cache-agnostic compute_cost_usd()
  - agent_run_id is NULL for failures that produce no agent_runs row
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Billing rates (mirrors platform_limits.BILLING_RATES — kept local to avoid
# circular import; if rates change update both)
# ---------------------------------------------------------------------------

_BILLING_RATES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":          {"input_per_mtok": 6.00,  "output_per_mtok": 30.00},
    "claude-opus-4-6":            {"input_per_mtok": 30.00, "output_per_mtok": 150.00},
    "claude-haiku-4-5-20251001":  {"input_per_mtok": 1.60,  "output_per_mtok": 8.00},
}
_DEFAULT_RATE = _BILLING_RATES["claude-sonnet-4-6"]

# Daily spend ceiling (Phase 3 spend guard). Overridable via env var.
DAILY_SPEND_CEILING_USD: float = float(os.getenv("DAILY_SPEND_CEILING_USD", "10.0"))


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

    Unlike platform_limits.compute_cost_usd() which is cache-agnostic,
    this accounts for cache_read (10% of input rate) and cache_creation
    (125% of input rate), giving the accurate per-invocation cost.
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
    shape: str,
    trigger_type: str,
    status: str,
    error_reason: Optional[str] = None,
    error_detail: Optional[str] = None,
    tool_rounds: Optional[int] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cache_read_tokens: Optional[int] = None,
    cache_create_tokens: Optional[int] = None,
    model: Optional[str] = None,
    duration_ms: Optional[int] = None,
    agent_run_id: Optional[str] = None,
) -> None:
    """Write one row to execution_events. Never raises.

    Args:
        client:             Supabase service client
        user_id:            User UUID
        slug:               Recurrence slug
        shape:              deliverable | accumulation | action | maintenance
        trigger_type:       scheduled | manual | back_office
        status:             success | failed | skipped
        error_reason:       taxonomy key (see observability.md Error Reason Taxonomy)
        error_detail:       exception message, truncated to 2000 chars
        tool_rounds:        number of LLM tool rounds executed
        input_tokens:       fresh input tokens (excludes cache)
        output_tokens:      output tokens
        cache_read_tokens:  cache read tokens
        cache_create_tokens: cache creation tokens
        model:              model name for cost rate lookup
        duration_ms:        wall-clock duration of the invocation
        agent_run_id:       agent_runs.id if a row was created (NULL for early exits)
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
            "shape": shape,
            "trigger_type": trigger_type,
            "status": status,
        }
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
        if agent_run_id is not None:
            row["agent_run_id"] = agent_run_id

        client.table("execution_events").insert(row).execute()

        logger.info(
            "[TELEMETRY] %s/%s %s%s",
            shape, slug, status,
            f" cost=${cost_usd:.4f}" if cost_usd else "",
        )
    except Exception as e:
        logger.warning("[TELEMETRY] record_execution_event failed (non-fatal): %s", e)
