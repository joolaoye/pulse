from dataclasses import dataclass
from typing import List, Optional

from pulse.types import (
    AssembledEpisodeAudio,
    EpisodeTurnTiming,
    SynthesizedDialogueBatch,
)

DEFAULT_TURN_TIMING_TOLERANCE_SECONDS = 0.05
ASSEMBLED_OUTPUT_FORMAT = "mp3"


@dataclass(frozen=True)
class AssembledAudioChunk:
    audio_content: bytes


@dataclass(frozen=True)
class _Mp3FrameHeader:
    mpeg_version: str
    bitrate_kbps: int
    sample_rate_hz: int
    channels: int
    frame_length_bytes: int
    samples_per_frame: int
    has_crc: bool


@dataclass(frozen=True)
class _Mp3StreamParameters:
    mpeg_version: str
    bitrate_kbps: int
    sample_rate_hz: int
    channels: int


@dataclass(frozen=True)
class _ParsedMp3Batch:
    audio_content: bytes
    duration_seconds: float
    parameters: _Mp3StreamParameters


class AudioAssemblySession:
    def __init__(
        self,
        *,
        turn_timing_tolerance_seconds: float,
    ) -> None:
        self._turn_timing_tolerance_seconds = turn_timing_tolerance_seconds
        self._expected_batch_index = 0
        self._next_script_turn_index = 0
        self._output_format: Optional[str] = None
        self._parameters: Optional[_Mp3StreamParameters] = None
        self._duration_seconds = 0.0
        self._turn_timings: List[EpisodeTurnTiming] = []
        self._completed = False

    def process_batch(
        self,
        *,
        synthesized_dialogue_batch: SynthesizedDialogueBatch,
    ) -> AssembledAudioChunk:
        if self._completed:
            raise RuntimeError("Audio assembly is already complete.")

        self._validate_batch_sequence(
            synthesized_dialogue_batch=synthesized_dialogue_batch,
        )

        parsed_batch = _parse_mp3_batch(
            synthesized_dialogue_batch=synthesized_dialogue_batch,
        )

        if self._parameters is None:
            self._parameters = parsed_batch.parameters
        else:
            _validate_batch_compatibility(
                reference_parameters=self._parameters,
                observed_parameters=parsed_batch.parameters,
                batch_index=synthesized_dialogue_batch.batch_index,
            )

        self._validate_turn_timing_bounds(
            synthesized_dialogue_batch=synthesized_dialogue_batch,
            parsed_duration_seconds=parsed_batch.duration_seconds,
        )

        episode_offset_seconds = self._duration_seconds
        self._turn_timings.extend(
            EpisodeTurnTiming(
                script_turn_index=turn_timing.script_turn_index,
                speaker_id=turn_timing.speaker_id,
                start_time_seconds=(episode_offset_seconds + turn_timing.start_time_seconds),
                end_time_seconds=(episode_offset_seconds + turn_timing.end_time_seconds),
            )
            for turn_timing in synthesized_dialogue_batch.turn_timings
        )
        self._duration_seconds += parsed_batch.duration_seconds
        self._expected_batch_index += 1
        self._next_script_turn_index += len(synthesized_dialogue_batch.turn_timings)

        return AssembledAudioChunk(
            audio_content=parsed_batch.audio_content,
        )

    def complete(self) -> AssembledEpisodeAudio:
        if self._completed:
            raise RuntimeError("Audio assembly is already complete.")

        if self._expected_batch_index == 0 or self._parameters is None:
            raise ValueError("Audio assembly requires at least one synthesized dialogue batch.")

        self._completed = True

        return AssembledEpisodeAudio(
            output_format=ASSEMBLED_OUTPUT_FORMAT,
            duration_seconds=self._duration_seconds,
            turn_timings=self._turn_timings,
        )

    def _validate_batch_sequence(
        self,
        *,
        synthesized_dialogue_batch: SynthesizedDialogueBatch,
    ) -> None:
        if synthesized_dialogue_batch.batch_index != self._expected_batch_index:
            raise ValueError(
                "Direct MP3 assembly received a non-contiguous "
                f"batch index. Expected {self._expected_batch_index}, "
                f"received {synthesized_dialogue_batch.batch_index}."
            )

        if self._output_format is None:
            self._output_format = synthesized_dialogue_batch.output_format
        elif synthesized_dialogue_batch.output_format != self._output_format:
            raise ValueError(
                "Direct MP3 assembly requires every synthesized "
                "batch to use the same input format. "
                f"Expected '{self._output_format}', received "
                f"'{synthesized_dialogue_batch.output_format}' for batch "
                f"{synthesized_dialogue_batch.batch_index}."
            )

        input_format = (
            synthesized_dialogue_batch.output_format.split("_", maxsplit=1)[0].strip().lower()
        )

        if input_format != "mp3":
            raise ValueError(
                "Direct MP3 assembly only supports synthesized "
                f"MP3 batches. Received '{input_format}'."
            )

        if not synthesized_dialogue_batch.audio_content:
            raise ValueError(
                "Direct MP3 assembly received empty audio content "
                f"for batch {synthesized_dialogue_batch.batch_index}."
            )

        if not synthesized_dialogue_batch.turn_timings:
            raise ValueError(
                "Direct MP3 assembly received no turn timings for batch "
                f"{synthesized_dialogue_batch.batch_index}."
            )

        observed_script_turn_indexes = [
            timing.script_turn_index for timing in synthesized_dialogue_batch.turn_timings
        ]
        expected_script_turn_indexes = list(
            range(
                self._next_script_turn_index,
                self._next_script_turn_index + len(observed_script_turn_indexes),
            )
        )

        if observed_script_turn_indexes != expected_script_turn_indexes:
            raise ValueError(
                "Direct MP3 assembly received changed, duplicated, "
                "or non-contiguous script-turn indexes."
            )

    def _validate_turn_timing_bounds(
        self,
        *,
        synthesized_dialogue_batch: SynthesizedDialogueBatch,
        parsed_duration_seconds: float,
    ) -> None:
        for turn_timing in synthesized_dialogue_batch.turn_timings:
            if turn_timing.end_time_seconds > (
                parsed_duration_seconds + self._turn_timing_tolerance_seconds
            ):
                raise ValueError(
                    "A synthesized turn timing extends beyond "
                    "its parsed MP3 batch. "
                    f"Batch: {synthesized_dialogue_batch.batch_index}. "
                    f"Script turn: "
                    f"{turn_timing.script_turn_index}. "
                    f"Turn end: "
                    f"{turn_timing.end_time_seconds:.3f}s. "
                    f"Parsed duration: "
                    f"{parsed_duration_seconds:.3f}s."
                )


class AudioAssembler:
    output_format = ASSEMBLED_OUTPUT_FORMAT

    def __init__(
        self,
        *,
        turn_timing_tolerance_seconds: float = (DEFAULT_TURN_TIMING_TOLERANCE_SECONDS),
    ) -> None:
        if turn_timing_tolerance_seconds < 0:
            raise ValueError("Turn timing tolerance must be non-negative.")

        self.turn_timing_tolerance_seconds = turn_timing_tolerance_seconds

    def create_session(self) -> AudioAssemblySession:
        return AudioAssemblySession(
            turn_timing_tolerance_seconds=self.turn_timing_tolerance_seconds,
        )


def _parse_mp3_batch(
    *,
    synthesized_dialogue_batch: SynthesizedDialogueBatch,
) -> _ParsedMp3Batch:
    audio = memoryview(synthesized_dialogue_batch.audio_content)
    start_offset, end_offset = _id3_bounds(audio)

    first_frame_offset = _find_first_frame_offset(
        audio=audio,
        start_offset=start_offset,
        end_offset=end_offset,
    )

    if first_frame_offset is None:
        raise RuntimeError(
            "Direct MP3 assembly could not find an MPEG audio "
            f"frame in batch {synthesized_dialogue_batch.batch_index}."
        )

    offset = first_frame_offset
    audio_start: Optional[int] = None
    audio_end: Optional[int] = None
    reference_header: Optional[_Mp3FrameHeader] = None
    total_samples = 0

    while offset + 4 <= end_offset:
        header = _parse_frame_header(
            audio=audio,
            offset=offset,
        )

        if header is None:
            if _is_zero_padding(
                audio=audio,
                start_offset=offset,
                end_offset=end_offset,
            ):
                break

            raise RuntimeError(
                "Direct MP3 assembly found unexpected non-frame "
                f"data inside batch "
                f"{synthesized_dialogue_batch.batch_index} "
                f"at byte offset {offset}."
            )

        frame_end = offset + header.frame_length_bytes

        if frame_end > end_offset:
            raise RuntimeError(
                "Direct MP3 assembly found a truncated MPEG frame "
                f"in batch {synthesized_dialogue_batch.batch_index}."
            )

        if audio_start is None and _is_metadata_frame(
            audio=audio,
            offset=offset,
            header=header,
        ):
            offset = frame_end
            continue

        if reference_header is None:
            reference_header = header
        else:
            _validate_frame_compatibility(
                reference_header=reference_header,
                observed_header=header,
                batch_index=synthesized_dialogue_batch.batch_index,
            )

        if audio_start is None:
            audio_start = offset

        audio_end = frame_end
        total_samples += header.samples_per_frame
        offset = frame_end

    if reference_header is None or audio_start is None or audio_end is None:
        raise RuntimeError(
            "Direct MP3 assembly found no usable audio frames "
            f"in batch {synthesized_dialogue_batch.batch_index}."
        )

    return _ParsedMp3Batch(
        audio_content=bytes(audio[audio_start:audio_end]),
        duration_seconds=(total_samples / reference_header.sample_rate_hz),
        parameters=_Mp3StreamParameters(
            mpeg_version=reference_header.mpeg_version,
            bitrate_kbps=reference_header.bitrate_kbps,
            sample_rate_hz=reference_header.sample_rate_hz,
            channels=reference_header.channels,
        ),
    )


def _id3_bounds(
    audio: memoryview,
) -> tuple[int, int]:
    start_offset = 0
    end_offset = len(audio)

    if len(audio) >= 10 and bytes(audio[:3]) == b"ID3":
        size_bytes = bytes(audio[6:10])

        if any(value & 0x80 for value in size_bytes):
            raise RuntimeError("Direct MP3 assembly found an invalid ID3v2 synchsafe size.")

        tag_size = (
            (size_bytes[0] << 21) | (size_bytes[1] << 14) | (size_bytes[2] << 7) | size_bytes[3]
        )
        start_offset = 10 + tag_size

        if audio[5] & 0x10:
            start_offset += 10

    if (
        end_offset - start_offset >= 128
        and bytes(audio[end_offset - 128 : end_offset - 125]) == b"TAG"
    ):
        end_offset -= 128

    if start_offset > end_offset:
        return end_offset, end_offset

    return start_offset, end_offset


def _find_first_frame_offset(
    *,
    audio: memoryview,
    start_offset: int,
    end_offset: int,
) -> Optional[int]:
    for offset in range(start_offset, max(start_offset, end_offset - 3)):
        header = _parse_frame_header(
            audio=audio,
            offset=offset,
        )

        if header is not None and offset + header.frame_length_bytes <= end_offset:
            return offset

    return None


def _parse_frame_header(
    *,
    audio: memoryview,
    offset: int,
) -> Optional[_Mp3FrameHeader]:
    if offset + 4 > len(audio):
        return None

    header_value = int.from_bytes(
        audio[offset : offset + 4],
        byteorder="big",
    )

    if header_value & 0xFFE00000 != 0xFFE00000:
        return None

    version_bits = (header_value >> 19) & 0b11
    layer_bits = (header_value >> 17) & 0b11
    protection_bit = (header_value >> 16) & 0b1
    bitrate_index = (header_value >> 12) & 0b1111
    sample_rate_index = (header_value >> 10) & 0b11
    padding = (header_value >> 9) & 0b1
    channel_mode = (header_value >> 6) & 0b11

    if version_bits == 0b01:
        return None

    if layer_bits != 0b01:
        return None

    if bitrate_index in (0, 15):
        return None

    if sample_rate_index == 3:
        return None

    if version_bits == 0b11:
        mpeg_version = "1"
        bitrate_table = [
            32,
            40,
            48,
            56,
            64,
            80,
            96,
            112,
            128,
            160,
            192,
            224,
            256,
            320,
        ]
        sample_rate_table = [
            44100,
            48000,
            32000,
        ]
        samples_per_frame = 1152
        frame_length_bytes = (
            144000 * bitrate_table[bitrate_index - 1] // sample_rate_table[sample_rate_index]
            + padding
        )
    elif version_bits == 0b10:
        mpeg_version = "2"
        bitrate_table = [
            8,
            16,
            24,
            32,
            40,
            48,
            56,
            64,
            80,
            96,
            112,
            128,
            144,
            160,
        ]
        sample_rate_table = [
            22050,
            24000,
            16000,
        ]
        samples_per_frame = 576
        frame_length_bytes = (
            72000 * bitrate_table[bitrate_index - 1] // sample_rate_table[sample_rate_index]
            + padding
        )
    else:
        mpeg_version = "2.5"
        bitrate_table = [
            8,
            16,
            24,
            32,
            40,
            48,
            56,
            64,
            80,
            96,
            112,
            128,
            144,
            160,
        ]
        sample_rate_table = [
            11025,
            12000,
            8000,
        ]
        samples_per_frame = 576
        frame_length_bytes = (
            72000 * bitrate_table[bitrate_index - 1] // sample_rate_table[sample_rate_index]
            + padding
        )

    return _Mp3FrameHeader(
        mpeg_version=mpeg_version,
        bitrate_kbps=bitrate_table[bitrate_index - 1],
        sample_rate_hz=sample_rate_table[sample_rate_index],
        channels=1 if channel_mode == 0b11 else 2,
        frame_length_bytes=frame_length_bytes,
        samples_per_frame=samples_per_frame,
        has_crc=protection_bit == 0,
    )


def _is_metadata_frame(
    *,
    audio: memoryview,
    offset: int,
    header: _Mp3FrameHeader,
) -> bool:
    crc_length = 2 if header.has_crc else 0

    if header.mpeg_version == "1":
        side_information_length = 17 if header.channels == 1 else 32
    else:
        side_information_length = 9 if header.channels == 1 else 17

    frame_end = offset + header.frame_length_bytes
    xing_offset = offset + 4 + crc_length + side_information_length

    if _frame_tag(
        audio=audio,
        tag_offset=xing_offset,
        frame_end=frame_end,
    ) in (
        b"Xing",
        b"Info",
    ):
        return True

    return (
        _frame_tag(
            audio=audio,
            tag_offset=offset + 4 + 32,
            frame_end=frame_end,
        )
        == b"VBRI"
    )


def _frame_tag(
    *,
    audio: memoryview,
    tag_offset: int,
    frame_end: int,
) -> bytes:
    tag_end = tag_offset + 4

    if tag_end > frame_end or tag_end > len(audio):
        return b""

    return bytes(audio[tag_offset:tag_end])


def _is_zero_padding(
    *,
    audio: memoryview,
    start_offset: int,
    end_offset: int,
) -> bool:
    return all(audio[index] == 0 for index in range(start_offset, end_offset))


def _validate_frame_compatibility(
    *,
    reference_header: _Mp3FrameHeader,
    observed_header: _Mp3FrameHeader,
    batch_index: int,
) -> None:
    if observed_header.mpeg_version != reference_header.mpeg_version:
        raise ValueError(
            f"Direct MP3 assembly found incompatible MPEG versions inside batch {batch_index}."
        )

    if observed_header.sample_rate_hz != reference_header.sample_rate_hz:
        raise ValueError(
            f"Direct MP3 assembly found incompatible sample rates inside batch {batch_index}."
        )

    if observed_header.channels != reference_header.channels:
        raise ValueError(
            f"Direct MP3 assembly found incompatible channel counts inside batch {batch_index}."
        )

    if observed_header.bitrate_kbps != reference_header.bitrate_kbps:
        raise ValueError(
            "Direct MP3 assembly found variable-bitrate audio "
            f"in batch {batch_index}. The assembler currently "
            "requires CBR MP3."
        )


def _validate_batch_compatibility(
    *,
    reference_parameters: _Mp3StreamParameters,
    observed_parameters: _Mp3StreamParameters,
    batch_index: int,
) -> None:
    if observed_parameters.mpeg_version != reference_parameters.mpeg_version:
        raise ValueError(
            f"Direct MP3 assembly received incompatible MPEG versions. Batch: {batch_index}."
        )

    if observed_parameters.sample_rate_hz != reference_parameters.sample_rate_hz:
        raise ValueError(
            "Direct MP3 assembly received incompatible sample "
            f"rates. Batch: {batch_index}. Expected: "
            f"{reference_parameters.sample_rate_hz} Hz. Received: "
            f"{observed_parameters.sample_rate_hz} Hz."
        )

    if observed_parameters.channels != reference_parameters.channels:
        raise ValueError(
            "Direct MP3 assembly received incompatible channel "
            f"counts. Batch: {batch_index}. Expected: "
            f"{reference_parameters.channels}. Received: "
            f"{observed_parameters.channels}."
        )

    if observed_parameters.bitrate_kbps != reference_parameters.bitrate_kbps:
        raise ValueError(
            "Direct MP3 assembly received incompatible bitrates. "
            f"Batch: {batch_index}. Expected: "
            f"{reference_parameters.bitrate_kbps} kbps. Received: "
            f"{observed_parameters.bitrate_kbps} kbps."
        )
