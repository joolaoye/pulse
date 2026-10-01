from typing import List

import pytest

from pulse.services.audio.assembler import AudioAssembler
from pulse.types import (
    AssembledEpisodeAudio,
    SynthesizedDialogueBatch,
    SynthesizedTurnTiming,
)

MPEG1_FRAME_SAMPLES = 1152
MPEG1_SAMPLE_RATE_HZ = 44100


def _frame_length(
    *,
    version_bits: int,
    bitrate_index: int,
    sample_rate_index: int,
    padding: int = 0,
) -> int:
    if version_bits == 0b11:
        bitrate_table = [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
        sample_rate_table = [44100, 48000, 32000]
        scale = 144000
    else:
        bitrate_table = [8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
        sample_rate_table = [22050, 24000, 16000] if version_bits == 0b10 else [11025, 12000, 8000]
        scale = 72000

    return (
        scale * bitrate_table[bitrate_index - 1] // sample_rate_table[sample_rate_index] + padding
    )


def _header(
    *,
    version_bits: int = 0b11,
    bitrate_index: int = 9,
    sample_rate_index: int = 0,
    padding: int = 0,
    channel_mode: int = 0,
) -> bytes:
    value = 0xFFE00000
    value |= (version_bits & 0b11) << 19
    value |= 0b01 << 17
    value |= 1 << 16
    value |= (bitrate_index & 0b1111) << 12
    value |= (sample_rate_index & 0b11) << 10
    value |= (padding & 1) << 9
    value |= (channel_mode & 0b11) << 6

    return value.to_bytes(4, "big")


def build_frame(
    *,
    version_bits: int = 0b11,
    bitrate_index: int = 9,
    sample_rate_index: int = 0,
    padding: int = 0,
    channel_mode: int = 0,
    marker: int = 0,
    metadata_tag: bytes | None = None,
) -> bytes:
    frame = bytearray(
        _frame_length(
            version_bits=version_bits,
            bitrate_index=bitrate_index,
            sample_rate_index=sample_rate_index,
            padding=padding,
        )
    )
    frame[:4] = _header(
        version_bits=version_bits,
        bitrate_index=bitrate_index,
        sample_rate_index=sample_rate_index,
        padding=padding,
        channel_mode=channel_mode,
    )
    frame[4] = marker

    if metadata_tag is not None:
        frame[36:40] = metadata_tag

    return bytes(frame)


def _id3v2(payload: bytes) -> bytes:
    size = len(payload)
    size_bytes = bytes(
        [
            (size >> 21) & 0x7F,
            (size >> 14) & 0x7F,
            (size >> 7) & 0x7F,
            size & 0x7F,
        ]
    )

    return b"ID3" + bytes([3, 0, 0]) + size_bytes + payload


def _id3v1() -> bytes:
    return b"TAG" + (b"\x00" * 125)


def _batch(
    *,
    batch_index: int,
    audio: bytes,
    turns: List[tuple[int, str, float, float]],
    output_format: str = "mp3_44100_128",
    duration_seconds: float = 30.0,
) -> SynthesizedDialogueBatch:
    return SynthesizedDialogueBatch(
        batch_index=batch_index,
        audio_content=audio,
        output_format=output_format,
        duration_seconds=duration_seconds,
        turn_timings=[
            SynthesizedTurnTiming(
                script_turn_index=script_turn_index,
                speaker_id=speaker_id,
                start_time_seconds=start_time_seconds,
                end_time_seconds=end_time_seconds,
            )
            for script_turn_index, speaker_id, start_time_seconds, end_time_seconds in turns
        ],
    )


def _retained_audio_lengths(value: object, seen: set[int] | None = None) -> List[int]:
    if seen is None:
        seen = set()

    marker = id(value)

    if marker in seen:
        return []

    seen.add(marker)

    if isinstance(value, (bytes, bytearray, memoryview)):
        return [len(value)] if len(value) else []

    if isinstance(value, dict):
        lengths: List[int] = []

        for item in value.values():
            lengths.extend(_retained_audio_lengths(item, seen))

        return lengths

    if isinstance(value, (list, tuple, set)):
        lengths = []

        for item in value:
            lengths.extend(_retained_audio_lengths(item, seen))

        return lengths

    if hasattr(value, "__dict__"):
        lengths = []

        for item in vars(value).values():
            lengths.extend(_retained_audio_lengths(item, seen))

        return lengths

    return []


def _frame_duration_seconds(*, frame_count: int) -> float:
    return frame_count * MPEG1_FRAME_SAMPLES / MPEG1_SAMPLE_RATE_HZ


def test_valid_batches_accumulate_episode_timing_without_retaining_audio() -> None:
    first_frame = build_frame(marker=0x11)
    second_frame = build_frame(marker=0x22)
    session = AudioAssembler().create_session()

    first_chunk = session.process_batch(
        synthesized_dialogue_batch=_batch(
            batch_index=0,
            audio=first_frame * 2,
            turns=[(0, "host", 0.0, 0.01)],
        ),
    )
    second_chunk = session.process_batch(
        synthesized_dialogue_batch=_batch(
            batch_index=1,
            audio=second_frame,
            turns=[(1, "guest", 0.0, 0.02)],
            duration_seconds=10.0,
        ),
    )
    metadata = session.complete()
    first_duration = _frame_duration_seconds(frame_count=2)

    assert first_chunk.audio_content == first_frame * 2
    assert second_chunk.audio_content == second_frame
    assert isinstance(metadata, AssembledEpisodeAudio)
    assert metadata.output_format == "mp3"
    assert metadata.duration_seconds == pytest.approx(
        first_duration + _frame_duration_seconds(frame_count=1)
    )
    assert metadata.turn_timings[0].script_turn_index == 0
    assert metadata.turn_timings[0].speaker_id == "host"
    assert metadata.turn_timings[0].start_time_seconds == 0.0
    assert metadata.turn_timings[0].end_time_seconds == 0.01
    assert metadata.turn_timings[1].script_turn_index == 1
    assert metadata.turn_timings[1].speaker_id == "guest"
    assert metadata.turn_timings[1].start_time_seconds == pytest.approx(first_duration)
    assert metadata.turn_timings[1].end_time_seconds == pytest.approx(first_duration + 0.02)
    assert set(metadata.model_dump().keys()) == {
        "output_format",
        "duration_seconds",
        "turn_timings",
    }
    assert not hasattr(metadata, "audio_content")
    assert _retained_audio_lengths(session) == []


@pytest.mark.parametrize(
    ("frame", "match"),
    [
        (
            build_frame(version_bits=0b10, bitrate_index=9, sample_rate_index=0),
            "incompatible MPEG versions",
        ),
        (
            build_frame(sample_rate_index=1),
            "incompatible sample",
        ),
        (
            build_frame(channel_mode=0b11),
            "incompatible channel",
        ),
        (
            build_frame(bitrate_index=10),
            "incompatible bitrates",
        ),
    ],
)
def test_incompatible_follow_up_batch_is_rejected(frame: bytes, match: str) -> None:
    session = AudioAssembler().create_session()
    session.process_batch(
        synthesized_dialogue_batch=_batch(
            batch_index=0,
            audio=build_frame(),
            turns=[(0, "host", 0.0, 0.01)],
        ),
    )

    with pytest.raises(ValueError, match=match):
        session.process_batch(
            synthesized_dialogue_batch=_batch(
                batch_index=1,
                audio=frame,
                turns=[(1, "guest", 0.0, 0.01)],
            ),
        )


def test_non_contiguous_batch_index_is_rejected() -> None:
    session = AudioAssembler().create_session()
    session.process_batch(
        synthesized_dialogue_batch=_batch(
            batch_index=0,
            audio=build_frame(),
            turns=[(0, "host", 0.0, 0.01)],
        ),
    )

    with pytest.raises(ValueError, match="non-contiguous"):
        session.process_batch(
            synthesized_dialogue_batch=_batch(
                batch_index=2,
                audio=build_frame(),
                turns=[(1, "guest", 0.0, 0.01)],
            ),
        )


def test_non_contiguous_script_turn_indexes_are_rejected() -> None:
    session = AudioAssembler().create_session()
    session.process_batch(
        synthesized_dialogue_batch=_batch(
            batch_index=0,
            audio=build_frame(),
            turns=[(0, "host", 0.0, 0.01)],
        ),
    )

    with pytest.raises(ValueError, match="script-turn"):
        session.process_batch(
            synthesized_dialogue_batch=_batch(
                batch_index=1,
                audio=build_frame(),
                turns=[(2, "guest", 0.0, 0.01)],
            ),
        )


@pytest.mark.parametrize("metadata_tag", [b"Xing", b"Info", b"VBRI"])
def test_metadata_frames_and_id3_tags_are_excluded(metadata_tag: bytes) -> None:
    audio_frame = build_frame(marker=0x5A)
    tagged_audio = _id3v2(b"SKIP") + build_frame(metadata_tag=metadata_tag) + audio_frame + _id3v1()
    session = AudioAssembler().create_session()

    chunk = session.process_batch(
        synthesized_dialogue_batch=_batch(
            batch_index=0,
            audio=tagged_audio,
            turns=[(0, "host", 0.0, 0.01)],
        ),
    )
    metadata = session.complete()

    assert chunk.audio_content == audio_frame
    assert metadata_tag not in chunk.audio_content
    assert b"ID3" not in chunk.audio_content
    assert b"TAG" not in chunk.audio_content
    assert metadata.duration_seconds == pytest.approx(_frame_duration_seconds(frame_count=1))
    assert _retained_audio_lengths(session) == []


def test_turn_timing_past_parsed_duration_is_rejected() -> None:
    session = AudioAssembler().create_session()

    with pytest.raises(ValueError, match="extends beyond"):
        session.process_batch(
            synthesized_dialogue_batch=_batch(
                batch_index=0,
                audio=build_frame(),
                turns=[(0, "host", 0.0, 1.0)],
                duration_seconds=1.0,
            ),
        )


def test_many_batches_are_not_concatenated() -> None:
    session = AudioAssembler().create_session()
    frames = [build_frame(marker=index + 1) for index in range(6)]
    chunks = [
        session.process_batch(
            synthesized_dialogue_batch=_batch(
                batch_index=index,
                audio=frame,
                turns=[(index, "host", 0.0, 0.01)],
            ),
        )
        for index, frame in enumerate(frames)
    ]
    metadata = session.complete()

    assert [chunk.audio_content for chunk in chunks] == frames
    assert metadata.duration_seconds == pytest.approx(
        _frame_duration_seconds(frame_count=len(frames))
    )
    assert len(metadata.turn_timings) == len(frames)
    assert _retained_audio_lengths(session) == []
    assert not hasattr(metadata, "audio_content")
