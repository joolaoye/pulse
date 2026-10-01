from typing import List

from pulse.agents import (
    BodyTurnPlanningAgent,
    BodyTurnPlanningInput,
)
from pulse.services.planning.duration import allocate_weighted_durations
from pulse.types import (
    Beat,
    BeatTurnPlan,
    BodyTurnPlan,
    EpisodeBody,
    SegmentTurnPlan,
    SpeakerProfile,
    Turn,
)


class BodyTurnPlanner:
    def __init__(
        self,
        *,
        body_turn_planning_agent: BodyTurnPlanningAgent,
    ) -> None:
        self.body_turn_planning_agent = body_turn_planning_agent

    async def plan(
        self,
        *,
        episode_body: EpisodeBody,
        speakers: List[SpeakerProfile],
    ) -> BodyTurnPlan:
        segment_turn_plans: List[SegmentTurnPlan] = []

        for segment in episode_body.segments:
            beat_turn_plans: List[BeatTurnPlan] = [
                await self._plan_beat(
                    beat=beat,
                    speakers=speakers,
                )
                for beat in segment.beats
            ]

            segment_turn_plan = SegmentTurnPlan(
                segment=segment,
                beat_turn_plans=beat_turn_plans,
            )

            self._validate_duration(
                label="Segment",
                planned_duration_seconds=segment_turn_plan.total_duration_seconds,
                target_duration_seconds=segment.target_duration_seconds,
            )

            segment_turn_plans.append(segment_turn_plan)

        body_turn_plan = BodyTurnPlan(
            body=episode_body,
            segment_turn_plans=segment_turn_plans,
        )

        self._validate_duration(
            label="Body",
            planned_duration_seconds=body_turn_plan.total_duration_seconds,
            target_duration_seconds=episode_body.total_duration_seconds,
        )

        return body_turn_plan

    async def _plan_beat(
        self,
        *,
        beat: Beat,
        speakers: List[SpeakerProfile],
    ) -> BeatTurnPlan:
        output = await self.body_turn_planning_agent.arun(
            BodyTurnPlanningInput(
                beat=beat,
                speakers=speakers,
            )
        )

        turn_durations = allocate_weighted_durations(
            weights=[turn.duration_weight for turn in output.turns],
            target_duration_seconds=beat.target_duration_seconds,
        )

        beat_turn_plan = BeatTurnPlan(
            beat=beat,
            turns=[
                Turn(
                    speaker_id=planned_turn.speaker_id,
                    conversational_function=planned_turn.conversational_function,
                    editorial_objective=planned_turn.editorial_objective,
                    target_duration_seconds=duration,
                )
                for planned_turn, duration in zip(
                    output.turns,
                    turn_durations,
                    strict=True,
                )
            ],
        )

        self._validate_duration(
            label="Beat",
            planned_duration_seconds=beat_turn_plan.total_duration_seconds,
            target_duration_seconds=beat.target_duration_seconds,
        )

        return beat_turn_plan

    @staticmethod
    def _validate_duration(
        *,
        label: str,
        planned_duration_seconds: int,
        target_duration_seconds: int,
    ) -> None:
        if planned_duration_seconds != target_duration_seconds:
            raise ValueError(
                f"{label} turn duration mismatch: "
                f"planned={planned_duration_seconds}, "
                f"target={target_duration_seconds}."
            )
