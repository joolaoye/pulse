from typing import Any, List, cast

import pytest

from pulse.infrastructure.storage.r2.object_store import WorkerR2AudioObjectStore
from pulse.infrastructure.storage.repositories.audio import AudioRepository
from pulse.services.audio.assembler import AssembledAudioChunk
from pulse.services.audio.producer import AudioProducer
from pulse.types import (
    AssembledEpisodeAudio,
    DialogueBatch,
    DialogueBatchTurn,
    EpisodeScript,
    EpisodeTurnTiming,
    ScriptTurn,
    SpeakerVoiceBinding,
    StoredEpisodeAudio,
    SynthesizedDialogueBatch,
    SynthesizedTurnTiming,
)

BATCH_COUNT = 20


class RecordingSynthesizer:
    def __init__(
        self,
        *,
        events: List[tuple[Any, ...]],
        fail_at: int | None = None,
    ) -> None:
        self.events = events
        self.fail_at = fail_at

    async def synthesize(
        self,
        *,
        dialogue_batches: List[DialogueBatch],
    ) -> List[SynthesizedDialogueBatch]:
        self.events.append(("synthesize_all", len(dialogue_batches)))
        raise AssertionError("Audio production must not bulk-synthesize dialogue batches.")

    async def synthesize_batch(
        self,
        *,
        dialogue_batch: DialogueBatch,
    ) -> SynthesizedDialogueBatch:
        self.events.append(("synthesize", dialogue_batch.batch_index))

        if dialogue_batch.batch_index == self.fail_at:
            raise RuntimeError("synthesis failed")

        turn = dialogue_batch.turns[0]

        return SynthesizedDialogueBatch(
            batch_index=dialogue_batch.batch_index,
            audio_content=f"audio-{dialogue_batch.batch_index}".encode(),
            output_format="mp3_44100_128",
            duration_seconds=1.0,
            turn_timings=[
                SynthesizedTurnTiming(
                    script_turn_index=turn.script_turn_index,
                    speaker_id=turn.speaker_id,
                    start_time_seconds=0.0,
                    end_time_seconds=1.0,
                )
            ],
        )


class RecordingSession:
    def __init__(
        self,
        *,
        events: List[tuple[Any, ...]],
        fail_at: int | None = None,
    ) -> None:
        self.events = events
        self.fail_at = fail_at

    def process_batch(
        self,
        *,
        synthesized_dialogue_batch: SynthesizedDialogueBatch,
    ) -> AssembledAudioChunk:
        self.events.append(("process", synthesized_dialogue_batch.batch_index))

        if synthesized_dialogue_batch.batch_index == self.fail_at:
            raise RuntimeError("assembly failed")

        return AssembledAudioChunk(
            audio_content=f"chunk-{synthesized_dialogue_batch.batch_index}".encode(),
        )

    def complete(self) -> AssembledEpisodeAudio:
        self.events.append(("assembly_complete",))

        return AssembledEpisodeAudio(
            output_format="mp3",
            duration_seconds=float(BATCH_COUNT),
            turn_timings=[
                EpisodeTurnTiming(
                    script_turn_index=0,
                    speaker_id="host",
                    start_time_seconds=0.0,
                    end_time_seconds=1.0,
                )
            ],
        )


class RecordingAssembler:
    output_format = "mp3"

    def __init__(
        self,
        *,
        events: List[tuple[Any, ...]],
        fail_at: int | None = None,
    ) -> None:
        self.session = RecordingSession(
            events=events,
            fail_at=fail_at,
        )

    def create_session(self) -> RecordingSession:
        return self.session


class RecordingUpload:
    def __init__(
        self,
        *,
        events: List[tuple[Any, ...]],
        stored: StoredEpisodeAudio,
        fail_at: int | None = None,
        abort_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.stored = stored
        self.fail_at = fail_at
        self.abort_error = abort_error
        self.completed_with: dict[str, Any] | None = None
        self.aborted = False

    async def write(
        self,
        *,
        content: bytes,
    ) -> None:
        self.events.append(("write", content))

        if content == f"chunk-{self.fail_at}".encode():
            raise RuntimeError("write failed")

    async def complete(
        self,
        *,
        duration_seconds: float,
        turn_timings: List[EpisodeTurnTiming],
    ) -> StoredEpisodeAudio:
        self.events.append(("upload_complete",))
        self.completed_with = {
            "duration_seconds": duration_seconds,
            "turn_timings": turn_timings,
        }

        return self.stored

    async def abort(self) -> None:
        self.events.append(("abort",))
        self.aborted = True

        if self.abort_error is not None:
            raise self.abort_error


class RecordingRepository:
    def __init__(
        self,
        *,
        upload: RecordingUpload,
        events: List[tuple[Any, ...]],
    ) -> None:
        self.upload = upload
        self.events = events

    async def begin_upload(
        self,
        *,
        show_id: str,
        episode_id: str,
        output_format: str,
    ) -> RecordingUpload:
        self.events.append(("begin_upload", show_id, episode_id, output_format))

        return self.upload


class RecordingBatcher:
    def __init__(
        self,
        *,
        batches: List[DialogueBatch],
    ) -> None:
        self.batches = batches

    def batch(
        self,
        *,
        episode_script: EpisodeScript,
        speaker_voice_bindings: List[SpeakerVoiceBinding],
    ) -> List[DialogueBatch]:
        del episode_script, speaker_voice_bindings

        return self.batches


def _batches(count: int) -> List[DialogueBatch]:
    return [
        DialogueBatch(
            batch_index=index,
            turns=[
                DialogueBatchTurn(
                    script_turn_index=index,
                    speaker_id="host",
                    voice_id="voice-1",
                    spoken_text=f"Turn {index}",
                )
            ],
        )
        for index in range(count)
    ]


def _stored_audio() -> StoredEpisodeAudio:
    return StoredEpisodeAudio(
        object_key="shows/show-1/episodes/episode-1/audio.mp3",
        output_format="mp3",
        content_type="audio/mpeg",
        duration_seconds=float(BATCH_COUNT),
        size_bytes=12,
        turn_timings=[
            EpisodeTurnTiming(
                script_turn_index=0,
                speaker_id="host",
                start_time_seconds=0.0,
                end_time_seconds=1.0,
            )
        ],
    )


def _script() -> EpisodeScript:
    return EpisodeScript(
        turns=[
            ScriptTurn(
                speaker_id="host",
                spoken_text="Hello",
            )
        ]
    )


def _bindings() -> List[SpeakerVoiceBinding]:
    return [
        SpeakerVoiceBinding(
            speaker_id="host",
            voice_id="voice-1",
        )
    ]


def _producer(
    *,
    events: List[tuple[Any, ...]],
    upload: RecordingUpload,
    synthesis_fail_at: int | None = None,
    assembly_fail_at: int | None = None,
) -> AudioProducer:
    return AudioProducer(
        dialogue_batcher=cast(
            Any,
            RecordingBatcher(batches=_batches(BATCH_COUNT)),
        ),
        dialogue_synthesizer=cast(
            Any,
            RecordingSynthesizer(
                events=events,
                fail_at=synthesis_fail_at,
            ),
        ),
        audio_assembler=cast(
            Any,
            RecordingAssembler(
                events=events,
                fail_at=assembly_fail_at,
            ),
        ),
        audio_repository=cast(
            Any,
            RecordingRepository(
                upload=upload,
                events=events,
            ),
        ),
    )


async def test_batches_are_synthesized_processed_and_written_one_at_a_time() -> None:
    events: List[tuple[Any, ...]] = []
    stored = _stored_audio()
    upload = RecordingUpload(
        events=events,
        stored=stored,
    )
    producer = _producer(
        events=events,
        upload=upload,
    )

    result = await producer.produce(
        show_id="show-1",
        episode_id="episode-1",
        episode_script=_script(),
        speaker_voice_bindings=_bindings(),
    )

    expected: List[tuple[Any, ...]] = [
        ("begin_upload", "show-1", "episode-1", "mp3"),
    ]

    for index in range(BATCH_COUNT):
        expected.extend(
            [
                ("synthesize", index),
                ("process", index),
                ("write", f"chunk-{index}".encode()),
            ]
        )

    expected.extend(
        [
            ("assembly_complete",),
            ("upload_complete",),
        ]
    )

    assert events == expected
    assert [event[0] for event in events if event[0] in {"synthesize", "process", "write"}] == [
        phase for _index in range(BATCH_COUNT) for phase in ("synthesize", "process", "write")
    ]
    for index in range(BATCH_COUNT):
        synthesized_at = events.index(("synthesize", index))
        processed_at = events.index(("process", index))
        written_at = events.index(("write", f"chunk-{index}".encode()))
        assert synthesized_at < processed_at < written_at
        if index + 1 < BATCH_COUNT:
            assert written_at < events.index(("synthesize", index + 1))
    assert result is stored
    assert upload.completed_with is not None
    assert upload.completed_with["duration_seconds"] == float(BATCH_COUNT)
    assert upload.aborted is False
    assert not any(event[0] == "synthesize_all" for event in events)


async def test_synthesis_failure_aborts_the_upload_and_preserves_the_error() -> None:
    events: List[tuple[Any, ...]] = []
    upload = RecordingUpload(
        events=events,
        stored=_stored_audio(),
    )
    producer = _producer(
        events=events,
        upload=upload,
        synthesis_fail_at=1,
    )

    with pytest.raises(RuntimeError, match="synthesis failed"):
        await producer.produce(
            show_id="show-1",
            episode_id="episode-1",
            episode_script=_script(),
            speaker_voice_bindings=_bindings(),
        )

    assert events == [
        ("begin_upload", "show-1", "episode-1", "mp3"),
        ("synthesize", 0),
        ("process", 0),
        ("write", b"chunk-0"),
        ("synthesize", 1),
        ("abort",),
    ]
    assert upload.aborted is True
    assert upload.completed_with is None


async def test_assembly_failure_aborts_the_upload_and_preserves_the_error() -> None:
    events: List[tuple[Any, ...]] = []
    upload = RecordingUpload(
        events=events,
        stored=_stored_audio(),
    )
    producer = _producer(
        events=events,
        upload=upload,
        assembly_fail_at=1,
    )

    with pytest.raises(RuntimeError, match="assembly failed"):
        await producer.produce(
            show_id="show-1",
            episode_id="episode-1",
            episode_script=_script(),
            speaker_voice_bindings=_bindings(),
        )

    assert ("process", 1) in events
    assert ("write", b"chunk-1") not in events
    assert ("synthesize", 2) not in events
    assert events[-1] == ("abort",)
    assert upload.aborted is True
    assert upload.completed_with is None


async def test_write_failure_aborts_the_upload_and_preserves_the_error() -> None:
    events: List[tuple[Any, ...]] = []
    upload = RecordingUpload(
        events=events,
        stored=_stored_audio(),
        fail_at=0,
    )
    producer = _producer(
        events=events,
        upload=upload,
    )

    with pytest.raises(RuntimeError, match="write failed"):
        await producer.produce(
            show_id="show-1",
            episode_id="episode-1",
            episode_script=_script(),
            speaker_voice_bindings=_bindings(),
        )

    assert events == [
        ("begin_upload", "show-1", "episode-1", "mp3"),
        ("synthesize", 0),
        ("process", 0),
        ("write", b"chunk-0"),
        ("abort",),
    ]
    assert upload.aborted is True
    assert upload.completed_with is None


async def test_abort_failure_does_not_replace_the_original_error() -> None:
    events: List[tuple[Any, ...]] = []
    upload = RecordingUpload(
        events=events,
        stored=_stored_audio(),
        abort_error=RuntimeError("abort failed"),
    )
    producer = _producer(
        events=events,
        upload=upload,
        synthesis_fail_at=0,
    )

    with pytest.raises(RuntimeError, match="synthesis failed"):
        await producer.produce(
            show_id="show-1",
            episode_id="episode-1",
            episode_script=_script(),
            speaker_voice_bindings=_bindings(),
        )

    assert upload.aborted is True


class _MultipartUpload:
    def __init__(
        self,
        *,
        fail_part: bool = False,
        fail_complete: bool = False,
        fail_abort: bool = False,
    ) -> None:
        self.fail_part = fail_part
        self.fail_complete = fail_complete
        self.fail_abort = fail_abort
        self.parts: List[tuple[int, bytes]] = []
        self.completed = False
        self.aborted = False

    async def uploadPart(
        self,
        part_number: int,
        content: bytes,
    ) -> dict[str, Any]:
        if self.fail_part:
            raise RuntimeError("part upload failed")

        self.parts.append((part_number, bytes(content)))

        return {
            "partNumber": part_number,
            "etag": f"etag-{part_number}",
        }

    async def complete(
        self,
        parts: List[dict[str, Any]],
    ) -> None:
        del parts

        if self.fail_complete:
            raise RuntimeError("complete failed")

        self.completed = True

    async def abort(self) -> None:
        self.aborted = True

        if self.fail_abort:
            raise RuntimeError("abort failed")


class _MultipartBucket:
    def __init__(
        self,
        upload: _MultipartUpload,
    ) -> None:
        self.upload = upload
        self.keys: List[str] = []

    async def createMultipartUpload(
        self,
        object_key: str,
        options: dict[str, Any],
    ) -> _MultipartUpload:
        del options
        self.keys.append(object_key)

        return self.upload


def _worker_producer(
    *,
    events: List[tuple[Any, ...]],
    upload: _MultipartUpload,
) -> AudioProducer:
    return AudioProducer(
        dialogue_batcher=cast(
            Any,
            RecordingBatcher(batches=_batches(BATCH_COUNT)),
        ),
        dialogue_synthesizer=cast(
            Any,
            RecordingSynthesizer(events=events),
        ),
        audio_assembler=cast(
            Any,
            RecordingAssembler(events=events),
        ),
        audio_repository=AudioRepository(
            object_store=WorkerR2AudioObjectStore(
                bucket=_MultipartBucket(upload),
                part_size_bytes=4,
            ),
        ),
    )


async def test_multipart_part_upload_failure_aborts_without_returning_audio() -> None:
    events: List[tuple[Any, ...]] = []
    multipart = _MultipartUpload(fail_part=True)
    producer = _worker_producer(
        events=events,
        upload=multipart,
    )
    result: StoredEpisodeAudio | None = None

    with pytest.raises(RuntimeError, match="part upload failed"):
        result = await producer.produce(
            show_id="show-1",
            episode_id="episode-1",
            episode_script=_script(),
            speaker_voice_bindings=_bindings(),
        )

    assert result is None
    assert multipart.aborted is True
    assert multipart.completed is False
    assert ("synthesize", 1) not in events


async def test_multipart_completion_failure_propagates_and_aborts() -> None:
    events: List[tuple[Any, ...]] = []
    multipart = _MultipartUpload(fail_complete=True)
    producer = _worker_producer(
        events=events,
        upload=multipart,
    )
    result: StoredEpisodeAudio | None = None

    with pytest.raises(RuntimeError, match="complete failed"):
        result = await producer.produce(
            show_id="show-1",
            episode_id="episode-1",
            episode_script=_script(),
            speaker_voice_bindings=_bindings(),
        )

    assert result is None
    assert multipart.parts
    assert multipart.aborted is True
    assert multipart.completed is False
    assert ("assembly_complete",) in events


async def test_multipart_abort_failure_preserves_the_completion_error() -> None:
    events: List[tuple[Any, ...]] = []
    multipart = _MultipartUpload(
        fail_complete=True,
        fail_abort=True,
    )
    producer = _worker_producer(
        events=events,
        upload=multipart,
    )
    result: StoredEpisodeAudio | None = None

    with pytest.raises(RuntimeError, match="complete failed"):
        result = await producer.produce(
            show_id="show-1",
            episode_id="episode-1",
            episode_script=_script(),
            speaker_voice_bindings=_bindings(),
        )

    assert result is None
    assert multipart.aborted is True
