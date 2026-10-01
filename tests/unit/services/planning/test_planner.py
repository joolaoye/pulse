from pulse.services.planning.planner import Planner
from pulse.types import (
    Beat,
    BeatTurnPlan,
    BodyTurnPlan,
    ClosingTurnPlan,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    EpisodeBody,
    EpisodeClosing,
    EpisodeOpening,
    EpisodePlan,
    OpeningTurnPlan,
    ProcessedSignal,
    Segment,
    SegmentTurnPlan,
    SpeakerProfile,
    Theme,
    ThemedSignalCluster,
    Turn,
    TurnPlan,
)


def _episode_plan() -> EpisodePlan:
    beat = Beat(
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
        target_duration_seconds=270,
    )
    segment = Segment(
        title="Segment",
        narrative_goal="Goal",
        target_duration_seconds=270,
        beats=[beat],
    )
    body = EpisodeBody(segments=[segment])
    return EpisodePlan(
        opening=EpisodeOpening(
            target_duration_seconds=15,
            objective="Objective",
            hook_strategy="Hook",
            podcast_introduction_goal="Show",
            speaker_introduction_goal="Speakers",
            listener_promise="Promise",
            transition_goal="Transition",
        ),
        body=body,
        closing=EpisodeClosing(
            target_duration_seconds=15,
            objective="Objective",
            resolution_strategy="Resolve",
            final_takeaway="Takeaway",
            closing_goal="Close",
        ),
    )


def _turn(seconds: int) -> Turn:
    return Turn(
        speaker_id="host",
        conversational_function="explain",
        editorial_objective="Advance the episode",
        target_duration_seconds=seconds,
    )


def _turn_plan(episode_plan: EpisodePlan) -> TurnPlan:
    segment = episode_plan.body.segments[0]
    return TurnPlan(
        opening=OpeningTurnPlan(
            episode_opening=episode_plan.opening,
            turns=[_turn(15)],
        ),
        body=BodyTurnPlan(
            body=episode_plan.body,
            segment_turn_plans=[
                SegmentTurnPlan(
                    segment=segment,
                    beat_turn_plans=[
                        BeatTurnPlan(beat=segment.beats[0], turns=[_turn(270)]),
                    ],
                )
            ],
        ),
        closing=ClosingTurnPlan(
            episode_closing=episode_plan.closing,
            turns=[_turn(15)],
        ),
    )


class _EpisodePlanner:
    def __init__(self, episode_plan: EpisodePlan) -> None:
        self.episode_plan = episode_plan
        self.calls = []

    async def plan(
        self,
        *,
        themed_signal_clusters,
        processed_signals,
        target_episode_duration_seconds: int,
    ):
        self.calls.append(
            (themed_signal_clusters, processed_signals, target_episode_duration_seconds)
        )
        return self.episode_plan


class _TurnPlanner:
    def __init__(self, turn_plan: TurnPlan) -> None:
        self.turn_plan = turn_plan
        self.calls = []

    async def plan(self, *, episode_plan: EpisodePlan, speakers):
        self.calls.append((episode_plan, speakers))
        return self.turn_plan


async def test_planner_passes_episode_context_then_speakers() -> None:
    episode_plan = _episode_plan()
    turn_plan = _turn_plan(episode_plan)
    clusters = [
        ThemedSignalCluster(
            cluster_id=1,
            relevance_score=0.8,
            theme=Theme(title="Theme", summary="Summary"),
            signal_ids=["signal-a"],
        )
    ]
    signals = [
        ProcessedSignal(
            signal_id="signal-a",
            title="Signal",
            markdown_context="Signal",
            relevance_score=0.8,
            source="x",
        )
    ]
    speakers = [
        SpeakerProfile(
            speaker_id="host",
            display_name="Host",
            podcast_role="Host",
            persona="Curious",
            speaking_style="Direct",
        )
    ]
    episode_planner = _EpisodePlanner(episode_plan)
    turn_planner = _TurnPlanner(turn_plan)

    result = await Planner(
        episode_planner=episode_planner,
        turn_planner=turn_planner,
    ).plan(
        themed_signal_clusters=clusters,
        processed_signals=signals,
        target_episode_duration_seconds=300,
        speakers=speakers,
    )

    assert episode_planner.calls == [(clusters, signals, 300)]
    assert turn_planner.calls == [(episode_plan, speakers)]
    assert result is turn_plan
