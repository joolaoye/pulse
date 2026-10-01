from datetime import (
    datetime,
    time,
    timezone,
)
import re
import sqlite3
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
)

import pytest

from pulse.infrastructure.db.repositories import (
    PodcastPipelineScheduleRepository,
)
from pulse.types import (
    PodcastPipelineSchedule,
)


def _normalize_sql(
    sql: str,
) -> str:
    return re.sub(
        r"\?\d+",
        "?",
        sql,
    )


class SqliteDatabaseClient:
    def __init__(
        self,
    ) -> None:
        self.connection = sqlite3.connect(":memory:")

        self.connection.row_factory = sqlite3.Row

        self.connection.execute("PRAGMA foreign_keys = ON;")

    async def query(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> List[Dict[str, Any]]:
        cursor = self.connection.execute(
            _normalize_sql(sql),
            params or [],
        )

        rows = cursor.fetchall()

        self.connection.commit()

        return [dict(row) for row in rows]

    async def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> None:
        self.connection.execute(
            _normalize_sql(sql),
            params or [],
        )

        self.connection.commit()


@pytest.fixture
def db_client() -> SqliteDatabaseClient:
    client = SqliteDatabaseClient()

    client.connection.executescript(
        """
        CREATE TABLE podcast_pipeline (
            pipeline_id TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL
                CHECK (
                    enabled IN (0, 1)
                )
        );

        CREATE TABLE podcast_pipeline_schedule (
            pipeline_id TEXT PRIMARY KEY,
            local_time TEXT NOT NULL,
            timezone TEXT NOT NULL,
            next_run_at TEXT NOT NULL,
            last_dispatched_at TEXT,

            created_at TEXT NOT NULL
                DEFAULT (
                    strftime(
                        '%Y-%m-%dT%H:%M:%fZ',
                        'now'
                    )
                ),

            updated_at TEXT NOT NULL
                DEFAULT (
                    strftime(
                        '%Y-%m-%dT%H:%M:%fZ',
                        'now'
                    )
                ),

            FOREIGN KEY (
                pipeline_id
            )
            REFERENCES podcast_pipeline (
                pipeline_id
            )
            ON UPDATE CASCADE
            ON DELETE CASCADE
        );
        """
    )

    return client


async def create_pipeline(
    *,
    client: SqliteDatabaseClient,
    pipeline_id: str,
    enabled: bool = True,
) -> None:
    await client.execute(
        """
        INSERT INTO podcast_pipeline (
            pipeline_id,
            enabled
        )
        VALUES (
            ?1,
            ?2
        );
        """,
        [
            pipeline_id,
            int(enabled),
        ],
    )


def create_schedule(
    *,
    pipeline_id: str,
    next_run_at: datetime,
    local_time: time = time(
        hour=8,
    ),
) -> PodcastPipelineSchedule:
    return PodcastPipelineSchedule(
        pipeline_id=pipeline_id,
        local_time=local_time,
        timezone="America/Chicago",
        next_run_at=next_run_at,
    )


@pytest.mark.asyncio
async def test_upsert_persists_and_replaces_schedule(
    db_client: SqliteDatabaseClient,
) -> None:
    await create_pipeline(
        client=db_client,
        pipeline_id="pulse-main",
    )

    repository = PodcastPipelineScheduleRepository(
        db_client=db_client,
    )

    await repository.upsert(
        schedule=create_schedule(
            pipeline_id="pulse-main",
            next_run_at=datetime(
                2026,
                9,
                25,
                13,
                0,
                tzinfo=timezone.utc,
            ),
        )
    )

    await repository.upsert(
        schedule=create_schedule(
            pipeline_id="pulse-main",
            local_time=time(
                hour=9,
            ),
            next_run_at=datetime(
                2026,
                9,
                25,
                14,
                0,
                tzinfo=timezone.utc,
            ),
        )
    )

    schedule = await repository.get(
        pipeline_id="pulse-main",
    )

    assert schedule is not None
    assert schedule.local_time == time(
        hour=9,
    )
    assert schedule.next_run_at == datetime(
        2026,
        9,
        25,
        14,
        0,
        tzinfo=timezone.utc,
    )


@pytest.mark.asyncio
async def test_remove_schedule(
    db_client: SqliteDatabaseClient,
) -> None:
    await create_pipeline(
        client=db_client,
        pipeline_id="pulse-main",
    )

    repository = PodcastPipelineScheduleRepository(
        db_client=db_client,
    )

    await repository.upsert(
        schedule=create_schedule(
            pipeline_id="pulse-main",
            next_run_at=datetime(
                2026,
                9,
                25,
                13,
                0,
                tzinfo=timezone.utc,
            ),
        )
    )

    assert await repository.remove(
        pipeline_id="pulse-main",
    )

    assert (
        await repository.get(
            pipeline_id="pulse-main",
        )
        is None
    )


@pytest.mark.asyncio
async def test_list_due_returns_multiple_pipelines_once(
    db_client: SqliteDatabaseClient,
) -> None:
    repository = PodcastPipelineScheduleRepository(
        db_client=db_client,
    )

    for pipeline_id in (
        "pipeline-a",
        "pipeline-b",
    ):
        await create_pipeline(
            client=db_client,
            pipeline_id=pipeline_id,
        )

        await repository.upsert(
            schedule=create_schedule(
                pipeline_id=pipeline_id,
                next_run_at=datetime(
                    2026,
                    9,
                    25,
                    12,
                    0,
                    tzinfo=timezone.utc,
                ),
            )
        )

    due = await repository.list_due(
        cutoff=datetime(
            2026,
            9,
            25,
            13,
            0,
            tzinfo=timezone.utc,
        )
    )

    assert [schedule.pipeline_id for schedule in due] == [
        "pipeline-a",
        "pipeline-b",
    ]


@pytest.mark.asyncio
async def test_stale_advance_does_not_overwrite_changed_schedule(
    db_client: SqliteDatabaseClient,
) -> None:
    await create_pipeline(
        client=db_client,
        pipeline_id="pulse-main",
    )

    repository = PodcastPipelineScheduleRepository(
        db_client=db_client,
    )

    original = datetime(
        2026,
        9,
        25,
        13,
        0,
        tzinfo=timezone.utc,
    )

    await repository.upsert(
        schedule=create_schedule(
            pipeline_id="pulse-main",
            next_run_at=original,
        )
    )

    changed = create_schedule(
        pipeline_id="pulse-main",
        local_time=time(
            hour=10,
        ),
        next_run_at=datetime(
            2026,
            9,
            25,
            15,
            0,
            tzinfo=timezone.utc,
        ),
    )

    await repository.upsert(
        schedule=changed,
    )

    advanced = await repository.advance_occurrence(
        pipeline_id="pulse-main",
        expected_next_run_at=original,
        next_run_at=datetime(
            2026,
            9,
            26,
            13,
            0,
            tzinfo=timezone.utc,
        ),
        dispatched_at=datetime(
            2026,
            9,
            25,
            13,
            5,
            tzinfo=timezone.utc,
        ),
    )

    persisted = await repository.get(
        pipeline_id="pulse-main",
    )

    assert advanced is False
    assert persisted is not None
    assert persisted.local_time == time(
        hour=10,
    )
    assert persisted.next_run_at == changed.next_run_at
