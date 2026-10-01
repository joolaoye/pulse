from dataclasses import dataclass
from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    GenerateScriptUpdate,
    WorkflowState,
)
from pulse.services.scripting import ScriptGenerator
from pulse.types import (
    EpisodeScript,
    PodcastProfile,
    ProcessedSignal,
    SpeakerProfile,
    TurnPlan,
)


@dataclass(frozen=True)
class _GenerateScriptNodeInput:
    turn_plan: TurnPlan
    speakers: List[SpeakerProfile]
    signals: List[ProcessedSignal]
    podcast_profile: PodcastProfile


class GenerateScriptNode(
    BaseNode[
        WorkflowState,
        _GenerateScriptNodeInput,
        EpisodeScript,
        GenerateScriptUpdate,
    ],
):
    name = "generate_script"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        script_generator: ScriptGenerator,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.script_generator = script_generator

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> _GenerateScriptNodeInput:
        if "turn_plan" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="turn_plan",
            )

        if "speakers" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="speakers",
            )

        if "processed_signals_by_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="processed_signals_by_id",
            )

        if "podcast_profile" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="podcast_profile",
            )

        return _GenerateScriptNodeInput(
            turn_plan=state["turn_plan"],
            speakers=state["speakers"],
            signals=list(state["processed_signals_by_id"].values()),
            podcast_profile=state["podcast_profile"],
        )

    async def _execute(
        self,
        *,
        input_data: _GenerateScriptNodeInput,
    ) -> EpisodeScript:
        return await self.script_generator.generate(
            turn_plan=input_data.turn_plan,
            speakers=input_data.speakers,
            signals=input_data.signals,
            podcast_profile=input_data.podcast_profile,
        )

    def _build_state_update(
        self,
        *,
        output_data: EpisodeScript,
    ) -> GenerateScriptUpdate:
        return {
            "episode_script": output_data,
        }

    def _summarize_input(
        self,
        *,
        input_data: _GenerateScriptNodeInput,
    ) -> Dict[str, object]:
        return {
            "speaker_count": len(input_data.speakers),
            "signal_count": len(input_data.signals),
        }

    def _summarize_output(
        self,
        *,
        output_data: EpisodeScript,
    ) -> Dict[str, object]:
        return {
            "script_turn_count": len(output_data.turns),
        }
