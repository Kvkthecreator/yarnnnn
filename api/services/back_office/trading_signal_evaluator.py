"""Back Office: Trading Signal Evaluator — ADR-253 D4 + ADR-254.

Deterministic replacement for the LLM-backed `signal-evaluation` recurrence.
Reads {ticker}.yaml indicator files (ADR-254 format), evaluates each declared
signal's boolean trigger rules, writes signals/{slug}.yaml state files.

ADR-254: all file I/O uses yaml.safe_load / yaml.dump. No regex, no frontmatter parsing.

Signal evaluation scope (ADR-253 D4 + ADR-254 D5):
- Daily-bar signals (SMA/RSI crossovers): evaluated here deterministically
- Intraday signals (VWAP, ORB, hourly RSI): marked evaluable=false with note;
  evaluated by trade-proposal recurrence at session open with live 1H bars

When a daily-bar signal fires:
  1. Writes signals/{slug}.yaml with triggered_today list
  2. Fires trade-proposal invocation
  3. Writes _signal_trigger.flag (Reviewer heartbeat trigger)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import yaml as _yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal evaluators — daily-bar signals only
# ---------------------------------------------------------------------------

def _eval_momentum_breakout(ind: dict, ticker: str) -> bool:
    """Signal 1 / IH-1 style: price > SMA-20 > SMA-50, RSI 55-75."""
    p, s20, s50, rsi = ind.get("price"), ind.get("sma_20"), ind.get("sma_50"), ind.get("rsi_14")
    if any(v is None for v in [p, s20, s50, rsi]):
        return False
    return p > s20 > s50 and 55 <= rsi <= 75


def _eval_mean_reversion(ind: dict, ticker: str) -> bool:
    """Signal 2 / daily mean-reversion: RSI < 25, price within 5% of SMA-200, SMA-20 > SMA-50."""
    p, s20, s50, s200, rsi = ind.get("price"), ind.get("sma_20"), ind.get("sma_50"), ind.get("sma_200"), ind.get("rsi_14")
    if any(v is None for v in [p, s20, s50, s200, rsi]):
        return False
    return rsi < 25 and abs(p - s200) / s200 <= 0.05 and s20 > s50


def _eval_sector_etf(ind: dict, ticker: str) -> bool:
    """Signal 4 style: ETF momentum (price > SMA-20 > SMA-50, RSI >= 55)."""
    etfs = {"SMH", "SOXX", "QQQ", "SPY", "XLK", "XLY", "IWM", "XLF"}
    if ticker.upper() not in etfs:
        return False
    p, s20, s50, rsi = ind.get("price"), ind.get("sma_20"), ind.get("sma_50"), ind.get("rsi_14")
    if any(v is None for v in [p, s20, s50, rsi]):
        return False
    return p > s20 > s50 and rsi >= 55


# Map signal slug patterns to evaluators.
# Intraday signals explicitly not evaluable from daily bars.
_DAILY_BAR_EVALUATORS = {
    "ih-1-momentum-breakout": _eval_momentum_breakout,
    "ih-1-vwap-reversion-long": None,       # intraday — VWAP requires 1H bars
    "ih-2-mean-reversion-oversold": _eval_mean_reversion,
    "ih-2-or-breakout-long": None,           # intraday — ORB requires first-hour bar
    "ih-3-mean-reversion-bounce": _eval_mean_reversion,
    "ih-4-range-top-fade-short": None,       # intraday
    "ih-4-pead": None,                       # requires earnings data
    "ih-5-vix-regime-filter": None,          # not a trade signal, portfolio scalar
}

_INTRADAY_NOTE = (
    "Intraday signal — requires live 1H bar data at session open. "
    "Evaluated by trade-proposal recurrence (LLM-backed, has live Alpaca tools). "
    "Not evaluable from daily bars."
)


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Evaluate signals across universe. Returns back-office executor shape."""
    started_at = datetime.now(timezone.utc)
    actions_taken: list[dict] = []
    errors: list[str] = []
    any_triggered = False

    try:
        # 1. Load ticker indicator files (.yaml, ADR-254)
        ticker_indicators = await _load_ticker_indicators(client, user_id)
        if not ticker_indicators:
            return _shape_result(started_at, [], ["No ticker .yaml files — run track-universe first"], False)

        # 2. Discover signal slugs from existing signal state files or known list
        signal_slugs = await _discover_signal_slugs(client, user_id)
        if not signal_slugs:
            signal_slugs = list(_DAILY_BAR_EVALUATORS.keys())

        logger.info("[SIGNAL_EVAL] user=%s tickers=%d signals=%d", user_id[:8], len(ticker_indicators), len(signal_slugs))

        # 3. Evaluate each signal
        for slug in signal_slugs:
            try:
                evaluator = _DAILY_BAR_EVALUATORS.get(slug)

                if evaluator is None:
                    # Intraday or unevaluable — write state with evaluable:false
                    await _write_signal_yaml(
                        client, user_id, slug,
                        triggered_tickers=[], watch_tickers=[],
                        evaluable=False, evaluation_note=_INTRADAY_NOTE,
                        started_at=started_at,
                    )
                    actions_taken.append({"signal": slug, "triggered": [], "evaluable": False})
                    continue

                triggered, watch = [], []
                for ticker, ind in ticker_indicators.items():
                    try:
                        if evaluator(ind, ticker):
                            triggered.append(ticker)
                        rsi = ind.get("rsi_14")
                        if rsi and rsi < 35 and "mean-reversion" in slug:
                            watch.append(ticker)
                    except Exception as e:
                        errors.append(f"{slug}/{ticker}: {e}")

                await _write_signal_yaml(
                    client, user_id, slug,
                    triggered_tickers=triggered, watch_tickers=watch,
                    evaluable=True, evaluation_note=None,
                    started_at=started_at,
                )
                actions_taken.append({"signal": slug, "triggered": triggered, "watch": watch, "evaluable": True})

                if triggered:
                    any_triggered = True
                    logger.info("[SIGNAL_EVAL] FIRED %s on %s user=%s", slug, triggered, user_id[:8])

            except Exception as e:
                logger.warning("[SIGNAL_EVAL] %s failed: %s", slug, e)
                errors.append(f"{slug}: {e}")

        # 4. If any daily-bar signal fired: write trigger flag + fire trade-proposal
        if any_triggered:
            await _write_trigger_flag(client, user_id, actions_taken, started_at)
            await _fire_trade_proposal(client, user_id)
            actions_taken.append({"action": "trigger_flag_written"})
            actions_taken.append({"action": "trade_proposal_fired"})

        return _shape_result(started_at, actions_taken, errors, any_triggered)

    except Exception as exc:
        logger.error("[SIGNAL_EVAL] top-level failure user=%s: %s", user_id[:8], exc)
        return _shape_result(started_at, [], [str(exc)], False)


# ---------------------------------------------------------------------------
# Ticker indicator loader — yaml.safe_load (ADR-254)
# ---------------------------------------------------------------------------

async def _load_ticker_indicators(client: Any, user_id: str) -> dict[str, dict]:
    """Load all {ticker}.yaml files from /workspace/context/trading/."""
    try:
        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/trading/%.yaml")
            .not_.like("path", "/workspace/context/trading/signals/%")
            .not_.like("path", "/workspace/context/trading/_%")
            .execute()
        )
        indicators: dict[str, dict] = {}
        for row in result.data or []:
            path = row.get("path", "")
            ticker = path.split("/")[-1].replace(".yaml", "").upper()
            if not ticker or ticker.startswith("_"):
                continue
            try:
                parsed = _yaml.safe_load(row.get("content") or "") or {}
                if isinstance(parsed, dict) and parsed.get("price"):
                    indicators[ticker] = parsed
            except _yaml.YAMLError:
                pass
        return indicators
    except Exception as exc:
        logger.warning("[SIGNAL_EVAL] _load_ticker_indicators failed: %s", exc)
        return {}


async def _discover_signal_slugs(client: Any, user_id: str) -> list[str]:
    """Discover signal slugs from existing signals/*.yaml files."""
    try:
        result = (
            client.table("workspace_files")
            .select("path")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/trading/signals/%.yaml")
            .execute()
        )
        slugs = []
        for row in result.data or []:
            slug = row["path"].split("/")[-1].replace(".yaml", "")
            if slug:
                slugs.append(slug)
        return slugs
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Signal state file writer — .yaml (ADR-254)
# ---------------------------------------------------------------------------

async def _write_signal_yaml(
    client: Any, user_id: str, signal_slug: str,
    triggered_tickers: list, watch_tickers: list,
    evaluable: bool, evaluation_note: str | None,
    started_at: datetime,
) -> None:
    from services.authored_substrate import write_revision

    ts = started_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {
        "signal_slug":     signal_slug,
        "evaluated_at":    ts,
        "evaluable":       evaluable,
        "state":           "active",
        "watch_tickers":   watch_tickers,
        "triggered_today": triggered_tickers,
        "trigger_count":   len(triggered_tickers),
        "expectancy_r_20": None,
        "expectancy_r_40": None,
    }
    if evaluation_note:
        data["evaluation_note"] = evaluation_note

    content = f"# {signal_slug} signal state — ADR-254\n"
    content += _yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    path = f"/workspace/context/trading/signals/{signal_slug}.yaml"

    write_revision(
        client, user_id=user_id, path=path, content=content,
        authored_by="system:trading_signal_evaluator",
        message=f"signal evaluation {ts} triggered={triggered_tickers}",
        summary=f"Signal {signal_slug}: {'FIRED ' + str(triggered_tickers) if triggered_tickers else 'no trigger'}",
    )


async def _write_trigger_flag(client: Any, user_id: str, actions: list, now: datetime) -> None:
    from services.authored_substrate import write_revision
    fired = [a["signal"] for a in actions if a.get("triggered") and a.get("evaluable")]
    content = _yaml.dump({"signal_fires": fired, "evaluated_at": now.isoformat()})
    write_revision(
        client, user_id=user_id,
        path="/workspace/context/trading/_signal_trigger.flag",
        content=content,
        authored_by="system:trading_signal_evaluator",
        message=f"Signal trigger: {fired}",
        summary="Signal trigger flag written — Reviewer heartbeat will fire",
    )


async def _fire_trade_proposal(client: Any, user_id: str) -> None:
    try:
        from services.recurrence import walk_workspace_recurrences
        import asyncio
        decls = await asyncio.to_thread(walk_workspace_recurrences, client, user_id)
        trade_decl = next((d for d in decls if "trade-proposal" in d.slug), None)
        if trade_decl:
            from services.invocation_dispatcher import dispatch
            await dispatch(trade_decl)
    except Exception as exc:
        logger.warning("[SIGNAL_EVAL] trade-proposal fire failed: %s", exc)


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def _shape_result(started_at: datetime, actions: list, errors: list, any_triggered: bool) -> dict:
    duration_s = (datetime.now(timezone.utc) - started_at).total_seconds()
    fired = [a for a in actions if a.get("triggered") and a.get("evaluable")]
    intraday = [a for a in actions if not a.get("evaluable", True)]

    lines = [
        "# Signal Evaluator", "",
        f"**Ran**: {started_at.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"**Duration**: {duration_s:.2f}s",
        f"**Daily-bar signals fired**: {len(fired)}",
        f"**Intraday signals (skipped — live data needed)**: {len(intraday)}",
        f"**Errors**: {len(errors)}",
    ]
    if fired:
        lines += ["", "## Fired signals"] + [f"- `{a['signal']}` on {a['triggered']}" for a in fired]
    if errors:
        lines += ["", "## Errors"] + [f"- {e}" for e in errors]

    summary = (
        f"Signal evaluation: {len(fired)} signal(s) fired — trade-proposal invoked"
        if any_triggered else f"Signal evaluation: no daily-bar signals triggered"
    )
    return {"output_markdown": "\n".join(lines) + "\n", "summary": summary[:200], "actions_taken": actions}
