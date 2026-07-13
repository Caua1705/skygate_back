from datetime import datetime, timedelta, timezone

from src.utils.time import calculate_free_time_minutes


def test_free_time_supports_different_timezone_offsets():
    now = datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc)
    boarding_time = datetime(2026, 7, 13, 13, 0, tzinfo=timezone(timedelta(hours=-3)))

    result = calculate_free_time_minutes(boarding_time, estimated_time_minutes=15, now=now)

    assert result == 45

