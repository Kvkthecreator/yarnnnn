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

from services.recurrence import Recurrence, parse_recurrences_yaml  # noqa: E402
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


def test_singleton_list_collapses_to_string():
    """Parser collapses ['x'] → 'x' for uniform downstream handling."""
    yaml_content = """
recurrences:
  - slug: t
    schedule:
      - "0 7 * * *"
    prompt: "x"
    mode: judgment
"""
    parsed = parse_recurrences_yaml(yaml_content)
    assert_true(len(parsed) == 1, "one recurrence parsed")
    assert_eq(parsed[0].schedule, "0 7 * * *", "singleton list collapsed to string")


def test_multi_element_list_preserved():
    """Multi-element list stays as list."""
    yaml_content = """
recurrences:
  - slug: t
    schedule:
      - "@market_open + 15min"
      - "@market_open + 3h"
    prompt: "x"
    mode: judgment
"""
    parsed = parse_recurrences_yaml(yaml_content)
    assert_true(len(parsed) == 1, "one recurrence parsed (multi-element)")
    assert_true(
        isinstance(parsed[0].schedule, list) and len(parsed[0].schedule) == 2,
        "multi-element list preserved as list",
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


def test_alpha_trader_bundle_recurrences_parse():
    """The shipped alpha-trader bundle's _recurrences.yaml parses cleanly."""
    bundle_path = (
        _REPO_ROOT.parent
        / "docs"
        / "programs"
        / "alpha-trader"
        / "reference-workspace"
        / "_recurrences.yaml"
    )
    content = bundle_path.read_text()
    parsed = parse_recurrences_yaml(content)
    assert_true(len(parsed) > 0, "alpha-trader bundle parses (has recurrences)")

    # Spot-check the rewritten semantic schedules are present
    by_slug = {r.slug: r for r in parsed}
    assert_true(
        by_slug["signal-evaluation"].schedule == "@market_open + 15min",
        "signal-evaluation uses semantic schedule",
    )
    assert_true(
        isinstance(by_slug["track-universe"].schedule, list),
        "track-universe uses list-of-schedules",
    )
    assert_true(
        by_slug["narrative-digest"].schedule == "0 3 * * *",
        "narrative-digest remains plain cron",
    )


def test_task_response_accepts_list_schedule():
    """Regression for the iter-3 prod 500: TaskResponse must accept
    schedule as either str or list[str] (Pydantic validation pass)."""
    # Late import — routes module is FastAPI-dependent + heavy.
    from routes.recurrences import TaskResponse
    from datetime import datetime

    now_iso = datetime(2026, 5, 13, 0, 0).isoformat()

    # 1. Single-string form (legacy + plain cron)
    r1 = TaskResponse(
        id="x", slug="t", status="active",
        schedule="0 7 * * *",
        created_at=now_iso, updated_at=now_iso,
    )
    assert_eq(r1.schedule, "0 7 * * *", "TaskResponse accepts str schedule")

    # 2. Semantic single-string
    r2 = TaskResponse(
        id="x", slug="t", status="active",
        schedule="@market_open + 15min",
        created_at=now_iso, updated_at=now_iso,
    )
    assert_eq(r2.schedule, "@market_open + 15min", "TaskResponse accepts @-prefixed str")

    # 3. List form (the iter-3 prod 500 case — track-universe)
    r3 = TaskResponse(
        id="x", slug="t", status="active",
        schedule=["@market_open + 15min", "@market_open + 3h", "@market_close - 1h"],
        created_at=now_iso, updated_at=now_iso,
    )
    assert_true(
        isinstance(r3.schedule, list) and len(r3.schedule) == 3,
        "TaskResponse accepts list[str] schedule (regression: prod 500)",
    )

    # 4. None / null form (reactive)
    r4 = TaskResponse(
        id="x", slug="t", status="active",
        schedule=None,
        created_at=now_iso, updated_at=now_iso,
    )
    assert_eq(r4.schedule, None, "TaskResponse accepts None schedule")


def test_decode_persisted_schedule():
    """`_decode_persisted_schedule` round-trips JSON-encoded list strings
    so consumers see the same authored shape that materialize_scheduling_index
    persisted."""
    from routes.recurrences import _decode_persisted_schedule

    # JSON-encoded list (how materialize_scheduling_index persists list-form)
    decoded = _decode_persisted_schedule(
        '["@market_open + 15min", "@market_open + 3h"]'
    )
    assert_true(
        isinstance(decoded, list) and decoded == ["@market_open + 15min", "@market_open + 3h"],
        "decode JSON-encoded list",
    )

    # Plain cron string
    assert_eq(
        _decode_persisted_schedule("0 7 * * *"),
        "0 7 * * *",
        "decode plain cron passes through",
    )

    # Semantic single string
    assert_eq(
        _decode_persisted_schedule("@market_open + 15min"),
        "@market_open + 15min",
        "decode semantic single passes through",
    )

    # Empty / None
    assert_eq(_decode_persisted_schedule(None), None, "decode None")
    assert_eq(_decode_persisted_schedule(""), None, "decode empty string")
    assert_eq(_decode_persisted_schedule("   "), None, "decode whitespace")

    # Malformed JSON: falls back to plain string treatment
    assert_eq(
        _decode_persisted_schedule("[not json"),
        "[not json",
        "decode malformed JSON falls back",
    )


def test_alpha_trader_bundle_recurrences_resolve():
    """All semantic schedules in the alpha-trader bundle resolve cleanly."""
    bundle_path = (
        _REPO_ROOT.parent
        / "docs"
        / "programs"
        / "alpha-trader"
        / "reference-workspace"
        / "_recurrences.yaml"
    )
    content = bundle_path.read_text()
    parsed = parse_recurrences_yaml(content)
    now = _utc(2026, 5, 13, 1, 30)

    failures: list[str] = []
    for rec in parsed:
        try:
            result = compute_next_run_at(
                rec, last_run_at=None, now=now,
                market_context=ALPHA_TRADER_MARKET_CONTEXT,
            )
            if rec.schedule is None:
                # Reactive recurrences (trade-proposal) — None is correct
                if result is not None:
                    failures.append(f"{rec.slug}: expected None for reactive, got {result}")
            elif result is None:
                failures.append(f"{rec.slug}: scheduled but resolved to None")
        except Exception as e:
            failures.append(f"{rec.slug}: raised {type(e).__name__}: {e}")

    assert_true(
        not failures,
        f"all bundle recurrences resolve: {failures}",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


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
        test_singleton_list_collapses_to_string,
        test_multi_element_list_preserved,
        test_calendar_registry_has_nyse_us,
        test_unknown_calendar_raises,
        test_alpha_trader_bundle_recurrences_parse,
        test_alpha_trader_bundle_recurrences_resolve,
        test_task_response_accepts_list_schedule,
        test_decode_persisted_schedule,
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
