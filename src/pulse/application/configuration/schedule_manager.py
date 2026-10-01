from datetime import (
    datetime,
    time,
    timezone,
)
from typing import (
    List,
    Optional,
)

from pulse.application.configuration.errors import (
    PodcastPipelineNotFoundError,
    PodcastPipelineScheduleNotFoundError,
)
from pulse.application.configuration.schedule_time import (
    next_daily_occurrence,
)
from pulse.infrastructure.db.repositories import (
    PodcastPipelineRepository,
    PodcastPipelineScheduleRepository,
)
from pulse.types import (
    PodcastPipelineSchedule,
)


class ScheduleManager:
    def __init__(
        self,
        *,
        podcast_pipeline_repository: PodcastPipelineRepository,
        podcast_pipeline_schedule_repository: PodcastPipelineScheduleRepository,
    ) -> None:
        self._podcast_pipeline_repository = podcast_pipeline_repository
        self._podcast_pipeline_schedule_repository = podcast_pipeline_schedule_repository

    async def set(
        self,
        *,
        pipeline_id: str,
        local_time: time,
        timezone_name: str,
        after: Optional[datetime] = None,
    ) -> PodcastPipelineSchedule:
        pipeline_id = self._validate_pipeline_id(
            pipeline_id=pipeline_id,
        )

        await self._require_pipeline(
            pipeline_id=pipeline_id,
        )

        if after is None:
            after = datetime.now(timezone.utc)

        next_run_at = next_daily_occurrence(
            local_time=local_time,
            timezone_name=timezone_name,
            after=after,
        )

        schedule = PodcastPipelineSchedule(
            pipeline_id=pipeline_id,
            local_time=local_time,
            timezone=timezone_name,
            next_run_at=next_run_at,
        )

        await self._podcast_pipeline_schedule_repository.upsert(
            schedule=schedule,
        )

        persisted_schedule = await self._podcast_pipeline_schedule_repository.get(
            pipeline_id=pipeline_id,
        )

        if persisted_schedule is None:
            raise RuntimeError("Podcast pipeline schedule was not persisted.")

        return persisted_schedule

    async def get(
        self,
        *,
        pipeline_id: str,
    ) -> PodcastPipelineSchedule:
        pipeline_id = self._validate_pipeline_id(
            pipeline_id=pipeline_id,
        )

        schedule = await self._podcast_pipeline_schedule_repository.get(
            pipeline_id=pipeline_id,
        )

        if schedule is None:
            raise PodcastPipelineScheduleNotFoundError(
                f"Podcast pipeline '{pipeline_id}' does not have a schedule."
            )

        return schedule

    async def remove(
        self,
        *,
        pipeline_id: str,
    ) -> None:
        pipeline_id = self._validate_pipeline_id(
            pipeline_id=pipeline_id,
        )

        removed = await self._podcast_pipeline_schedule_repository.remove(
            pipeline_id=pipeline_id,
        )

        if not removed:
            raise PodcastPipelineScheduleNotFoundError(
                f"Podcast pipeline '{pipeline_id}' does not have a schedule."
            )

    async def list_due(
        self,
        *,
        cutoff: datetime,
    ) -> List[PodcastPipelineSchedule]:
        return await self._podcast_pipeline_schedule_repository.list_due(
            cutoff=cutoff,
        )

    async def advance_occurrence(
        self,
        *,
        schedule: PodcastPipelineSchedule,
        dispatched_at: datetime,
    ) -> bool:
        next_run_at = next_daily_occurrence(
            local_time=schedule.local_time,
            timezone_name=schedule.timezone,
            after=dispatched_at,
        )

        return await self._podcast_pipeline_schedule_repository.advance_occurrence(
            pipeline_id=schedule.pipeline_id,
            expected_next_run_at=schedule.next_run_at,
            next_run_at=next_run_at,
            dispatched_at=dispatched_at,
        )

    async def _require_pipeline(
        self,
        *,
        pipeline_id: str,
    ) -> None:
        pipeline = await self._podcast_pipeline_repository.get(
            pipeline_id=pipeline_id,
        )

        if pipeline is None:
            raise PodcastPipelineNotFoundError(f"Podcast pipeline '{pipeline_id}' does not exist.")

    @staticmethod
    def _validate_pipeline_id(
        *,
        pipeline_id: str,
    ) -> str:
        pipeline_id = pipeline_id.strip()

        if not pipeline_id:
            raise ValueError("Podcast pipeline ID cannot be empty.")

        return pipeline_id
