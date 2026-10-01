from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver

from pulse.application.composition.audio import create_audio_producer
from pulse.application.composition.configuration import (
    create_podcast_pipeline_runtime_factory,
)
from pulse.application.composition.grouping import create_signal_group_builder
from pulse.application.composition.infrastructure import WorkflowInfrastructure
from pulse.application.composition.models import ResourceNames
from pulse.application.composition.planning import create_planner
from pulse.application.composition.publishing import create_podcast_publisher
from pulse.application.composition.retrieval import create_x_retriever
from pulse.application.composition.scripting import (
    create_episode_metadata_generator,
    create_script_generator,
)
from pulse.application.runtime.podcast_pipeline_runtime_factory import (
    PodcastPipelineRuntimeFactory,
)
from pulse.services.audio import AudioProducer
from pulse.services.episode_metadata import EpisodeMetadataGenerator
from pulse.services.grouping import SignalGroupBuilder
from pulse.services.planning import Planner
from pulse.services.publishing import PodcastPublisher
from pulse.services.retrieval import XRetriever
from pulse.services.scripting import ScriptGenerator


@dataclass(frozen=True)
class PulseApplication:
    podcast_pipeline_runtime_factory: PodcastPipelineRuntimeFactory
    x_retriever: XRetriever
    signal_group_builder: SignalGroupBuilder
    planner: Planner
    script_generator: ScriptGenerator
    episode_metadata_generator: EpisodeMetadataGenerator
    audio_producer: AudioProducer
    podcast_publisher: PodcastPublisher
    checkpointer: BaseCheckpointSaver


def _require_non_empty(
    *,
    name: str,
    value: str,
) -> str:
    if not value.strip():
        raise ValueError(f"{name} cannot be empty.")

    return value


def assemble_application(
    *,
    infrastructure: WorkflowInfrastructure,
    checkpointer: BaseCheckpointSaver,
    resources: ResourceNames,
    r2_bucket: object | None = None,
) -> PulseApplication:
    _require_non_empty(
        name="Vectorize index name",
        value=resources.vectorize_index_name,
    )
    _require_non_empty(
        name="Podcast bucket name",
        value=resources.podcast_bucket_name,
    )

    x_retriever = create_x_retriever(
        x_client=infrastructure.x_client,
        d1_client=infrastructure.d1_client,
    )

    podcast_pipeline_runtime_factory = create_podcast_pipeline_runtime_factory(
        d1_client=infrastructure.d1_client,
        vectorize_client=infrastructure.vectorize_client,
        embedding_provider=infrastructure.embedding_provider,
        x_retriever=x_retriever,
        vectorize_index_name=resources.vectorize_index_name,
    )

    signal_group_builder = create_signal_group_builder(
        anthropic_provider=infrastructure.anthropic_provider,
    )

    planner = create_planner(
        anthropic_provider=infrastructure.anthropic_provider,
    )

    script_generator = create_script_generator(
        anthropic_provider=infrastructure.anthropic_provider,
    )

    episode_metadata_generator = create_episode_metadata_generator(
        anthropic_provider=infrastructure.anthropic_provider,
    )

    audio_producer = create_audio_producer(
        r2_client=infrastructure.r2_client,
        elevenlabs_dialogue_provider=(infrastructure.elevenlabs_dialogue_provider),
        bucket_name=resources.podcast_bucket_name,
        r2_bucket=r2_bucket,
    )

    podcast_publisher = create_podcast_publisher(
        d1_client=infrastructure.d1_client,
        r2_client=infrastructure.r2_client,
        bucket_name=resources.podcast_bucket_name,
    )

    return PulseApplication(
        podcast_pipeline_runtime_factory=podcast_pipeline_runtime_factory,
        x_retriever=x_retriever,
        signal_group_builder=signal_group_builder,
        planner=planner,
        script_generator=script_generator,
        episode_metadata_generator=episode_metadata_generator,
        audio_producer=audio_producer,
        podcast_publisher=podcast_publisher,
        checkpointer=checkpointer,
    )


@asynccontextmanager
async def assemble_workflow(
    *,
    infrastructure: WorkflowInfrastructure,
    checkpointer: BaseCheckpointSaver,
    resources: ResourceNames,
    r2_bucket: object | None = None,
) -> AsyncIterator[PulseApplication]:
    try:
        yield assemble_application(
            infrastructure=infrastructure,
            checkpointer=checkpointer,
            resources=resources,
            r2_bucket=r2_bucket,
        )
    finally:
        await infrastructure.aclose()
