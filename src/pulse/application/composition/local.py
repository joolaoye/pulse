from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import AsyncIterator

from pulse.application.composition.assemble import PulseApplication, assemble_workflow
from pulse.application.composition.infrastructure import create_rest_infrastructure
from pulse.application.composition.models import (
    CloudflareRestCredentials,
    ProviderCredentials,
    ResourceNames,
)
from pulse.application.environment import require_environment_variable
from pulse.application.orchestration.checkpointing import (
    create_sqlite_checkpointer,
)

DEFAULT_CHECKPOINT_DATABASE_PATH = Path("runtime/pulse-checkpoints.sqlite")


def _load_cloudflare_rest_credentials() -> CloudflareRestCredentials:
    return CloudflareRestCredentials(
        api_token=require_environment_variable(
            variable_name="PULSE_CLOUDFLARE_API_TOKEN",
        ),
        account_id=require_environment_variable(
            variable_name="CLOUDFLARE_ACCOUNT_ID",
        ),
        d1_database_id=require_environment_variable(
            variable_name="CLOUDFLARE_D1_DATABASE_ID",
        ),
    )


def _load_provider_credentials() -> ProviderCredentials:
    return ProviderCredentials(
        anthropic_api_key=require_environment_variable(
            variable_name="ANTHROPIC_API_KEY",
        ),
        voyage_api_key=require_environment_variable(
            variable_name="VOYAGE_API_KEY",
        ),
        x_bearer_token=require_environment_variable(
            variable_name="X_BEARER_TOKEN",
        ),
        elevenlabs_api_key=require_environment_variable(
            variable_name="ELEVENLABS_API_KEY",
        ),
    )


def _load_resource_names() -> ResourceNames:
    return ResourceNames(
        vectorize_index_name=require_environment_variable(
            variable_name="PULSE_VECTORIZE_INDEX_NAME",
        ),
        podcast_bucket_name=require_environment_variable(
            variable_name="PULSE_PODCAST_BUCKET_NAME",
        ),
    )


def _load_checkpoint_database_path() -> Path:
    value = os.getenv("PULSE_CHECKPOINT_DATABASE_PATH")

    path = Path(value) if value is not None and value.strip() else DEFAULT_CHECKPOINT_DATABASE_PATH

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


@asynccontextmanager
async def bootstrap_local() -> AsyncIterator[PulseApplication]:
    infrastructure = create_rest_infrastructure(
        cloudflare=_load_cloudflare_rest_credentials(),
        providers=_load_provider_credentials(),
    )

    async with (
        create_sqlite_checkpointer(
            database_path=_load_checkpoint_database_path(),
        ) as checkpointer,
        assemble_workflow(
            infrastructure=infrastructure,
            checkpointer=checkpointer,
            resources=_load_resource_names(),
        ) as application,
    ):
        yield application
