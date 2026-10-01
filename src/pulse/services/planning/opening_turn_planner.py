from typing import List

from pulse.agents import (
    OpeningTurnPlanningAgent,
    OpeningTurnPlanningInput,
)
from pulse.services.planning.duration import allocate_weighted_durations
from pulse.types import (
    EpisodeOpening,
    OpeningTurnPlan,
    Segment,
    SpeakerProfile,
    Turn,
)


class OpeningTurnPlanner:
    def __init__(
        self,
        *,
        opening_turn_planning_agent: OpeningTurnPlanningAgent,
    ) -> None:
        self.opening_turn_planning_agent = opening_turn_planning_agent

    async def plan(
        self,
        *,
        episode_opening: EpisodeOpening,
        first_segment: Segment,
        speakers: List[SpeakerProfile],
    ) -> OpeningTurnPlan:
        output = await self.opening_turn_planning_agent.arun(
            OpeningTurnPlanningInput(
                episode_opening=episode_opening,
                first_segment=first_segment,
                speakers=speakers,
            )
        )

        turn_durations = allocate_weighted_durations(
            weights=[turn.duration_weight for turn in output.turns],
            target_duration_seconds=episode_opening.target_duration_seconds,
        )

        opening_turn_plan = OpeningTurnPlan(
            episode_opening=episode_opening,
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
            opening_turn_plan=opening_turn_plan,
        )

        return opening_turn_plan

    @staticmethod
    def _validate_duration(
        *,
        opening_turn_plan: OpeningTurnPlan,
    ) -> None:
        planned_duration_seconds = sum(
            turn.target_duration_seconds for turn in opening_turn_plan.turns
        )

        target_duration_seconds = opening_turn_plan.episode_opening.target_duration_seconds

        if planned_duration_seconds != target_duration_seconds:
            raise ValueError(
                "Opening turn duration mismatch: "
                f"planned={planned_duration_seconds}, "
                f"target={target_duration_seconds}."
            )
