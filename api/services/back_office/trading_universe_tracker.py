"""Back Office: Trading Universe Tracker — ADR-253 D4 + ADR-254.

Deterministic replacement for the LLM-backed `track-universe` recurrence.
Fetches OHLCV bars from Alpaca for each universe ticker, computes indicators
(SMA-20/50/200, RSI-14, ATR-14, volume-20d-avg), writes one {ticker}.yaml
per ticker under /workspace/context/trading/.

ADR-254: output files are .yaml (machine-parsed by signal evaluator).
Universe reads from _universe.yaml via yaml.safe_load — no regex prose parsing.

Zero LLM cost. Runs in ~2-5 seconds per batch. Saves ~$1.50/run vs Sonnet.

Output: /workspace/context/trading/{ticker}.yaml
  ticker: NVDA
  last_updated: "2026-05-07T08:01:23Z"
  price: 851.20
  sma_20: 842.10
  sma_50: 820.55
  sma_200: 750.30
  rsi_14: 48.2
  atr_14: 12.45
  volume_20d_avg: 45230000
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import yaml as _yaml

logger = logging.getLogger(__name__)


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Track universe indicators for all declared tickers."""
    started_at = datetime.now(timezone.utc)
    actions_taken: list[dict] = []
    errors: list[str] = []

    try:
        # 1. Load credentials
        api_key, api_secret, paper = await _load_trading_credentials(client, user_id)
        if not api_key:
            return _shape_result(started_at, [], ["No active trading integration — skipping"], 0, 0)

        # 2. Read universe from _universe.yaml (ADR-254 — yaml.safe_load, no regex)
        tickers = await _read_universe(client, user_id)
        if not tickers:
            return _shape_result(started_at, [], ["No tickers in _universe.yaml"], 0, 0)

        logger.info("[UNIVERSE_TRACKER] user=%s tickers=%d paper=%s", user_id[:8], len(tickers), paper)

        # 3. Fetch bars + compute indicators
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
                    limit=210,
                )
                if not bars or len(bars) < 20:
                    errors.append(f"{ticker}: insufficient data ({len(bars) if bars else 0} bars)")
                    continue

                indicators = _compute_indicators(bars)
                await _write_ticker_yaml(client, user_id, ticker, indicators, started_at)
                actions_taken.append({"ticker": ticker, "action": "write_ticker_yaml"})
                succeeded += 1

            except Exception as e:
                logger.warning("[UNIVERSE_TRACKER] %s failed: %s", ticker, e)
                errors.append(f"{ticker}: {e}")

        return _shape_result(started_at, actions_taken, errors, succeeded, len(tickers))

    except Exception as exc:
        logger.error("[UNIVERSE_TRACKER] top-level failure user=%s: %s", user_id[:8], exc)
        return _shape_result(started_at, [], [str(exc)], 0, 0)


# ---------------------------------------------------------------------------
# Universe reader — yaml.safe_load from _universe.yaml (ADR-254)
# ---------------------------------------------------------------------------

async def _read_universe(client: Any, user_id: str) -> list[str]:
    """Read ticker list from _universe.yaml. Zero regex."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", "/workspace/context/trading/_universe.yaml")
            .limit(1)
            .execute()
        )
        if not result.data:
            logger.info("[UNIVERSE_TRACKER] _universe.yaml not found for user=%s", user_id[:8])
            return []
        content = result.data[0].get("content") or ""
        from services.review_policy import load_workspace_yaml
        parsed = load_workspace_yaml(content)
        tickers = parsed.get("tickers") or []
        return [str(t).upper().strip() for t in tickers if str(t).strip()][:20]
    except Exception as exc:
        logger.warning("[UNIVERSE_TRACKER] _read_universe failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Indicator computation — pure Python, zero LLM
# ---------------------------------------------------------------------------

def _compute_indicators(bars: list[dict]) -> dict:
    """Compute SMA/RSI/ATR/volume from daily bars (newest-first from Alpaca)."""
    closes = [b["close"] for b in reversed(bars)]
    highs  = [b["high"]  for b in reversed(bars)]
    lows   = [b["low"]   for b in reversed(bars)]
    vols   = [b["volume"] for b in reversed(bars)]
    n = len(closes)

    def sma(p: int) -> float | None:
        return round(sum(closes[-p:]) / p, 4) if n >= p else None

    def rsi(p: int = 14) -> float | None:
        if n < p + 1:
            return None
        deltas = [closes[i] - closes[i-1] for i in range(1, n)]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        ag = sum(gains[-p:]) / p
        al = sum(losses[-p:]) / p
        return round(100 - 100 / (1 + ag / al), 2) if al > 0 else 100.0

    def atr(p: int = 14) -> float | None:
        if n < p + 1:
            return None
        trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
               for i in range(1, n)]
        return round(sum(trs[-p:]) / p, 4)

    def vol_avg(p: int = 20) -> float | None:
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
# YAML file writer (ADR-254 — .yaml not .md)
# ---------------------------------------------------------------------------

async def _write_ticker_yaml(
    client: Any, user_id: str, ticker: str, indicators: dict, now: datetime,
) -> None:
    """Write {ticker}.yaml to /workspace/context/trading/."""
    from services.authored_substrate import write_revision

    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {"ticker": ticker.upper(), "last_updated": ts, **indicators}
    content = f"# {ticker.upper()} indicators — written by trading_universe_tracker (ADR-254)\n"
    content += _yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    path = f"/workspace/context/trading/{ticker.upper()}.yaml"
    write_revision(
        client, user_id=user_id, path=path, content=content,
        authored_by="system:trading_universe_tracker",
        message=f"indicators {ts}",
        summary=f"Updated {ticker} indicators",
    )


# ---------------------------------------------------------------------------
# Credential loading + result shape
# ---------------------------------------------------------------------------

async def _load_trading_credentials(client: Any, user_id: str) -> tuple[str, str, bool]:
    try:
        from integrations.core.tokens import get_token_manager
        result = (
            client.table("platform_connections")
            .select("credentials_encrypted, metadata")
            .eq("user_id", user_id).eq("platform", "trading").eq("status", "active")
            .limit(1).execute()
        )
        if not result.data:
            return "", "", True
        row = result.data[0]
        creds = get_token_manager().decrypt(row["credentials_encrypted"])
        paper = (row.get("metadata") or {}).get("paper", True)
        if ":" not in creds:
            return "", "", True
        api_key, api_secret = creds.split(":", 1)
        return api_key, api_secret, paper
    except Exception as exc:
        logger.warning("[UNIVERSE_TRACKER] credential load failed: %s", exc)
        return "", "", True


def _shape_result(started_at: datetime, actions: list, errors: list, succeeded: int, total: int) -> dict:
    duration_s = (datetime.now(timezone.utc) - started_at).total_seconds()
    lines = [
        "# Universe Tracker", "",
        f"**Ran**: {started_at.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"**Duration**: {duration_s:.1f}s",
        f"**Tickers updated**: {succeeded}/{total}",
        f"**Errors**: {len(errors)}",
    ]
    if errors:
        lines += ["", "## Errors"] + [f"- {e}" for e in errors]
    summary = (
        f"Universe tracker: {succeeded}/{total} tickers updated"
        if total else f"Universe tracker: skipped ({', '.join(errors[:1])})"
    )
    return {"output_markdown": "\n".join(lines) + "\n", "summary": summary[:200], "actions_taken": actions}
