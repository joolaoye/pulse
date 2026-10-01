from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pulse.infrastructure.db.d1 import DatabaseClient
from pulse.types import PodcastPipelineSchedule

GET_PODCAST_PIPELINE_SCHEDULE_QUERY = """
SELECT
    pipeline_id,
    local_time,
    timezone,
    next_run_at,
    last_dispatched_at
FROM podcast_pipeline_schedule
WHERE pipeline_id = ?1;
"""


UPSERT_PODCAST_PIPELINE_SCHEDULE_QUERY = """
INSERT INTO podcast_pipeline_schedule (
    pipeline_id,
    local_time,
    timezone,
    next_run_at,
    last_dispatched_at
)
VALUES (
    ?1,
    ?2,
    ?3,
    ?4,
    ?5
)
ON CONFLICT (pipeline_id)
DO UPDATE SET
    local_time = excluded.local_time,
    timezone = excluded.timezone,
    next_run_at = excluded.next_run_at,
    updated_at = strftime(
        '%Y-%m-%dT%H:%M:%fZ',
        'now'
    );
"""


REMOVE_PODCAST_PIPELINE_SCHEDULE_QUERY = """
DELETE FROM podcast_pipeline_schedule
WHERE pipeline_id = ?1
RETURNING pipeline_id;
"""


LIST_DUE_PODCAST_PIPELINE_SCHEDULES_QUERY = """
SELECT
    schedule.pipeline_id,
    schedule.local_time,
    schedule.timezone,
    schedule.next_run_at,
    schedule.last_dispatched_at
FROM podcast_pipeline_schedule AS schedule
JOIN podcast_pipeline AS pipeline
    ON pipeline.pipeline_id = schedule.pipeline_id
WHERE
    schedule.next_run_at <= ?1
    AND pipeline.enabled = 1
ORDER BY
    schedule.next_run_at ASC,
    schedule.pipeline_id ASC;
"""


ADVANCE_PODCAST_PIPELINE_SCHEDULE_QUERY = """
UPDATE podcast_pipeline_schedule
SET
    next_run_at = ?3,
    last_dispatched_at = ?4,
    updated_at = strftime(
        '%Y-%m-%dT%H:%M:%fZ',
        'now'
    )
WHERE
    pipeline_id = ?1
    AND next_run_at = ?2
RETURNING pipeline_id;
"""


class PodcastPipelineScheduleRepository:
    def __init__(
        self,
        *,
        db_client: DatabaseClient,
    ) -> None:
        self.db_client = db_client

    async def get(
        self,
        *,
        pipeline_id: str,
    ) -> Optional[PodcastPipelineSchedule]:
        rows = await self.db_client.query(
            sql=GET_PODCAST_PIPELINE_SCHEDULE_QUERY,
            params=[pipeline_id],
        )

        if not rows:
            return None

        return self._deserialize_schedule(
            row=rows[0],
        )

    async def upsert(
        self,
        *,
        schedule: PodcastPipelineSchedule,
    ) -> None:
        await self.db_client.execute(
            sql=UPSERT_PODCAST_PIPELINE_SCHEDULE_QUERY,
            params=self._serialize_schedule(
                schedule=schedule,
            ),
        )

    async def remove(
        self,
        *,
        pipeline_id: str,
    ) -> bool:
        rows = await self.db_client.query(
            sql=REMOVE_PODCAST_PIPELINE_SCHEDULE_QUERY,
            params=[pipeline_id],
        )

        return bool(rows)

    async def list_due(
        self,
        *,
        cutoff: datetime,
    ) -> List[PodcastPipelineSchedule]:
        rows = await self.db_client.query(
            sql=LIST_DUE_PODCAST_PIPELINE_SCHEDULES_QUERY,
            params=[
                self._serialize_utc_datetime(
                    value=cutoff,
                ),
            ],
        )

        return [
            self._deserialize_schedule(
                row=row,
            )
            for row in rows
        ]

    async def advance_occurrence(
        self,
        *,
        pipeline_id: str,
        expected_next_run_at: datetime,
        next_run_at: datetime,
        dispatched_at: datetime,
    ) -> bool:
        rows = await self.db_client.query(
            sql=ADVANCE_PODCAST_PIPELINE_SCHEDULE_QUERY,
            params=[
                pipeline_id,
                self._serialize_utc_datetime(
                    value=expected_next_run_at,
                ),
                self._serialize_utc_datetime(
                    value=next_run_at,
                ),
                self._serialize_utc_datetime(
                    value=dispatched_at,
                ),
            ],
        )

        return bool(rows)

    @classmethod
    def _serialize_schedule(
        cls,
        *,
        schedule: PodcastPipelineSchedule,
    ) -> List[Any]:
        last_dispatched_at = (
            cls._serialize_utc_datetime(
                value=schedule.last_dispatched_at,
            )
            if schedule.last_dispatched_at is not None
            else None
        )

        return [
            schedule.pipeline_id,
            schedule.local_time.strftime("%H:%M"),
            schedule.timezone,
            cls._serialize_utc_datetime(
                value=schedule.next_run_at,
            ),
            last_dispatched_at,
        ]

    @staticmethod
    def _deserialize_schedule(
        *,
        row: Dict[str, Any],
    ) -> PodcastPipelineSchedule:
        return PodcastPipelineSchedule.model_validate(row)

    @staticmethod
    def _serialize_utc_datetime(
        *,
        value: datetime,
    ) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Schedule timestamps must be timezone-aware.")

        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace(
                "+00:00",
                "Z",
            )
        )
