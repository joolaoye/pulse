from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver

from pulse.application.composition.assemble import PulseApplication, assemble_workflow
from pulse.application.composition.infrastructure import create_rest_infrastructure
from pulse.application.composition.models import (
    CloudflareRestCredentials,
    ProviderCredentials,
    ResourceNames,
)


@asynccontextmanager
async def bootstrap_cloud(
    *,
    checkpointer: BaseCheckpointSaver,
    resources: ResourceNames,
    cloudflare: CloudflareRestCredentials,
    providers: ProviderCredentials,
    r2_bucket: object | None = None,
) -> AsyncIterator[PulseApplication]:
    if r2_bucket is None:
        raise RuntimeError(
            "Cloud audio production requires the PULSE_PODCAST_BUCKET R2 binding. "
            "Refusing to fall back to a spooled REST upload."
        )

    infrastructure = create_rest_infrastructure(
        cloudflare=cloudflare,
        providers=providers,
    )

    async with assemble_workflow(
        infrastructure=infrastructure,
        checkpointer=checkpointer,
        resources=resources,
        r2_bucket=r2_bucket,
    ) as application:
        yield application
