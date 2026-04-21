"""
Risk Gate Primitive — ADR-192 Phase 2

Pre-trade validation for trading-order submission. Runs before any
`submit_order` / `submit_bracket_order` / `submit_trailing_stop` call
dispatched through `handle_platform_tool`. Reads trader-declared risk
parameters from `/workspace/context/trading/_risk.md` and evaluates the
proposed order against them.

**Mode semantics:**
- **autonomous**: called when the trader is NOT present to approve each
  order (e.g., by a scheduled task or by ADR-195's autonomous decision
  loop). Fails closed on missing params + on rule violations.
- **supervised**: called when the trader is present (chat, manual trigger).
  Fails closed on rule violations, but missing params produce a warning
  rather than a block — this preserves today's behavior for traders who
  haven't configured risk params yet.

**The gate is pure Python, zero LLM cost.** It is deterministic; the same
inputs produce the same output. Callers handle the returned dict:

    {
        "approved": bool,
        "reason": str,          # human-readable
        "warnings": list[str],  # non-blocking cautions
        "mode": str,            # echoed
    }

If `approved` is False, the platform-tool handler returns a failure result
to the LLM/caller rather than calling Alpaca. The caller (YARNNN or an
agent) sees the rejection and can either ask the user to adjust limits,
propose a smaller order, or abandon the action.

**Storage:** `/workspace/context/trading/_risk.md` as structured markdown
with one `key: value` per line. Values may be numbers, booleans, strings,
or bracketed lists `[AAPL, MSFT]`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


RISK_MD_PATH = "/workspace/context/trading/_risk.md"


# =============================================================================
# Primary entry point
# =============================================================================

async def check_risk_limits(
    client: Any,
    user_id: str,
    proposed_order: dict,
    mode: str = "supervised",
) -> dict:
    """Evaluate a proposed order against trader-declared risk parameters.

    Args:
        client: Supabase client for reading workspace_files + platform_connection.
        user_id: Trader's user id.
        proposed_order: dict describing the proposed order. Expected keys:
            ticker, side, qty, and optionally order_type, limit_price,
            stop_price, entry_limit_price, take_profit_limit_price,
            stop_loss_stop_price, trail_percent, trail_price, order_class.
        mode: "autonomous" | "supervised". Default "supervised".

    Returns:
        {approved: bool, reason: str, warnings: list[str], mode: str}
    """
    risk_params = await _load_risk_params(client, user_id)

    # Missing-params handling depends on mode
    if risk_params is None:
        if mode == "autonomous":
            return {
                "approved": False,
                "reason": (
                    "No risk parameters declared. Create "
                    f"/workspace/context/trading/_risk.md (see scaffold_default_risk_md) "
                    "before enabling autonomous trading."
                ),
                "warnings": [],
                "mode": mode,
            }
        # Supervised: advisory warning, order still flows
        return {
            "approved": True,
            "reason": "Supervised execution; no risk parameters configured.",
            "warnings": [
                "Risk parameters not set at /workspace/context/trading/_risk.md. "
                "Autonomous execution will fail-closed until configured."
            ],
            "mode": mode,
        }

    # Params present — run the rule battery
    account_state = await _fetch_account_state(client, user_id)
    failures: list[str] = []
    warnings: list[str] = []

    ticker = (proposed_order.get("ticker") or "").upper()
    if not ticker:
        failures.append("missing ticker")

    # Ticker whitelist/blacklist
    if ticker:
        allowed = risk_params.get("allowed_tickers") or []
        blocked = risk_params.get("blocked_tickers") or []
        if allowed and ticker not in allowed:
            failures.append(f"{ticker} not in allowed_tickers ({', '.join(allowed)})")
        if ticker in blocked:
            failures.append(f"{ticker} is in blocked_tickers")

    # Order size in shares
    qty = _safe_float(proposed_order.get("qty"))
    max_order_shares = risk_params.get("max_order_size_shares")
    if max_order_shares is not None and qty is not None and qty > max_order_shares:
        failures.append(
            f"order size {qty} exceeds max_order_size_shares ({max_order_shares})"
        )

    # Notional position size (requires a price to estimate against)
    price_estimate = _derive_price_estimate(proposed_order)
    max_position_usd = risk_params.get("max_position_size_usd")
    if max_position_usd is not None and qty is not None:
        if price_estimate is not None:
            notional = qty * price_estimate
            if notional > max_position_usd:
                failures.append(
                    f"notional ${notional:.2f} exceeds max_position_size_usd "
                    f"(${max_position_usd})"
                )
        else:
            warnings.append(
                "max_position_size_usd configured but order is market with no "
                "estimable price — notional check skipped"
            )

    # Portfolio percent limit
    max_pct = risk_params.get("max_position_percent_of_portfolio")
    equity = _safe_float(account_state.get("equity"))
    if max_pct is not None and qty is not None and price_estimate is not None and equity:
        notional = qty * price_estimate
        pct = (notional / equity) * 100
        if pct > max_pct:
            failures.append(
                f"position would be {pct:.1f}% of portfolio, exceeds "
                f"max_position_percent_of_portfolio ({max_pct}%)"
            )

    # Daily P&L loss threshold
    max_daily_loss = risk_params.get("max_daily_loss_usd")
    todays_pnl = _safe_float(account_state.get("todays_pnl"))
    if max_daily_loss is not None and todays_pnl is not None:
        if todays_pnl <= -float(max_daily_loss):
            failures.append(
                f"today's P&L (${todays_pnl:.2f}) has hit max_daily_loss_usd "
                f"(-${max_daily_loss}); no new positions"
            )

    # Day-trade count (PDT rule)
    max_day_trades = risk_params.get("max_day_trades")
    daytrade_count = account_state.get("daytrade_count")
    if max_day_trades is not None and daytrade_count is not None:
        try:
            if int(daytrade_count) >= int(max_day_trades):
                failures.append(
                    f"daytrade_count ({daytrade_count}) has hit max_day_trades "
                    f"({max_day_trades}) — PDT risk"
                )
        except (TypeError, ValueError):
            pass

    # Require stop-loss
    if risk_params.get("require_stop_loss"):
        has_stop = (
            proposed_order.get("stop_loss_stop_price")
            or proposed_order.get("stop_price")
            or proposed_order.get("trail_percent")
            or proposed_order.get("trail_price")
            or proposed_order.get("order_class") == "bracket"
            or proposed_order.get("order_type") == "trailing_stop"
        )
        if not has_stop:
            failures.append(
                "require_stop_loss=true but order has no stop (not bracket, "
                "not trailing, no stop_price)"
            )

    # Trading hours (approximate US market hours check)
    if risk_params.get("trading_hours_only"):
        if not _is_us_market_hours():
            failures.append(
                "trading_hours_only=true but order submitted outside approximate "
                "US market hours (Mon-Fri 13:30-20:00 UTC / 9:30-16:00 ET)"
            )

    if failures:
        return {
            "approved": False,
            "reason": "Risk check failed: " + "; ".join(failures),
            "warnings": warnings,
            "mode": mode,
        }

    return {
        "approved": True,
        "reason": "Within declared risk parameters.",
        "warnings": warnings,
        "mode": mode,
    }


# =============================================================================
# Workspace readers
# =============================================================================

async def _load_risk_params(client: Any, user_id: str) -> Optional[dict]:
    """Load _risk.md from the user's workspace. Returns None if absent."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", RISK_MD_PATH)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        content = rows[0].get("content") or ""
        if not content.strip():
            return None
        return _parse_risk_md(content)
    except Exception as e:
        logger.warning(f"[RISK_GATE] Failed to load _risk.md for {user_id[:8]}: {e}")
        return None


def _parse_risk_md(content: str) -> dict:
    """Parse _risk.md markdown into a flat dict of typed values.

    Supports:
      key: value       → string, int, or float
      key: true/false  → bool
      key: [a, b, c]   → list of uppercased strings (for tickers)
    """
    params: dict = {}
    for raw in content.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        if ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip().rstrip(",")
        if not key or not value:
            continue

        # Bracketed list
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner:
                items = [item.strip().strip('"').strip("'").upper() for item in inner.split(",")]
                params[key] = [i for i in items if i]
            else:
                params[key] = []
            continue

        # Boolean
        lowered = value.lower()
        if lowered in ("true", "yes", "on"):
            params[key] = True
            continue
        if lowered in ("false", "no", "off"):
            params[key] = False
            continue

        # Number (int preferred when no decimal)
        try:
            if "." in value:
                params[key] = float(value)
            else:
                params[key] = int(value)
        except ValueError:
            params[key] = value

    return params


async def _fetch_account_state(client: Any, user_id: str) -> dict:
    """Fetch current trading account state (equity, P&L, daytrade count).

    Returns an empty dict if the user has no active trading connection or
    the Alpaca call fails. Risk gate degrades gracefully — size / ticker
    rules that don't need account state still apply.
    """
    try:
        conn_result = (
            client.table("platform_connections")
            .select("access_token, metadata")
            .eq("user_id", user_id)
            .eq("platform", "trading")
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        rows = conn_result.data or []
        if not rows:
            return {}
        conn = rows[0]

        # Decrypt + call get_account
        try:
            from integrations.core.tokens import decrypt_token  # type: ignore
        except Exception:
            # Alternative path (some services import via different module)
            from services.encryption import decrypt_token  # type: ignore

        token_raw = conn.get("access_token") or ""
        try:
            token_data = decrypt_token(token_raw) if token_raw else {}
        except Exception as e:
            logger.warning(f"[RISK_GATE] token decrypt failed: {e}")
            return {}

        if isinstance(token_data, str):
            # Older tokens may be encrypted JSON strings; try parse
            import json
            try:
                token_data = json.loads(token_data)
            except Exception:
                return {}
        if not isinstance(token_data, dict):
            return {}

        api_key = token_data.get("api_key") or token_data.get("key")
        api_secret = token_data.get("api_secret") or token_data.get("secret")
        if not (api_key and api_secret):
            return {}

        metadata = conn.get("metadata") or {}
        paper = metadata.get("mode", "paper") == "paper"

        from integrations.core.alpaca_client import get_trading_client
        alpaca = get_trading_client()
        account = await alpaca.get_account(api_key, api_secret, paper)
        if isinstance(account, dict) and account.get("error"):
            return {}

        # Alpaca doesn't expose "todays_pnl" directly; equity_change_today or
        # a derivation from last_equity - equity covers it. Best-effort.
        last_equity = _safe_float(account.get("last_equity"))
        equity = _safe_float(account.get("equity"))
        todays_pnl = None
        if last_equity is not None and equity is not None:
            todays_pnl = equity - last_equity

        return {
            "equity": equity,
            "buying_power": _safe_float(account.get("buying_power")),
            "daytrade_count": account.get("daytrade_count"),
            "todays_pnl": todays_pnl,
        }
    except Exception as e:
        logger.warning(f"[RISK_GATE] account state fetch failed: {e}")
        return {}


# =============================================================================
# Helpers
# =============================================================================

def _safe_float(value: Any) -> Optional[float]:
    """Coerce value to float if possible; otherwise None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _derive_price_estimate(proposed_order: dict) -> Optional[float]:
    """Best-effort price for notional calculations.

    Uses limit / entry-limit / stop prices in that order. Market orders
    without any price context return None; caller treats that as
    'cannot validate' and surfaces a warning rather than a failure.
    """
    for key in ("limit_price", "entry_limit_price", "stop_loss_stop_price", "stop_price"):
        value = _safe_float(proposed_order.get(key))
        if value is not None:
            return value
    return None


def _is_us_market_hours() -> bool:
    """Approximate US market-hours check (no NYSE holiday calendar).

    Returns True on Mon-Fri between 13:30 UTC and 20:00 UTC (rough ET
    equivalent ignoring DST drift of ≤1 hour). Intentionally simple;
    precision tightens if the alpha reveals DST-edge false negatives.
    """
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Sat=5, Sun=6
        return False
    minutes_utc = now.hour * 60 + now.minute
    # 13:30 UTC = 9:30 ET (EST); 20:00 UTC = 16:00 ET (EST).
    # DST introduces a 60-minute shift but the window is generous enough.
    return 13 * 60 + 30 <= minutes_utc <= 20 * 60


# =============================================================================
# Scaffold helper (used at trading connect time; wired in Phase 5)
# =============================================================================

def scaffold_default_risk_md() -> str:
    """Return conservative-default `_risk.md` content for trading onboarding.

    Written to /workspace/context/trading/_risk.md when a user connects
    their trading account (if the file doesn't already exist). User is
    expected to review and adjust before enabling autonomous trading.
    """
    return """# Risk Parameters

<!-- Conservative defaults for trading autonomy.
     REVIEW and adjust these values before enabling autonomous execution.
     Autonomous orders are rejected if this file is missing or if rules fail.
     -->

max_position_size_usd: 1000
max_position_percent_of_portfolio: 10
max_daily_loss_usd: 200
max_day_trades: 2
max_order_size_shares: 100
require_stop_loss: true
trading_hours_only: true
allowed_tickers: []
blocked_tickers: []

<!-- Parameter notes:
- allowed_tickers: empty list `[]` means no whitelist (all tickers allowed).
  Set to e.g. `[AAPL, MSFT, SPY]` to restrict to specific tickers.
- blocked_tickers: add tickers you never want to trade (e.g., volatile small-caps).
- max_day_trades: 3 is the US PDT threshold; 2 leaves one in reserve.
- require_stop_loss: true blocks plain buy/sell without a stop. Use
  bracket order or trailing stop to satisfy.
- trading_hours_only: true blocks orders outside approximate US market
  hours (Mon-Fri 9:30-16:00 ET). Set false to allow pre/post-market.
- max_position_size_usd: notional cap per order. Requires a price (limit
  or derived) to evaluate — market orders skip this check with a warning.
- max_position_percent_of_portfolio: position-size as % of total equity.
- max_daily_loss_usd: blocks new positions once today's unrealized P&L
  has dropped this far. Uses equity - last_equity as daily P&L proxy.
-->
"""
