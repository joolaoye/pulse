import asyncio
from typing import Any, Dict, List, Optional, cast

from pulse.services.signals.semantic_deduplicator import (
    SemanticDeduplicator,
)
from pulse.types import EmbeddedSignal


class FakeVectorizeClient:
    def __init__(
        self,
        *,
        matches: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.matches = matches or []
        self.queries: List[Dict[str, Any]] = []

    async def query_vector(
        self,
        *,
        index_name: str,
        vector: List[float],
        top_k: int,
        metadata_filter: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        self.queries.append(
            {
                "index_name": index_name,
                "vector": vector,
                "top_k": top_k,
                "metadata_filter": metadata_filter,
            }
        )

        return self.matches


def _embedded_signal(
    *,
    signal_id: str,
    embedding: List[float],
) -> EmbeddedSignal:
    return EmbeddedSignal(
        signal_id=signal_id,
        embedding=embedding,
        embedding_version="test",
    )


def test_detects_within_run_duplicate_at_similarity_threshold() -> None:
    deduplicator = SemanticDeduplicator(
        vectorize_client=cast(
            Any,
            FakeVectorizeClient(),
        ),
        pipeline_id="pipeline-1",
        similarity_threshold=0.8,
    )

    candidate = _embedded_signal(
        signal_id="signal-2",
        embedding=[0.8, 0.6],
    )

    accepted = _embedded_signal(
        signal_id="signal-1",
        embedding=[1.0, 0.0],
    )

    assert deduplicator.is_duplicate_within_run(
        embedded_signal=candidate,
        accepted_signals=[accepted],
    )


def test_does_not_detect_within_run_duplicate_below_threshold() -> None:
    deduplicator = SemanticDeduplicator(
        vectorize_client=cast(
            Any,
            FakeVectorizeClient(),
        ),
        pipeline_id="pipeline-1",
        similarity_threshold=0.85,
    )

    candidate = _embedded_signal(
        signal_id="signal-2",
        embedding=[0.8, 0.6],
    )

    accepted = _embedded_signal(
        signal_id="signal-1",
        embedding=[1.0, 0.0],
    )

    assert not deduplicator.is_duplicate_within_run(
        embedded_signal=candidate,
        accepted_signals=[accepted],
    )


def test_does_not_detect_within_run_duplicate_without_accepted_signals() -> None:
    deduplicator = SemanticDeduplicator(
        vectorize_client=cast(
            Any,
            FakeVectorizeClient(),
        ),
        pipeline_id="pipeline-1",
    )

    candidate = _embedded_signal(
        signal_id="signal-1",
        embedding=[1.0, 0.0],
    )

    assert not deduplicator.is_duplicate_within_run(
        embedded_signal=candidate,
        accepted_signals=[],
    )


async def _test_detects_historical_duplicate() -> None:
    client = FakeVectorizeClient(
        matches=[
            {
                "id": "existing-vector",
                "score": 0.91,
            }
        ]
    )

    deduplicator = SemanticDeduplicator(
        vectorize_client=cast(
            Any,
            client,
        ),
        pipeline_id="pipeline-1",
        top_k=1,
        similarity_threshold=0.85,
    )

    embedded_signal = _embedded_signal(
        signal_id="signal-1",
        embedding=[1.0, 0.0],
    )

    result = await deduplicator.is_duplicate(
        index_name="signals-index",
        embedded_signal=embedded_signal,
    )

    assert result is True

    assert client.queries == [
        {
            "index_name": "signals-index",
            "vector": [1.0, 0.0],
            "top_k": 1,
            "metadata_filter": {
                "pipeline_id": "pipeline-1",
            },
        }
    ]


def test_detects_historical_duplicate() -> None:
    asyncio.run(_test_detects_historical_duplicate())


async def _test_does_not_detect_historical_duplicate_below_threshold() -> None:
    client = FakeVectorizeClient(
        matches=[
            {
                "id": "existing-vector",
                "score": 0.84,
            }
        ]
    )

    deduplicator = SemanticDeduplicator(
        vectorize_client=cast(
            Any,
            client,
        ),
        pipeline_id="pipeline-1",
        similarity_threshold=0.85,
    )

    result = await deduplicator.is_duplicate(
        index_name="signals-index",
        embedded_signal=_embedded_signal(
            signal_id="signal-1",
            embedding=[1.0, 0.0],
        ),
    )

    assert result is False


def test_does_not_detect_historical_duplicate_below_threshold() -> None:
    asyncio.run(_test_does_not_detect_historical_duplicate_below_threshold())


async def _test_does_not_detect_historical_duplicate_without_matches() -> None:
    client = FakeVectorizeClient()

    deduplicator = SemanticDeduplicator(
        vectorize_client=cast(
            Any,
            client,
        ),
        pipeline_id="pipeline-1",
    )

    result = await deduplicator.is_duplicate(
        index_name="signals-index",
        embedded_signal=_embedded_signal(
            signal_id="signal-1",
            embedding=[1.0, 0.0],
        ),
    )

    assert result is False


def test_does_not_detect_historical_duplicate_without_matches() -> None:
    asyncio.run(_test_does_not_detect_historical_duplicate_without_matches())
