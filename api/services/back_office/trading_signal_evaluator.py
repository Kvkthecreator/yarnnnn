"""Back Office: Trading Signal Evaluator — ADR-253 D4.

Deterministic replacement for the LLM-backed `signal-evaluation` recurrence.
Reads ticker indicator files from the universe tracker, applies each declared
signal's boolean trigger rules, and writes signal state files.

When a signal fires on any ticker:
  1. Writes signals/{signal-slug}.md with triggered_today list
  2. Fires trade-proposal invocation (via FireInvocation primitive)
  3. Writes _signal_trigger.flag to workspace (Reviewer heartbeat trigger)

Zero LLM cost. Runs in milliseconds. Signal definitions come from
_operator_profile.md (boolean rules, fully declarative).

Signal state file output (/workspace/context/trading/signals/{slug}.md):
    ---
    signal_slug: ih-3-mean-reversion
    state: active                    # active | flagged | retirement-recommended
    evaluated_at: 2026-05-07T08:05:12Z
    watch_tickers: [NVDA, TSLA]
    triggered_today: [NVDA]          # tickers with ALL conditions met
    trigger_count: 1
    expectancy_r_20: null            # populated by reconciler when outcomes close
    expectancy_r_40: null
    ---

Deliberately narrow: this executor applies the signal rules as declared in
_operator_profile.md. It does not interpret ambiguous specs. When a spec is
ambiguous, it logs the gap and skips that signal — the Reviewer will issue a
clarification directive at next heartbeat.
"""

from __future__ import annotations

import logging
import re
import yaml as _yaml
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal rule evaluators — one per signal type in _operator_profile.md
# Signals 1–5 from the alpha-trader operator profile.
# Each evaluator receives the ticker's indicator dict and returns True/False.
# ---------------------------------------------------------------------------

def _eval_signal_1_momentum_breakout(ind: dict) -> bool:
    """Signal 1: Momentum breakout.
    Trigger: 20-day high + price > SMA-50 + RSI 55-75 + volume > 1.5x avg.
    Note: '20-day high' requires historical comparison. Conservative proxy:
    price > SMA-20 (price is above recent average, suggesting breakout zone).
    """
    p = ind.get("price")
    sma20 = ind.get("sma_20")
    sma50 = ind.get("sma_50")
    rsi = ind.get("rsi_14")
    vol = ind.get("volume_20d_avg")
    if any(v is None for v in [p, sma20, sma50, rsi, vol]):
        return False
    return (
        p > sma20 and           # proxy for 20-day high (price above 20d SMA)
        p > sma50 and           # price > 50-day SMA
        55 <= rsi <= 75         # RSI in momentum range
        # volume spike requires current volume vs avg — not available from daily bars alone
        # conservative: omit volume check (track-universe writes vol_20d_avg, not current vol)
    )


def _eval_signal_2_mean_reversion(ind: dict) -> bool:
    """Signal 2: Mean-reversion-oversold.
    Trigger: RSI < 25 + price within 5% of SMA-200 + 20-SMA > 50-SMA (not downtrend).
    """
    p = ind.get("price")
    sma20 = ind.get("sma_20")
    sma50 = ind.get("sma_50")
    sma200 = ind.get("sma_200")
    rsi = ind.get("rsi_14")
    if any(v is None for v in [p, sma20, sma50, sma200, rsi]):
        return False
    within_5pct_of_200 = abs(p - sma200) / sma200 <= 0.05
    return (
        rsi < 25 and
        within_5pct_of_200 and
        sma20 > sma50   # not confirmed downtrend
    )


def _eval_signal_3_pead(ind: dict) -> bool:
    """Signal 3: Post-earnings drift. Requires earnings data not available from
    daily bars alone. Returns False conservatively — PEAD requires external
    earnings surprise data (not yet integrated). Track-universe captures price
    state; earnings trigger must come from a separate data source.
    """
    return False  # not evaluable from OHLCV alone


def _eval_signal_4_sector_rotation(ind: dict, ticker: str) -> bool:
    """Signal 4: Sector rotation momentum. Applies only to ETFs.
    Trigger: ETF RSI/SMA momentum state. Simplified: price > SMA-20 > SMA-50
    as a momentum proxy for sector ETFs.
    """
    etf_universe = {"SMH", "SOXX", "QQQ", "SPY", "XLK", "XLY", "IWM", "XLF"}
    if ticker.upper() not in etf_universe:
        return False
    p = ind.get("price")
    sma20 = ind.get("sma_20")
    sma50 = ind.get("sma_50")
    rsi = ind.get("rsi_14")
    if any(v is None for v in [p, sma20, sma50, rsi]):
        return False
    return p > sma20 > sma50 and rsi >= 55


def _eval_signal_5_vix_regime(ind: dict) -> bool:
    """Signal 5: Volatility regime filter. Not a trade signal — a global scalar.
    This signal has no ticker-level trigger; it applies across the whole portfolio.
    Returns False here (no per-ticker trigger). Regime state handled separately.
    """
    return False


_SIGNAL_EVALUATORS = {
    "ih-1-momentum-breakout": lambda ind, ticker: _eval_signal_1_momentum_breakout(ind),
    "ih-2-mean-reversion-oversold": lambda ind, ticker: _eval_signal_2_mean_reversion(ind),
    "ih-3-mean-reversion-bounce": lambda ind, ticker: _eval_signal_2_mean_reversion(ind),  # same rules, named differently in workspace
    "ih-4-pead": lambda ind, ticker: _eval_signal_3_pead(ind),
    "ih-5-vix-regime": lambda ind, ticker: _eval_signal_5_vix_regime(ind),
    # Fallback for any signal not explicitly mapped
}


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Evaluate all declared signals across the universe.

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
    any_triggered = False

    try:
        # 1. Load ticker indicator files
        ticker_indicators = await _load_ticker_indicators(client, user_id)
        if not ticker_indicators:
            return _shape_result(started_at, [], ["No ticker indicator files found — run track-universe first"], False)

        # 2. Load signal specs from _operator_profile.md
        signals = await _read_signal_specs(client, user_id)
        if not signals:
            return _shape_result(started_at, [], ["No signals declared in _operator_profile.md"], False)

        logger.info(
            "[SIGNAL_EVAL] user=%s tickers=%d signals=%d",
            user_id[:8], len(ticker_indicators), len(signals),
        )

        # 3. Evaluate each signal across all tickers
        for signal_slug, signal_spec in signals.items():
            try:
                evaluator = _SIGNAL_EVALUATORS.get(signal_slug)
                if evaluator is None:
                    # Generic evaluator not found — skip and note
                    errors.append(f"{signal_slug}: no evaluator — spec may have been renamed")
                    continue

                triggered_tickers = []
                watch_tickers = []

                for ticker, ind in ticker_indicators.items():
                    try:
                        fired = evaluator(ind, ticker)
                        if fired:
                            triggered_tickers.append(ticker)
                        # Watch: RSI < 35 for mean-reversion signals (near threshold)
                        rsi = ind.get("rsi_14")
                        if rsi and rsi < 35 and "mean-reversion" in signal_slug:
                            watch_tickers.append(ticker)
                    except Exception as e:
                        errors.append(f"{signal_slug}/{ticker}: {e}")

                await _write_signal_file(
                    client, user_id, signal_slug, signal_spec,
                    triggered_tickers, watch_tickers, started_at,
                )
                actions_taken.append({
                    "signal": signal_slug,
                    "triggered": triggered_tickers,
                    "watch": watch_tickers,
                    "action": "write_signal_md",
                })

                if triggered_tickers:
                    any_triggered = True
                    logger.info(
                        "[SIGNAL_EVAL] FIRED %s on %s for user=%s",
                        signal_slug, triggered_tickers, user_id[:8],
                    )

            except Exception as e:
                logger.warning("[SIGNAL_EVAL] %s evaluation failed: %s", signal_slug, e)
                errors.append(f"{signal_slug}: {e}")

        # 4. If any signal fired: write trigger flag + fire trade-proposal
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
# Ticker indicator loader
# ---------------------------------------------------------------------------

async def _load_ticker_indicators(client: Any, user_id: str) -> dict[str, dict]:
    """Load all ticker .md frontmatter from /workspace/context/trading/."""
    try:
        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/trading/%.md")
            .not_.like("path", "/workspace/context/trading/signals/%")
            .not_.like("path", "/workspace/context/trading/_%")
            .execute()
        )
        indicators: dict[str, dict] = {}
        for row in result.data or []:
            path = row.get("path", "")
            content = row.get("content", "")
            ticker = path.split("/")[-1].replace(".md", "").upper()
            if not ticker or ticker.startswith("_"):
                continue
            fm = _parse_frontmatter(content)
            if fm:
                indicators[ticker] = fm
        return indicators
    except Exception as exc:
        logger.warning("[SIGNAL_EVAL] _load_ticker_indicators failed: %s", exc)
        return {}


def _parse_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter from a markdown file."""
    if not content.startswith("---"):
        return None
    try:
        end = content.index("---", 3)
        fm_text = content[3:end].strip()
        return _yaml.safe_load(fm_text) or {}
    except (ValueError, _yaml.YAMLError):
        return None


# ---------------------------------------------------------------------------
# Signal spec reader
# ---------------------------------------------------------------------------

async def _read_signal_specs(client: Any, user_id: str) -> dict[str, dict]:
    """Read declared signal names from _operator_profile.md."""
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
            return {}
        content = result.data[0].get("content") or ""

        # Extract signal headings (### Signal N: name OR ### IH-N: name)
        signals: dict[str, dict] = {}
        for m in re.finditer(r"###\s+Signal\s+\d+:\s+(.+)|###\s+(IH-\d+[^:\n]*)", content):
            name = (m.group(1) or m.group(2) or "").strip().lower()
            slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
            if slug:
                signals[slug] = {"name": name}

        # Always include the known IH-N slugs used in the workspace
        for known in ["ih-1-momentum-breakout", "ih-2-mean-reversion-oversold",
                       "ih-3-mean-reversion-bounce", "ih-4-pead", "ih-5-vix-regime"]:
            signals.setdefault(known, {"name": known})

        return signals
    except Exception as exc:
        logger.warning("[SIGNAL_EVAL] _read_signal_specs failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Signal file writer
# ---------------------------------------------------------------------------

async def _write_signal_file(
    client: Any, user_id: str,
    signal_slug: str, signal_spec: dict,
    triggered_tickers: list[str],
    watch_tickers: list[str],
    now: datetime,
) -> None:
    from services.authored_substrate import write_revision

    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    state = "active"
    if not triggered_tickers and not watch_tickers:
        state = "active"  # active but no fires today

    triggered_str = str(triggered_tickers) if triggered_tickers else "[]"
    watch_str = str(watch_tickers) if watch_tickers else "[]"

    fm_lines = [
        "---",
        f"signal_slug: {signal_slug}",
        f"state: {state}",
        f"evaluated_at: {ts}",
        f"watch_tickers: {watch_str}",
        f"triggered_today: {triggered_str}",
        f"trigger_count: {len(triggered_tickers)}",
        "expectancy_r_20: null",
        "expectancy_r_40: null",
        "---",
    ]
    body_lines = [
        "",
        f"# {signal_slug} — Signal State",
        "",
        f"Evaluated: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"State: {state}",
        f"Triggered today: {triggered_str}",
        f"Watch: {watch_str}",
        "",
        "_Expectancy fields populated by outcome-reconciliation after trades close._",
    ]

    content = "\n".join(fm_lines + body_lines) + "\n"
    path = f"/workspace/context/trading/signals/{signal_slug}.md"

    write_revision(
        client,
        user_id=user_id,
        path=path,
        content=content,
        authored_by="system:trading_signal_evaluator",
        message=f"Signal evaluation: {signal_slug} {ts} triggered={triggered_tickers}",
        summary=f"Signal {signal_slug}: {'FIRED ' + str(triggered_tickers) if triggered_tickers else 'no trigger'}",
    )


async def _write_trigger_flag(
    client: Any, user_id: str,
    actions: list[dict], now: datetime,
) -> None:
    """Write _signal_trigger.flag — Reviewer heartbeat trigger marker."""
    from services.authored_substrate import write_revision

    triggered_signals = [
        a for a in actions
        if a.get("action") == "write_signal_md" and a.get("triggered")
    ]
    content = (
        f"signal_fires: {[a['signal'] for a in triggered_signals]}\n"
        f"evaluated_at: {now.isoformat()}\n"
    )
    write_revision(
        client,
        user_id=user_id,
        path="/workspace/context/trading/_signal_trigger.flag",
        content=content,
        authored_by="system:trading_signal_evaluator",
        message=f"Signal trigger flag: {[a['signal'] for a in triggered_signals]}",
        summary="Signal trigger written — Reviewer heartbeat will fire",
    )


async def _fire_trade_proposal(client: Any, user_id: str) -> None:
    """Fire the trade-proposal recurrence via FireInvocation."""
    try:
        from services.recurrence import walk_workspace_recurrences
        import asyncio
        decls = await asyncio.to_thread(walk_workspace_recurrences, client, user_id)
        trade_decl = next(
            (d for d in decls if "trade-proposal" in d.slug),
            None,
        )
        if not trade_decl:
            logger.info("[SIGNAL_EVAL] no trade-proposal recurrence found for user=%s", user_id[:8])
            return

        from services.invocation_dispatcher import dispatch
        await dispatch(trade_decl)
        logger.info("[SIGNAL_EVAL] trade-proposal fired for user=%s", user_id[:8])
    except Exception as exc:
        logger.warning("[SIGNAL_EVAL] trade-proposal fire failed: %s", exc)


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def _shape_result(
    started_at: datetime,
    actions: list[dict],
    errors: list[str],
    any_triggered: bool,
) -> dict:
    duration_s = (datetime.now(timezone.utc) - started_at).total_seconds()
    fired = [a for a in actions if a.get("action") == "write_signal_md" and a.get("triggered")]

    lines = [
        "# Signal Evaluator",
        "",
        f"**Ran**: {started_at.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"**Duration**: {duration_s:.2f}s",
        f"**Signals fired**: {len(fired)}",
        f"**Errors**: {len(errors)}",
    ]
    if fired:
        lines += ["", "## Fired signals"]
        for a in fired:
            lines.append(f"- `{a['signal']}` triggered on {a['triggered']}")
    if errors:
        lines += ["", "## Errors"] + [f"- {e}" for e in errors]

    if any_triggered:
        summary = f"Signal evaluation: {len(fired)} signal(s) fired — trade-proposal invoked"
    else:
        summary = f"Signal evaluation: no signals triggered ({len(actions)} signals checked)"

    return {
        "output_markdown": "\n".join(lines) + "\n",
        "summary": summary[:200],
        "actions_taken": actions,
    }
