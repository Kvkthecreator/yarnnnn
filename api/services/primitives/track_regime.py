"""TrackRegime Primitive — ADR-271 Thread A.

Deterministic mechanical primitive that fetches VIXY + SPY 1Day bars from
Alpaca, computes the regime predicate (vix_regime_active + trend_regime),
and writes ``/workspace/context/trading/_regime.yaml`` per the schema in
``/workspace/specs/regime-state.md``.

Zero LLM cost. Runs in ~1-2 seconds. Replaces the judgment-mode
``track-regime`` recurrence prompt that previously dispatched a Sonnet
specialist to do the same deterministic predicate math.

Surface:
    @primitive: TrackRegime()

No arguments — thresholds (vixy_active_threshold, vixy_deactivation_threshold)
are read at runtime from ``/workspace/specs/regime-state.md`` so the
operator can tune them in the spec doc without redeploying. The recurrence's
bundle prompt is exactly this one-line directive.

Behavior:
    1. Load active trading credentials (platform_connections.platform='trading').
    2. Read thresholds from regime-state spec (fallback defaults if absent).
    3. Fetch VIXY 25 days + SPY 55 days of 1Day bars.
    4. Compute vix_regime_active + deactivation_streak_days from VIXY.
    5. Compute trend_regime (uptrend/downtrend/chop) from SPY SMAs.
    6. Write _regime.yaml atomically.
    7. Return ``{success, items_processed, paths_written, errors}``.

Dispatch surface:
    - Mechanical recurrence dispatcher only (per ADR-264 D3). Not in
      CHAT_PRIMITIVES / HEADLESS_PRIMITIVES / REVIEWER_PRIMITIVES.
      Registered in HANDLERS for _dispatch_mechanical routing.

Attribution:
    All writes go through ``write_revision(authored_by="system:track-regime")``
    per ADR-209 Authored Substrate.

ADR-263 §"Why this rewrite" named ``track-regime`` alongside
``track-universe`` as the kind of deterministic predicate math that was
miscategorized as judgment work. This primitive enacts the mechanical
mode for it.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import yaml as _yaml

logger = logging.getLogger(__name__)


_VIXY_BARS = 25  # enough for SMA-20 + 1 day buffer
_SPY_BARS = 55   # enough for SMA-50 + 1 day buffer
_DEACTIVATION_STREAK_WINDOW = 30  # cap streak counter at 30 days

_REGIME_SPEC_PATH = "/workspace/specs/regime-state.md"
_REGIME_OUTPUT_PATH = "/workspace/context/trading/_regime.yaml"

# Spec-doc defaults — used if regime-state.md doesn't override.
# Match the published values in docs/programs/alpha-trader/.../specs/regime-state.md
# (vixy_active_threshold: 22.0, vixy_deactivation_threshold: 17.5).
_DEFAULT_VIXY_ACTIVE_THRESHOLD = 22.0
_DEFAULT_VIXY_DEACTIVATION_THRESHOLD = 17.5


async def handle_track_regime(auth: Any, input: dict) -> dict:
    """Fetch VIXY+SPY bars, compute regime predicate, write _regime.yaml.

    Arguments are ignored. The bundle prompt should be exactly
    ``@primitive: TrackRegime()``.

    Returns standard mechanical-primitive shape.
    """
    user_id = getattr(auth, "user_id", None)
    client = getattr(auth, "client", None)
    if not user_id or not client:
        return {"success": False, "error": "auth_required", "items_processed": 0,
                "paths_written": [], "errors": ["missing auth.user_id or auth.client"]}

    started_at = datetime.now(timezone.utc)
    errors: list[str] = []

    api_key, api_secret, paper = await _load_trading_credentials(client, user_id)
    if not api_key:
        return {"success": False, "error": "capability_missing",
                "items_processed": 0, "paths_written": [],
                "errors": ["no active trading platform_connection"]}

    # Read operator-tunable thresholds from the spec doc.
    active_t, deactivation_t = await _read_thresholds(client, user_id)

    logger.info(
        "[TRACK_REGIME] user=%s vixy_active=%s vixy_deactivation=%s paper=%s",
        user_id[:8], active_t, deactivation_t, paper,
    )

    from integrations.core.alpaca_client import get_trading_client
    alpaca = get_trading_client()

    # VIXY — volatility regime
    try:
        vixy_bars = await alpaca.get_bars(
            api_key=api_key, api_secret=api_secret,
            symbol="VIXY", timeframe="1Day", limit=_VIXY_BARS,
        )
    except Exception as exc:
        errors.append(f"VIXY fetch failed: {exc}")
        vixy_bars = []

    # SPY — trend regime
    try:
        spy_bars = await alpaca.get_bars(
            api_key=api_key, api_secret=api_secret,
            symbol="SPY", timeframe="1Day", limit=_SPY_BARS,
        )
    except Exception as exc:
        errors.append(f"SPY fetch failed: {exc}")
        spy_bars = []

    if not vixy_bars or not spy_bars:
        # Both feeds need at least minimum bars to compute the predicate.
        # If either is missing, attempt the stale-fallback path: keep the
        # prior _regime.yaml if it's fresh enough; otherwise return failure.
        await _emit_stale_fallback(client, user_id, errors, started_at)
        return {"success": False, "error": "insufficient_bars",
                "items_processed": 0, "paths_written": [], "errors": errors}

    vixy_state = _compute_vixy_regime(
        vixy_bars, active_t, deactivation_t,
    )
    spy_state = _compute_spy_regime(spy_bars)

    payload = {
        "last_updated": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        # VIXY proxy state
        "vixy_close":                    vixy_state["vixy_close"],
        "vixy_sma_20":                   vixy_state["vixy_sma_20"],
        "vixy_active_threshold":         active_t,
        "vixy_deactivation_threshold":   deactivation_t,
        # Computed VIX regime
        "vix_regime_active":             vixy_state["vix_regime_active"],
        "deactivation_streak_days":      vixy_state["deactivation_streak_days"],
        # SPY trend regime
        "spy_close":                     spy_state["spy_close"],
        "spy_sma_20":                    spy_state["spy_sma_20"],
        "spy_sma_50":                    spy_state["spy_sma_50"],
        "trend_regime":                  spy_state["trend_regime"],
        # Data quality
        "data_stale":                    False,
    }

    path = await _write_regime_yaml(client, user_id, payload, started_at)
    return {
        "success": True,
        "items_processed": 1,
        "paths_written": [path],
        "errors": errors,  # may include partial warnings even on success
    }


# ---------------------------------------------------------------------------
# Threshold reader — pulls from regime-state.md spec doc
# ---------------------------------------------------------------------------

async def _read_thresholds(
    client: Any, user_id: str,
) -> tuple[float, float]:
    """Read vixy_active_threshold + vixy_deactivation_threshold from spec.

    Falls back to spec-doc-published defaults if the file is missing or
    the lines aren't parseable. Operator tunes by editing the spec doc.
    """
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", _REGIME_SPEC_PATH)
            .limit(1)
            .execute()
        )
        if not result.data:
            return _DEFAULT_VIXY_ACTIVE_THRESHOLD, _DEFAULT_VIXY_DEACTIVATION_THRESHOLD
        content = result.data[0].get("content") or ""
    except Exception as exc:
        logger.warning("[TRACK_REGIME] threshold read failed: %s", exc)
        return _DEFAULT_VIXY_ACTIVE_THRESHOLD, _DEFAULT_VIXY_DEACTIVATION_THRESHOLD

    active = _extract_threshold(content, "vixy_active_threshold",
                                 _DEFAULT_VIXY_ACTIVE_THRESHOLD)
    deactivation = _extract_threshold(content, "vixy_deactivation_threshold",
                                       _DEFAULT_VIXY_DEACTIVATION_THRESHOLD)
    return active, deactivation


def _extract_threshold(text: str, key: str, default: float) -> float:
    """Pull a `key: NN.N` value out of the spec's example YAML block.

    The spec markdown contains a YAML block showing the schema with example
    values; we extract the published default from there. If the spec gets
    rewritten in a way that hides the YAML, fall back to default.
    """
    pattern = re.compile(
        rf"^\s*{re.escape(key)}\s*:\s*([0-9]+(?:\.[0-9]+)?)",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return default


# ---------------------------------------------------------------------------
# VIXY regime — vix_regime_active + deactivation_streak_days
# ---------------------------------------------------------------------------

def _compute_vixy_regime(
    bars: list[dict],
    active_threshold: float,
    deactivation_threshold: float,
) -> dict:
    """Compute VIX regime from VIXY 1Day bars.

    bars are returned newest-first by Alpaca (sort=desc); reverse for math.
    """
    closes = [b["close"] for b in reversed(bars)]
    n = len(closes)
    vixy_close = round(closes[-1], 4) if n else 0.0
    vixy_sma_20 = round(sum(closes[-20:]) / 20, 4) if n >= 20 else None

    vix_regime_active = bool(
        vixy_sma_20 is not None
        and vixy_close > active_threshold
        and vixy_close > vixy_sma_20
    )

    # Deactivation streak — consecutive trailing days at or below deactivation_threshold.
    streak = 0
    for c in reversed(closes):
        if c < deactivation_threshold:
            streak += 1
            if streak >= _DEACTIVATION_STREAK_WINDOW:
                break
        else:
            break

    return {
        "vixy_close": vixy_close,
        "vixy_sma_20": vixy_sma_20,
        "vix_regime_active": vix_regime_active,
        "deactivation_streak_days": streak,
    }


# ---------------------------------------------------------------------------
# SPY trend regime — uptrend / downtrend / chop
# ---------------------------------------------------------------------------

def _compute_spy_regime(bars: list[dict]) -> dict:
    """Compute trend regime from SPY 1Day bars."""
    closes = [b["close"] for b in reversed(bars)]
    n = len(closes)
    spy_close = round(closes[-1], 4) if n else 0.0
    spy_sma_20 = round(sum(closes[-20:]) / 20, 4) if n >= 20 else None
    # If we have <50 bars, compute SMA-50 from whatever we have (best-effort)
    # so the spec's downstream consumers see a number rather than null;
    # mark via comment in the spec, not here.
    spy_sma_50 = round(sum(closes[-50:]) / min(n, 50), 4) if n >= 20 else None

    trend = "chop"
    if spy_sma_20 is not None and spy_sma_50 is not None:
        if spy_sma_20 > spy_sma_50 and spy_close > spy_sma_20:
            trend = "uptrend"
        elif spy_sma_20 < spy_sma_50 and spy_close < spy_sma_20:
            trend = "downtrend"

    return {
        "spy_close": spy_close,
        "spy_sma_20": spy_sma_20,
        "spy_sma_50": spy_sma_50,
        "trend_regime": trend,
    }


# ---------------------------------------------------------------------------
# Stale-fallback path — when Alpaca is unreachable
# ---------------------------------------------------------------------------

async def _emit_stale_fallback(
    client: Any, user_id: str, errors: list[str], now: datetime,
) -> None:
    """Per the bundle prompt's stale-fallback contract.

    If the existing _regime.yaml is fresh (within 24h), keep it silently.
    If it's stale (>24h) or missing, log to decisions.md so the morning
    Reviewer wake sees the freshness gap.
    """
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", _REGIME_OUTPUT_PATH)
            .limit(1)
            .execute()
        )
        if not result.data:
            await _append_freshness_note(client, user_id, "no _regime.yaml exists", errors, now)
            return
        # Use load_workspace_yaml for frontmatter-tolerance: TrackRegime
        # writes _regime.yaml without frontmatter, but if a prior version
        # forked from a bundle template had one, this stays robust.
        from services.review_policy import load_workspace_yaml
        existing = load_workspace_yaml(result.data[0].get("content") or "")
        last_updated_str = existing.get("last_updated")
        if not last_updated_str:
            await _append_freshness_note(client, user_id, "_regime.yaml missing last_updated", errors, now)
            return
        try:
            last_updated = datetime.strptime(
                last_updated_str.replace("Z", "+00:00"),
                "%Y-%m-%dT%H:%M:%S%z",
            )
        except Exception:
            await _append_freshness_note(client, user_id, "_regime.yaml last_updated unparseable", errors, now)
            return
        age_hours = (now - last_updated).total_seconds() / 3600
        if age_hours > 24:
            await _append_freshness_note(
                client, user_id,
                f"_regime.yaml stale ({age_hours:.1f}h since last update)",
                errors, now,
            )
        # else: silent — prior data is fresh enough.
    except Exception as exc:
        logger.warning("[TRACK_REGIME] stale-fallback path failed: %s", exc)


async def _append_freshness_note(
    client: Any, user_id: str, reason: str, errors: list[str], now: datetime,
) -> None:
    """Append a freshness-degradation note to /workspace/review/decisions.md."""
    from services.authored_substrate import write_revision

    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    note = (
        f"\n\n--- regime-freshness-gap ---\n"
        f"timestamp: {ts}\n"
        f"slug: track-regime\n"
        f"trigger: reactive\n"
        f"reviewer_identity: system:track-regime\n"
        f"---\n"
        f"track-regime could not refresh substrate. Reason: {reason}. "
        f"Errors during fetch: {'; '.join(errors) if errors else 'none recorded'}.\n"
    )

    try:
        existing = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", "/workspace/review/decisions.md")
            .limit(1)
            .execute()
        )
        prior = existing.data[0].get("content") if existing.data else ""
        new_content = (prior or "") + note
        write_revision(
            client, user_id=user_id,
            path="/workspace/review/decisions.md",
            content=new_content,
            authored_by="system:track-regime",
            message=f"freshness-gap {ts}",
            summary=f"track-regime: {reason[:120]}",
        )
    except Exception as exc:
        logger.warning("[TRACK_REGIME] decisions.md append failed: %s", exc)


# ---------------------------------------------------------------------------
# YAML writer — ADR-209 attributed revision
# ---------------------------------------------------------------------------

async def _write_regime_yaml(
    client: Any, user_id: str, payload: dict, now: datetime,
) -> str:
    """Write /workspace/context/trading/_regime.yaml."""
    from services.authored_substrate import write_revision

    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        "# Regime state — written by TrackRegime primitive (ADR-271 Thread A)\n"
        f"# See /workspace/specs/regime-state.md for schema + threshold tuning.\n"
    )
    body = _yaml.dump(
        payload, default_flow_style=False, allow_unicode=True, sort_keys=False,
    )
    content = header + body

    write_revision(
        client, user_id=user_id, path=_REGIME_OUTPUT_PATH, content=content,
        authored_by="system:track-regime",
        message=f"regime refresh {ts}",
        summary=(
            f"VIX {'active' if payload['vix_regime_active'] else 'inactive'} · "
            f"trend {payload['trend_regime']}"
        ),
    )
    return _REGIME_OUTPUT_PATH


# ---------------------------------------------------------------------------
# Credential loading (mirror of track_universe's; identical pattern)
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
        logger.warning("[TRACK_REGIME] credential load failed: %s", exc)
        return "", "", True


__all__ = ["handle_track_regime"]
