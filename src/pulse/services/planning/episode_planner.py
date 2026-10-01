import asyncio
from typing import List

from pulse.services.planning.body_planner import BodyPlanner
from pulse.services.planning.closing_planner import ClosingPlanner
from pulse.services.planning.opening_planner import OpeningPlanner
from pulse.types import (
    EpisodePlan,
    ProcessedSignal,
    ThemedSignalCluster,
)

EPISODE_OPENING_DURATION_RATIO = 0.05
EPISODE_CLOSING_DURATION_RATIO = 0.05


class EpisodePlanner:
    def __init__(
        self,
        *,
        body_planner: BodyPlanner,
        opening_planner: OpeningPlanner,
        closing_planner: ClosingPlanner,
    ) -> None:
        self.body_planner = body_planner
        self.opening_planner = opening_planner
        self.closing_planner = closing_planner

    async def plan(
        self,
        *,
        themed_signal_clusters: List[ThemedSignalCluster],
        processed_signals: List[ProcessedSignal],
        target_episode_duration_seconds: int,
    ) -> EpisodePlan:
        target_opening_duration_seconds = int(
            target_episode_duration_seconds * EPISODE_OPENING_DURATION_RATIO
        )

        target_closing_duration_seconds = int(
            target_episode_duration_seconds * EPISODE_CLOSING_DURATION_RATIO
        )

        target_body_duration_seconds = (
            target_episode_duration_seconds
            - target_opening_duration_seconds
            - target_closing_duration_seconds
        )

        episode_body = await self.body_planner.plan(
            themed_signal_clusters=themed_signal_clusters,
            processed_signals=processed_signals,
            target_body_duration_seconds=target_body_duration_seconds,
        )

        opening, closing = await asyncio.gather(
            self.opening_planner.plan(
                episode_body=episode_body,
                target_duration_seconds=target_opening_duration_seconds,
            ),
            self.closing_planner.plan(
                episode_body=episode_body,
                target_duration_seconds=target_closing_duration_seconds,
            ),
        )

        episode_plan = EpisodePlan(
            opening=opening,
            body=episode_body,
            closing=closing,
        )

        self._validate_episode_duration(
            episode_plan=episode_plan,
            target_episode_duration_seconds=target_episode_duration_seconds,
        )

        return episode_plan

    @staticmethod
    def _validate_episode_duration(
        *,
        episode_plan: EpisodePlan,
        target_episode_duration_seconds: int,
    ) -> None:
        if episode_plan.total_duration_seconds != target_episode_duration_seconds:
            raise ValueError(
                "Episode plan duration does not match the requested target episode duration."
            )
