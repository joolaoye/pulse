from typing import List

import pytest

from pulse.infrastructure.storage.repositories.audio import AudioRepository
from pulse.types import EpisodeTurnTiming, StoredEpisodeAudio


class FakeAudioObjectUpload:
    def __init__(self) -> None:
        self.writes: List[bytes] = []
        self.completed = False
        self.aborted = False

    async def write(
        self,
        *,
        content: bytes,
    ) -> None:
        self.writes.append(content)

    async def complete(self) -> int:
        self.completed = True

        return sum(len(content) for content in self.writes)

    async def abort(self) -> None:
        self.aborted = True


class FakeAudioObjectStore:
    def __init__(self) -> None:
        self.uploads: List[tuple[str, str, FakeAudioObjectUpload]] = []

    async def begin_upload(
        self,
        *,
        object_key: str,
        content_type: str,
    ) -> FakeAudioObjectUpload:
        upload = FakeAudioObjectUpload()
        self.uploads.append((object_key, content_type, upload))

        return upload


def _timings() -> List[EpisodeTurnTiming]:
    return [
        EpisodeTurnTiming(
            script_turn_index=0,
            speaker_id="host",
            start_time_seconds=0.0,
            end_time_seconds=1.5,
        ),
        EpisodeTurnTiming(
            script_turn_index=1,
            speaker_id="guest",
            start_time_seconds=1.5,
            end_time_seconds=3.0,
        ),
    ]


async def test_upload_uses_the_deterministic_key_and_mp3_content_type() -> None:
    store = FakeAudioObjectStore()
    repository = AudioRepository(object_store=store)

    upload = await repository.begin_upload(
        show_id="show-1",
        episode_id="episode-9",
        output_format="mp3",
    )
    await upload.write(content=b"one")
    await upload.write(content=b"two-two")
    stored = await upload.complete(
        duration_seconds=3.0,
        turn_timings=_timings(),
    )

    assert store.uploads[0][0] == "shows/show-1/episodes/episode-9/audio.mp3"
    assert store.uploads[0][1] == "audio/mpeg"
    object_upload = store.uploads[0][2]
    assert object_upload.writes == [b"one", b"two-two"]
    assert object_upload.completed is True
    assert stored == StoredEpisodeAudio(
        object_key="shows/show-1/episodes/episode-9/audio.mp3",
        output_format="mp3",
        content_type="audio/mpeg",
        duration_seconds=3.0,
        size_bytes=10,
        turn_timings=_timings(),
    )


async def test_retrying_the_same_episode_reuses_the_object_key() -> None:
    store = FakeAudioObjectStore()
    repository = AudioRepository(object_store=store)

    await repository.begin_upload(
        show_id="show-1",
        episode_id="episode-9",
        output_format="mp3",
    )
    await repository.begin_upload(
        show_id="show-1",
        episode_id="episode-9",
        output_format="mp3",
    )

    assert [upload[0] for upload in store.uploads] == [
        "shows/show-1/episodes/episode-9/audio.mp3",
        "shows/show-1/episodes/episode-9/audio.mp3",
    ]


async def test_abort_is_forwarded_to_the_object_upload() -> None:
    store = FakeAudioObjectStore()
    repository = AudioRepository(object_store=store)
    upload = await repository.begin_upload(
        show_id="show-1",
        episode_id="episode-9",
        output_format="mp3",
    )

    await upload.write(content=b"partial")
    await upload.abort()

    object_upload = store.uploads[0][2]
    assert object_upload.writes == [b"partial"]
    assert object_upload.aborted is True
    assert object_upload.completed is False


async def test_unsupported_output_format_does_not_start_an_upload() -> None:
    store = FakeAudioObjectStore()
    repository = AudioRepository(object_store=store)

    with pytest.raises(ValueError, match="Unsupported audio output format"):
        await repository.begin_upload(
            show_id="show-1",
            episode_id="episode-9",
            output_format="wav",
        )

    assert store.uploads == []
