from typing import List

from pulse.services.planning.body_turn_planner import BodyTurnPlanner
from pulse.services.planning.closing_turn_planner import ClosingTurnPlanner
from pulse.services.planning.opening_turn_planner import OpeningTurnPlanner
from pulse.types import (
    EpisodePlan,
    SpeakerProfile,
    TurnPlan,
)


class TurnPlanner:
    def __init__(
        self,
        *,
        opening_turn_planner: OpeningTurnPlanner,
        body_turn_planner: BodyTurnPlanner,
        closing_turn_planner: ClosingTurnPlanner,
    ) -> None:
        self.opening_turn_planner = opening_turn_planner
        self.body_turn_planner = body_turn_planner
        self.closing_turn_planner = closing_turn_planner

    async def plan(
        self,
        *,
        episode_plan: EpisodePlan,
        speakers: List[SpeakerProfile],
    ) -> TurnPlan:
        episode_body = episode_plan.body

        if not episode_body.segments:
            raise ValueError("Turn planning requires at least one episode body segment.")

        opening = await self.opening_turn_planner.plan(
            episode_opening=episode_plan.opening,
            first_segment=episode_body.segments[0],
            speakers=speakers,
        )

        body = await self.body_turn_planner.plan(
            episode_body=episode_body,
            speakers=speakers,
        )

        closing = await self.closing_turn_planner.plan(
            episode_closing=episode_plan.closing,
            final_segment=episode_body.segments[-1],
            speakers=speakers,
        )

        turn_plan = TurnPlan(
            opening=opening,
            body=body,
            closing=closing,
        )

        self._validate_duration(
            episode_plan=episode_plan,
            turn_plan=turn_plan,
        )

        return turn_plan

    @staticmethod
    def _validate_duration(
        *,
        episode_plan: EpisodePlan,
        turn_plan: TurnPlan,
    ) -> None:
        if turn_plan.total_duration_seconds != episode_plan.total_duration_seconds:
            raise ValueError(
                "Turn plan duration mismatch: "
                f"planned={turn_plan.total_duration_seconds}, "
                f"target={episode_plan.total_duration_seconds}."
            )
