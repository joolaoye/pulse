from typing import List

from pulse.application.configuration.errors import (
    PodcastPipelineAlreadyExistsError,
    PodcastPipelineNotFoundError,
    PodcastShowNotFoundError,
)
from pulse.application.configuration.models import (
    PodcastPipelineUpdate,
)
from pulse.infrastructure.db.repositories import (
    PodcastPipelineRepository,
    PodcastShowRepository,
)
from pulse.types import PodcastPipeline


class PipelineManager:
    def __init__(
        self,
        *,
        podcast_pipeline_repository: PodcastPipelineRepository,
        podcast_show_repository: PodcastShowRepository,
    ) -> None:
        self._podcast_pipeline_repository = podcast_pipeline_repository
        self._podcast_show_repository = podcast_show_repository

    async def create(
        self,
        *,
        pipeline: PodcastPipeline,
    ) -> PodcastPipeline:
        existing_pipeline = await self._podcast_pipeline_repository.get(
            pipeline_id=pipeline.pipeline_id,
        )

        if existing_pipeline is not None:
            raise PodcastPipelineAlreadyExistsError(
                f"Podcast pipeline '{pipeline.pipeline_id}' already exists."
            )

        await self._require_podcast_show(
            show_id=pipeline.show_id,
        )

        await self._podcast_pipeline_repository.create(
            pipeline=pipeline,
        )

        return pipeline

    async def get(
        self,
        *,
        pipeline_id: str,
    ) -> PodcastPipeline:
        pipeline_id = self._validate_pipeline_id(
            pipeline_id=pipeline_id,
        )

        pipeline = await self._podcast_pipeline_repository.get(
            pipeline_id=pipeline_id,
        )

        if pipeline is None:
            raise PodcastPipelineNotFoundError(f"Podcast pipeline '{pipeline_id}' does not exist.")

        return pipeline

    async def list(self) -> List[PodcastPipeline]:
        return await self._podcast_pipeline_repository.list()

    async def update(
        self,
        *,
        pipeline_id: str,
        update: PodcastPipelineUpdate,
    ) -> PodcastPipeline:
        existing_pipeline = await self.get(
            pipeline_id=pipeline_id,
        )

        updated_pipeline = PodcastPipeline.model_validate(
            {
                **existing_pipeline.model_dump(mode="python"),
                **update.model_dump(exclude_unset=True),
            }
        )

        await self._require_podcast_show(
            show_id=updated_pipeline.show_id,
        )

        await self._podcast_pipeline_repository.update(
            pipeline=updated_pipeline,
        )

        return updated_pipeline

    async def enable(
        self,
        *,
        pipeline_id: str,
    ) -> PodcastPipeline:
        return await self._set_enabled(
            pipeline_id=pipeline_id,
            enabled=True,
        )

    async def disable(
        self,
        *,
        pipeline_id: str,
    ) -> PodcastPipeline:
        return await self._set_enabled(
            pipeline_id=pipeline_id,
            enabled=False,
        )

    async def _set_enabled(
        self,
        *,
        pipeline_id: str,
        enabled: bool,
    ) -> PodcastPipeline:
        pipeline = await self.get(
            pipeline_id=pipeline_id,
        )

        if pipeline.enabled == enabled:
            return pipeline

        await self._podcast_pipeline_repository.set_enabled(
            pipeline_id=pipeline.pipeline_id,
            enabled=enabled,
        )

        return pipeline.model_copy(
            update={"enabled": enabled},
        )

    async def _require_podcast_show(
        self,
        *,
        show_id: str,
    ) -> None:
        podcast_show = await self._podcast_show_repository.get(
            show_id=show_id,
        )

        if podcast_show is None:
            raise PodcastShowNotFoundError(f"Podcast show '{show_id}' does not exist.")

    @staticmethod
    def _validate_pipeline_id(
        *,
        pipeline_id: str,
    ) -> str:
        pipeline_id = pipeline_id.strip()

        if not pipeline_id:
            raise ValueError("Podcast pipeline ID cannot be empty.")

        return pipeline_id
