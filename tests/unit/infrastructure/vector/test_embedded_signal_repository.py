import hashlib

import pytest

from pulse.infrastructure.vector.repositories.embedded_signals import EmbeddedSignalRepository
from pulse.types import EmbeddedSignal, Signal


class _VectorizeClient:
    def __init__(self) -> None:
        self.upserts: list[dict] = []

    async def upsert_vector(
        self,
        *,
        index_name: str,
        vector_id: str,
        values: list[float],
        metadata: dict,
    ) -> None:
        self.upserts.append(
            {
                "index_name": index_name,
                "vector_id": vector_id,
                "values": values,
                "metadata": metadata,
            }
        )


def _signal(signal_id: str = "signal-42") -> Signal:
    return Signal(id=signal_id, source="x", content="Rates moved overnight.")


def _embedded(signal_id: str = "signal-42") -> EmbeddedSignal:
    return EmbeddedSignal(
        signal_id=signal_id,
        embedding=[0.2, 0.8],
        embedding_version="voyage-3",
    )


async def test_vector_identity_is_derived_from_pipeline_source_and_signal() -> None:
    client = _VectorizeClient()
    repository = EmbeddedSignalRepository(
        vectorize_client=client,
        index_name="signals-index",
        pipeline_id="pipeline-7",
    )

    await repository.persist(signal=_signal(), embedded_signal=_embedded())

    expected_id = hashlib.sha256(b"pipeline-7:x:signal-42").hexdigest()
    assert client.upserts == [
        {
            "index_name": "signals-index",
            "vector_id": expected_id,
            "values": [0.2, 0.8],
            "metadata": {
                "pipeline_id": "pipeline-7",
                "source": "x",
                "signal_id": "signal-42",
                "embedding_version": "voyage-3",
            },
        }
    ]


async def test_mismatched_signal_and_embedding_ids_are_rejected_before_upsert() -> None:
    client = _VectorizeClient()
    repository = EmbeddedSignalRepository(
        vectorize_client=client,
        index_name="signals-index",
        pipeline_id="pipeline-7",
    )

    with pytest.raises(ValueError):
        await repository.persist(
            signal=_signal("signal-42"),
            embedded_signal=_embedded("signal-other"),
        )

    assert client.upserts == []
