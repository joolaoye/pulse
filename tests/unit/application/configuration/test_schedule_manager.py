from datetime import (
    datetime,
    time,
    timezone,
)
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
)

import pytest

from pulse.application.configuration.schedule_manager import (
    ScheduleManager,
)
from pulse.types import (
    PodcastPipelineSchedule,
)


@pytest.mark.asyncio
async def test_set_calculates_and_persists_next_occurrence() -> None:
    pipeline_repository = AsyncMock()
    schedule_repository = AsyncMock()

    pipeline_repository.get.return_value = SimpleNamespace(
        pipeline_id="pulse-main",
        enabled=True,
    )

    persisted = PodcastPipelineSchedule(
        pipeline_id="pulse-main",
        local_time=time(
            hour=8,
        ),
        timezone="America/Chicago",
        next_run_at=datetime(
            2026,
            9,
            25,
            13,
            0,
            tzinfo=timezone.utc,
        ),
    )

    schedule_repository.get.return_value = persisted

    manager = ScheduleManager(
        podcast_pipeline_repository=pipeline_repository,
        podcast_pipeline_schedule_repository=schedule_repository,
    )

    result = await manager.set(
        pipeline_id="pulse-main",
        local_time=time(
            hour=8,
        ),
        timezone_name="America/Chicago",
        after=datetime(
            2026,
            9,
            25,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )

    persisted_argument = schedule_repository.upsert.await_args.kwargs["schedule"]

    assert persisted_argument.next_run_at == datetime(
        2026,
        9,
        25,
        13,
        0,
        tzinfo=timezone.utc,
    )

    assert result == persisted


@pytest.mark.asyncio
async def test_advance_occurrence_coalesces_missed_days() -> None:
    pipeline_repository = AsyncMock()
    schedule_repository = AsyncMock()

    schedule_repository.advance_occurrence.return_value = True

    manager = ScheduleManager(
        podcast_pipeline_repository=pipeline_repository,
        podcast_pipeline_schedule_repository=schedule_repository,
    )

    schedule = PodcastPipelineSchedule(
        pipeline_id="pulse-main",
        local_time=time(
            hour=8,
        ),
        timezone="America/Chicago",
        next_run_at=datetime(
            2026,
            9,
            21,
            13,
            0,
            tzinfo=timezone.utc,
        ),
    )

    result = await manager.advance_occurrence(
        schedule=schedule,
        dispatched_at=datetime(
            2026,
            9,
            24,
            19,
            0,
            tzinfo=timezone.utc,
        ),
    )

    arguments = schedule_repository.advance_occurrence.await_args.kwargs

    assert result is True

    assert arguments["expected_next_run_at"] == schedule.next_run_at

    assert arguments["next_run_at"] == datetime(
        2026,
        9,
        25,
        13,
        0,
        tzinfo=timezone.utc,
    )
