from pathlib import Path

import pytest

from pulse.application.setup.config import PulseInitializationConfig
from pulse.application.setup.errors import (
    PulseResourceCollisionError,
    PulseResourceCompatibilityError,
)
from pulse.application.setup.initializer import PulseInitializer

COMPATIBLE_INDEX = {"config": {"dimensions": 1024, "metric": "cosine"}}


def _config(tmp_path: Path) -> PulseInitializationConfig:
    return PulseInitializationConfig(
        x_bearer_token="x-token",
        voyage_api_key="voyage-key",
        anthropic_api_key="anthropic-key",
        elevenlabs_api_key="elevenlabs-key",
        cloudflare_account_id="account-1",
        cloudflare_api_token="cf-token",
        d1_database_name="pulse-db",
        vectorize_index_name="pulse-signals",
        checkpoint_database_path=tmp_path / "checkpoints" / "pulse.sqlite3",
        podcast_bucket_name="pulse-podcasts",
    )


class _Provisioner:
    def __init__(self, *, d1: dict | None = None, bucket: dict | None = None) -> None:
        self.d1 = d1
        self.bucket = bucket
        self.created_databases: list[str] = []
        self.created_buckets: list[str] = []

    async def get_d1_database(self, *, database_name: str) -> dict | None:
        del database_name
        return self.d1

    async def get_r2_bucket(self, *, bucket_name: str) -> dict | None:
        del bucket_name
        return self.bucket

    async def create_d1_database(self, *, database_name: str) -> dict:
        self.created_databases.append(database_name)
        return {"uuid": "created-database"}

    async def create_r2_bucket(self, *, bucket_name: str) -> None:
        self.created_buckets.append(bucket_name)


class _Vectorize:
    def __init__(self, index: dict | None) -> None:
        self.index = index
        self.created_indexes: list[str] = []

    async def index_exists(self, *, index_name: str) -> bool:
        del index_name
        return self.index is not None

    async def get_index(self, *, index_name: str) -> dict | None:
        del index_name
        return self.index

    async def create_index(self, *, index_name: str, **kwargs) -> None:
        del kwargs
        self.created_indexes.append(index_name)

    async def list_metadata_indexes(self, *, index_name: str) -> list[dict]:
        del index_name
        return [{"propertyName": "pipeline_id", "indexType": "string"}]


class _Migrations:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def apply_d1_migrations(self, **kwargs) -> None:
        self.calls.append(kwargs)


def _initializer(
    *,
    d1: dict | None = None,
    index: dict | None = None,
    bucket: dict | None = None,
    reuse: bool = False,
) -> tuple[PulseInitializer, _Provisioner, _Vectorize, _Migrations]:
    provisioner = _Provisioner(d1=d1, bucket=bucket)
    vectorize = _Vectorize(index)
    migrations = _Migrations()
    initializer = PulseInitializer(
        cloudflare_provisioner=provisioner,
        vectorize_client=vectorize,
        wrangler_runner=migrations,
        reuse_existing_cloudflare_resources=reuse,
    )
    return initializer, provisioner, vectorize, migrations


def _silence_local_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        PulseInitializer,
        "_write_wrangler_config",
        staticmethod(lambda **kwargs: None),
    )
    monkeypatch.setattr(
        PulseInitializer,
        "_write_environment",
        staticmethod(lambda **kwargs: None),
    )
    monkeypatch.setattr(
        PulseInitializer,
        "_ensure_environment_file",
        staticmethod(lambda: None),
    )


@pytest.mark.parametrize(
    ("d1", "index", "bucket"),
    [
        ({"uuid": "existing-database"}, None, None),
        (None, COMPATIBLE_INDEX, None),
        (None, None, {"name": "pulse-podcasts"}),
    ],
)
async def test_existing_resource_is_rejected_unless_reuse_is_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    d1: dict | None,
    index: dict | None,
    bucket: dict | None,
) -> None:
    _silence_local_writes(monkeypatch)
    initializer, provisioner, vectorize, migrations = _initializer(
        d1=d1, index=index, bucket=bucket
    )

    with pytest.raises(PulseResourceCollisionError):
        await initializer.initialize(config=_config(tmp_path))

    assert provisioner.created_databases == []
    assert provisioner.created_buckets == []
    assert vectorize.created_indexes == []
    assert migrations.calls == []


@pytest.mark.parametrize(
    "index",
    [
        {"config": {"dimensions": 512, "metric": "cosine"}},
        {"config": {"dimensions": 1024, "metric": "euclidean"}},
    ],
)
async def test_incompatible_vectorize_index_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    index: dict,
) -> None:
    _silence_local_writes(monkeypatch)
    initializer, provisioner, vectorize, migrations = _initializer(
        d1={"uuid": "existing-database"},
        index=index,
        reuse=True,
    )

    with pytest.raises(PulseResourceCompatibilityError):
        await initializer.initialize(config=_config(tmp_path))

    assert provisioner.created_databases == []
    assert vectorize.created_indexes == []
    assert migrations.calls == []
