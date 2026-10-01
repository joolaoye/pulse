from pulse.infrastructure.embeddings import VoyageEmbeddingProvider
from pulse.types import EmbeddedSignal, Signal


class SignalEmbedder:
    def __init__(
        self,
        *,
        embedding_provider: VoyageEmbeddingProvider,
    ) -> None:
        self.embedding_provider = embedding_provider

    async def embed_signal(
        self,
        *,
        signal: Signal,
    ) -> EmbeddedSignal:
        embedding = await self.embedding_provider.embed(signal.content)

        return EmbeddedSignal(
            signal_id=signal.id,
            embedding=embedding,
            embedding_version=self.embedding_provider.model_name,
        )
