from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from pulse.application.orchestration.logging.node_logger import NodeLogger
from pulse.application.orchestration.nodes.base_node import BaseNode
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import (
    PublishEpisodeUpdate,
    WorkflowState,
)
from pulse.services.publishing import PodcastPublisher
from pulse.types import (
    EpisodeMetadata,
    EpisodePublicationRequest,
    PodcastShow,
    PublicationResult,
    StoredEpisodeAudio,
)


@dataclass(frozen=True)
class _PublishEpisodeNodeInput:
    episode_id: str
    published_at: datetime
    podcast_show: PodcastShow
    episode_metadata: EpisodeMetadata
    stored_episode_audio: StoredEpisodeAudio


class PublishEpisodeNode(
    BaseNode[
        WorkflowState,
        _PublishEpisodeNodeInput,
        PublicationResult,
        PublishEpisodeUpdate,
    ],
):
    name = "publish_episode"

    def __init__(
        self,
        *,
        node_logger: NodeLogger,
        podcast_publisher: PodcastPublisher,
    ) -> None:
        super().__init__(
            node_logger=node_logger,
        )
        self.podcast_publisher = podcast_publisher

    def _read_input(
        self,
        *,
        state: WorkflowState,
    ) -> _PublishEpisodeNodeInput:
        if "episode_id" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="episode_id",
            )

        if "published_at" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="published_at",
            )

        if "podcast_show" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="podcast_show",
            )

        if "episode_metadata" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="episode_metadata",
            )

        if "stored_episode_audio" not in state:
            raise MissingNodeInputError(
                node_name=self.name,
                input_name="stored_episode_audio",
            )

        return _PublishEpisodeNodeInput(
            episode_id=state["episode_id"],
            published_at=state["published_at"],
            podcast_show=state["podcast_show"],
            episode_metadata=state["episode_metadata"],
            stored_episode_audio=state["stored_episode_audio"],
        )

    async def _execute(
        self,
        *,
        input_data: _PublishEpisodeNodeInput,
    ) -> PublicationResult:
        publication_request = EpisodePublicationRequest(
            episode_id=input_data.episode_id,
            show_id=input_data.podcast_show.show_id,
            title=input_data.episode_metadata.title,
            description=input_data.episode_metadata.description,
            published_at=input_data.published_at,
            stored_audio=input_data.stored_episode_audio,
        )

        return await self.podcast_publisher.publish(
            podcast_show=input_data.podcast_show,
            publication_request=publication_request,
        )

    def _build_state_update(
        self,
        *,
        output_data: PublicationResult,
    ) -> PublishEpisodeUpdate:
        return {"publication_result": output_data}

    def _summarize_input(
        self,
        *,
        input_data: _PublishEpisodeNodeInput,
    ) -> Dict[str, object]:
        return {
            "show_id": input_data.podcast_show.show_id,
            "episode_id": input_data.episode_id,
            "audio_size_bytes": input_data.stored_episode_audio.size_bytes,
            "audio_duration_seconds": (input_data.stored_episode_audio.duration_seconds),
        }

    def _summarize_output(
        self,
        *,
        output_data: PublicationResult,
    ) -> Dict[str, object]:
        return {
            "show_id": output_data.show_id,
            "episode_id": output_data.episode_id,
            "guid": output_data.guid,
            "publication_status": "published",
        }
