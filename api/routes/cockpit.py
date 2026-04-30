"""
Cockpit endpoints — operator-facing surfaces for the four-face cockpit
(ADR-228 + ADR-242).

Today's surface:
  GET /api/cockpit/money-truth/{user_id}
    — Alpaca account snapshot for the MoneyTruth face's bundle override
      path (ADR-242 D1). Returns the live brokerage state when the
      operator has connected Alpaca; falls back to a normalized "no live
      data" shape that the FE handles with substrate-fallback rendering.

The endpoint is named by what it returns (Alpaca account snapshot), not
by who consumes it (cockpit). Future readers wanting Alpaca live equity
for any reason can use the same endpoint.

Auth boundary: `user_id` in the path must match `auth.user_id`. No
cross-user reads.

Per ADR-242 §"Singular Implementation discipline": this is the singular
live-snapshot path. No parallel surface elsewhere.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class MoneyTruthResponse(BaseModel):
    """Normalized brokerage snapshot for the MoneyTruth face.

    When `live: True`, all numeric fields are populated from the live
    platform. When `live: False`, `fallback_reason` indicates why and
    the numeric fields are None — the FE renders substrate-fallback
    state per ADR-242 D2.
    """
    live: bool
    provider: Optional[str] = None
    paper: Optional[bool] = None
    equity: Optional[float] = None
    cash: Optional[float] = None
    buying_power: Optional[float] = None
    day_pnl: Optional[float] = None
    day_pnl_pct: Optional[float] = None
    positions_count: Optional[int] = None
    as_of: Optional[str] = None
    # Fallback shape — populated when live=False.
    fallback_reason: Optional[str] = None  # 'no_platform_connection' | 'alpaca_unreachable' | 'no_credentials'


# ---------------------------------------------------------------------------
# GET /cockpit/money-truth/{user_id}
# ---------------------------------------------------------------------------

@router.get("/money-truth/{user_id}", response_model=MoneyTruthResponse)
async def get_money_truth(user_id: str, auth: UserClient) -> MoneyTruthResponse:
    """ADR-242 D1: live brokerage snapshot for the MoneyTruth face.

    Reads `platform_connections` for the operator's `trading` row,
    decrypts credentials (`api_key:api_secret` format per ADR-187),
    calls Alpaca's `/v2/account` + `/v2/positions`. On any error
    (no connection, no credentials, Alpaca unreachable), returns the
    normalized `live: False` shape. The FE's `TraderMoneyTruth`
    component handles graceful degradation.
    """
    # Auth boundary — no cross-user reads.
    if user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="Cannot read other users' cockpit data")

    from integrations.core.tokens import get_token_manager
    from integrations.core.alpaca_client import get_trading_client
    from datetime import datetime, timezone

    # Read the trading platform connection.
    try:
        result = (
            auth.client.table("platform_connections")
            .select("credentials_encrypted, metadata, status")
            .eq("user_id", user_id)
            .eq("platform", "trading")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(f"[COCKPIT] platform_connections read failed for {user_id[:8]}: {exc}")
        return MoneyTruthResponse(live=False, fallback_reason="no_platform_connection")

    rows = result.data or []
    if not rows:
        return MoneyTruthResponse(live=False, fallback_reason="no_platform_connection")

    row = rows[0]
    if row.get("status") != "active":
        return MoneyTruthResponse(live=False, fallback_reason="no_platform_connection")

    encrypted_credentials = row.get("credentials_encrypted")
    if not encrypted_credentials:
        return MoneyTruthResponse(live=False, fallback_reason="no_credentials")

    # Decrypt and split. ADR-187 stores `api_key:api_secret` joined.
    try:
        token_manager = get_token_manager()
        decrypted = token_manager.decrypt(encrypted_credentials)
        if ":" not in decrypted:
            return MoneyTruthResponse(live=False, fallback_reason="no_credentials")
        api_key, api_secret = decrypted.split(":", 1)
    except Exception as exc:
        logger.warning(f"[COCKPIT] credential decrypt failed for {user_id[:8]}: {exc}")
        return MoneyTruthResponse(live=False, fallback_reason="no_credentials")

    paper = bool((row.get("metadata") or {}).get("paper", True))

    # Live Alpaca call.
    try:
        client = get_trading_client()
        account = await client.get_account(api_key, api_secret, paper)
        if isinstance(account, dict) and account.get("error"):
            logger.info(f"[COCKPIT] Alpaca account error for {user_id[:8]}: {account.get('error')}")
            return MoneyTruthResponse(live=False, fallback_reason="alpaca_unreachable")
        positions = await client.get_positions(api_key, api_secret, paper)
    except Exception as exc:
        logger.warning(f"[COCKPIT] Alpaca call failed for {user_id[:8]}: {exc}")
        return MoneyTruthResponse(live=False, fallback_reason="alpaca_unreachable")

    # Normalize numeric fields. Alpaca returns strings; cast to float
    # silently and fall back to None on parse error (the FE displays
    # absent fields as "—" rather than 0).
    def _num(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    equity = _num(account.get("equity"))
    cash = _num(account.get("cash"))
    buying_power = _num(account.get("buying_power"))

    # Day P&L: derive from positions sum of `change_today`. Alpaca's
    # account endpoint exposes equity but not day Δ directly; positions
    # carry per-symbol change_today which sums to day P&L for open
    # positions. Closed/realized P&L for today is in account history;
    # MoneyTruth face shows the open-position day delta as the headline.
    day_pnl: Optional[float] = None
    if isinstance(positions, list):
        try:
            day_pnl = sum(_num(p.get("change_today")) or 0.0 for p in positions)
        except Exception:
            day_pnl = None

    day_pnl_pct: Optional[float] = None
    if equity is not None and equity > 0 and day_pnl is not None:
        day_pnl_pct = (day_pnl / equity) * 100.0

    return MoneyTruthResponse(
        live=True,
        provider="alpaca",
        paper=paper,
        equity=equity,
        cash=cash,
        buying_power=buying_power,
        day_pnl=day_pnl,
        day_pnl_pct=day_pnl_pct,
        positions_count=len(positions) if isinstance(positions, list) else 0,
        as_of=datetime.now(timezone.utc).isoformat(),
    )
