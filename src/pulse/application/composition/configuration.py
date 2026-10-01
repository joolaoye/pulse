from pulse.application.runtime.podcast_pipeline_runtime_factory import (
    PodcastPipelineRuntimeFactory,
)
from pulse.infrastructure.db.d1 import D1Client
from pulse.infrastructure.db.repositories import (
    PodcastPipelineRepository,
    PodcastShowRepository,
)
from pulse.infrastructure.embeddings.voyage import VoyageEmbeddingProvider
from pulse.infrastructure.vector.vectorize import VectorizeClient
from pulse.services.retrieval import XRetriever


def create_podcast_pipeline_runtime_factory(
    *,
    d1_client: D1Client,
    vectorize_client: VectorizeClient,
    embedding_provider: VoyageEmbeddingProvider,
    x_retriever: XRetriever,
    vectorize_index_name: str,
) -> PodcastPipelineRuntimeFactory:
    return PodcastPipelineRuntimeFactory(
        podcast_pipeline_repository=PodcastPipelineRepository(
            db_client=d1_client,
        ),
        podcast_show_repository=PodcastShowRepository(
            db_client=d1_client,
        ),
        d1_client=d1_client,
        vectorize_client=vectorize_client,
        embedding_provider=embedding_provider,
        x_retriever=x_retriever,
        vectorize_index_name=vectorize_index_name,
    )
