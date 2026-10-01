import hashlib
from typing import Protocol

from pulse.infrastructure.vector import VectorizeClient
from pulse.types import EmbeddedSignal, Signal


class EmbeddedSignalRepositoryProtocol(Protocol):
    async def persist(
        self,
        *,
        signal: Signal,
        embedded_signal: EmbeddedSignal,
    ) -> None: ...


class EmbeddedSignalRepository:
    def __init__(
        self,
        *,
        vectorize_client: VectorizeClient,
        index_name: str,
        pipeline_id: str,
    ) -> None:
        self.vectorize_client = vectorize_client
        self.index_name = index_name
        self.pipeline_id = pipeline_id

    async def persist(
        self,
        *,
        signal: Signal,
        embedded_signal: EmbeddedSignal,
    ) -> None:
        if signal.id != embedded_signal.signal_id:
            raise ValueError("Signal ID does not match embedded signal ID.")

        await self.vectorize_client.upsert_vector(
            index_name=self.index_name,
            vector_id=self._build_vector_id(signal=signal),
            values=embedded_signal.embedding,
            metadata={
                "pipeline_id": self.pipeline_id,
                "source": signal.source,
                "signal_id": signal.id,
                "embedding_version": embedded_signal.embedding_version,
            },
        )

    def _build_vector_id(
        self,
        *,
        signal: Signal,
    ) -> str:
        identity = f"{self.pipeline_id}:{signal.source}:{signal.id}"

        return hashlib.sha256(identity.encode("utf-8")).hexdigest()
