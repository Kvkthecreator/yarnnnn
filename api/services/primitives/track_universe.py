"""TrackUniverse Primitive — ADR-271 Thread A.

Deterministic mechanical primitive that fetches OHLCV bars from Alpaca for
each declared universe ticker, computes indicators (SMA-20/50/200, RSI-14,
ATR-14, volume-20d-avg), and writes one ``{TICKER}.yaml`` file per ticker
under ``/workspace/operation/trading/``.

Zero LLM cost. Runs in ~2-5 seconds. Replaces the judgment-mode
``track-universe`` recurrence prompt that previously dispatched a Sonnet
specialist to do the same indicator math.

Surface:
    @primitive: TrackUniverse()

No arguments — universe membership is read from
``/workspace/operation/trading/_universe.yaml`` (operator-authored ticker list).
The recurrence's bundle prompt is exactly this one-line directive.

Behavior:
    1. Load active trading credentials (platform_connections.platform='trading').
    2. Read ticker list from ``_universe.yaml`` (yaml.safe_load; zero regex).
    3. For each ticker: fetch 1Day bars, compute indicators, write {TICKER}.yaml.
    4. Return ``{success, items_processed, paths_written, errors}``.

Dispatch surface:
    - Capture lane only (ADR-393; per ADR-264 D3 — operators don't directly
      invoke mechanical primitives from chat). Not in CHAT_PRIMITIVES, not in
      HEADLESS_PRIMITIVES, not in FREDDIE_PRIMITIVES. Registered in HANDLERS so
      the capture lane (``services.capture.lane``) can route a `_captures.yaml`
      `@primitive: TrackUniverse()` declaration to it.

Attribution:
    All writes go through ``write_revision(authored_by="system:track-universe")``
    per ADR-209 Authored Substrate.

This primitive does ONE job: mirror universe indicator state into substrate.
It does not evaluate signals, propose trades, or invoke the Reviewer.
``mode=mechanical`` on the recurrence (per ADR-263) is what keeps the
Reviewer asleep on these writes.

Recovers code originally landed by ADR-253 Commit 2 (commit 551c7b6) +
ADR-254 Commit 4 (commit 9dea639) that was swept by ADR-261 Phase B
(commit 42f984c). ADR-263 §"Why this rewrite" named ``track-universe`` as
the canonical mechanical-vs-judgment mismatch case; this primitive restores
the deterministic path.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import yaml as _yaml

logger = logging.getLogger(__name__)


_MAX_UNIVERSE_TICKERS = 20  # operator-bound; bundle ICP caps at 5-10
_BARS_LIMIT = 210  # enough for SMA-200 + warmup


async def handle_track_universe(auth: Any, input: dict) -> dict:
    """Fetch bars + compute indicators for every ticker in _universe.yaml.

    Arguments are ignored — universe membership lives in
    ``/workspace/operation/trading/_universe.yaml``. The bundle prompt should
    be exactly ``@primitive: TrackUniverse()``.

    Returns standard mechanical-primitive shape:
        {
            "success": bool,
            "items_processed": int,   # tickers updated
            "paths_written": list[str],
            "errors": list[str],
        }
    """
    user_id = getattr(auth, "user_id", None)
    client = getattr(auth, "client", None)
    if not user_id or not client:
        return {"success": False, "error": "auth_required", "items_processed": 0,
                "paths_written": [], "errors": ["missing auth.user_id or auth.client"]}

    started_at = datetime.now(timezone.utc)
    paths_written: list[str] = []
    errors: list[str] = []

    api_key, api_secret, paper = await _load_trading_credentials(client, user_id)
    if not api_key:
        return {"success": False, "error": "capability_missing",
                "items_processed": 0, "paths_written": [],
                "errors": ["no active trading platform_connection"]}

    tickers = await _read_universe(client, user_id)
    if not tickers:
        return {"success": False, "error": "no_universe",
                "items_processed": 0, "paths_written": [],
                "errors": ["_universe.yaml missing or empty"]}

    logger.info(
        "[TRACK_UNIVERSE] user=%s tickers=%d paper=%s",
        user_id[:8], len(tickers), paper,
    )

    from integrations.core.alpaca_client import get_trading_client
    alpaca = get_trading_client()

    succeeded = 0
    for ticker in tickers:
        try:
            bars = await alpaca.get_bars(
                api_key=api_key,
                api_secret=api_secret,
                symbol=ticker,
                timeframe="1Day",
                limit=_BARS_LIMIT,
            )
            if not bars or len(bars) < 20:
                errors.append(f"{ticker}: insufficient bars ({len(bars) if bars else 0})")
                continue

            indicators = _compute_indicators(bars)
            path = await _write_ticker_yaml(
                client, user_id, ticker, indicators, started_at,
            )
            paths_written.append(path)
            succeeded += 1
        except Exception as exc:
            logger.warning("[TRACK_UNIVERSE] %s failed: %s", ticker, exc)
            errors.append(f"{ticker}: {exc}")

    success = succeeded > 0
    return {
        "success": success,
        "items_processed": succeeded,
        "paths_written": paths_written,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Universe reader — yaml.safe_load from _universe.yaml (ADR-254)
# ---------------------------------------------------------------------------

async def _read_universe(client: Any, user_id: str) -> list[str]:
    """Read ticker list from /workspace/operation/trading/_universe.yaml.

    Uses the canonical `load_workspace_yaml` helper (services.review_policy)
    which strips the bundle-forked frontmatter block (`tier:`, `prompt:`)
    before parsing. Without this, yaml.safe_load on the full content
    returns only the frontmatter dict and `tickers` is silently absent.
    """
    from services.review_policy import load_workspace_yaml
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", "/workspace/operation/trading/_universe.yaml")
            .limit(1)
            .execute()
        )
        if not result.data:
            logger.info(
                "[TRACK_UNIVERSE] _universe.yaml not found for user=%s",
                user_id[:8],
            )
            return []
        content = result.data[0].get("content") or ""
        parsed = load_workspace_yaml(content)
        tickers = parsed.get("tickers") or []
        return [
            str(t).upper().strip()
            for t in tickers
            if isinstance(t, str) and str(t).strip()
        ][:_MAX_UNIVERSE_TICKERS]
    except Exception as exc:
        logger.warning("[TRACK_UNIVERSE] _read_universe failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Indicator computation — pure Python, zero LLM
# ---------------------------------------------------------------------------

def _compute_indicators(bars: list[dict]) -> dict:
    """Compute SMA/RSI/ATR/volume from daily bars.

    Alpaca returns bars newest-first when ``sort=desc`` is set (see
    alpaca_client.get_bars). We reverse to oldest-first for indicator math.
    """
    closes = [b["close"]  for b in reversed(bars)]
    highs  = [b["high"]   for b in reversed(bars)]
    lows   = [b["low"]    for b in reversed(bars)]
    vols   = [b["volume"] for b in reversed(bars)]
    n = len(closes)

    def sma(p: int):
        return round(sum(closes[-p:]) / p, 4) if n >= p else None

    def rsi(p: int = 14):
        if n < p + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        ag = sum(gains[-p:]) / p
        al = sum(losses[-p:]) / p
        if al == 0:
            return 100.0
        return round(100 - 100 / (1 + ag / al), 2)

    def atr(p: int = 14):
        if n < p + 1:
            return None
        trs = [
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            for i in range(1, n)
        ]
        return round(sum(trs[-p:]) / p, 4)

    def vol_avg(p: int = 20):
        return round(sum(vols[-p:]) / p, 0) if n >= p else None

    return {
        "price":          round(closes[-1], 4),
        "sma_20":         sma(20),
        "sma_50":         sma(50),
        "sma_200":        sma(200),
        "rsi_14":         rsi(14),
        "atr_14":         atr(14),
        "volume_20d_avg": vol_avg(20),
    }


# ---------------------------------------------------------------------------
# YAML writer — ADR-209 attributed revision
# ---------------------------------------------------------------------------

async def _write_ticker_yaml(
    client: Any,
    user_id: str,
    ticker: str,
    indicators: dict,
    now: datetime,
) -> str:
    """Write /workspace/operation/trading/{TICKER}.yaml. Returns the path."""
    from services.authored_substrate import write_revision

    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {"ticker": ticker.upper(), "last_updated": ts, **indicators}
    header = (
        f"# {ticker.upper()} indicators — written by TrackUniverse primitive "
        f"(ADR-271 Thread A)\n"
    )
    body = _yaml.dump(
        data, default_flow_style=False, allow_unicode=True, sort_keys=False,
    )
    content = header + body

    path = f"/workspace/operation/trading/{ticker.upper()}.yaml"
    write_revision(
        client,
        user_id=user_id,
        path=path,
        content=content,
        authored_by="system:track-universe",
        message=f"indicators {ts}",
        summary=f"Updated {ticker} indicators",
    )
    return path


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

async def _load_trading_credentials(
    client: Any, user_id: str,
) -> tuple[str, str, bool]:
    """Load Alpaca API key/secret + paper flag from platform_connections."""
    try:
        from integrations.core.tokens import get_token_manager
        result = (
            client.table("platform_connections")
            .select("credentials_encrypted, metadata")
            .eq("user_id", user_id)
            .eq("platform", "trading")
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not result.data:
            return "", "", True
        row = result.data[0]
        creds = get_token_manager().decrypt(row["credentials_encrypted"])
        paper = bool((row.get("metadata") or {}).get("paper", True))
        if ":" not in creds:
            return "", "", True
        api_key, api_secret = creds.split(":", 1)
        return api_key, api_secret, paper
    except Exception as exc:
        logger.warning("[TRACK_UNIVERSE] credential load failed: %s", exc)
        return "", "", True


__all__ = ["handle_track_universe"]
