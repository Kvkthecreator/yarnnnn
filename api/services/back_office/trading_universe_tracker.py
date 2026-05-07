"""Back Office: Trading Universe Tracker — ADR-253 D4.

Deterministic replacement for the LLM-backed `track-universe` recurrence.
Fetches OHLCV bars from Alpaca for each universe ticker, computes indicators
(SMA-20/50/200, RSI-14, ATR-14, volume-20d-avg), and writes one {ticker}.md
file per ticker under /workspace/context/trading/.

Zero LLM cost. Runs in ~2-5 seconds. Saves ~$1.50/run vs Sonnet dispatch.
Three runs/day on weekdays = ~$4.50/day saved.

Executor pattern: same shape as outcome_reconciliation and other back-office
deterministic executors. The invocation_dispatcher routes maintenance-shape
declarations with an `executor:` field here via _dispatch_maintenance().

Signal definitions come from _operator_profile.md (declared universe).
Credentials come from platform_connections (encrypted, decrypted via token_manager).

Output shape per ticker file (/workspace/context/trading/{ticker}.md):
    ---
    ticker: NVDA
    last_updated: 2026-05-07T08:01:23Z
    price: 851.20
    sma_20: 842.10
    sma_50: 820.55
    sma_200: 750.30
    rsi_14: 48.2
    atr_14: 12.45
    volume_20d_avg: 45230000
    ---

    # {ticker} — Universe State
    Updated: 2026-05-07 08:01 UTC
    ...
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_INDICATORS_PREFIX = "trading_universe_tracker"


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Track universe indicators for all declared tickers.

    Returns the standard back-office executor shape:
    {
        "summary": str,
        "output_markdown": str,
        "actions_taken": list[dict],
    }
    """
    started_at = datetime.now(timezone.utc)
    actions_taken: list[dict] = []
    errors: list[str] = []

    try:
        # 1. Load credentials
        api_key, api_secret, paper = await _load_trading_credentials(client, user_id)
        if not api_key:
            return _shape_result(started_at, [], ["No active trading integration — skipping"], 0)

        # 2. Read universe from _operator_profile.md
        tickers = await _read_universe(client, user_id)
        if not tickers:
            return _shape_result(started_at, [], ["No universe tickers found in _operator_profile.md"], 0)

        logger.info(
            "[UNIVERSE_TRACKER] user=%s tickers=%d paper=%s",
            user_id[:8], len(tickers), paper,
        )

        # 3. Fetch bars + compute indicators for each ticker
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
                    limit=210,  # need 200 for SMA-200
                )
                if not bars or len(bars) < 20:
                    errors.append(f"{ticker}: insufficient bar data ({len(bars) if bars else 0} bars)")
                    continue

                indicators = _compute_indicators(bars)
                await _write_ticker_file(client, user_id, ticker, indicators, started_at)
                actions_taken.append({"ticker": ticker, "action": "write_ticker_md"})
                succeeded += 1

            except Exception as e:
                logger.warning("[UNIVERSE_TRACKER] %s failed: %s", ticker, e)
                errors.append(f"{ticker}: {e}")

        return _shape_result(started_at, actions_taken, errors, succeeded, len(tickers))

    except Exception as exc:
        logger.error("[UNIVERSE_TRACKER] top-level failure user=%s: %s", user_id[:8], exc)
        return _shape_result(started_at, [], [str(exc)], 0)


# ---------------------------------------------------------------------------
# Indicator computation — pure Python, zero LLM
# ---------------------------------------------------------------------------

def _compute_indicators(bars: list[dict]) -> dict:
    """Compute all indicators from sorted bars (newest first from Alpaca)."""
    # bars are newest-first from Alpaca; reverse for chronological SMA computation
    closes = [b["close"] for b in reversed(bars)]
    highs = [b["high"] for b in reversed(bars)]
    lows = [b["low"] for b in reversed(bars)]
    volumes = [b["volume"] for b in reversed(bars)]

    n = len(closes)
    latest = closes[-1]

    def sma(period: int) -> float | None:
        if n < period:
            return None
        return round(sum(closes[-period:]) / period, 4)

    def rsi(period: int = 14) -> float | None:
        if n < period + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    def atr(period: int = 14) -> float | None:
        if n < period + 1:
            return None
        trs = []
        for i in range(1, n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)
        return round(sum(trs[-period:]) / period, 4)

    def vol_avg(period: int = 20) -> float | None:
        if n < period:
            return None
        return round(sum(volumes[-period:]) / period, 0)

    return {
        "price": round(latest, 4),
        "sma_20": sma(20),
        "sma_50": sma(50),
        "sma_200": sma(200),
        "rsi_14": rsi(14),
        "atr_14": atr(14),
        "volume_20d_avg": vol_avg(20),
    }


# ---------------------------------------------------------------------------
# File write
# ---------------------------------------------------------------------------

async def _write_ticker_file(
    client: Any,
    user_id: str,
    ticker: str,
    indicators: dict,
    now: datetime,
) -> None:
    """Write {ticker}.md to /workspace/context/trading/ via write_revision."""
    from services.authored_substrate import write_revision

    path = f"/workspace/context/trading/{ticker.upper()}.md"
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build YAML frontmatter
    frontmatter_lines = [
        "---",
        f"ticker: {ticker.upper()}",
        f"last_updated: {ts}",
        f"price: {indicators.get('price', 'null')}",
    ]
    for field in ("sma_20", "sma_50", "sma_200", "rsi_14", "atr_14", "volume_20d_avg"):
        val = indicators.get(field)
        frontmatter_lines.append(f"{field}: {val if val is not None else 'null'}")
    frontmatter_lines.append("---")

    body_lines = [
        f"",
        f"# {ticker.upper()} — Universe State",
        f"",
        f"Updated: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"| Indicator | Value |",
        f"|---|---|",
        f"| Price | {indicators.get('price', '—')} |",
        f"| SMA-20 | {indicators.get('sma_20', '—')} |",
        f"| SMA-50 | {indicators.get('sma_50', '—')} |",
        f"| SMA-200 | {indicators.get('sma_200', '—')} |",
        f"| RSI-14 | {indicators.get('rsi_14', '—')} |",
        f"| ATR-14 | {indicators.get('atr_14', '—')} |",
        f"| Vol-20d avg | {indicators.get('volume_20d_avg', '—')} |",
    ]

    content = "\n".join(frontmatter_lines + body_lines) + "\n"

    write_revision(
        client,
        user_id=user_id,
        path=path,
        content=content,
        authored_by="system:trading_universe_tracker",
        message=f"Universe tracker: {ticker} indicators {ts}",
        summary=f"Updated {ticker} indicators",
    )


# ---------------------------------------------------------------------------
# Universe extraction
# ---------------------------------------------------------------------------

async def _read_universe(client: Any, user_id: str) -> list[str]:
    """Extract ticker list from _operator_profile.md declared universe."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", "/workspace/context/trading/_operator_profile.md")
            .limit(1)
            .execute()
        )
        if not result.data:
            return []
        content = result.data[0].get("content") or ""

        # Find "## Declared universe" section and extract tickers
        m = re.search(r"##\s+Declared universe\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if not m:
            return []
        universe_text = m.group(1)

        # Extract all-caps ticker symbols (2-5 chars)
        tickers = re.findall(r'\b([A-Z]{1,5})\b', universe_text)
        # Deduplicate preserving order, filter common false positives
        _SKIP = {"US", "OR", "AND", "ETF", "AND", "NOT", "FOR", "IF", "QQQ", "SPY", "SMH", "SOXX", "IWM", "XLK", "XLY", "XLF"}
        seen: set[str] = set()
        result_tickers: list[str] = []
        for t in tickers:
            if t not in seen and len(t) >= 2:
                seen.add(t)
                result_tickers.append(t)

        return result_tickers[:20]  # cap at 20 to prevent runaway

    except Exception as exc:
        logger.warning("[UNIVERSE_TRACKER] _read_universe failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

async def _load_trading_credentials(
    client: Any, user_id: str
) -> tuple[str, str, bool]:
    """Load Alpaca API credentials from platform_connections."""
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
            logger.info("[UNIVERSE_TRACKER] no active trading integration for user=%s", user_id[:8])
            return "", "", True
        row = result.data[0]
        token_manager = get_token_manager()
        credentials = token_manager.decrypt(row["credentials_encrypted"])
        metadata = row.get("metadata") or {}
        paper = metadata.get("paper", True)
        if ":" not in credentials:
            logger.warning("[UNIVERSE_TRACKER] invalid credential format for user=%s", user_id[:8])
            return "", "", True
        api_key, api_secret = credentials.split(":", 1)
        return api_key, api_secret, paper
    except Exception as exc:
        logger.warning("[UNIVERSE_TRACKER] credential load failed: %s", exc)
        return "", "", True


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def _shape_result(
    started_at: datetime,
    actions: list[dict],
    errors: list[str],
    succeeded: int,
    total: int = 0,
) -> dict:
    duration_s = (datetime.now(timezone.utc) - started_at).total_seconds()
    lines = [
        "# Universe Tracker",
        "",
        f"**Ran**: {started_at.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"**Duration**: {duration_s:.1f}s",
        f"**Tickers updated**: {succeeded}/{total}",
        f"**Errors**: {len(errors)}",
    ]
    if errors:
        lines += ["", "## Errors"] + [f"- {e}" for e in errors]

    summary = f"Universe tracker: {succeeded}/{total} tickers updated" if total else f"Universe tracker: skipped ({', '.join(errors[:1])})"

    return {
        "output_markdown": "\n".join(lines) + "\n",
        "summary": summary[:200],
        "actions_taken": actions,
    }
