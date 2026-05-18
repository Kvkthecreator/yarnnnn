"""
Platform Limits Service — ADR-172 (Usage-First Billing) + ADR-291 (Unified Cost Ledger)

Single gate: effective balance > 0. No tier limits, no capability gates.

Balance model:
  balance_usd on workspace = sum of all top-ups + grants (signup $3, topup $10/$25/$50,
  subscription $20 refill, admin grants).
  Effective balance = balance_usd − SUM(execution_events.cost_usd since last subscription_refill_at).

Token metering (ADR-291 — substrate collapse):
  Every LLM call → record_execution_event() → execution_events table.
  Cost computed via services.telemetry.compute_cost_usd_inclusive (cache-aware, 2x markup).
  Billing rates live in services.telemetry._BILLING_RATES — single source of truth.

Subscription (optional):
  Pro Monthly $19/mo or Pro Yearly $180/yr.
  Subscriber = is_subscriber flag in usage summary (UI only, no capability gating).
  Subscription billing event resets balance to $20 via balance_transactions row.
"""

import logging
from typing import Optional, Literal
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

SyncFrequency = Literal["1x_daily", "2x_daily", "4x_daily", "hourly"]


# =============================================================================
# Billing rates + cost computation — ADR-291 sunset
# =============================================================================
# Rates and cost computation live in services.telemetry now:
#   - _BILLING_RATES (single source of truth for 2x markup)
#   - compute_cost_usd_inclusive() (cache-aware)
# This module only orchestrates the gate (check_balance); cost math is one
# function in one place per Singular Implementation (ADR-291 D2).

# =============================================================================
# Sync schedule helpers (scheduling infra only — no tier gate)
# =============================================================================

SYNC_SCHEDULES = {
    "1x_daily": ["08:00"],
    "2x_daily": ["08:00", "18:00"],
    "4x_daily": ["00:00", "06:00", "12:00", "18:00"],
    "hourly": None,
}

_SCHEDULE_MATCH_WINDOW = 10

TIMEZONE_ALIASES = {
    "seoul": "Asia/Seoul",
}


def _resolve_timezone(user_timezone: Optional[str]) -> pytz.BaseTzInfo:
    tz_value = (user_timezone or "UTC").strip()
    if not tz_value:
        return pytz.UTC
    try:
        return pytz.timezone(tz_value)
    except pytz.UnknownTimeZoneError:
        pass
    alias = TIMEZONE_ALIASES.get(tz_value.lower())
    if alias:
        return pytz.timezone(alias)
    normalized = tz_value.replace(" ", "_")
    if "/" not in normalized:
        suffix = f"/{normalized.lower()}"
        matches = [name for name in pytz.all_timezones if name.lower().endswith(suffix)]
        if len(matches) == 1:
            return pytz.timezone(matches[0])
    return pytz.UTC


def normalize_timezone_name(user_timezone: Optional[str]) -> str:
    return _resolve_timezone(user_timezone).zone


def get_next_sync_time(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> str:
    tz = _resolve_timezone(user_timezone)
    now = datetime.now(tz)
    if sync_frequency == "hourly":
        next_sync = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        schedule = SYNC_SCHEDULES.get(sync_frequency, ["08:00"])
        next_sync = _find_next_scheduled_time(now, schedule, tz)
    return next_sync.isoformat()


def _find_next_scheduled_time(now, schedule, tz):
    today = now.date()
    for time_str in schedule:
        hour, minute = map(int, time_str.split(":"))
        scheduled = tz.localize(datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute)))
        if scheduled > now:
            return scheduled
    tomorrow = today + timedelta(days=1)
    hour, minute = map(int, schedule[0].split(":"))
    return tz.localize(datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute)))


def should_sync_now(sync_frequency: SyncFrequency, user_timezone: str = "UTC") -> bool:
    tz = _resolve_timezone(user_timezone)
    now = datetime.now(tz)
    if sync_frequency == "hourly":
        return now.minute < _SCHEDULE_MATCH_WINDOW
    schedule = SYNC_SCHEDULES.get(sync_frequency, [])
    for time_str in schedule:
        hour, minute = map(int, time_str.split(":"))
        if now.hour == hour and now.minute < _SCHEDULE_MATCH_WINDOW:
            return True
    return False


# =============================================================================
# Subscription status helpers (UI + refill — not capability gating)
# =============================================================================

def get_user_tier(client, user_id: str) -> str:
    """Returns 'pro' or 'free'. Preserved for legacy callers — not used for gating."""
    try:
        result = client.table("workspaces")\
            .select("subscription_status")\
            .eq("owner_id", user_id)\
            .limit(1)\
            .execute()
        rows = result.data or []
        if rows:
            status = rows[0].get("subscription_status", "free")
            if status in ("starter", "pro"):
                return "pro"
        return "free"
    except Exception:
        return "free"


def is_subscriber(client, user_id: str) -> bool:
    """True if user has an active Pro subscription (monthly or yearly)."""
    return get_user_tier(client, user_id) == "pro"


def get_sync_frequency_for_user(client, user_id: str) -> SyncFrequency:
    """All users get hourly sync — preserved for scheduler compatibility."""
    return "hourly"


# =============================================================================
# Balance — ADR-172: single enforcement gate
# =============================================================================

def get_effective_balance(client, user_id: str) -> float:
    """Effective balance = workspace.balance_usd − spend since last refill.

    Uses get_effective_balance() RPC (migration 144).
    Returns 0.0 on error (fail-safe: block if unknown).
    """
    try:
        result = client.rpc("get_effective_balance", {"p_user_id": user_id}).execute()
        val = result.data
        return float(val) if val is not None else 0.0
    except Exception as e:
        logger.warning(f"[BALANCE] Failed to get effective balance for {user_id}: {e}")
        return 0.0


def check_balance(client, user_id: str) -> tuple[bool, float]:
    """Check if user has positive effective balance.

    Returns: (allowed, effective_balance_usd)
    Hard stop at zero — no soft overage.
    """
    balance = get_effective_balance(client, user_id)
    return balance > 0, balance


def grant_balance(client, workspace_id: str, amount_usd: float, kind: str,
                  lemon_order_id: str = None, lemon_subscription_id: str = None,
                  metadata: dict = None) -> None:
    """Add to workspace balance and record in balance_transactions.

    kind: 'signup_grant' | 'topup' | 'subscription_refill' | 'admin_grant'
    For 'subscription_refill': also resets subscription_refill_at to now.
    """
    try:
        # Add to balance
        workspace = client.table("workspaces")\
            .select("balance_usd")\
            .eq("id", workspace_id)\
            .limit(1)\
            .execute()
        if not workspace.data:
            logger.warning(f"[BALANCE] Workspace {workspace_id} not found for grant")
            return

        current = float(workspace.data[0].get("balance_usd", 0) or 0)
        update_data = {"balance_usd": round(current + amount_usd, 4)}

        if kind == "subscription_refill":
            # Reset refill anchor so spend counter restarts
            update_data["subscription_refill_at"] = datetime.utcnow().isoformat()
            # For subscription refill: set balance to $20, don't accumulate
            update_data["balance_usd"] = amount_usd

        client.table("workspaces").update(update_data).eq("id", workspace_id).execute()

        # Record transaction
        tx = {
            "workspace_id": workspace_id,
            "kind": kind,
            "amount_usd": amount_usd,
        }
        if lemon_order_id:
            tx["lemon_order_id"] = lemon_order_id
        if lemon_subscription_id:
            tx["lemon_subscription_id"] = lemon_subscription_id
        if metadata:
            tx["metadata"] = metadata
        client.table("balance_transactions").insert(tx).execute()

    except Exception as e:
        logger.warning(f"[BALANCE] Failed to grant {kind} ${amount_usd} to workspace {workspace_id}: {e}")


# =============================================================================
# Monthly spend display — ADR-291 (reads from execution_events)
# =============================================================================

def get_monthly_spend_usd(client, user_id: str) -> float:
    """Total LLM spend this calendar month (analytics/display — not enforcement).

    ADR-291: reads execution_events.cost_usd, the sole canonical cost ledger.
    """
    try:
        from datetime import datetime as _dt
        month_start = _dt.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        result = (
            client.table("execution_events")
            .select("cost_usd")
            .eq("user_id", user_id)
            .gte("created_at", month_start)
            .execute()
        )
        rows = result.data or []
        return round(sum(float(r.get("cost_usd") or 0) for r in rows), 6)
    except Exception as e:
        logger.warning(f"[BALANCE] get_monthly_spend_usd failed: {e}")
        return 0.0


# =============================================================================
# Usage summary — consumed by /api/user/limits
# =============================================================================

def get_usage_summary(client, user_id: str, user_timezone: str = "UTC") -> dict:
    """Balance-first usage summary (ADR-172).

    Returns:
        balance_usd: effective remaining balance
        spend_usd: total token spend this month (display only)
        is_subscriber: True if active Pro subscription
        subscription_plan: 'pro' | 'pro_yearly' | None
        next_refill: ISO timestamp of next subscription billing (if subscriber)
    """
    balance = get_effective_balance(client, user_id)
    spend = get_monthly_spend_usd(client, user_id)
    subscriber = is_subscriber(client, user_id)

    # Get subscription details for display
    sub_plan = None
    next_refill = None
    try:
        ws = client.table("workspaces")\
            .select("subscription_plan, subscription_expires_at")\
            .eq("owner_id", user_id)\
            .limit(1)\
            .execute()
        if ws.data:
            sub_plan = ws.data[0].get("subscription_plan")
            next_refill = ws.data[0].get("subscription_expires_at")
    except Exception:
        pass

    return {
        "balance_usd": round(balance, 4),
        "spend_usd": round(spend, 4),
        "is_subscriber": subscriber,
        "subscription_plan": sub_plan,
        "next_refill": next_refill,
    }
