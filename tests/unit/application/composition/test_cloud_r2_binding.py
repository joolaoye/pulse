from typing import Any, cast

import pytest

from pulse.application.composition.assemble import assemble_application
from pulse.application.composition.cloud import bootstrap_cloud
from pulse.application.composition.infrastructure import create_rest_infrastructure
from pulse.application.composition.models import (
    CloudflareRestCredentials,
    ProviderCredentials,
    ResourceNames,
)
from pulse.infrastructure.storage.r2.client import R2Client
from pulse.infrastructure.storage.r2.object_store import (
    R2AudioObjectStore,
    WorkerR2AudioObjectStore,
    create_audio_object_store,
)


class _BoundBucket:
    pass


def _resources() -> ResourceNames:
    return ResourceNames(
        vectorize_index_name="pulse-signals",
        podcast_bucket_name="pulse-podcasts",
    )


def _cloudflare() -> CloudflareRestCredentials:
    return CloudflareRestCredentials(
        api_token="token",
        account_id="account-1",
        d1_database_id="7877d04a-87d6-4689-bf4c-a3b6a7d16175",
    )


def _providers() -> ProviderCredentials:
    return ProviderCredentials(
        anthropic_api_key="anthropic",
        voyage_api_key="voyage",
        x_bearer_token="x-token",
        elevenlabs_api_key="elevenlabs",
    )


def test_missing_worker_bucket_selects_the_local_rest_store() -> None:
    store = create_audio_object_store(
        r2_client=cast(R2Client, object()),
        bucket_name="pulse-podcasts",
        bucket=None,
    )

    assert isinstance(store, R2AudioObjectStore)


def test_explicit_worker_bucket_selects_the_multipart_store() -> None:
    bucket = _BoundBucket()
    store = create_audio_object_store(
        r2_client=cast(R2Client, object()),
        bucket_name="pulse-podcasts",
        bucket=bucket,
    )

    assert isinstance(store, WorkerR2AudioObjectStore)
    assert store._bucket is bucket


async def test_cloud_bootstrap_rejects_a_missing_r2_binding() -> None:
    with pytest.raises(RuntimeError, match="PULSE_PODCAST_BUCKET"):
        async with bootstrap_cloud(
            checkpointer=cast(Any, object()),
            resources=_resources(),
            cloudflare=_cloudflare(),
            providers=_providers(),
            r2_bucket=None,
        ):
            raise AssertionError("Cloud composition continued without an R2 binding.")


async def test_cloud_bootstrap_uses_the_worker_r2_binding() -> None:
    bucket = _BoundBucket()

    async with bootstrap_cloud(
        checkpointer=cast(Any, object()),
        resources=_resources(),
        cloudflare=_cloudflare(),
        providers=_providers(),
        r2_bucket=bucket,
    ) as application:
        store = application.audio_producer.audio_repository.object_store

        assert isinstance(store, WorkerR2AudioObjectStore)
        assert not isinstance(store, R2AudioObjectStore)
        assert store._bucket is bucket


async def test_local_composition_uses_the_spooled_rest_store() -> None:
    infrastructure = create_rest_infrastructure(
        cloudflare=_cloudflare(),
        providers=_providers(),
    )

    try:
        application = assemble_application(
            infrastructure=infrastructure,
            checkpointer=cast(Any, object()),
            resources=_resources(),
        )
        store = application.audio_producer.audio_repository.object_store

        assert isinstance(store, R2AudioObjectStore)
        assert not isinstance(store, WorkerR2AudioObjectStore)
    finally:
        await infrastructure.aclose()
