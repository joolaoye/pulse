from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from dotenv import set_key

from pulse.application.setup.config import PulseInitializationConfig
from pulse.application.setup.errors import (
    PulseResourceCollisionError,
    PulseResourceCompatibilityError,
)
from pulse.infrastructure.cloudflare import (
    WRANGLER_CONFIG_PATH,
    CloudflareClient,
    CloudflareConfig,
    CloudflareProvisioner,
    WranglerRunner,
    render_wrangler_config,
)
from pulse.infrastructure.vector import (
    VectorizeClient,
    wait_until_metadata_index_available,
)

_VECTORIZE_DIMENSIONS = 1024
_VECTORIZE_METRIC = "cosine"

_PIPELINE_METADATA_PROPERTY = "pipeline_id"
_PIPELINE_METADATA_INDEX_TYPE = "string"

_ENV_PATH = Path(".env")


class PulseInitializer:
    def __init__(
        self,
        *,
        cloudflare_provisioner: CloudflareProvisioner,
        vectorize_client: VectorizeClient,
        wrangler_runner: WranglerRunner,
        reuse_existing_cloudflare_resources: bool = False,
    ) -> None:
        self._cloudflare_provisioner = cloudflare_provisioner
        self._vectorize_client = vectorize_client
        self._wrangler_runner = wrangler_runner
        self._reuse_existing_cloudflare_resources = reuse_existing_cloudflare_resources

    async def initialize(
        self,
        *,
        config: PulseInitializationConfig,
    ) -> None:
        self._ensure_checkpoint_directory(
            database_path=config.checkpoint_database_path,
        )

        d1_database = await self._cloudflare_provisioner.get_d1_database(
            database_name=config.d1_database_name,
        )
        vectorize_index = await self._get_vectorize_index(
            index_name=config.vectorize_index_name,
        )
        podcast_bucket = await self._cloudflare_provisioner.get_r2_bucket(
            bucket_name=config.podcast_bucket_name,
        )

        if vectorize_index is not None:
            self._validate_vectorize_index(
                index_name=config.vectorize_index_name,
                index=vectorize_index,
            )

        self._validate_resource_collisions(
            config=config,
            d1_database=d1_database,
            vectorize_index=vectorize_index,
            podcast_bucket=podcast_bucket,
        )

        if d1_database is None:
            d1_database = await self._cloudflare_provisioner.create_d1_database(
                database_name=config.d1_database_name,
            )

        d1_database_id = self._resolve_d1_database_id(
            database=d1_database,
        )

        await self._wrangler_runner.apply_d1_migrations(
            database_name=config.d1_database_name,
            database_id=d1_database_id,
        )

        if vectorize_index is None:
            await self._vectorize_client.create_index(
                index_name=config.vectorize_index_name,
                dimensions=_VECTORIZE_DIMENSIONS,
                metric=_VECTORIZE_METRIC,
                description="Pulse shared signal embedding index.",
            )

        await self._ensure_pipeline_metadata_index(
            index_name=config.vectorize_index_name,
        )

        if podcast_bucket is None:
            await self._cloudflare_provisioner.create_r2_bucket(
                bucket_name=config.podcast_bucket_name,
            )

        self._write_wrangler_config(
            config=config,
            d1_database_id=d1_database_id,
        )

        self._ensure_environment_file()

        self._write_environment(
            config=config,
            d1_database_id=d1_database_id,
        )

    async def _get_vectorize_index(
        self,
        *,
        index_name: str,
    ) -> Optional[Dict[str, Any]]:
        if not await self._vectorize_client.index_exists(
            index_name=index_name,
        ):
            return None

        return await self._vectorize_client.get_index(
            index_name=index_name,
        )

    def _validate_resource_collisions(
        self,
        *,
        config: PulseInitializationConfig,
        d1_database: Optional[Dict[str, Any]],
        vectorize_index: Optional[Dict[str, Any]],
        podcast_bucket: Optional[Dict[str, Any]],
    ) -> None:
        if self._reuse_existing_cloudflare_resources:
            return

        resources: List[str] = []

        if d1_database is not None:
            resources.append(f"D1 database '{config.d1_database_name}'")

        if vectorize_index is not None:
            resources.append(f"Vectorize index '{config.vectorize_index_name}'")

        if podcast_bucket is not None:
            resources.append(f"R2 bucket '{config.podcast_bucket_name}'")

        if resources:
            raise PulseResourceCollisionError(
                resources=resources,
            )

    @staticmethod
    def _validate_vectorize_index(
        *,
        index_name: str,
        index: Dict[str, Any],
    ) -> None:
        index_config = index.get("config", {})

        dimensions = index_config.get("dimensions")
        metric = index_config.get("metric")

        if dimensions != _VECTORIZE_DIMENSIONS:
            raise PulseResourceCompatibilityError(
                f"Vectorize index '{index_name}' uses "
                f"{dimensions} dimensions. "
                f"Pulse requires {_VECTORIZE_DIMENSIONS}."
            )

        if metric != _VECTORIZE_METRIC:
            raise PulseResourceCompatibilityError(
                f"Vectorize index '{index_name}' uses metric "
                f"'{metric}'. Pulse requires '{_VECTORIZE_METRIC}'."
            )

    async def _ensure_pipeline_metadata_index(
        self,
        *,
        index_name: str,
    ) -> None:
        metadata_indexes = await self._vectorize_client.list_metadata_indexes(
            index_name=index_name,
        )

        for metadata_index in metadata_indexes:
            property_name = metadata_index.get("propertyName")

            if property_name != _PIPELINE_METADATA_PROPERTY:
                continue

            index_type = metadata_index.get("indexType")

            if not isinstance(index_type, str):
                raise PulseResourceCompatibilityError(
                    "Vectorize metadata index "
                    f"'{property_name}' on '{index_name}' "
                    "returned an invalid index type."
                )

            if index_type.strip().lower() != _PIPELINE_METADATA_INDEX_TYPE:
                raise PulseResourceCompatibilityError(
                    "Vectorize metadata index "
                    f"'{property_name}' on '{index_name}' "
                    f"has type '{index_type}'. Pulse requires "
                    f"'{_PIPELINE_METADATA_INDEX_TYPE}'."
                )

            return

        await self._vectorize_client.create_metadata_index(
            index_name=index_name,
            property_name=_PIPELINE_METADATA_PROPERTY,
            index_type=_PIPELINE_METADATA_INDEX_TYPE,
        )

        await wait_until_metadata_index_available(
            vectorize_client=self._vectorize_client,
            index_name=index_name,
            property_name=_PIPELINE_METADATA_PROPERTY,
        )

    @staticmethod
    def _resolve_d1_database_id(
        *,
        database: Dict[str, Any],
    ) -> str:
        database_id = database.get("uuid")

        if not isinstance(database_id, str):
            raise RuntimeError(
                "Cloudflare D1 database response did not contain a valid database UUID."
            )

        database_id = database_id.strip()

        if not database_id:
            raise RuntimeError("Cloudflare D1 database response contained an empty database UUID.")

        return database_id

    @staticmethod
    def _ensure_environment_file() -> None:
        _ENV_PATH.touch(
            exist_ok=True,
        )

    @staticmethod
    def _ensure_checkpoint_directory(
        *,
        database_path: Path,
    ) -> None:
        database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _write_environment(
        *,
        config: PulseInitializationConfig,
        d1_database_id: str,
    ) -> None:
        values = {
            "X_BEARER_TOKEN": config.x_bearer_token,
            "VOYAGE_API_KEY": config.voyage_api_key,
            "ANTHROPIC_API_KEY": config.anthropic_api_key,
            "ELEVENLABS_API_KEY": config.elevenlabs_api_key,
            "CLOUDFLARE_ACCOUNT_ID": config.cloudflare_account_id,
            "PULSE_CLOUDFLARE_API_TOKEN": config.cloudflare_api_token,
            "PULSE_D1_DATABASE_NAME": config.d1_database_name,
            "CLOUDFLARE_D1_DATABASE_ID": d1_database_id,
            "PULSE_VECTORIZE_INDEX_NAME": config.vectorize_index_name,
            "PULSE_PODCAST_BUCKET_NAME": config.podcast_bucket_name,
            "PULSE_CHECKPOINT_DATABASE_PATH": str(config.checkpoint_database_path),
        }

        for variable_name, value in values.items():
            set_key(
                dotenv_path=str(_ENV_PATH),
                key_to_set=variable_name,
                value_to_set=value,
            )

    @staticmethod
    def _write_wrangler_config(
        *,
        config: PulseInitializationConfig,
        d1_database_id: str,
    ) -> None:
        rendered = render_wrangler_config(
            account_id=config.cloudflare_account_id,
            d1_database_name=config.d1_database_name,
            d1_database_id=d1_database_id,
            vectorize_index_name=config.vectorize_index_name,
            podcast_bucket_name=config.podcast_bucket_name,
        )

        WRANGLER_CONFIG_PATH.write_text(
            rendered,
        )


@asynccontextmanager
async def bootstrap_setup(
    *,
    config: PulseInitializationConfig,
    reuse_existing_cloudflare_resources: bool = False,
) -> AsyncIterator[PulseInitializer]:
    cloudflare_client = CloudflareClient(
        config=CloudflareConfig(
            api_token=config.cloudflare_api_token,
            account_id=config.cloudflare_account_id,
        ),
    )

    try:
        yield PulseInitializer(
            cloudflare_provisioner=CloudflareProvisioner(
                cloudflare_client=cloudflare_client,
            ),
            vectorize_client=VectorizeClient(
                cloudflare_client=cloudflare_client,
            ),
            wrangler_runner=WranglerRunner(
                cloudflare_account_id=config.cloudflare_account_id,
                cloudflare_api_token=config.cloudflare_api_token,
            ),
            reuse_existing_cloudflare_resources=(reuse_existing_cloudflare_resources),
        )
    finally:
        await cloudflare_client.aclose()
