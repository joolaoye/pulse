from typing import List

from pulse.services.planning.episode_planner import EpisodePlanner
from pulse.services.planning.turn_planner import TurnPlanner
from pulse.types import (
    ProcessedSignal,
    SpeakerProfile,
    ThemedSignalCluster,
    TurnPlan,
)


class Planner:
    def __init__(
        self,
        *,
        episode_planner: EpisodePlanner,
        turn_planner: TurnPlanner,
    ) -> None:
        self.episode_planner = episode_planner
        self.turn_planner = turn_planner

    async def plan(
        self,
        *,
        themed_signal_clusters: List[ThemedSignalCluster],
        processed_signals: List[ProcessedSignal],
        target_episode_duration_seconds: int,
        speakers: List[SpeakerProfile],
    ) -> TurnPlan:
        episode_plan = await self.episode_planner.plan(
            themed_signal_clusters=themed_signal_clusters,
            processed_signals=processed_signals,
            target_episode_duration_seconds=target_episode_duration_seconds,
        )

        return await self.turn_planner.plan(
            episode_plan=episode_plan,
            speakers=speakers,
        )
