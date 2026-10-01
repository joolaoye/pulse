from dataclasses import dataclass
from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    PlanEpisodeUpdate,
    WorkflowState,
)
from pulse.services.planning import Planner
from pulse.types import (
    ProcessedSignal,
    SpeakerProfile,
    ThemedSignalCluster,
    TurnPlan,
)


@dataclass(frozen=True)
class _PlanEpisodeNodeInput:
    themed_signal_clusters: List[ThemedSignalCluster]
    processed_signals: List[ProcessedSignal]
    target_episode_duration_seconds: int
    speakers: List[SpeakerProfile]


class PlanEpisodeNode(
    BaseNode[
        WorkflowState,
        _PlanEpisodeNodeInput,
        TurnPlan,
        PlanEpisodeUpdate,
    ],
):
    name = "plan_episode"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        planner: Planner,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.planner = planner

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> _PlanEpisodeNodeInput:
        if "themed_signal_clusters" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="themed_signal_clusters",
            )

        if "processed_signals_by_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="processed_signals_by_id",
            )

        if "target_episode_duration_seconds" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="target_episode_duration_seconds",
            )

        if "speakers" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="speakers",
            )

        return _PlanEpisodeNodeInput(
            themed_signal_clusters=state["themed_signal_clusters"],
            processed_signals=list(state["processed_signals_by_id"].values()),
            target_episode_duration_seconds=state["target_episode_duration_seconds"],
            speakers=state["speakers"],
        )

    async def _execute(
        self,
        *,
        input_data: _PlanEpisodeNodeInput,
    ) -> TurnPlan:
        return await self.planner.plan(
            themed_signal_clusters=input_data.themed_signal_clusters,
            processed_signals=input_data.processed_signals,
            target_episode_duration_seconds=(input_data.target_episode_duration_seconds),
            speakers=input_data.speakers,
        )

    def _build_state_update(
        self,
        *,
        output_data: TurnPlan,
    ) -> PlanEpisodeUpdate:
        return {
            "turn_plan": output_data,
        }

    def _summarize_input(
        self,
        *,
        input_data: _PlanEpisodeNodeInput,
    ) -> Dict[str, object]:
        return {
            "themed_signal_cluster_count": len(input_data.themed_signal_clusters),
            "processed_signal_count": len(input_data.processed_signals),
            "speaker_count": len(input_data.speakers),
            "target_episode_duration_seconds": (input_data.target_episode_duration_seconds),
        }

    def _summarize_output(
        self,
        *,
        output_data: TurnPlan,
    ) -> Dict[str, object]:
        return {
            "turn_plan_created": True,
        }
