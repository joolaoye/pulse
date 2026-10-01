from pulse.services.planning.segment_planner import SegmentPlanner
from pulse.types import (
    Beat,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    ProcessedSignal,
    Segment,
    SegmentOutline,
    Shortlist,
    Topic,
)


def _signal(signal_id: str) -> ProcessedSignal:
    return ProcessedSignal(
        signal_id=signal_id,
        title=signal_id,
        markdown_context=signal_id,
        relevance_score=0.8,
        source="x",
    )


def _beat(primary_signal_id: str, duration_seconds: int) -> Beat:
    return Beat(
        primary_signal_id=primary_signal_id,
        title=primary_signal_id,
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
        target_duration_seconds=duration_seconds,
    )


class _ShortlistPlanner:
    def __init__(self, topics: list[Topic]) -> None:
        self.topics = topics
        self.calls = []

    async def plan(self, *, segment_outline: SegmentOutline, relevant_signals):
        self.calls.append((segment_outline, relevant_signals))
        return Shortlist(topics=self.topics)


class _BeatPlanner:
    def __init__(self) -> None:
        self.calls = []

    async def plan(
        self, *, topic: Topic, relevant_signals, target_duration_seconds: int, previous_beat
    ):
        beat = _beat(topic.primary_signal_id, target_duration_seconds)
        self.calls.append((topic, relevant_signals, target_duration_seconds, previous_beat, beat))
        return beat


async def test_segment_plans_beats_in_topic_order_with_allocated_durations() -> None:
    outline = SegmentOutline(
        cluster_id=1,
        title="Segment",
        narrative_goal="Develop the cluster",
        target_duration_seconds=5,
    )
    signals = [_signal("signal-a"), _signal("signal-b")]
    topics = [
        Topic(
            primary_signal_id="signal-b",
            editorial_goal="First",
            duration_weight=1,
        ),
        Topic(
            primary_signal_id="signal-a",
            editorial_goal="Second",
            duration_weight=1,
        ),
    ]
    previous = Segment(
        title="Previous",
        narrative_goal="Previous",
        target_duration_seconds=5,
        beats=[_beat("signal-earlier", 5)],
    )
    shortlist_planner = _ShortlistPlanner(topics)
    beat_planner = _BeatPlanner()

    segment = await SegmentPlanner(
        shortlist_planner=shortlist_planner,
        beat_planner=beat_planner,
    ).plan(
        segment_outline=outline,
        relevant_signals=signals,
        previous_segment=previous,
    )

    assert shortlist_planner.calls == [(outline, signals)]
    assert [call[2] for call in beat_planner.calls] == [3, 2]
    assert beat_planner.calls[0][3] is previous.beats[-1]
    assert beat_planner.calls[1][3] is beat_planner.calls[0][4]
    assert [beat.primary_signal_id for beat in segment.beats] == ["signal-b", "signal-a"]
    assert segment.title == "Segment"
    assert segment.target_duration_seconds == 5
