"""
Market Calendars — ADR-268 §D4.

Holiday-calendar registry + session-window resolver for market-context-aware
recurrences. Bundles declare a `calendar:` key in their MANIFEST.yaml's
`market_context:` block; that key resolves to a MarketCalendar instance
that knows:

  - Which dates are trading days (vs. weekends + holidays)
  - The session windows (regular_hours, pre_market, after_hours) anchored
    to the market's timezone

The scheduler's semantic-schedule resolver (services/scheduling.py
::resolve_semantic_schedule) consults this module to convert
`@market_open + 15min` into the next valid UTC datetime.

Module ownership (per CLAUDE.md discipline rule 10):
- Owner: market-temporal concerns. Sibling to services.scheduling
  (cron + semantic timing math) and services.bundle_reader (which loads
  the market_context dict from a bundle's MANIFEST).
- Consumers: services.scheduling.resolve_semantic_schedule.
- Producers: bundle authors declaring `calendar:` in MANIFEST.yaml.

Initial implementation per ADR-268 §D4: hand-rolled NyseUsCalendar with
inline 2026 + 2027 holiday dates. Hand-rolling avoids adding
pandas-market-calendars as a dependency for one consumer. When a second
market lands (Korean equities, futures), evaluate the dep at that point.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


# Session names recognized by the semantic-schedule vocabulary.
SESSIONS = ("regular_hours", "pre_market", "after_hours")


@dataclass(frozen=True)
class SessionWindow:
    """One session's open/close times in the market's local timezone.

    `open_hhmm` and `close_hhmm` are strings like "09:30" — parsed by
    `as_datetime_on(date, tz)` into timezone-aware datetimes.
    """

    open_hhmm: str
    close_hhmm: str

    def _parse(self, hhmm: str) -> time:
        hh, mm = hhmm.split(":")
        return time(int(hh), int(mm))

    def as_datetime_on(self, d: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
        """Return (open_dt, close_dt) in the market's timezone for date d."""
        open_t = self._parse(self.open_hhmm)
        close_t = self._parse(self.close_hhmm)
        return (
            datetime.combine(d, open_t, tzinfo=tz),
            datetime.combine(d, close_t, tzinfo=tz),
        )


class MarketCalendar:
    """Base interface for market calendars.

    Subclasses declare:
      - `trading_days` rule (which weekdays are tradeable in principle)
      - `holidays` set (specific dates that are closed despite being tradeable weekdays)
      - `sessions` map (session name → SessionWindow)

    Multi-market support extends this by adding new subclasses to CALENDARS.
    """

    name: str
    timezone: ZoneInfo
    trading_weekdays: set[int]  # 0=Mon, 6=Sun
    holidays: set[date]
    sessions: dict[str, SessionWindow]

    def is_trading_day(self, d: date) -> bool:
        return d.weekday() in self.trading_weekdays and d not in self.holidays

    def session_window(self, d: date, session: str) -> tuple[datetime, datetime]:
        if session not in self.sessions:
            raise ValueError(f"unknown session {session!r} for {self.name}")
        return self.sessions[session].as_datetime_on(d, self.timezone)

    def next_trading_day_on_or_after(self, d: date) -> date:
        """Return the next trading day >= d. Bounded to look 30 days ahead;
        if no trading day found in 30 days, raises (should be impossible for
        any sane calendar)."""
        for offset in range(30):
            candidate = d + timedelta(days=offset)
            if self.is_trading_day(candidate):
                return candidate
        raise RuntimeError(f"no trading day found within 30 days of {d}")


# ---------------------------------------------------------------------------
# NYSE / NASDAQ US Equities Calendar
# ---------------------------------------------------------------------------

# US equities trade Mon–Fri 09:30–16:00 ET, with pre-market 04:00–09:30 ET
# and after-hours 16:00–20:00 ET (Alpaca-supported).
#
# Holidays observed by NYSE + NASDAQ (full closes only; half-days are treated
# as full days for v1 per ADR-268 §"Out of scope"). Source: nyse.com market
# holidays page, verified 2026-05-13.

_NYSE_HOLIDAYS_2026 = {
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # Martin Luther King Jr. Day
    date(2026, 2, 16),   # Presidents' Day / Washington's Birthday
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day (observed; July 4 is Saturday)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
}

_NYSE_HOLIDAYS_2027 = {
    date(2027, 1, 1),    # New Year's Day
    date(2027, 1, 18),   # MLK
    date(2027, 2, 15),   # Presidents' Day
    date(2027, 3, 26),   # Good Friday
    date(2027, 5, 31),   # Memorial Day
    date(2027, 6, 18),   # Juneteenth (observed; June 19 is Saturday)
    date(2027, 7, 5),    # Independence Day (observed; July 4 is Sunday)
    date(2027, 9, 6),    # Labor Day
    date(2027, 11, 25),  # Thanksgiving
    date(2027, 12, 24),  # Christmas (observed; Dec 25 is Saturday)
}


class NyseUsCalendar(MarketCalendar):
    name = "nyse_us"
    timezone = ZoneInfo("America/New_York")
    trading_weekdays = {0, 1, 2, 3, 4}  # Mon–Fri
    holidays = _NYSE_HOLIDAYS_2026 | _NYSE_HOLIDAYS_2027
    sessions = {
        "regular_hours": SessionWindow("09:30", "16:00"),
        "pre_market":    SessionWindow("04:00", "09:30"),
        "after_hours":   SessionWindow("16:00", "20:00"),
    }


# ---------------------------------------------------------------------------
# Registry — bundle MANIFEST `calendar:` key → MarketCalendar instance
# ---------------------------------------------------------------------------

CALENDARS: dict[str, MarketCalendar] = {
    "nyse_us": NyseUsCalendar(),
    # Future extensions land here:
    #   "korea_krx": KoreaKrxCalendar(),     # KRX 09:00–15:30 KST
    #   "crypto_24x7": AlwaysOpenCalendar(), # 24/7
    #   "cme_futures": CmeFuturesCalendar(), # Sun 18:00 ET → Fri 17:00 ET
}


def get_calendar(key: str) -> Optional[MarketCalendar]:
    """Return the MarketCalendar for `key`, or None if unknown.

    Caller is responsible for handling None (typically by surfacing a
    bundle-config error to the operator)."""
    return CALENDARS.get(key)


# ---------------------------------------------------------------------------
# Market-context helpers — used by services.scheduling.resolve_semantic_schedule
# ---------------------------------------------------------------------------


def calendar_for_market_context(market_context: dict) -> MarketCalendar:
    """Resolve a bundle's market_context dict to its MarketCalendar.

    Raises ValueError if the calendar key is missing or unknown — surface
    loudly rather than silently use a wrong calendar.
    """
    calendar_key = market_context.get("calendar")
    if not calendar_key:
        raise ValueError(
            "market_context missing 'calendar' key — bundle MANIFEST.yaml "
            "must declare e.g. 'calendar: nyse_us'"
        )
    cal = get_calendar(calendar_key)
    if cal is None:
        known = sorted(CALENDARS.keys())
        raise ValueError(
            f"unknown calendar {calendar_key!r}; known: {known}. "
            f"Add a MarketCalendar subclass + CALENDARS entry in "
            f"api/services/market_calendars.py to extend."
        )
    return cal


__all__ = [
    "SESSIONS",
    "SessionWindow",
    "MarketCalendar",
    "NyseUsCalendar",
    "CALENDARS",
    "get_calendar",
    "calendar_for_market_context",
]
