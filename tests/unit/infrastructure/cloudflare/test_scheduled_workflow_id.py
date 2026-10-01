from datetime import (
    datetime,
    timedelta,
    timezone,
)

from pulse.infrastructure.cloudflare import (
    build_scheduled_workflow_id,
)


def test_scheduled_workflow_id_is_deterministic() -> None:
    scheduled_for = datetime(
        2026,
        9,
        25,
        13,
        0,
        tzinfo=timezone.utc,
    )

    first = build_scheduled_workflow_id(
        pipeline_id="pulse-main",
        scheduled_for=scheduled_for,
    )

    second = build_scheduled_workflow_id(
        pipeline_id="pulse-main",
        scheduled_for=scheduled_for,
    )

    assert first == second


def test_scheduled_workflow_id_normalizes_same_instant() -> None:
    utc_time = datetime(
        2026,
        9,
        25,
        13,
        0,
        tzinfo=timezone.utc,
    )

    local_time = datetime(
        2026,
        9,
        25,
        8,
        0,
        tzinfo=timezone(
            timedelta(
                hours=-5,
            )
        ),
    )

    assert build_scheduled_workflow_id(
        pipeline_id="pulse-main",
        scheduled_for=utc_time,
    ) == build_scheduled_workflow_id(
        pipeline_id="pulse-main",
        scheduled_for=local_time,
    )


def test_scheduled_workflow_id_differs_by_occurrence() -> None:
    first = build_scheduled_workflow_id(
        pipeline_id="pulse-main",
        scheduled_for=datetime(
            2026,
            9,
            25,
            13,
            0,
            tzinfo=timezone.utc,
        ),
    )

    second = build_scheduled_workflow_id(
        pipeline_id="pulse-main",
        scheduled_for=datetime(
            2026,
            9,
            26,
            13,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert first != second


def test_scheduled_workflow_id_differs_by_pipeline() -> None:
    scheduled_for = datetime(
        2026,
        9,
        25,
        13,
        0,
        tzinfo=timezone.utc,
    )

    assert build_scheduled_workflow_id(
        pipeline_id="pipeline-a",
        scheduled_for=scheduled_for,
    ) != build_scheduled_workflow_id(
        pipeline_id="pipeline-b",
        scheduled_for=scheduled_for,
    )
