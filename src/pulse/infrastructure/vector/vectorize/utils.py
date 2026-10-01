import asyncio
import time
from typing import Any, Dict, List

from pulse.infrastructure.vector.vectorize.client import VectorizeClient

VECTORIZE_DEFAULT_POLLING_INTERVAL_SECONDS = 2.0
VECTORIZE_DEFAULT_POLLING_TIMEOUT_SECONDS = 120.0


async def wait_until_vector_available(
    *,
    vectorize_client: VectorizeClient,
    index_name: str,
    expected_vector_id: str,
    polling_interval_seconds: float = VECTORIZE_DEFAULT_POLLING_INTERVAL_SECONDS,
    timeout_seconds: float = VECTORIZE_DEFAULT_POLLING_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    start_time = time.monotonic()

    while True:
        vectors = await vectorize_client.get_vectors_by_ids(
            index_name=index_name,
            vector_ids=[expected_vector_id],
        )

        if any(vector.get("id") == expected_vector_id for vector in vectors):
            return vectors

        if time.monotonic() - start_time >= timeout_seconds:
            raise TimeoutError(
                f"Timed out waiting for vector '{expected_vector_id}' "
                f"to become available in index '{index_name}'."
            )

        await asyncio.sleep(polling_interval_seconds)


async def wait_until_metadata_index_available(
    *,
    vectorize_client: VectorizeClient,
    index_name: str,
    property_name: str,
    polling_interval_seconds: float = VECTORIZE_DEFAULT_POLLING_INTERVAL_SECONDS,
    timeout_seconds: float = VECTORIZE_DEFAULT_POLLING_TIMEOUT_SECONDS,
) -> None:
    start_time = time.monotonic()

    while True:
        metadata_indexes = await vectorize_client.list_metadata_indexes(
            index_name=index_name,
        )

        if any(
            metadata_index.get("propertyName") == property_name
            for metadata_index in metadata_indexes
        ):
            return

        if time.monotonic() - start_time >= timeout_seconds:
            raise TimeoutError(
                f"Timed out waiting for Vectorize metadata index "
                f"'{property_name}' on '{index_name}' to become available."
            )

        await asyncio.sleep(polling_interval_seconds)
