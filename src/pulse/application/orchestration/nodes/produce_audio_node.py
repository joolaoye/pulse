from dataclasses import dataclass
from typing import Dict, List

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    ProduceAudioUpdate,
    WorkflowState,
)
from pulse.services.audio import AudioProducer
from pulse.types import (
    EpisodeScript,
    SpeakerVoiceBinding,
    StoredEpisodeAudio,
)


@dataclass(frozen=True)
class _ProduceAudioNodeInput:
    episode_script: EpisodeScript
    speaker_voice_bindings: List[SpeakerVoiceBinding]
    show_id: str
    episode_id: str


class ProduceAudioNode(
    BaseNode[
        WorkflowState,
        _ProduceAudioNodeInput,
        StoredEpisodeAudio,
        ProduceAudioUpdate,
    ],
):
    name = "produce_audio"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        audio_producer: AudioProducer,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.audio_producer = audio_producer

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> _ProduceAudioNodeInput:
        if "episode_script" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="episode_script",
            )

        if "speaker_voice_bindings" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="speaker_voice_bindings",
            )

        if "podcast_show" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="podcast_show",
            )

        if "episode_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="episode_id",
            )

        return _ProduceAudioNodeInput(
            episode_script=state["episode_script"],
            speaker_voice_bindings=state["speaker_voice_bindings"],
            show_id=state["podcast_show"].show_id,
            episode_id=state["episode_id"],
        )

    async def _execute(
        self,
        *,
        input_data: _ProduceAudioNodeInput,
    ) -> StoredEpisodeAudio:
        return await self.audio_producer.produce(
            episode_script=input_data.episode_script,
            speaker_voice_bindings=input_data.speaker_voice_bindings,
            show_id=input_data.show_id,
            episode_id=input_data.episode_id,
        )

    def _build_state_update(
        self,
        *,
        output_data: StoredEpisodeAudio,
    ) -> ProduceAudioUpdate:
        return {
            "stored_episode_audio": output_data,
        }

    def _summarize_input(
        self,
        *,
        input_data: _ProduceAudioNodeInput,
    ) -> Dict[str, object]:
        return {
            "script_turn_count": len(input_data.episode_script.turns),
            "speaker_voice_binding_count": len(input_data.speaker_voice_bindings),
            "show_id": input_data.show_id,
            "episode_id": input_data.episode_id,
        }

    def _summarize_output(
        self,
        *,
        output_data: StoredEpisodeAudio,
    ) -> Dict[str, object]:
        return {
            "output_format": output_data.output_format,
            "duration_seconds": output_data.duration_seconds,
            "size_bytes": output_data.size_bytes,
            "turn_timing_count": len(output_data.turn_timings),
        }
