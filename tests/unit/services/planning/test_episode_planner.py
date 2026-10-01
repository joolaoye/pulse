import pytest

from pulse.services.planning.episode_planner import EpisodePlanner
from pulse.types import (
    Beat,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    EpisodeBody,
    EpisodeClosing,
    EpisodeOpening,
    ProcessedSignal,
    Segment,
    Theme,
    ThemedSignalCluster,
)


def _signal() -> ProcessedSignal:
    return ProcessedSignal(
        signal_id="signal-a",
        title="Signal",
        markdown_context="Signal",
        relevance_score=0.8,
        source="x",
    )


def _cluster() -> ThemedSignalCluster:
    return ThemedSignalCluster(
        cluster_id=1,
        relevance_score=0.8,
        theme=Theme(title="Theme", summary="Summary"),
        signal_ids=["signal-a"],
    )


def _body(duration_seconds: int) -> EpisodeBody:
    return EpisodeBody(
        segments=[
            Segment(
                title="Segment",
                narrative_goal="Goal",
                target_duration_seconds=duration_seconds,
                beats=[
                    Beat(
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
                        target_duration_seconds=duration_seconds,
                    )
                ],
            )
        ]
    )


class _BodyPlanner:
    def __init__(self, duration_seconds: int | None = None) -> None:
        self.duration_seconds = duration_seconds
        self.calls = []

    async def plan(
        self,
        *,
        themed_signal_clusters,
        processed_signals,
        target_body_duration_seconds: int,
    ):
        self.calls.append((themed_signal_clusters, processed_signals, target_body_duration_seconds))
        return _body(self.duration_seconds or target_body_duration_seconds)


class _OpeningPlanner:
    def __init__(self) -> None:
        self.calls = []

    async def plan(self, *, episode_body: EpisodeBody, target_duration_seconds: int):
        self.calls.append((episode_body, target_duration_seconds))
        return EpisodeOpening(
            target_duration_seconds=target_duration_seconds,
            objective="Objective",
            hook_strategy="Hook",
            podcast_introduction_goal="Introduce the show",
            speaker_introduction_goal="Introduce the speakers",
            listener_promise="Promise",
            transition_goal="Transition",
        )


class _ClosingPlanner:
    def __init__(self) -> None:
        self.calls = []

    async def plan(self, *, episode_body: EpisodeBody, target_duration_seconds: int):
        self.calls.append((episode_body, target_duration_seconds))
        return EpisodeClosing(
            target_duration_seconds=target_duration_seconds,
            objective="Objective",
            resolution_strategy="Resolve",
            final_takeaway="Takeaway",
            closing_goal="Close",
        )


async def test_episode_plan_reserves_opening_and_closing_time() -> None:
    clusters = [_cluster()]
    signals = [_signal()]
    body_planner = _BodyPlanner()
    opening_planner = _OpeningPlanner()
    closing_planner = _ClosingPlanner()

    episode_plan = await EpisodePlanner(
        body_planner=body_planner,
        opening_planner=opening_planner,
        closing_planner=closing_planner,
    ).plan(
        themed_signal_clusters=clusters,
        processed_signals=signals,
        target_episode_duration_seconds=300,
    )

    assert body_planner.calls == [(clusters, signals, 270)]
    assert opening_planner.calls[0][1] == 15
    assert closing_planner.calls[0][1] == 15
    assert opening_planner.calls[0][0] is closing_planner.calls[0][0]
    assert episode_plan.total_duration_seconds == 300
    assert episode_plan.body.segments[0].beats[0].primary_signal_id == "signal-a"


async def test_episode_plan_rejects_a_duration_mismatch() -> None:
    with pytest.raises(ValueError):
        await EpisodePlanner(
            body_planner=_BodyPlanner(duration_seconds=100),
            opening_planner=_OpeningPlanner(),
            closing_planner=_ClosingPlanner(),
        ).plan(
            themed_signal_clusters=[_cluster()],
            processed_signals=[_signal()],
            target_episode_duration_seconds=300,
        )
