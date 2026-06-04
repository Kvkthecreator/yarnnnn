"""Regression gate — execution-path market-hours awareness.

Finding: docs/evaluations/2026-06-04-temporal-awareness-kernel-vs-program-audit/

The alpha-trader risk gate's `trading_hours_only` rule previously used a
hand-rolled UTC-window approximation (`_is_us_market_hours`) that ignored DST
and NYSE holidays — the root cause of "continuous market-hour difficulty" on
the paper accounts. It now routes through the kernel NYSE calendar
(`services.market_calendars.NyseUsCalendar.is_open_now`), which is DST- and
holiday-correct.

This gate locks in:
  1. `is_open_now()` correctness across RTH / edges / weekend / holiday / DST.
  2. The deleted approximation does not reappear (Singular Implementation).
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from services.market_calendars import get_calendar

ET = ZoneInfo("America/New_York")


def _utc(et_dt: datetime) -> datetime:
    return et_dt.astimezone(timezone.utc)


@pytest.fixture(scope="module")
def cal():
    return get_calendar("nyse_us")


@pytest.mark.parametrize(
    "label, et_dt, expected",
    [
        ("RTH midday (summer/EDT)", datetime(2026, 6, 3, 10, 0, tzinfo=ET), True),
        ("RTH midday (winter/EST)", datetime(2026, 12, 23, 10, 0, tzinfo=ET), True),
        # The exact bug: 15:50 EST = 20:50 UTC. Old fixed 13:30-20:00 UTC window
        # falsely rejected this valid in-hours order. New code correctly opens.
        ("RTH late edge winter EST", datetime(2026, 12, 23, 15, 50, tzinfo=ET), True),
        ("just after close", datetime(2026, 6, 3, 16, 1, tzinfo=ET), False),
        ("pre-open", datetime(2026, 6, 3, 9, 29, tzinfo=ET), False),
        ("weekend", datetime(2026, 6, 6, 11, 0, tzinfo=ET), False),
        # Holidays the old approximation let through entirely:
        ("Memorial Day", datetime(2026, 5, 25, 11, 0, tzinfo=ET), False),
        ("Christmas", datetime(2026, 12, 25, 11, 0, tzinfo=ET), False),
        ("Juneteenth", datetime(2026, 6, 19, 11, 0, tzinfo=ET), False),
    ],
)
def test_is_open_now(cal, label, et_dt, expected):
    assert cal.is_open_now(now=_utc(et_dt)) is expected, label


def test_pre_market_session_distinct_from_rth(cal):
    # 08:00 ET is pre-market, not regular hours.
    pre = _utc(datetime(2026, 6, 3, 8, 0, tzinfo=ET))
    assert cal.is_open_now("regular_hours", now=pre) is False
    assert cal.is_open_now("pre_market", now=pre) is True


def test_approximation_helper_is_gone():
    """Singular Implementation: the crude `_is_us_market_hours` must not exist."""
    import services.risk_gate as rg

    assert not hasattr(rg, "_is_us_market_hours")


def test_risk_gate_uses_the_calendar():
    """The gate routes through the kernel calendar accessor."""
    import services.risk_gate as rg

    assert hasattr(rg, "_nyse_calendar")
    assert rg._nyse_calendar() is get_calendar("nyse_us")
