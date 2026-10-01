from datetime import (
    datetime,
    time,
    timezone,
)

from pulse.application.configuration.schedule_time import (
    next_daily_occurrence,
)


def test_next_daily_occurrence_before_today() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=8,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            9,
            25,
            12,
            30,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        9,
        25,
        13,
        0,
        tzinfo=timezone.utc,
    )


def test_next_daily_occurrence_after_today() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=8,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            9,
            25,
            13,
            30,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        9,
        26,
        13,
        0,
        tzinfo=timezone.utc,
    )


def test_next_daily_occurrence_is_strictly_after_cutoff() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=8,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            9,
            25,
            13,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        9,
        26,
        13,
        0,
        tzinfo=timezone.utc,
    )


def test_next_daily_occurrence_coalesces_overdue_days() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=8,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            9,
            25,
            18,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        9,
        26,
        13,
        0,
        tzinfo=timezone.utc,
    )


def test_next_daily_occurrence_converts_timezone() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=8,
        ),
        timezone_name="America/Los_Angeles",
        after=datetime(
            2026,
            9,
            25,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        9,
        25,
        15,
        0,
        tzinfo=timezone.utc,
    )


def test_next_daily_occurrence_uses_first_fall_back_occurrence() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=1,
            minute=30,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            11,
            1,
            5,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        11,
        1,
        6,
        30,
        tzinfo=timezone.utc,
    )


def test_next_daily_occurrence_does_not_run_twice_on_fall_back() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=1,
            minute=30,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            11,
            1,
            7,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        11,
        2,
        7,
        30,
        tzinfo=timezone.utc,
    )


def test_next_daily_occurrence_moves_forward_across_spring_gap() -> None:
    result = next_daily_occurrence(
        local_time=time(
            hour=2,
            minute=30,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            3,
            8,
            6,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert result == datetime(
        2026,
        3,
        8,
        8,
        30,
        tzinfo=timezone.utc,
    )
