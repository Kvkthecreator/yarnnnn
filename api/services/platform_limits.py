"""
Platform Limits Service — ADR-396 (Type-B subscription over the metered balance)
+ ADR-291 (Unified Cost Ledger). Supersedes the ADR-172 flat pay-as-you-go shape.

Single gate: effective balance > 0. No capability gates (ADR-172 discipline
preserved — a tier sets ceilings, never feature locks).

Balance model (ADR-396, allowance layer retired by ADR-490):
  Usage is PAY-AS-YOU-GO: the signup grant + paid TOP-UPS accumulate onto
  balance_usd and never reset ("balance IS the currency", no credit unit).
  Hard-stop at zero. Tiers grant a $0 monthly allowance (ADR-490 §1③ — the
  Type-B included-allowance layer is retired; allowance_usd survives as a
  grandfathered/machinery column).
  Effective balance = (allowance_usd + balance_usd) − SUM(billed spend since the
  anchor), where billed = COALESCE(execution_events.billed_usd, cost_usd)
  (ADR-490 §2 — the pool draws provider cost × the platform margin). Computed in
  the get_effective_balance RPC (migrations 194/200/224).

Grants:
  grant_allowance()  — kept as the banking/anchor engine (banks surviving value,
                       moves the anchor); with ADR-490 tier allowances it grants $0.
  grant_balance()    — additive top-ups + signup/admin grants onto balance_usd.
  (Legacy 'subscription_refill' balance-reset removed by ADR-396 — it wiped top-ups.)

Token metering (ADR-291 — substrate collapse):
  Every LLM call → record_execution_event() → execution_events table.
  cost_usd = actual provider cost (compute_cost_usd_inclusive, cache-aware);
  billed_usd = cost × billing_tiers.USAGE_BILLING_MULTIPLIER (ADR-490), stamped at
  the same single write site. Rates live in services.telemetry._BILLING_RATES.

Transparency (ADR-396): the customer surfaces show ACTIVITY (usage + allowance
consumed), NOT dollar figures. Dollars stay internal to this service + the ledger.
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
#   - _BILLING_RATES (provider list prices — single source of truth)
#   - compute_cost_usd_inclusive() (cache-aware, at-cost)
#   - billed_usd = cost × billing_tiers.USAGE_BILLING_MULTIPLIER (ADR-490)
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
    """Returns 'free' | 'starter' | 'pro' — the workspace's subscription tier
    (ADR-396). Reads `subscription_tier` via the billing_tiers source of truth.
    Not used for gating (the balance gate is tier-agnostic); drives display +
    the retention/connector ceilings."""
    from services.billing_tiers import get_tier
    return get_tier(client, user_id)


def is_subscriber(client, user_id: str) -> bool:
    """True if the workspace is on any paid tier (ADR-396)."""
    from services.billing_tiers import PAID_TIERS
    return get_user_tier(client, user_id) in PAID_TIERS


def get_sync_frequency_for_user(client, user_id: str) -> SyncFrequency:
    """All users get hourly sync — preserved for scheduler compatibility."""
    return "hourly"


# =============================================================================
# Balance — ADR-172: single enforcement gate
# =============================================================================

def _acting_workspace_id(user_id: str, workspace_id: Optional[str] = None) -> Optional[str]:
    """The workspace whose pool the caller draws (ADR-407 Phase 0). Resolution
    mirrors the ADR-373 sweep spine: explicit → request contextvar → owner
    resolution. A member acting in a granted workspace resolves THAT workspace
    (contextvar), so their spend gates against — and debits — the shared pool."""
    from services.workspace_context import effective_workspace_id
    return effective_workspace_id(user_id, workspace_id)


def get_effective_balance(client, user_id: str, workspace_id: Optional[str] = None) -> float:
    """Effective balance = (allowance + balance) − spend since the anchor, for
    the ACTING WORKSPACE (ADR-407 Phase 0; get_effective_balance RPC re-keyed
    to p_workspace_id in migration 200).

    Returns 0.0 on error or when no workspace resolves (fail-safe: block if unknown).
    """
    try:
        ws = _acting_workspace_id(user_id, workspace_id)
        if not ws:
            logger.warning(f"[BALANCE] No workspace resolves for {user_id}; gating closed")
            return 0.0
        result = client.rpc("get_effective_balance", {"p_workspace_id": ws}).execute()
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


def check_draw(
    client,
    user_id: str,
    *,
    workspace_id: Optional[str] = None,
    principal_id: Optional[str] = None,
) -> tuple[bool, Optional[str], dict]:
    """THE draw gate — may this principal draw the workspace pool right now?

    ADR-445 §9 (closed 2026-07-28, ADR-491 Phase 3): the per-member cap used to
    bind at exactly ONE call site (the addressed path) while lanes, studio, and
    images drew the pool with no gate at all — a cap that bounds one
    conversation surface, not a member. This helper is the single
    implementation both checks share; every costed, member-facing entry calls
    it ONCE before launching model work:

      1. the pool hard-stop (ADR-396) — applies to every principal;
      2. the per-member cap (ADR-445 §7 P4, member_caps) — layered on top;
         the owner is never capped; absent cap = uncapped.

    Returns (allowed, reason, detail):
      (True,  None,               {})                       — draw away
      (False, 'balance_exhausted', {'balance_usd': ...})    — pool empty
      (False, 'member_capped',     {'cap_usd', 'spent_usd'}) — this principal
                                                              is at their cap

    NOT called on the wake/recurrence lane: standing work attributes to the
    owner (the radar/recurrence convention), who is never capped — the wake
    path keeps its own check_balance. Fail-safe semantics are inherited from
    the parts: a cap read error → uncapped (the hard-stop backstops); a balance
    read error → 0.0 → blocked (never over-spend on a DB hiccup).
    """
    allowed, balance = check_balance(client, user_id)
    if not allowed:
        return False, "balance_exhausted", {"balance_usd": round(balance, 4)}
    from services.member_caps import check_member_cap
    cap_ok, cap_usd, cap_spent = check_member_cap(
        client, user_id, principal_id, workspace_id=workspace_id
    )
    if not cap_ok:
        return False, "member_capped", {
            "cap_usd": cap_usd,
            "spent_usd": round(cap_spent, 4),
        }
    return True, None, {}


def spend_by_principal(
    client, user_id: str, workspace_id: Optional[str] = None
) -> list[dict]:
    """ADR-416 Phase 1 — per-principal spend attribution over the workspace pool.

    "Who spent what" — the legibility consumer of `execution_events.principal_id`
    (which migration 192 captured but nothing read). Returns one row per acting
    principal for the ACTING WORKSPACE, over the SAME window the balance gate uses
    (migration 206 mirrors get_effective_balance's anchor), so the rows sum to the
    pool's spend-since-anchor.

    This is a READ, never a gate: the hard-stop stays workspace-summed (one pool,
    ADR-416 D-root); this only attributes the draws within it. The balance
    mechanics are untouched.

    Returns [] on error or when no workspace resolves (fail-safe: legibility, not
    enforcement — an empty rollup never blocks spend).

    Each row: {"principal_id": str, "spend_usd": float, "event_count": int}.
    """
    try:
        ws = _acting_workspace_id(user_id, workspace_id)
        if not ws:
            return []
        result = client.rpc("spend_by_principal", {"p_workspace_id": ws}).execute()
        rows = result.data or []
        return [
            {
                "principal_id": r.get("principal_id"),
                "spend_usd": float(r.get("spend_usd") or 0),
                "event_count": int(r.get("event_count") or 0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"[SPEND] Failed per-principal rollup for {user_id}: {e}")
        return []


def grant_allowance(client, workspace_id: str, user_id: str, allowance_usd: float,
                    lemon_subscription_id: str = None, metadata: dict = None,
                    period_anchor: str = None) -> bool:
    """Grant a monthly included allowance (ADR-396 — the billing-cycle event).

    Type-B rule (confirmed 2026-07-01): allowance EXPIRES each cycle, paid top-ups
    ALWAYS survive. Spend draws allowance-first then top-ups (get_effective_balance
    sums both against spend), so at grant time the surviving top-up portion is:

        surviving_topups = min(old_balance_usd, max(0, effective_balance))

    Proof: with pool = allowance A + topups T and cycle spend S (allowance-first),
    top-ups remaining = T if S≤A else T−(S−A); effective = (A+T)−S. If S≤A then
    effective ≥ T so min(T, effective)=T (all top-ups intact). If S>A then
    effective = T−(S−A) < T so min(T, effective)=effective (allowance gone). Both
    collapse to the formula. This replaces the legacy subscription_refill that
    RESET balance to a flat $20 and wiped paid top-ups — the ADR-396 core fix.

    Sets allowance_usd = the fresh allowance, banks surviving top-ups into
    balance_usd, and moves allowance_granted_at (the new spend anchor) so the
    spend counter restarts for the cycle.

    IDEMPOTENCY (2026-07-02): a single Lemon Squeezy subscription emits SEVERAL
    events for one billing action (subscription_created + subscription_updated +
    subscription_payment_success all fire on the first payment), and each would
    otherwise re-anchor allowance_granted_at — resetting the spend-since-anchor
    window and silently handing back any allowance already consumed this cycle (a
    revenue leak on a renewal with mid-cycle spend). The guard: re-anchor ONLY when
    this is genuinely a new cycle. `period_anchor` is the LS `renews_at` for the
    billing period being granted; it is compared against `workspaces.allowance_period`
    (the period the CURRENT allowance was last granted for — migration 195). A repeat
    call carrying the SAME period_anchor with an UNCHANGED allowance amount is a
    duplicate event and is a no-op. A tier change (allowance amount differs) always
    re-grants; a new period (period_anchor moved) always re-grants. When period_anchor
    is None (legacy callers / top-ups) the guard is inert and behavior is unchanged.

    NOTE: the guard keys off `allowance_period`, NOT `subscription_expires_at` — the
    webhook updates subscription_expires_at to the new renews_at BEFORE calling this,
    so it can't distinguish a fresh cycle from a duplicate. allowance_period is
    written only here, when a grant actually applies.

    Returns True if the grant was applied, False if skipped as a duplicate.
    """
    try:
        ws = (
            client.table("workspaces")
            .select("balance_usd, allowance_usd, allowance_period")
            .eq("id", workspace_id)
            .limit(1)
            .execute()
        )
        if not ws.data:
            logger.warning(f"[BALANCE] Workspace {workspace_id} not found for allowance grant")
            return False

        row = ws.data[0]
        current_allowance = round(float(row.get("allowance_usd", 0) or 0), 4)
        granted_period = row.get("allowance_period")

        # Idempotency guard: same billing period ALREADY GRANTED + same allowance
        # amount = a duplicate LS event → no-op (do NOT re-anchor the spend window).
        if (
            period_anchor is not None
            and granted_period is not None
            and granted_period == period_anchor
            and current_allowance == round(allowance_usd, 4)
        ):
            logger.info(
                f"[BALANCE] Skipping duplicate allowance grant for workspace {workspace_id} "
                f"(period {period_anchor} already granted at ${current_allowance})"
            )
            return False

        effective = get_effective_balance(client, user_id, workspace_id=workspace_id)
        old_balance = float(row.get("balance_usd", 0) or 0)
        surviving_topups = round(min(old_balance, max(0.0, effective)), 4)

        client.table("workspaces").update({
            "allowance_usd": round(allowance_usd, 4),
            "balance_usd": surviving_topups,
            "allowance_granted_at": datetime.utcnow().isoformat(),
            "allowance_period": period_anchor,
        }).eq("id", workspace_id).execute()

        tx = {
            "workspace_id": workspace_id,
            "kind": "allowance_grant",
            "amount_usd": allowance_usd,
        }
        if lemon_subscription_id:
            tx["lemon_subscription_id"] = lemon_subscription_id
        tx["metadata"] = {**(metadata or {}), "banked_topups_usd": surviving_topups}
        client.table("balance_transactions").insert(tx).execute()
        return True

    except Exception as e:
        logger.warning(f"[BALANCE] Failed to grant allowance ${allowance_usd} to workspace {workspace_id}: {e}")
        return False


def grant_balance(client, workspace_id: str, amount_usd: float, kind: str,
                  lemon_order_id: str = None, lemon_subscription_id: str = None,
                  metadata: dict = None) -> None:
    """Add to the topped-up balance and record in balance_transactions.

    kind: 'signup_grant' | 'topup' | 'admin_grant' — the ADDITIVE grants. Top-ups
    accumulate onto balance_usd and never reset (ADR-396 — balance IS the currency,
    the overage pool beneath the allowance). The monthly allowance is granted by
    grant_allowance(), NOT here — the legacy 'subscription_refill' balance-reset
    branch was removed by ADR-396 (it wiped paid top-ups).
    """
    try:
        workspace = client.table("workspaces")\
            .select("balance_usd")\
            .eq("id", workspace_id)\
            .limit(1)\
            .execute()
        if not workspace.data:
            logger.warning(f"[BALANCE] Workspace {workspace_id} not found for grant")
            return

        current = float(workspace.data[0].get("balance_usd", 0) or 0)
        client.table("workspaces").update(
            {"balance_usd": round(current + amount_usd, 4)}
        ).eq("id", workspace_id).execute()

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
# Spend display — ADR-291 (reads from execution_events)
# =============================================================================

def _spend_anchor(ws_row: dict) -> Optional[str]:
    """The spend-window anchor for a workspace row — the SINGLE source of the
    anchor precedence, matched byte-for-byte by the get_effective_balance RPC
    (migration 194): allowance_granted_at → subscription_refill_at → created_at.

    The allowance grant moves allowance_granted_at each cycle, so spend counts
    from the current cycle's grant; a never-subscribed workspace falls through to
    created_at (lifetime spend, same as pre-ADR-396). Any Python reader that sums
    spend against the balance MUST anchor here, or spend + remaining won't
    reconcile to the pool."""
    return (
        ws_row.get("allowance_granted_at")
        or ws_row.get("subscription_refill_at")
        or ws_row.get("created_at")
    )


def get_lifetime_spend_usd(client, user_id: str) -> float:
    """Total LLM spend since the current balance anchor (analytics/display).

    This is the SAME spend window the effective-balance RPC subtracts (ADR-396):
    cost since the allowance anchor (allowance_granted_at → subscription_refill_at
    → created_at). Anchoring spend and remaining on one window is what makes the
    billing surface reconcile — spend + remaining == (allowance_usd + balance_usd)
    by construction. ADR-291 + ADR-490: reads the billed draw
    (COALESCE(billed_usd, cost_usd)) from the sole canonical cost ledger.
    """
    try:
        ws_id = _acting_workspace_id(user_id)
        if not ws_id:
            return 0.0
        ws = (
            client.table("workspaces")
            .select("allowance_granted_at, subscription_refill_at, created_at")
            .eq("id", ws_id)
            .limit(1)
            .execute()
        )
        if not ws.data:
            return 0.0
        anchor = _spend_anchor(ws.data[0])
        result = (
            client.table("execution_events")
            .select("cost_usd, billed_usd")
            .eq("workspace_id", ws_id)
            .gt("created_at", anchor)
            .execute()
        )
        rows = result.data or []
        return round(
            sum(float(r.get("billed_usd") or r.get("cost_usd") or 0) for r in rows), 6
        )
    except Exception as e:
        logger.warning(f"[BALANCE] get_lifetime_spend_usd failed: {e}")
        return 0.0


# =============================================================================
# Usage summary — consumed by /api/user/limits
# =============================================================================

def get_usage_summary(client, user_id: str, user_timezone: str = "UTC") -> dict:
    """Balance-first usage summary (ADR-172).

    Returns:
        balance_usd: effective remaining balance (raw − spend since anchor)
        spend_usd: total token spend since the current balance anchor.
            Same window as the effective-balance subtraction, so
            spend_usd + balance_usd == raw_balance_usd (display only).
        raw_balance_usd: total grants/top-ups before any spend is netted —
            the denominator for the usage progress bar.
        is_subscriber: True if active Pro subscription
        subscription_plan: 'pro' | 'pro_yearly' | None
        next_refill: ISO timestamp of next subscription billing (if subscriber)
    """
    balance = get_effective_balance(client, user_id)
    spend = get_lifetime_spend_usd(client, user_id)
    tier = get_user_tier(client, user_id)
    subscriber = tier in ("starter", "pro")

    # Get subscription details + the allowance pool for display. raw_balance is the
    # POOL the RPC draws from (allowance_usd + balance_usd), so spend + balance ==
    # raw_balance by construction and the usage bar's denominator is correct.
    next_refill = None
    raw_balance = round(balance + spend, 4)  # fallback: reconstruct from anchor window
    allowance = 0.0
    topup_balance = 0.0
    try:
        ws_id = _acting_workspace_id(user_id)
        ws = client.table("workspaces")\
            .select("subscription_expires_at, balance_usd, allowance_usd")\
            .eq("id", ws_id)\
            .limit(1)\
            .execute() if ws_id else None
        if ws is None:
            raise ValueError("no acting workspace")
        if ws.data:
            next_refill = ws.data[0].get("subscription_expires_at")
            allowance = round(float(ws.data[0].get("allowance_usd") or 0), 4)
            topup_balance = round(float(ws.data[0].get("balance_usd") or 0), 4)
            raw_balance = round(allowance + topup_balance, 4)
    except Exception:
        pass

    return {
        "balance_usd": round(balance, 4),
        "spend_usd": round(spend, 4),
        "raw_balance_usd": raw_balance,
        "allowance_usd": allowance,
        "topup_balance_usd": topup_balance,
        "tier": tier,
        "is_subscriber": subscriber,
        "subscription_plan": tier if subscriber else None,
        "next_refill": next_refill,
    }


# =============================================================================
# Usage detail — consumed by /api/user/usage-detail (Usage tab expansion)
# =============================================================================

_USAGE_DETAIL_TOP_N = 6
_USAGE_DETAIL_TREND_DAYS = 14


def get_usage_detail(client, user_id: str) -> dict:
    """Spend breakdown + trend + activity for the Usage tab.

    All derived from execution_events (ADR-291 canonical cost ledger) over
    the current balance anchor window — same window as get_usage_summary, so
    the breakdown's total equals spend_usd. Zero new logging; pure read.

    Returns:
        by_work: list of {slug, runs, cost_usd, pct} — top N work items by
            cost, plus a synthetic {slug: "other"} bucket for the tail.
        trend: list of {date, cost_usd} for the last 14 calendar days
            (zero-filled), oldest→newest, for a spend sparkline/bars.
        activity: {runs, success_rate, avg_cost_usd, failed} over the window.
    """
    from datetime import datetime as _dt, timedelta as _td

    empty = {
        "by_work": [],
        "trend": [],
        "activity": {"runs": 0, "success_rate": None, "avg_cost_usd": 0.0, "failed": 0},
    }
    try:
        ws_id = _acting_workspace_id(user_id)
        if not ws_id:
            return empty
        ws = (
            client.table("workspaces")
            .select("allowance_granted_at, subscription_refill_at, created_at")
            .eq("id", ws_id)
            .limit(1)
            .execute()
        )
        if not ws.data:
            return empty
        anchor = _spend_anchor(ws.data[0])

        rows = (
            client.table("execution_events")
            .select("slug, cost_usd, billed_usd, status, created_at")
            .eq("workspace_id", ws_id)
            .gt("created_at", anchor)
            .execute()
        ).data or []
    except Exception as e:
        logger.warning(f"[USAGE] get_usage_detail failed: {e}")
        return empty

    # ── Spend by work item (ADR-490: billed draw, cost_usd fallback) ──
    per_slug: dict[str, dict] = {}
    total_cost = 0.0
    for r in rows:
        cost = float(r.get("billed_usd") or r.get("cost_usd") or 0)
        slug = r.get("slug") or "unknown"
        bucket = per_slug.setdefault(slug, {"slug": slug, "runs": 0, "cost_usd": 0.0})
        bucket["runs"] += 1
        bucket["cost_usd"] += cost
        total_cost += cost

    ranked = sorted(per_slug.values(), key=lambda b: b["cost_usd"], reverse=True)
    top = ranked[:_USAGE_DETAIL_TOP_N]
    tail = ranked[_USAGE_DETAIL_TOP_N:]
    by_work = [
        {
            "slug": b["slug"],
            "runs": b["runs"],
            "cost_usd": round(b["cost_usd"], 4),
            "pct": round(b["cost_usd"] / total_cost * 100) if total_cost > 0 else 0,
        }
        for b in top
    ]
    if tail:
        tail_cost = sum(b["cost_usd"] for b in tail)
        by_work.append({
            "slug": "other",
            "runs": sum(b["runs"] for b in tail),
            "cost_usd": round(tail_cost, 4),
            "pct": round(tail_cost / total_cost * 100) if total_cost > 0 else 0,
        })

    # ── 14-day spend trend (zero-filled) ──────────────────────────────
    today = _dt.utcnow().date()
    days = [today - _td(days=i) for i in range(_USAGE_DETAIL_TREND_DAYS - 1, -1, -1)]
    by_day: dict[str, float] = {d.isoformat(): 0.0 for d in days}
    for r in rows:
        created = r.get("created_at")
        if not created:
            continue
        day = str(created)[:10]
        if day in by_day:
            by_day[day] += float(r.get("billed_usd") or r.get("cost_usd") or 0)
    trend = [{"date": d, "cost_usd": round(by_day[d], 4)} for d in by_day]

    # ── Activity summary ──────────────────────────────────────────────
    runs = len(rows)
    failed = sum(1 for r in rows if r.get("status") == "failed")
    success_rate = round((runs - failed) / runs * 100) if runs > 0 else None
    avg_cost = round(total_cost / runs, 4) if runs > 0 else 0.0

    return {
        "by_work": by_work,
        "trend": trend,
        "activity": {
            "runs": runs,
            "success_rate": success_rate,
            "avg_cost_usd": avg_cost,
            "failed": failed,
        },
    }
