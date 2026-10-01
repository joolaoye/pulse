import asyncio
import base64
import binascii
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from pulse.infrastructure.tts.elevenlabs.config import (
    ELEVENLABS_TEXT_TO_DIALOGUE_WITH_TIMESTAMPS_URL,
    ElevenLabsConfig,
)
from pulse.infrastructure.tts.elevenlabs.models import (
    ElevenLabsDialogueInput,
    ElevenLabsDialogueResult,
    ElevenLabsProviderError,
    ElevenLabsVoiceSegment,
)


class ElevenLabsDialogueProvider:
    def __init__(
        self,
        *,
        config: ElevenLabsConfig,
    ) -> None:
        self.config = config
        self.http_client = httpx.AsyncClient(
            timeout=config.timeout_seconds,
        )

    async def synthesize(
        self,
        *,
        dialogue_inputs: List[ElevenLabsDialogueInput],
    ) -> ElevenLabsDialogueResult:
        self._validate_dialogue_inputs(
            dialogue_inputs=dialogue_inputs,
        )

        for attempt_index in range(self.config.max_attempts):
            try:
                return await self._synthesize_once(
                    dialogue_inputs=dialogue_inputs,
                )
            except ElevenLabsProviderError as error:
                final_attempt = attempt_index + 1 >= self.config.max_attempts

                if not error.retryable or final_attempt:
                    raise

                await asyncio.sleep(
                    self._retry_delay(
                        retry_index=attempt_index,
                    )
                )

        raise RuntimeError("ElevenLabs dialogue synthesis exhausted its attempts.")

    async def _synthesize_once(
        self,
        *,
        dialogue_inputs: List[ElevenLabsDialogueInput],
    ) -> ElevenLabsDialogueResult:
        try:
            response = await self.http_client.post(
                ELEVENLABS_TEXT_TO_DIALOGUE_WITH_TIMESTAMPS_URL,
                headers=self._build_headers(),
                params=self._build_query_params(),
                json=self._build_request_body(
                    dialogue_inputs=dialogue_inputs,
                ),
            )
        except (
            httpx.TransportError,
            TimeoutError,
        ) as error:
            raise ElevenLabsProviderError(
                message=(f"ElevenLabs dialogue synthesis encountered a transport failure: {error}"),
                retryable=True,
            ) from error

        if not response.is_success:
            raise self._translate_http_error(
                response=response,
            )

        response_body = self._parse_response_body(
            response=response,
        )

        audio_content = self._decode_audio_content(
            audio_base64=self._parse_audio_base64(
                response_body=response_body,
            )
        )

        voice_segments = self._parse_voice_segments(
            response_body=response_body,
        )

        self._validate_dialogue_result(
            dialogue_inputs=dialogue_inputs,
            audio_content=audio_content,
            voice_segments=voice_segments,
        )

        return ElevenLabsDialogueResult(
            audio_content=audio_content,
            voice_segments=voice_segments,
        )

    def _retry_delay(
        self,
        *,
        retry_index: int,
    ) -> float:
        delay = (
            self.config.initial_retry_delay_seconds
            * self.config.retry_backoff_multiplier**retry_index
        )

        return min(
            delay,
            self.config.max_retry_delay_seconds,
        )

    def _build_headers(self) -> Dict[str, str]:
        return {
            "xi-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }

    def _build_query_params(self) -> Dict[str, str]:
        return {
            "output_format": self.config.output_format,
        }

    def _build_request_body(
        self,
        *,
        dialogue_inputs: List[ElevenLabsDialogueInput],
    ) -> Dict[str, Any]:
        request_body: Dict[str, Any] = {
            "inputs": [
                {
                    "text": dialogue_input.text,
                    "voice_id": dialogue_input.voice_id,
                }
                for dialogue_input in dialogue_inputs
            ],
            "model_id": self.config.model_id,
            "apply_text_normalization": (self.config.text_normalization_mode),
        }

        if self.config.language_code is not None:
            request_body["language_code"] = self.config.language_code

        return request_body

    @staticmethod
    def _parse_response_body(
        *,
        response: httpx.Response,
    ) -> Dict[str, Any]:
        try:
            response_body = response.json()
        except ValueError as error:
            raise ElevenLabsProviderError(
                message=("ElevenLabs returned an invalid JSON response."),
                retryable=False,
                status_code=response.status_code,
            ) from error

        if not isinstance(response_body, dict):
            raise ElevenLabsProviderError(
                message=("ElevenLabs returned an unexpected response body."),
                retryable=False,
                status_code=response.status_code,
            )

        return response_body

    @staticmethod
    def _parse_audio_base64(
        *,
        response_body: Dict[str, Any],
    ) -> str:
        audio_base64 = response_body.get("audio_base64")

        if not isinstance(audio_base64, str):
            raise ValueError("ElevenLabs returned invalid base64 audio content.")

        if not audio_base64:
            raise ValueError("ElevenLabs returned empty base64 audio content.")

        return audio_base64

    def _parse_voice_segments(
        self,
        *,
        response_body: Dict[str, Any],
    ) -> List[ElevenLabsVoiceSegment]:
        raw_voice_segments = response_body.get("voice_segments")

        if not isinstance(raw_voice_segments, list):
            raise ValueError("ElevenLabs returned invalid voice segment data.")

        voice_segments: List[ElevenLabsVoiceSegment] = []

        for segment_index, raw_voice_segment in enumerate(raw_voice_segments):
            if not isinstance(raw_voice_segment, dict):
                raise ValueError(
                    f"ElevenLabs returned invalid voice segment data at index {segment_index}."
                )

            voice_segments.append(
                self._parse_voice_segment(
                    raw_voice_segment=raw_voice_segment,
                    segment_index=segment_index,
                )
            )

        return voice_segments

    @staticmethod
    def _parse_voice_segment(
        *,
        raw_voice_segment: Dict[str, Any],
        segment_index: int,
    ) -> ElevenLabsVoiceSegment:
        required_fields = {
            "voice_id",
            "start_time_seconds",
            "end_time_seconds",
            "character_start_index",
            "character_end_index",
            "dialogue_input_index",
        }

        missing_fields = required_fields - raw_voice_segment.keys()

        if missing_fields:
            raise ValueError(
                f"ElevenLabs voice segment {segment_index} "
                "is missing required fields: "
                f"{', '.join(sorted(missing_fields))}."
            )

        try:
            return ElevenLabsVoiceSegment(
                voice_id=raw_voice_segment["voice_id"],
                start_time_seconds=raw_voice_segment["start_time_seconds"],
                end_time_seconds=raw_voice_segment["end_time_seconds"],
                character_start_index=raw_voice_segment["character_start_index"],
                character_end_index=raw_voice_segment["character_end_index"],
                dialogue_input_index=raw_voice_segment["dialogue_input_index"],
            )
        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                f"ElevenLabs returned invalid voice segment data at index {segment_index}."
            ) from error

    @staticmethod
    def _validate_dialogue_inputs(
        *,
        dialogue_inputs: List[ElevenLabsDialogueInput],
    ) -> None:
        if not dialogue_inputs:
            raise ValueError("ElevenLabs dialogue synthesis requires at least one dialogue input.")

        for input_index, dialogue_input in enumerate(dialogue_inputs):
            if not dialogue_input.text.strip():
                raise ValueError(f"ElevenLabs dialogue input {input_index} contains blank text.")

            if not dialogue_input.voice_id.strip():
                raise ValueError(
                    f"ElevenLabs dialogue input {input_index} contains a blank voice identifier."
                )

    @staticmethod
    def _decode_audio_content(
        *,
        audio_base64: str,
    ) -> bytes:
        try:
            audio_content = base64.b64decode(
                audio_base64,
                validate=True,
            )
        except (
            binascii.Error,
            ValueError,
        ) as error:
            raise ValueError("ElevenLabs returned invalid base64 audio content.") from error

        if not audio_content:
            raise ValueError("ElevenLabs returned empty decoded audio content.")

        return audio_content

    @staticmethod
    def _validate_dialogue_result(
        *,
        dialogue_inputs: List[ElevenLabsDialogueInput],
        audio_content: bytes,
        voice_segments: List[ElevenLabsVoiceSegment],
    ) -> None:
        if not audio_content:
            raise ValueError("ElevenLabs dialogue synthesis returned no audio content.")

        if not voice_segments:
            raise ValueError("ElevenLabs dialogue synthesis returned no voice segments.")

        represented_input_indexes: Set[int] = set()

        for segment_index, voice_segment in enumerate(voice_segments):
            input_index = voice_segment.dialogue_input_index

            if input_index < 0:
                raise ValueError(
                    f"ElevenLabs voice segment {segment_index} "
                    "references a negative dialogue input index "
                    f"{input_index}."
                )

            if input_index >= len(dialogue_inputs):
                raise ValueError(
                    f"ElevenLabs voice segment {segment_index} "
                    "references invalid dialogue input index "
                    f"{input_index}."
                )

            if voice_segment.end_time_seconds < voice_segment.start_time_seconds:
                raise ValueError(f"ElevenLabs voice segment {segment_index} ends before it begins.")

            if voice_segment.character_end_index < voice_segment.character_start_index:
                raise ValueError(
                    f"ElevenLabs voice segment {segment_index} has invalid character indexes."
                )

            expected_voice_id = dialogue_inputs[input_index].voice_id

            if voice_segment.voice_id != expected_voice_id:
                raise ValueError(
                    "ElevenLabs returned an unexpected voice "
                    f"identifier for dialogue input {input_index}. "
                    f"Expected '{expected_voice_id}', received "
                    f"'{voice_segment.voice_id}'."
                )

            represented_input_indexes.add(input_index)

        missing_input_indexes = set(range(len(dialogue_inputs))) - represented_input_indexes

        if missing_input_indexes:
            missing_indexes = ", ".join(
                str(input_index) for input_index in sorted(missing_input_indexes)
            )

            raise ValueError(
                "ElevenLabs returned no voice segment for "
                f"dialogue input indexes: {missing_indexes}."
            )

    @staticmethod
    def _is_retryable_status_code(
        *,
        status_code: Optional[int],
    ) -> bool:
        if status_code is None:
            return False

        return status_code in {408, 429} or 500 <= status_code <= 599

    def _translate_http_error(
        self,
        *,
        response: httpx.Response,
    ) -> ElevenLabsProviderError:
        status_code = response.status_code

        error_message = response.reason_phrase or "ElevenLabs dialogue synthesis failed."

        error_code: Optional[str] = None

        try:
            error_body = response.json()
        except ValueError:
            error_body = None

        if isinstance(error_body, dict):
            error_message, error_code = self._extract_error_details(
                error_body=error_body,
                fallback_message=error_message,
            )

        return ElevenLabsProviderError(
            message=error_message,
            retryable=self._is_retryable_status_code(
                status_code=status_code,
            ),
            status_code=status_code,
            error_code=error_code,
        )

    @staticmethod
    def _extract_error_details(
        *,
        error_body: Dict[str, Any],
        fallback_message: str,
    ) -> Tuple[str, Optional[str]]:
        error_message = fallback_message
        error_code: Optional[str] = None

        error_detail = error_body.get("detail")

        if isinstance(error_detail, dict):
            detail_message = error_detail.get("message")
            detail_code = error_detail.get("code")

            if detail_message:
                error_message = str(detail_message)

            if detail_code:
                error_code = str(detail_code)

        elif isinstance(error_detail, str):
            error_message = error_detail

        else:
            top_level_message = error_body.get("message")

            if top_level_message:
                error_message = str(top_level_message)

        return error_message, error_code

    @property
    def output_format(self) -> str:
        return self.config.output_format

    async def aclose(self) -> None:
        await self.http_client.aclose()
