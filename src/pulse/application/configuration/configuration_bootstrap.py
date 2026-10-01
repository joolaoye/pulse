from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from pulse.application.composition.cloud import CloudflareRestCredentials
from pulse.application.configuration.pipeline_manager import PipelineManager
from pulse.application.configuration.schedule_manager import ScheduleManager
from pulse.application.configuration.show_manager import ShowManager
from pulse.application.environment import (
    load_environment,
    require_environment_variable,
)
from pulse.infrastructure.cloudflare import (
    CloudflareClient,
    CloudflareConfig,
)
from pulse.infrastructure.db.d1 import (
    D1Client,
    D1Config,
)
from pulse.infrastructure.db.repositories import (
    PodcastPipelineRepository,
    PodcastPipelineScheduleRepository,
    PodcastShowRepository,
)


@dataclass(frozen=True)
class ConfigurationApplication:
    show_manager: ShowManager
    pipeline_manager: PipelineManager
    schedule_manager: ScheduleManager


def create_configuration_application(
    *,
    d1_client: D1Client,
) -> ConfigurationApplication:
    podcast_show_repository = PodcastShowRepository(
        db_client=d1_client,
    )

    podcast_pipeline_repository = PodcastPipelineRepository(
        db_client=d1_client,
    )

    podcast_pipeline_schedule_repository = PodcastPipelineScheduleRepository(
        db_client=d1_client,
    )

    return ConfigurationApplication(
        show_manager=ShowManager(
            podcast_show_repository=podcast_show_repository,
        ),
        pipeline_manager=PipelineManager(
            podcast_pipeline_repository=podcast_pipeline_repository,
            podcast_show_repository=podcast_show_repository,
        ),
        schedule_manager=ScheduleManager(
            podcast_pipeline_repository=podcast_pipeline_repository,
            podcast_pipeline_schedule_repository=(podcast_pipeline_schedule_repository),
        ),
    )


@asynccontextmanager
async def bootstrap_cloud_configuration(
    *,
    cloudflare: CloudflareRestCredentials,
) -> AsyncIterator[ConfigurationApplication]:
    cloudflare_client = CloudflareClient(
        config=CloudflareConfig(
            api_token=cloudflare.api_token,
            account_id=cloudflare.account_id,
        )
    )

    try:
        d1_client = D1Client(
            cloudflare_client=cloudflare_client,
            config=D1Config(
                database_id=cloudflare.d1_database_id,
            ),
        )

        yield create_configuration_application(
            d1_client=d1_client,
        )

    finally:
        await cloudflare_client.aclose()


@asynccontextmanager
async def bootstrap_configuration() -> AsyncIterator[ConfigurationApplication]:
    load_environment()

    cloudflare_client = CloudflareClient(
        config=CloudflareConfig(
            api_token=require_environment_variable(
                variable_name="PULSE_CLOUDFLARE_API_TOKEN",
            ),
            account_id=require_environment_variable(
                variable_name="CLOUDFLARE_ACCOUNT_ID",
            ),
        )
    )

    try:
        d1_client = D1Client(
            cloudflare_client=cloudflare_client,
            config=D1Config(
                database_id=require_environment_variable(
                    variable_name="CLOUDFLARE_D1_DATABASE_ID",
                )
            ),
        )

        yield create_configuration_application(
            d1_client=d1_client,
        )

    finally:
        await cloudflare_client.aclose()
