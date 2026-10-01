from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from zoneinfo import (
    ZoneInfo,
    ZoneInfoNotFoundError,
)


def next_daily_occurrence(
    *,
    local_time: time,
    timezone_name: str,
    after: datetime,
) -> datetime:
    if local_time.tzinfo is not None:
        raise ValueError("Schedule time must be a local wall-clock time.")

    if local_time.second != 0 or local_time.microsecond != 0:
        raise ValueError("Schedule time must use minute precision.")

    if after.tzinfo is None or after.utcoffset() is None:
        raise ValueError("Schedule cutoff must be timezone-aware.")

    try:
        zone = ZoneInfo(timezone_name)

    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: '{timezone_name}'.") from exc

    after_utc = after.astimezone(timezone.utc)

    local_after = after_utc.astimezone(zone)

    candidate_date = local_after.date()

    while True:
        candidate = _resolve_local_datetime(
            candidate_date=candidate_date,
            local_time=local_time,
            zone=zone,
        )

        candidate_utc = candidate.astimezone(timezone.utc)

        if candidate_utc > after_utc:
            return candidate_utc

        candidate_date += timedelta(days=1)


def _resolve_local_datetime(
    *,
    candidate_date: date,
    local_time: time,
    zone: ZoneInfo,
) -> datetime:
    naive = datetime.combine(
        candidate_date,
        local_time,
    )

    first = naive.replace(
        tzinfo=zone,
        fold=0,
    )

    second = naive.replace(
        tzinfo=zone,
        fold=1,
    )

    first_round_trip = first.astimezone(timezone.utc).astimezone(zone)

    second_round_trip = second.astimezone(timezone.utc).astimezone(zone)

    if first_round_trip.replace(tzinfo=None) == naive:
        return first

    if second_round_trip.replace(tzinfo=None) == naive:
        return second

    forward_candidates = [
        candidate
        for candidate in (
            first_round_trip,
            second_round_trip,
        )
        if (candidate.replace(tzinfo=None) > naive)
    ]

    if not forward_candidates:
        raise ValueError("Could not resolve local schedule time.")

    return min(
        forward_candidates,
        key=lambda candidate: candidate.replace(tzinfo=None),
    )
