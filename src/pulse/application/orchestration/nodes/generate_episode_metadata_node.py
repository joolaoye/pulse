from typing import Dict

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    GenerateEpisodeMetadataUpdate,
    WorkflowState,
)
from pulse.services.episode_metadata import EpisodeMetadataGenerator
from pulse.types import (
    EpisodeMetadata,
    EpisodeScript,
)


class GenerateEpisodeMetadataNode(
    BaseNode[
        WorkflowState,
        EpisodeScript,
        EpisodeMetadata,
        GenerateEpisodeMetadataUpdate,
    ],
):
    name = "generate_episode_metadata"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        episode_metadata_generator: EpisodeMetadataGenerator,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.episode_metadata_generator = episode_metadata_generator

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> EpisodeScript:
        if "episode_script" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="episode_script",
            )

        return state["episode_script"]

    async def _execute(
        self,
        *,
        input_data: EpisodeScript,
    ) -> EpisodeMetadata:
        return await self.episode_metadata_generator.generate(
            episode_script=input_data,
        )

    def _build_state_update(
        self,
        *,
        output_data: EpisodeMetadata,
    ) -> GenerateEpisodeMetadataUpdate:
        return {
            "episode_metadata": output_data,
        }

    def _summarize_input(
        self,
        *,
        input_data: EpisodeScript,
    ) -> Dict[str, object]:
        return {
            "script_turn_count": len(input_data.turns),
        }

    def _summarize_output(
        self,
        *,
        output_data: EpisodeMetadata,
    ) -> Dict[str, object]:
        return {
            "episode_metadata_created": True,
        }
