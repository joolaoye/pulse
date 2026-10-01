from typing import List

from pulse.infrastructure.vector import VectorizeClient
from pulse.services.signals.similarity import cosine_similarity
from pulse.types import EmbeddedSignal

DEFAULT_TOP_K = 1
DEFAULT_SIMILARITY_THRESHOLD = 0.85


class SemanticDeduplicator:
    def __init__(
        self,
        *,
        vectorize_client: VectorizeClient,
        pipeline_id: str,
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self.vectorize_client = vectorize_client
        self.pipeline_id = pipeline_id
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def is_duplicate(
        self,
        *,
        index_name: str,
        embedded_signal: EmbeddedSignal,
    ) -> bool:
        matches = await self.vectorize_client.query_vector(
            index_name=index_name,
            vector=embedded_signal.embedding,
            top_k=self.top_k,
            metadata_filter={"pipeline_id": self.pipeline_id},
        )

        if not matches:
            return False

        return matches[0]["score"] >= self.similarity_threshold

    def is_duplicate_within_run(
        self,
        *,
        embedded_signal: EmbeddedSignal,
        accepted_signals: List[EmbeddedSignal],
    ) -> bool:
        return any(
            cosine_similarity(
                embedded_signal.embedding,
                accepted_signal.embedding,
            )
            >= self.similarity_threshold
            for accepted_signal in accepted_signals
        )
