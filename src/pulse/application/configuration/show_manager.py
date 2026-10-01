from typing import List

from pulse.application.configuration.errors import (
    PodcastShowAlreadyExistsError,
    PodcastShowNotFoundError,
)
from pulse.application.configuration.models import (
    PodcastShowUpdate,
)
from pulse.infrastructure.db.repositories import PodcastShowRepository
from pulse.types import PodcastShow


class ShowManager:
    def __init__(
        self,
        *,
        podcast_show_repository: PodcastShowRepository,
    ) -> None:
        self._podcast_show_repository = podcast_show_repository

    async def create(
        self,
        *,
        podcast_show: PodcastShow,
    ) -> PodcastShow:
        existing_podcast_show = await self._podcast_show_repository.get(
            show_id=podcast_show.show_id,
        )

        if existing_podcast_show is not None:
            raise PodcastShowAlreadyExistsError(
                f"Podcast show '{podcast_show.show_id}' already exists."
            )

        await self._podcast_show_repository.create(
            podcast_show=podcast_show,
        )

        return podcast_show

    async def get(
        self,
        *,
        show_id: str,
    ) -> PodcastShow:
        show_id = self._validate_show_id(
            show_id=show_id,
        )

        podcast_show = await self._podcast_show_repository.get(
            show_id=show_id,
        )

        if podcast_show is None:
            raise PodcastShowNotFoundError(f"Podcast show '{show_id}' does not exist.")

        return podcast_show

    async def list(self) -> List[PodcastShow]:
        return await self._podcast_show_repository.list()

    async def update(
        self,
        *,
        show_id: str,
        update: PodcastShowUpdate,
    ) -> PodcastShow:
        existing_podcast_show = await self.get(
            show_id=show_id,
        )

        updated_podcast_show = PodcastShow.model_validate(
            {
                **existing_podcast_show.model_dump(mode="python"),
                **update.model_dump(exclude_unset=True),
            }
        )

        await self._podcast_show_repository.update(
            podcast_show=updated_podcast_show,
        )

        return updated_podcast_show

    @staticmethod
    def _validate_show_id(
        *,
        show_id: str,
    ) -> str:
        show_id = show_id.strip()

        if not show_id:
            raise ValueError("Podcast show ID cannot be empty.")

        return show_id
