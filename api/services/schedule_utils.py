from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytz

from services.platform_limits import normalize_timezone_name

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "UTC"
DEFAULT_LOCAL_TIME = "09:00"


def get_user_timezone(client, user_id: str, default: str = DEFAULT_TIMEZONE) -> str:
    """Resolve user's configured timezone from /workspace/context/_shared/IDENTITY.md (ADR-206).

    Falls back to UTC when missing or invalid.
    """
    try:
        from services.workspace import UserMemory
        from services.workspace_paths import SHARED_IDENTITY_PATH

        um = UserMemory(client, user_id)
        profile = UserMemory._parse_memory_md(um.read_sync(SHARED_IDENTITY_PATH))
        return normalize_timezone_name(profile.get("timezone") or default)
    except Exception as e:
        logger.debug(f"[SCHEDULE] Failed to resolve user timezone for {user_id[:8]}: {e}")
        return normalize_timezone_name(default)


def format_datetime_for_timezone(
    value: datetime,
    user_timezone: str,
    fmt: str = "%b %-d %H:%M %Z",
) -> str:
    """Format an aware datetime in the user's timezone."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    tz_name = normalize_timezone_name(user_timezone or DEFAULT_TIMEZONE)
    local_value = value.astimezone(pytz.timezone(tz_name))
    formatted = local_value.strftime(fmt)
    if "%Z" in fmt and "UTC" not in formatted and not local_value.strftime("%Z"):
        return f"{formatted} {tz_name}".strip()
    return formatted


def format_daily_local_time_label(user_timezone: str, time_str: str = DEFAULT_LOCAL_TIME) -> str:
    """Return label like '09:00 KST' for user-facing schedule copy."""
    tz_name = normalize_timezone_name(user_timezone or DEFAULT_TIMEZONE)
    tz = pytz.timezone(tz_name)
    hour, minute = _parse_clock(time_str)
    probe = datetime.now(tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
    tz_abbr = probe.strftime("%Z") or tz_name
    return f"{time_str} {tz_abbr}"


def calculate_next_run_at(
    schedule: Any,
    last_run_at: Optional[datetime] = None,
    user_timezone: str = DEFAULT_TIMEZONE,
) -> Optional[datetime]:
    """Calculate next run time in UTC from a schedule value.

    Supports:
    - string cadence: daily|weekly|biweekly|monthly
    - cron expression strings
    - dict schedule shapes used by unified_scheduler
    - JSON-encoded dict string
    """
    now_utc = last_run_at or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    tz_name = normalize_timezone_name(user_timezone or DEFAULT_TIMEZONE)
    tz = pytz.timezone(tz_name)

    schedule_dict = _coerce_schedule_dict(schedule)
    if schedule_dict is not None:
        schedule_dict = dict(schedule_dict)
        schedule_dict.setdefault("timezone", tz_name)
        return _calculate_from_dict(schedule_dict, now_utc)

    if isinstance(schedule, str):
        schedule_str = schedule.strip()
        if not schedule_str:
            return None

        cadence = schedule_str.lower()
        if cadence in {"daily", "weekly", "biweekly", "monthly"}:
            return _calculate_simple_cadence(cadence, now_utc, tz).astimezone(timezone.utc)

        if _looks_like_cron(schedule_str):
            return _calculate_from_dict({"cron": schedule_str, "timezone": tz_name}, now_utc)

        # Unknown schedule value — preserve prior behavior.
        return now_utc + timedelta(hours=24)

    return None


def _calculate_from_dict(schedule: dict, from_time_utc: datetime) -> datetime:
    """Compute next-run time from a dict-shaped schedule.

    Supports both cron expressions (`schedule["cron"]`) and frequency-based
    schedules (`schedule["frequency"]` ∈ daily/weekly/biweekly/monthly with
    `day` + `time` + `timezone`). Pure timing math — no DB, no LLM.

    Inlined into schedule_utils per ADR-231 Phase 3.3 — previously imported
    from jobs.unified_scheduler, which created a circular layering
    (services → jobs). schedule_utils owns timing math; the scheduler
    consumes it, not the other way around.
    """
    from croniter import croniter

    tz_name = schedule.get("timezone", "UTC")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC

    # Cron expression takes precedence
    cron_expr = schedule.get("cron")
    if cron_expr:
        local_time = from_time_utc.astimezone(tz)
        cron = croniter(cron_expr, local_time)
        next_local = cron.get_next(datetime)
        return next_local.astimezone(timezone.utc)

    # Frequency-based fallback
    frequency = schedule.get("frequency", "weekly")
    day = (schedule.get("day") or "monday").lower()
    time_str = schedule.get("time", "09:00")
    try:
        hour, minute = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 9, 0

    local_now = from_time_utc.astimezone(tz)
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    target_day = days.index(day) if day in days else 0

    if frequency == "daily":
        next_run = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= local_now:
            next_run += timedelta(days=1)
    elif frequency == "weekly":
        current_day = local_now.weekday()
        days_ahead = target_day - current_day
        if days_ahead < 0:
            days_ahead += 7
        next_run = local_now + timedelta(days=days_ahead)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= local_now:
            next_run += timedelta(weeks=1)
    elif frequency == "biweekly":
        current_day = local_now.weekday()
        days_ahead = target_day - current_day
        if days_ahead < 0:
            days_ahead += 7
        next_run = local_now + timedelta(days=days_ahead)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= local_now:
            next_run += timedelta(weeks=2)
    elif frequency == "monthly":
        next_run = local_now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
        if next_run.month == 12:
            next_run = next_run.replace(year=next_run.year + 1, month=1)
        else:
            next_run = next_run.replace(month=next_run.month + 1)
        while next_run.weekday() != target_day:
            next_run += timedelta(days=1)
    else:
        # Unknown frequency — default to next week same time
        next_run = local_now + timedelta(weeks=1)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return next_run.astimezone(timezone.utc)


def _calculate_simple_cadence(cadence: str, now_utc: datetime, tz: pytz.BaseTzInfo) -> datetime:
    local_now = now_utc.astimezone(tz)
    hour, minute = _parse_clock(DEFAULT_LOCAL_TIME)

    if cadence == "daily":
        next_local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_local <= local_now:
            next_local += timedelta(days=1)
        return next_local

    if cadence == "weekly":
        # Preserve existing semantics: weekly means Monday at 09:00 (local timezone now).
        days_ahead = 7 - local_now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (local_now + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

    if cadence == "biweekly":
        target_day = 0  # Monday
        days_ahead = target_day - local_now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        next_local = (local_now + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        if next_local <= local_now:
            next_local += timedelta(weeks=2)
        return next_local

    # monthly
    if local_now.month == 12:
        return local_now.replace(
            year=local_now.year + 1,
            month=1,
            day=1,
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )
    return local_now.replace(
        month=local_now.month + 1,
        day=1,
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def _coerce_schedule_dict(schedule: Any) -> Optional[dict]:
    if isinstance(schedule, dict):
        return schedule
    if not isinstance(schedule, str):
        return None

    raw = schedule.strip()
    if not raw.startswith("{") or not raw.endswith("}"):
        return None

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _looks_like_cron(value: str) -> bool:
    parts = value.split()
    return 5 <= len(parts) <= 7


def _parse_clock(value: str) -> tuple[int, int]:
    try:
        hour, minute = value.split(":", 1)
        return int(hour), int(minute)
    except Exception:
        return 9, 0
