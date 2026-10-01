import pytest

from pulse.services.planning.body_planner import BodyPlanner
from pulse.types import (
    Beat,
    BodyOutline,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    ProcessedSignal,
    Segment,
    SegmentOutline,
    Theme,
    ThemedSignalCluster,
)


def _signal(signal_id: str) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=signal_id,
        relevance_score=0.8,
        source="x",
    )


def _cluster(cluster_id: int, signal_ids: list[str]) -> ThemedSignalCluster:
    return ThemedSignalCluster(
        cluster_id=cluster_id,
        relevance_score=0.7,
        theme=Theme(title=f"Theme {cluster_id}", summary="Summary"),
        signal_ids=signal_ids,
    )


def _beat() -> Beat:
    return Beat(
        primary_signal_id="signal-a",
        title="Beat",
        purpose="Purpose",
        conversation_angle=ConversationAngle(
            title="Angle",
            perspective="Developer",
            central_thesis="Thesis",
            narrative_hook="Hook",
            listener_value="Value",
            tension="Tension",
        ),
        questions=ConversationQuestions(
            questions=[ConversationQuestion(question="Why?", rationale="Because")]
        ),
        target_duration_seconds=5,
    )


class _OutlinePlanner:
    def __init__(self, outline: BodyOutline) -> None:
        self.outline = outline

    async def plan(
        self, *, themed_signal_clusters, processed_signals, target_body_duration_seconds: int
    ):
        self.args = (themed_signal_clusters, processed_signals, target_body_duration_seconds)
        return self.outline


class _SegmentPlanner:
    def __init__(self) -> None:
        self.calls = []

    async def plan(self, *, segment_outline: SegmentOutline, relevant_signals, previous_segment):
        segment = Segment(
            title=segment_outline.title,
            narrative_goal=segment_outline.narrative_goal,
            target_duration_seconds=segment_outline.target_duration_seconds,
            beats=[_beat()],
        )
        self.calls.append((segment_outline, relevant_signals, previous_segment, segment))
        return segment


async def test_body_resolves_each_segment_from_its_cluster_signals() -> None:
    clusters = [
        _cluster(2, ["signal-b", "signal-a"]),
        _cluster(1, ["signal-c"]),
    ]
    signals = [_signal("signal-a"), _signal("signal-b"), _signal("signal-c")]
    outline = BodyOutline(
        segments=[
            SegmentOutline(
                cluster_id=2,
                title="Second cluster",
                narrative_goal="First segment",
                target_duration_seconds=6,
            ),
            SegmentOutline(
                cluster_id=1,
                title="First cluster",
                narrative_goal="Second segment",
                target_duration_seconds=4,
            ),
        ]
    )
    outline_planner = _OutlinePlanner(outline)
    segment_planner = _SegmentPlanner()

    body = await BodyPlanner(
        body_outline_planner=outline_planner,
        segment_planner=segment_planner,
    ).plan(
        themed_signal_clusters=clusters,
        processed_signals=signals,
        target_body_duration_seconds=10,
    )

    assert outline_planner.args == (clusters, signals, 10)
    assert [signal.signal_id for signal in segment_planner.calls[0][1]] == [
        "signal-b",
        "signal-a",
    ]
    assert [signal.signal_id for signal in segment_planner.calls[1][1]] == ["signal-c"]
    assert segment_planner.calls[0][2] is None
    assert segment_planner.calls[1][2] is segment_planner.calls[0][3]
    assert [segment.title for segment in body.segments] == ["Second cluster", "First cluster"]


async def test_body_rejects_an_outline_cluster_that_was_not_provided() -> None:
    outline_planner = _OutlinePlanner(
        BodyOutline(
            segments=[
                SegmentOutline(
                    cluster_id=99,
                    title="Missing",
                    narrative_goal="Missing",
                    target_duration_seconds=10,
                )
            ]
        )
    )

    with pytest.raises(ValueError):
        await BodyPlanner(
            body_outline_planner=outline_planner,
            segment_planner=_SegmentPlanner(),
        ).plan(
            themed_signal_clusters=[_cluster(1, ["signal-a"])],
            processed_signals=[_signal("signal-a")],
            target_body_duration_seconds=10,
        )
