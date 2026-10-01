from typing import List, Protocol

from pulse.infrastructure.storage.objects import (
    AudioObjectStore,
    AudioObjectUpload,
)
from pulse.types import EpisodeTurnTiming, StoredEpisodeAudio

AUDIO_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
}


class EpisodeAudioUpload(Protocol):
    async def write(
        self,
        *,
        content: bytes,
    ) -> None: ...

    async def complete(
        self,
        *,
        duration_seconds: float,
        turn_timings: List[EpisodeTurnTiming],
    ) -> StoredEpisodeAudio: ...

    async def abort(self) -> None: ...


class AudioRepository:
    def __init__(
        self,
        *,
        object_store: AudioObjectStore,
    ) -> None:
        self.object_store = object_store

    async def begin_upload(
        self,
        *,
        show_id: str,
        episode_id: str,
        output_format: str,
    ) -> EpisodeAudioUpload:
        content_type = self._content_type(
            output_format=output_format,
        )
        object_key = self._build_audio_object_key(
            show_id=show_id,
            episode_id=episode_id,
            output_format=output_format,
        )
        object_upload = await self.object_store.begin_upload(
            object_key=object_key,
            content_type=content_type,
        )

        return _RepositoryAudioUpload(
            object_upload=object_upload,
            object_key=object_key,
            output_format=output_format,
            content_type=content_type,
        )

    @staticmethod
    def _content_type(
        *,
        output_format: str,
    ) -> str:
        try:
            return AUDIO_CONTENT_TYPES[output_format]
        except KeyError as error:
            raise ValueError(f"Unsupported audio output format: {output_format!r}.") from error

    @staticmethod
    def _build_audio_object_key(
        *,
        show_id: str,
        episode_id: str,
        output_format: str,
    ) -> str:
        normalized_output_format = output_format.strip().lower().lstrip(".")

        if not normalized_output_format:
            raise ValueError(
                "A podcast audio object key cannot be created without an output format."
            )

        if not normalized_output_format.isalnum():
            raise ValueError(
                "The podcast audio output format may only contain "
                f"letters and numbers. Received: {output_format}."
            )

        return f"shows/{show_id}/episodes/{episode_id}/audio.{normalized_output_format}"


class _RepositoryAudioUpload:
    def __init__(
        self,
        *,
        object_upload: AudioObjectUpload,
        object_key: str,
        output_format: str,
        content_type: str,
    ) -> None:
        self._object_upload = object_upload
        self._object_key = object_key
        self._output_format = output_format
        self._content_type = content_type

    async def write(
        self,
        *,
        content: bytes,
    ) -> None:
        if not content:
            raise ValueError("An audio upload chunk cannot be empty.")

        await self._object_upload.write(
            content=content,
        )

    async def complete(
        self,
        *,
        duration_seconds: float,
        turn_timings: List[EpisodeTurnTiming],
    ) -> StoredEpisodeAudio:
        size_bytes = await self._object_upload.complete()

        return StoredEpisodeAudio(
            object_key=self._object_key,
            output_format=self._output_format,
            content_type=self._content_type,
            duration_seconds=duration_seconds,
            size_bytes=size_bytes,
            turn_timings=turn_timings,
        )

    async def abort(self) -> None:
        await self._object_upload.abort()
