"""
alpha-trader program-data endpoints (ADR-312 D9; renamed from cockpit.py).

Mounted at `/api/programs/alpha-trader/*`. These are PROGRAM data routes
for the alpha-trader bundle's Home sections (TraderMoneyTruth, Trader-
Portfolio, TraderPositions, TraderOrders, TraderRegime, TraderSignals,
TraderExpectancy). ADR-312 D9 de-namespaced `/api/cockpit/*` — trader data
moved here (program-scoped), the kernel pace dial moved to `/api/pace`.

Two kinds of route:
  - Live brokerage reads (money-truth, portfolio-history, positions,
    recent-orders) — decrypt the operator's Alpaca credentials and call
    the live API; graceful `live: False` fallback on any error.
  - Substrate reads (regime, indicators, signals) — read workspace_files
    directly (zero LLM, zero platform calls); graceful empty-state.

Auth boundary: derives user from `auth.user_id`. No cross-user reads —
operators only see their own brokerage + substrate state.

Singular Implementation: this is the singular trader-data path. No
parallel surface elsewhere.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
# GET /api/programs/alpha-trader/money-truth
# ---------------------------------------------------------------------------

@router.get("/money-truth", response_model=MoneyTruthResponse)
async def get_money_truth(auth: UserClient) -> MoneyTruthResponse:
    """ADR-242 D1: live brokerage snapshot for the MoneyTruth face.

    Reads `platform_connections` for the operator's `trading` row,
    decrypts credentials (`api_key:api_secret` format per ADR-187),
    calls Alpaca's `/v2/account` + `/v2/positions`. On any error
    (no connection, no credentials, Alpaca unreachable), returns the
    normalized `live: False` shape. The FE's `TraderMoneyTruth`
    component handles graceful degradation.

    Auth boundary: derives user_id from auth (auth-scoped only;
    operators see their own brokerage state). Same pattern as
    /api/programs/surfaces.
    """
    user_id = auth.user_id

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
        logger.warning(f"[ALPHA-TRADER] platform_connections read failed for {user_id[:8]}: {exc}")
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
        logger.warning(f"[ALPHA-TRADER] credential decrypt failed for {user_id[:8]}: {exc}")
        return MoneyTruthResponse(live=False, fallback_reason="no_credentials")

    paper = bool((row.get("metadata") or {}).get("paper", True))

    # Live Alpaca call.
    try:
        client = get_trading_client()
        account = await client.get_account(api_key, api_secret, paper)
        if isinstance(account, dict) and account.get("error"):
            logger.info(f"[ALPHA-TRADER] Alpaca account error for {user_id[:8]}: {account.get('error')}")
            return MoneyTruthResponse(live=False, fallback_reason="alpaca_unreachable")
        positions = await client.get_positions(api_key, api_secret, paper)
    except Exception as exc:
        logger.warning(f"[ALPHA-TRADER] Alpaca call failed for {user_id[:8]}: {exc}")
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


# ---------------------------------------------------------------------------
# Shared credential helper — DRY pattern for the live-brokerage endpoints.
# ---------------------------------------------------------------------------

async def _get_alpaca_credentials(auth: UserClient):
    """Read + decrypt Alpaca credentials for the authed operator.

    Returns (api_key, api_secret, paper) or raises HTTPException on failure.
    Used by all three Phase C live-brokerage endpoints.
    """
    from integrations.core.tokens import get_token_manager

    result = (
        auth.client.table("platform_connections")
        .select("credentials_encrypted, metadata, status")
        .eq("user_id", auth.user_id)
        .eq("platform", "trading")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows or rows[0].get("status") != "active":
        raise HTTPException(status_code=404, detail="Trading platform not connected")

    encrypted = rows[0].get("credentials_encrypted")
    if not encrypted:
        raise HTTPException(status_code=422, detail="No trading credentials stored")

    token_manager = get_token_manager()
    try:
        decrypted = token_manager.decrypt(encrypted)
        if ":" not in decrypted:
            raise ValueError("bad format")
        api_key, api_secret = decrypted.split(":", 1)
    except Exception:
        raise HTTPException(status_code=422, detail="Failed to decrypt trading credentials")

    paper = bool((rows[0].get("metadata") or {}).get("paper", True))
    return api_key, api_secret, paper


# ---------------------------------------------------------------------------
# GET /api/programs/alpha-trader/portfolio-history
# ---------------------------------------------------------------------------

@router.get("/portfolio-history")
async def get_portfolio_history(
    auth: UserClient,
    period: str = "1M",
    timeframe: str = "1D",
) -> Dict:
    """ADR-243 Phase C: portfolio equity history for TraderPortfolio chart.

    Returns timestamps + equity series for the selected period/timeframe.
    On Alpaca error, returns {live: False, fallback_reason: ...}.
    """
    try:
        api_key, api_secret, paper = await _get_alpaca_credentials(auth)
    except HTTPException as e:
        return {"live": False, "fallback_reason": "no_platform_connection", "data": None}

    from integrations.core.alpaca_client import get_trading_client
    client = get_trading_client()
    try:
        history = await client.get_portfolio_history(api_key, api_secret, paper, period, timeframe)
        if isinstance(history, dict) and history.get("error"):
            return {"live": False, "fallback_reason": "alpaca_unreachable", "data": None}
        return {"live": True, "paper": paper, "period": period, "timeframe": timeframe, "data": history}
    except Exception as exc:
        logger.warning(f"[ALPHA-TRADER] portfolio_history failed for {auth.user_id[:8]}: {exc}")
        return {"live": False, "fallback_reason": "alpaca_unreachable", "data": None}


# ---------------------------------------------------------------------------
# GET /api/programs/alpha-trader/positions
# ---------------------------------------------------------------------------

@router.get("/positions")
async def get_positions(auth: UserClient) -> Dict:
    """ADR-243 Phase C: open positions for TraderPositions component."""
    try:
        api_key, api_secret, paper = await _get_alpaca_credentials(auth)
    except HTTPException:
        return {"live": False, "fallback_reason": "no_platform_connection", "positions": []}

    from integrations.core.alpaca_client import get_trading_client
    client = get_trading_client()
    try:
        positions = await client.get_positions(api_key, api_secret, paper)
        return {"live": True, "paper": paper, "positions": positions}
    except Exception as exc:
        logger.warning(f"[ALPHA-TRADER] positions failed for {auth.user_id[:8]}: {exc}")
        return {"live": False, "fallback_reason": "alpaca_unreachable", "positions": []}


# ---------------------------------------------------------------------------
# GET /api/programs/alpha-trader/recent-orders
# ---------------------------------------------------------------------------

@router.get("/recent-orders")
async def get_recent_orders(
    auth: UserClient,
    limit: int = 10,
) -> Dict:
    """ADR-243 Phase C: recent orders for TraderOrders component."""
    try:
        api_key, api_secret, paper = await _get_alpaca_credentials(auth)
    except HTTPException:
        return {"live": False, "fallback_reason": "no_platform_connection", "orders": []}

    from integrations.core.alpaca_client import get_trading_client
    client = get_trading_client()
    try:
        orders = await client.list_orders(api_key, api_secret, paper, status="all", limit=limit)
        return {"live": True, "paper": paper, "orders": orders}
    except Exception as exc:
        logger.warning(f"[ALPHA-TRADER] recent_orders failed for {auth.user_id[:8]}: {exc}")
        return {"live": False, "fallback_reason": "alpaca_unreachable", "orders": []}


# ---------------------------------------------------------------------------
# Substrate-read routes (ADR-273 Phase 3)
#
# These three routes read workspace_files directly — no platform calls, no
# LLM. They surface accumulated trading substrate (regime, per-ticker
# indicators, signals + reviewer trail) to the FE Home program sections.
#
# Path conventions per alpha-trader bundle:
#   /workspace/operation/trading/_regime.yaml          — TrackRegime output (D3)
#   /workspace/operation/trading/{TICKER}.yaml         — TrackUniverse output (D3)
#   /workspace/operation/trading/signals/{slug}.yaml   — reviewer/specialist writes
#   /workspace/persona/judgment_log.md                   — reviewer decision trail
#
# All three routes return `{ live: bool, ...payload }` with graceful empty
# states. The FE component renders an empty-state-with-context when
# `live: False` (e.g. "Regime tracker hasn't fired yet").
# ---------------------------------------------------------------------------

import yaml  # noqa: E402  — import at use site keeps the platform-only path lean


_REGIME_PATH = "/workspace/operation/trading/_regime.yaml"
_JUDGMENT_LOG_PATH = "/workspace/persona/judgment_log.md"
_SIGNALS_PREFIX = "/workspace/operation/trading/signals/"
_INDICATORS_PREFIX = "/workspace/operation/trading/"


def _parse_workspace_yaml(content: str) -> Dict[str, Any]:
    """Parse YAML body, tolerating optional frontmatter + leading comments.

    The trading substrate writers (TrackRegime, TrackUniverse) emit a
    leading `# ... — written by ...` comment, then a YAML body. Bundle-
    forked files prepend `--- ... ---` frontmatter (ADR-226). We strip
    both and return the parsed dict, or {} on failure.
    """
    if not content:
        return {}
    body = content
    if body.startswith("---"):
        # Strip frontmatter block (`--- ... ---`).
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    try:
        data = yaml.safe_load(body)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@router.get("/regime")
async def get_regime(auth: UserClient) -> Dict:
    """ADR-273 D3: read /workspace/operation/trading/_regime.yaml.

    Returns the regime predicate computed by the TrackRegime primitive.
    Zero LLM, zero platform calls. Empty-state when file absent (regime
    tracker hasn't fired yet) — FE renders "Regime tracker hasn't fired
    yet — paused or first run pending" per ADR-273 D6.
    """
    user_id = auth.user_id
    try:
        result = (
            auth.client.table("workspace_files")
            .select("content, updated_at")
            .eq("user_id", user_id)
            .eq("path", _REGIME_PATH)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(f"[ALPHA-TRADER] regime read failed for {user_id[:8]}: {exc}")
        return {"live": False, "fallback_reason": "read_failed"}

    if not result.data:
        return {"live": False, "fallback_reason": "no_substrate"}

    row = result.data[0]
    parsed = _parse_workspace_yaml(row.get("content") or "")
    if not parsed:
        return {"live": False, "fallback_reason": "parse_failed"}

    return {
        "live": True,
        "as_of": parsed.get("last_updated"),
        "trend_regime": parsed.get("trend_regime"),  # 'uptrend' | 'downtrend' | 'chop'
        "vix_regime_active": parsed.get("vix_regime_active"),
        "deactivation_streak_days": parsed.get("deactivation_streak_days"),
        "vixy_close": parsed.get("vixy_close"),
        "vixy_sma_20": parsed.get("vixy_sma_20"),
        "spy_close": parsed.get("spy_close"),
        "spy_sma_20": parsed.get("spy_sma_20"),
        "spy_sma_50": parsed.get("spy_sma_50"),
        "data_stale": parsed.get("data_stale", False),
    }


@router.get("/indicators")
async def get_indicators(
    auth: UserClient,
    ticker: str,
) -> Dict:
    """ADR-273 D3: read /workspace/operation/trading/{TICKER}.yaml.

    Returns the per-ticker indicators (SMA/RSI/ATR/volume) computed by
    the TrackUniverse primitive. Used by TraderPositions to merge live
    Alpaca position rows with accumulated indicator context.

    Empty-state when file absent — FE renders the position row without
    the indicator column (graceful per ADR-273 D6).
    """
    user_id = auth.user_id
    ticker_upper = ticker.upper().strip()
    if not ticker_upper.isalnum():
        raise HTTPException(status_code=400, detail="invalid ticker")
    path = f"{_INDICATORS_PREFIX}{ticker_upper}.yaml"

    try:
        result = (
            auth.client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(f"[ALPHA-TRADER] indicators read failed for {user_id[:8]}/{ticker_upper}: {exc}")
        return {"live": False, "ticker": ticker_upper, "fallback_reason": "read_failed"}

    if not result.data:
        return {"live": False, "ticker": ticker_upper, "fallback_reason": "no_substrate"}

    parsed = _parse_workspace_yaml(result.data[0].get("content") or "")
    if not parsed:
        return {"live": False, "ticker": ticker_upper, "fallback_reason": "parse_failed"}

    return {
        "live": True,
        "ticker": parsed.get("ticker", ticker_upper),
        "as_of": parsed.get("last_updated"),
        "price": parsed.get("price"),
        "sma_20": parsed.get("sma_20"),
        "sma_50": parsed.get("sma_50"),
        "sma_200": parsed.get("sma_200"),
        "rsi_14": parsed.get("rsi_14"),
        "atr_14": parsed.get("atr_14"),
        "volume_20d_avg": parsed.get("volume_20d_avg"),
    }


@router.get("/signals")
async def get_signals(auth: UserClient, limit: int = 10) -> Dict:
    """ADR-273 D3: list /workspace/operation/trading/signals/*.yaml.

    Returns up to `limit` most-recently-updated signal files. Each entry
    carries the parsed signal payload + a best-effort reviewer decision
    correlation from /workspace/persona/judgment_log.md (text-match on the
    signal slug). Closes the gap between "signal evaluator fires" and
    "operator sees what was evaluated and why the reviewer said no."

    Empty-state distinguishes two cases via `evaluator_last_run_at`:
    `null` means the evaluator has never fired; non-null means it ran
    but produced no signals (Reviewer escalated, stood down). FE uses
    this to render an accurate empty-state per ADR-273 D6.

    Correlation is best-effort + denormalized: if decisions.md is empty
    or doesn't mention the slug, the entry renders without
    `reviewer_decision`. Components do not retry or fail on missing
    correlation.
    """
    user_id = auth.user_id

    # Read signal-evaluation's last_run_at from the scheduling index. The
    # tasks row's last_run_at is the empirical fire timestamp — set by
    # record_task_run after every successful dispatch (services/scheduling.py).
    # Used to distinguish "never run" from "ran, found nothing" empty-states.
    evaluator_last_run_at: Optional[str] = None
    try:
        eval_row = (
            auth.client.table("tasks")
            .select("last_run_at")
            .eq("user_id", user_id)
            .eq("slug", "signal-evaluation")
            .limit(1)
            .execute()
        )
        if eval_row.data:
            evaluator_last_run_at = eval_row.data[0].get("last_run_at")
    except Exception:
        evaluator_last_run_at = None

    # List signal files (LIKE prefix match on path).
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content, updated_at")
            .eq("user_id", user_id)
            .like("path", f"{_SIGNALS_PREFIX}%.yaml")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as exc:
        logger.warning(f"[ALPHA-TRADER] signals list failed for {user_id[:8]}: {exc}")
        return {
            "live": False,
            "fallback_reason": "read_failed",
            "signals": [],
            "evaluator_last_run_at": evaluator_last_run_at,
        }

    if not result.data:
        return {
            "live": False,
            "fallback_reason": "no_substrate",
            "signals": [],
            "evaluator_last_run_at": evaluator_last_run_at,
        }

    # Read decisions.md once for correlation. Best-effort: failures are
    # silent (signals just render without reviewer decision).
    decisions_content = ""
    try:
        dec_result = (
            auth.client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", _JUDGMENT_LOG_PATH)
            .limit(1)
            .execute()
        )
        if dec_result.data:
            decisions_content = dec_result.data[0].get("content") or ""
    except Exception:
        decisions_content = ""

    signals: List[Dict[str, Any]] = []
    for row in result.data:
        path = row.get("path") or ""
        slug = path.removeprefix(_SIGNALS_PREFIX).removesuffix(".yaml")
        parsed = _parse_workspace_yaml(row.get("content") or "")
        reviewer_decision = _extract_reviewer_decision(decisions_content, slug)

        signals.append({
            "slug": slug,
            "path": path,
            "updated_at": row.get("updated_at"),
            "ticker": parsed.get("ticker"),
            "direction": parsed.get("direction"),
            "expectancy": parsed.get("expectancy"),
            "status": parsed.get("status"),
            "rationale": parsed.get("rationale"),
            "reviewer_decision": reviewer_decision,
        })

    return {
        "live": True,
        "signals": signals,
        "evaluator_last_run_at": evaluator_last_run_at,
    }


def _extract_reviewer_decision(decisions_md: str, signal_slug: str) -> Optional[Dict[str, Any]]:
    """Best-effort correlation: find a decision mentioning the signal slug.

    decisions.md is append-only narrative. We scan for the most-recent
    block mentioning the slug as a substring and extract `verdict` +
    `reasoning excerpt` if present. Returns None when no match.

    This is intentionally loose — exact schema coupling between
    decisions.md and signals/*.yaml is not enforced. The reviewer writes
    prose; we surface the trail when it correlates.
    """
    if not decisions_md or not signal_slug:
        return None
    # Decisions blocks are typically separated by `---` or `## ` headings.
    # Find any block containing the slug and capture surrounding context.
    needle = signal_slug.lower()
    haystack = decisions_md.lower()
    idx = haystack.rfind(needle)  # most recent mention
    if idx < 0:
        return None

    # Capture ~400-char window around the mention, snap to line boundaries.
    start = max(0, decisions_md.rfind("\n", 0, idx) + 1)
    end = min(len(decisions_md), idx + 400)
    end_nl = decisions_md.find("\n\n", idx, end)
    if end_nl > 0:
        end = end_nl
    excerpt = decisions_md[start:end].strip()

    # Best-effort verdict extraction — look for approve/reject/defer tokens.
    excerpt_lower = excerpt.lower()
    verdict: Optional[str] = None
    if "approve" in excerpt_lower:
        verdict = "approved"
    elif "reject" in excerpt_lower:
        verdict = "rejected"
    elif "defer" in excerpt_lower or "stand-down" in excerpt_lower or "stand down" in excerpt_lower:
        verdict = "deferred"

    return {
        "verdict": verdict,
        "excerpt": excerpt[:300],
    }

# Budget (ADR-327; supersedes the retired pace dial) is the kernel route
# api/routes/budget.py (`GET /api/budget`) — a kernel governance dial (the
# operation's dollar spend envelope), not trader-program data.
