from datetime import datetime, timezone

from services.schedule_utils import calculate_next_run_at, format_datetime_for_timezone


def test_daily_schedule_uses_user_timezone():
    base = datetime(2026, 4, 10, 1, 30, tzinfo=timezone.utc)  # 10:30 in Asia/Seoul
    next_run = calculate_next_run_at("daily", last_run_at=base, user_timezone="Asia/Seoul")
    assert next_run == datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc)


def test_weekly_schedule_stays_monday_in_user_timezone():
    base = datetime(2026, 4, 10, 15, 0, tzinfo=timezone.utc)  # Fri 08:00 in Los Angeles
    next_run = calculate_next_run_at("weekly", last_run_at=base, user_timezone="America/Los_Angeles")
    assert next_run == datetime(2026, 4, 13, 16, 0, tzinfo=timezone.utc)  # Mon 09:00 PDT


def test_cron_string_is_interpreted_in_user_timezone():
    base = datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc)  # 09:00 in Asia/Seoul
    next_run = calculate_next_run_at("0 9 * * *", last_run_at=base, user_timezone="Asia/Seoul")
    assert next_run == datetime(2026, 4, 11, 0, 0, tzinfo=timezone.utc)


def test_subject_time_format_is_localized():
    formatted = format_datetime_for_timezone(
        datetime(2026, 4, 9, 9, 0, tzinfo=timezone.utc),
        user_timezone="Asia/Seoul",
    )
    assert "18:00" in formatted
    assert formatted.endswith("KST")
