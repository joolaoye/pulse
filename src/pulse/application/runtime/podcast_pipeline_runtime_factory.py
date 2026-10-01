from dataclasses import dataclass

from pulse.application.execution.errors import (
    PodcastPipelineDisabledError,
    PodcastPipelineNotFoundError,
)
from pulse.infrastructure.db.d1 import D1Client
from pulse.infrastructure.db.repositories import (
    PodcastPipelineRepository,
    PodcastShowRepository,
    SignalRepository,
)
from pulse.infrastructure.embeddings.voyage import VoyageEmbeddingProvider
from pulse.infrastructure.vector.repositories import EmbeddedSignalRepository
from pulse.infrastructure.vector.vectorize import VectorizeClient
from pulse.services.ingestion import ExactDeduplicator, Ingestor
from pulse.services.interests import InterestEmbedder
from pulse.services.retrieval import XRetriever
from pulse.services.signals import (
    PostProcessor,
    SemanticDeduplicator,
    SignalCommitter,
    SignalEmbedder,
    SignalFilter,
    SignalScorer,
    XSignalAugmenter,
)
from pulse.services.signals.semantic_processor import SemanticProcessor
from pulse.types import PodcastPipeline, PodcastShow


@dataclass(frozen=True)
class PodcastPipelineRuntime:
    pipeline: PodcastPipeline
    podcast_show: PodcastShow
    ingestor: Ingestor
    semantic_processor: SemanticProcessor
    post_processor: PostProcessor
    signal_committer: SignalCommitter


class PodcastPipelineRuntimeFactory:
    def __init__(
        self,
        *,
        podcast_pipeline_repository: PodcastPipelineRepository,
        podcast_show_repository: PodcastShowRepository,
        d1_client: D1Client,
        vectorize_client: VectorizeClient,
        embedding_provider: VoyageEmbeddingProvider,
        x_retriever: XRetriever,
        vectorize_index_name: str,
    ) -> None:
        self.podcast_pipeline_repository = podcast_pipeline_repository
        self.podcast_show_repository = podcast_show_repository
        self.d1_client = d1_client
        self.vectorize_client = vectorize_client
        self.embedding_provider = embedding_provider
        self.x_retriever = x_retriever
        self.vectorize_index_name = vectorize_index_name

    async def create(
        self,
        *,
        pipeline_id: str,
    ) -> PodcastPipelineRuntime:
        pipeline = await self.podcast_pipeline_repository.get(
            pipeline_id=pipeline_id,
        )

        if pipeline is None:
            raise PodcastPipelineNotFoundError(f"Podcast pipeline {pipeline_id!r} does not exist.")

        if not pipeline.enabled:
            raise PodcastPipelineDisabledError(f"Podcast pipeline {pipeline_id!r} is disabled.")

        podcast_show = await self.podcast_show_repository.get(
            show_id=pipeline.show_id,
        )

        if podcast_show is None:
            raise ValueError(f"Podcast show {pipeline.show_id!r} does not exist.")

        return PodcastPipelineRuntime(
            pipeline=pipeline,
            podcast_show=podcast_show,
            ingestor=self._build_ingestor(
                pipeline_id=pipeline.pipeline_id,
            ),
            semantic_processor=self._build_semantic_processor(
                pipeline_id=pipeline.pipeline_id,
            ),
            post_processor=await self._build_post_processor(
                pipeline=pipeline,
            ),
            signal_committer=self._build_signal_committer(
                pipeline_id=pipeline.pipeline_id,
            ),
        )

    def _build_ingestor(
        self,
        *,
        pipeline_id: str,
    ) -> Ingestor:
        return Ingestor(
            exact_deduplicator=ExactDeduplicator(
                d1_client=self.d1_client,
                pipeline_id=pipeline_id,
            )
        )

    def _build_semantic_processor(
        self,
        *,
        pipeline_id: str,
    ) -> SemanticProcessor:
        return SemanticProcessor(
            signal_embedder=SignalEmbedder(
                embedding_provider=self.embedding_provider,
            ),
            semantic_deduplicator=SemanticDeduplicator(
                vectorize_client=self.vectorize_client,
                pipeline_id=pipeline_id,
            ),
            index_name=self.vectorize_index_name,
        )

    async def _build_post_processor(
        self,
        *,
        pipeline: PodcastPipeline,
    ) -> PostProcessor:
        embedded_interests = await InterestEmbedder(
            embedding_provider=self.embedding_provider,
        ).embed_markdown(
            markdown=pipeline.interest_profile_markdown,
        )

        return PostProcessor(
            signal_scorer=SignalScorer(),
            signal_filter=SignalFilter(),
            signal_augmenter=XSignalAugmenter(
                x_retriever=self.x_retriever,
            ),
            embedded_interests=embedded_interests,
        )

    def _build_signal_committer(
        self,
        *,
        pipeline_id: str,
    ) -> SignalCommitter:
        return SignalCommitter(
            signal_repository=SignalRepository(
                db_client=self.d1_client,
                pipeline_id=pipeline_id,
            ),
            embedded_signal_repository=EmbeddedSignalRepository(
                vectorize_client=self.vectorize_client,
                index_name=self.vectorize_index_name,
                pipeline_id=pipeline_id,
            ),
        )
