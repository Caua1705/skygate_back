from datetime import datetime, timezone


def calculate_free_time_minutes(
    boarding_time: datetime | None,
    estimated_time_minutes: float,
    now: datetime | None = None,
) -> float | None:
    if boarding_time is None:
        return None
    current_time = now or datetime.now(timezone.utc)
    minutes_until_boarding = (boarding_time - current_time).total_seconds() / 60
    return round(max(0.0, minutes_until_boarding - estimated_time_minutes), 2)


def is_route_feasible(
    boarding_time: datetime | None,
    total_estimated_time_minutes: float,
    now: datetime | None = None,
) -> bool | None:
    if boarding_time is None:
        return None
    current_time = now or datetime.now(timezone.utc)
    minutes_until_boarding = (boarding_time - current_time).total_seconds() / 60
    return total_estimated_time_minutes <= minutes_until_boarding
