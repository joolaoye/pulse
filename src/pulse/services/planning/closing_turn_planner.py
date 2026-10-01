from typing import List

from pulse.agents import (
    ClosingTurnPlanningAgent,
    ClosingTurnPlanningInput,
)
from pulse.services.planning.duration import allocate_weighted_durations
from pulse.types import (
    ClosingTurnPlan,
    EpisodeClosing,
    Segment,
    SpeakerProfile,
    Turn,
)


class ClosingTurnPlanner:
    def __init__(
        self,
        *,
        closing_turn_planning_agent: ClosingTurnPlanningAgent,
    ) -> None:
        self.closing_turn_planning_agent = closing_turn_planning_agent

    async def plan(
        self,
        *,
        episode_closing: EpisodeClosing,
        final_segment: Segment,
        speakers: List[SpeakerProfile],
    ) -> ClosingTurnPlan:
        output = await self.closing_turn_planning_agent.arun(
            ClosingTurnPlanningInput(
                episode_closing=episode_closing,
                final_segment=final_segment,
                speakers=speakers,
            )
        )

        turn_durations = allocate_weighted_durations(
            weights=[turn.duration_weight for turn in output.turns],
            target_duration_seconds=episode_closing.target_duration_seconds,
        )

        closing_turn_plan = ClosingTurnPlan(
            episode_closing=episode_closing,
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
            closing_turn_plan=closing_turn_plan,
        )

        return closing_turn_plan

    @staticmethod
    def _validate_duration(
        *,
        closing_turn_plan: ClosingTurnPlan,
    ) -> None:
        planned_duration_seconds = sum(
            turn.target_duration_seconds for turn in closing_turn_plan.turns
        )

        target_duration_seconds = closing_turn_plan.episode_closing.target_duration_seconds

        if planned_duration_seconds != target_duration_seconds:
            raise ValueError(
                "Closing turn duration mismatch: "
                f"planned={planned_duration_seconds}, "
                f"target={target_duration_seconds}."
            )
