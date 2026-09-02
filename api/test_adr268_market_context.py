"""Regression gate for ADR-268 — Market-Context-Aware Recurrences.

Verifies:
  - Plain UTC cron path (backward compat) — Recurrence with `schedule="0 7 * * *"` resolves without market_context.
  - Semantic anchor: `@market_open + 15min` → resolves to 09:45 ET next trading day.
  - Semantic anchor with negative offset: `@market_open - 30min` → 09:00 ET.
  - Semantic anchor at market close: `@market_close + 1h` → 17:00 ET.
  - Interval: `@every 1min during regular_hours` → first fire at next session open.
  - Interval mid-session: floor at 10:00 ET, `@every 5min during regular_hours` → 10:05 ET.
  - List-of-schedules: min of resolved members wins.
  - Holiday handling: anchor on Memorial Day (2026-05-25) skips to next trading day (2026-05-26).
  - Weekend handling: anchor at Sat → next Monday.
  - Loud failure: semantic schedule with no market_context raises ValueError.
  - Backward compat: bundle without market_context block returns None from get_market_context_for_user.
  - alpha-trader bundle migration: all semantic schedules parse, resolve, and reference defined sessions.

Run: cd api && .venv/bin/python -m api.test_adr268_market_context
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Ensure api/ is on sys.path so `services.*` imports resolve when run from repo root.
_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from types import SimpleNamespace  # noqa: E402


def Recurrence(**kw):  # noqa: N802 — ADR-632: the dataclass retired; the schedule math is duck-typed
    return SimpleNamespace(paused=False, paused_until=None, options={}, **kw)
from services.scheduling import compute_next_run_at, resolve_semantic_schedule  # noqa: E402
from services.market_calendars import (  # noqa: E402
    CALENDARS,
    NyseUsCalendar,
    calendar_for_market_context,
)


ET = ZoneInfo("America/New_York")


# Canonical alpha-trader market_context for tests
ALPHA_TRADER_MARKET_CONTEXT = {
    "exchange": "us_equities",
    "timezone": "America/New_York",
    "sessions": {
        "regular_hours": {"open": "09:30", "close": "16:00"},
        "pre_market": {"open": "04:00", "close": "09:30"},
        "after_hours": {"open": "16:00", "close": "20:00"},
    },
    "trading_days": "weekdays",
    "calendar": "nyse_us",
}


def _utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _et(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=ET)


# ---------------------------------------------------------------------------
# Assertions accumulator
# ---------------------------------------------------------------------------

PASSED = 0
FAILED: list[str] = []


def assert_eq(actual, expected, msg):
    global PASSED
    if actual == expected:
        PASSED += 1
    else:
        FAILED.append(f"{msg}\n  actual:   {actual}\n  expected: {expected}")


def assert_true(cond, msg):
    global PASSED
    if cond:
        PASSED += 1
    else:
        FAILED.append(msg)


def assert_raises(exc_type, fn, msg):
    global PASSED
    try:
        fn()
    except exc_type:
        PASSED += 1
        return
    except Exception as e:
        FAILED.append(f"{msg}\n  expected {exc_type.__name__}, got {type(e).__name__}: {e}")
        return
    FAILED.append(f"{msg}\n  expected {exc_type.__name__}, nothing raised")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_plain_cron_backward_compat():
    """Plain UTC cron resolves without market_context (backward compat)."""
    rec = Recurrence(slug="t", schedule="0 7 * * *", prompt="x")
    now = _utc(2026, 5, 13, 1, 30)  # Wed 01:30 UTC
    next_run = compute_next_run_at(rec, last_run_at=None, now=now)
    # Next 07:00 UTC after 01:30 UTC on Wed = same day 07:00 UTC
    assert_eq(next_run, _utc(2026, 5, 13, 7, 0), "plain cron forward")


def test_market_open_anchor():
    """`@market_open + 15min` resolves to next RTH open + 15min."""
    rec = Recurrence(slug="t", schedule="@market_open + 15min", prompt="x")
    now = _utc(2026, 5, 13, 13, 0)  # Wed 09:00 ET
    next_run = compute_next_run_at(
        rec, last_run_at=None, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    expected_et = _et(2026, 5, 13, 9, 45)
    assert_eq(next_run, expected_et.astimezone(timezone.utc), "@market_open + 15min")


def test_market_open_negative_offset():
    """`@market_open - 30min` resolves to 30 min before next open."""
    rec = Recurrence(slug="t", schedule="@market_open - 30min", prompt="x")
    now = _utc(2026, 5, 13, 8, 0)  # Wed 04:00 ET — well before open
    next_run = compute_next_run_at(
        rec, last_run_at=None, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    expected = _et(2026, 5, 13, 9, 0).astimezone(timezone.utc)  # 09:00 ET = 13:00 UTC EDT
    assert_eq(next_run, expected, "@market_open - 30min")


def test_market_close_anchor():
    """`@market_close + 1h` resolves to 1h after next RTH close."""
    rec = Recurrence(slug="t", schedule="@market_close + 1h", prompt="x")
    now = _utc(2026, 5, 13, 12, 0)  # Wed 08:00 ET
    next_run = compute_next_run_at(
        rec, last_run_at=None, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    expected = _et(2026, 5, 13, 17, 0).astimezone(timezone.utc)  # 17:00 ET
    assert_eq(next_run, expected, "@market_close + 1h")


def test_interval_at_session_open():
    """`@every 1min during regular_hours` first fire = session open."""
    rec = Recurrence(slug="t", schedule="@every 1min during regular_hours", prompt="x")
    now = _utc(2026, 5, 13, 8, 0)  # Wed 04:00 ET — before open
    next_run = compute_next_run_at(
        rec, last_run_at=None, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    expected = _et(2026, 5, 13, 9, 30).astimezone(timezone.utc)  # 09:30 ET
    assert_eq(next_run, expected, "interval first fire at open")


def test_interval_mid_session():
    """Interval mid-session advances to the next boundary."""
    rec = Recurrence(slug="t", schedule="@every 5min during regular_hours", prompt="x")
    # Wed 10:00 ET = 14:00 UTC EDT. Floor at 10:01 (last_run + 1min).
    last_run = _et(2026, 5, 13, 10, 0).astimezone(timezone.utc)
    now = _et(2026, 5, 13, 10, 1).astimezone(timezone.utc)
    next_run = compute_next_run_at(
        rec, last_run_at=last_run, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    # First fire at 09:30 ET, interval 5 min → 09:30, 09:35, ... 10:00, 10:05, ...
    # Floor is 10:01, so next = 10:05.
    expected = _et(2026, 5, 13, 10, 5).astimezone(timezone.utc)
    assert_eq(next_run, expected, "interval mid-session advances")


def test_list_of_schedules_min_wins():
    """List-form schedule → min(resolved members) wins."""
    rec = Recurrence(
        slug="t",
        schedule=[
            "@market_open + 15min",  # 09:45 ET
            "@market_open + 3h",     # 12:30 ET
            "@market_close - 1h",    # 15:00 ET
        ],
        prompt="x",
    )
    now = _utc(2026, 5, 13, 13, 0)  # Wed 09:00 ET — before any of the three
    next_run = compute_next_run_at(
        rec, last_run_at=None, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    # Earliest is 09:45 ET
    expected = _et(2026, 5, 13, 9, 45).astimezone(timezone.utc)
    assert_eq(next_run, expected, "list-of-schedules min wins")


def test_holiday_skips_to_next_trading_day():
    """Anchor on Memorial Day (2026-05-25 Mon, holiday) skips to Tue 2026-05-26."""
    rec = Recurrence(slug="t", schedule="@market_open", prompt="x")
    now = _utc(2026, 5, 25, 8, 0)  # Mon Memorial Day 04:00 ET
    next_run = compute_next_run_at(
        rec, last_run_at=None, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    expected = _et(2026, 5, 26, 9, 30).astimezone(timezone.utc)
    assert_eq(next_run, expected, "Memorial Day skip to Tue")


def test_weekend_skips_to_monday():
    """Anchor on Saturday → next Monday's open."""
    rec = Recurrence(slug="t", schedule="@market_open", prompt="x")
    now = _utc(2026, 5, 16, 12, 0)  # Sat
    next_run = compute_next_run_at(
        rec, last_run_at=None, now=now,
        market_context=ALPHA_TRADER_MARKET_CONTEXT,
    )
    expected = _et(2026, 5, 18, 9, 30).astimezone(timezone.utc)  # Mon
    assert_eq(next_run, expected, "Saturday skips to Monday")


def test_semantic_without_market_context_raises():
    """Semantic schedule + no market_context → ValueError (loud failure)."""
    rec = Recurrence(slug="t", schedule="@market_open", prompt="x")
    now = _utc(2026, 5, 13, 0, 0)
    assert_raises(
        ValueError,
        lambda: compute_next_run_at(rec, last_run_at=None, now=now, market_context=None),
        "semantic schedule without market_context raises ValueError",
    )


def test_calendar_registry_has_nyse_us():
    """The NYSE US calendar is registered."""
    assert_true("nyse_us" in CALENDARS, "nyse_us calendar registered")
    cal = calendar_for_market_context(ALPHA_TRADER_MARKET_CONTEXT)
    assert_true(isinstance(cal, NyseUsCalendar), "calendar_for_market_context returns NyseUsCalendar")


def test_unknown_calendar_raises():
    """Unknown calendar key raises with a clear message."""
    bad_ctx = {**ALPHA_TRADER_MARKET_CONTEXT, "calendar": "nonexistent_xyz"}
    assert_raises(
        ValueError,
        lambda: calendar_for_market_context(bad_ctx),
        "unknown calendar key raises ValueError",
    )


def test_recurrence_routes_stay_deleted():
    """ADR-603 D5 (2026-08-24): routes/recurrences.py is DELETED with the
    recurrence concept (production counted 0 declarations). The two tests
    that lived here (TaskResponse list-schedule; _decode_persisted_schedule
    round-trip) gated that file's serving layer and are retired with it —
    the semantic-schedule RESOLUTION they leaned on stays gated above."""
    import pathlib
    assert not (pathlib.Path(__file__).parent / "routes" / "recurrences.py").exists(),         "routes/recurrences.py must stay deleted (ADR-603 D5)"

def main():
    tests = [
        test_plain_cron_backward_compat,
        test_market_open_anchor,
        test_market_open_negative_offset,
        test_market_close_anchor,
        test_interval_at_session_open,
        test_interval_mid_session,
        test_list_of_schedules_min_wins,
        test_holiday_skips_to_next_trading_day,
        test_weekend_skips_to_monday,
        test_semantic_without_market_context_raises,
        test_calendar_registry_has_nyse_us,
        test_unknown_calendar_raises,
        test_recurrence_routes_stay_deleted,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAILED.append(f"{t.__name__} crashed: {type(e).__name__}: {e}")

    print(f"\nADR-268 regression gate: {PASSED} assertion(s) passed")
    if FAILED:
        print(f"FAILED: {len(FAILED)}")
        for f in FAILED:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
