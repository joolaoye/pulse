from typing import Optional

from pydantic import BaseModel, Field

ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io"
ELEVENLABS_TEXT_TO_DIALOGUE_WITH_TIMESTAMPS_URL = (
    f"{ELEVENLABS_API_BASE_URL}/v1/text-to-dialogue/with-timestamps"
)

DEFAULT_ELEVENLABS_MODEL_ID = "eleven_v3"
DEFAULT_ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_ELEVENLABS_TIMEOUT_SECONDS = 240.0
DEFAULT_ELEVENLABS_TEXT_NORMALIZATION_MODE = "auto"

DEFAULT_ELEVENLABS_MAX_ATTEMPTS = 3
DEFAULT_ELEVENLABS_INITIAL_RETRY_DELAY_SECONDS = 1.0
DEFAULT_ELEVENLABS_RETRY_BACKOFF_MULTIPLIER = 2.0
DEFAULT_ELEVENLABS_MAX_RETRY_DELAY_SECONDS = 8.0


class ElevenLabsConfig(BaseModel):
    api_key: str = Field(min_length=1)
    model_id: str = Field(
        default=DEFAULT_ELEVENLABS_MODEL_ID,
        min_length=1,
    )
    output_format: str = Field(
        default=DEFAULT_ELEVENLABS_OUTPUT_FORMAT,
        min_length=1,
    )
    timeout_seconds: float = Field(
        default=DEFAULT_ELEVENLABS_TIMEOUT_SECONDS,
        gt=0,
    )
    language_code: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
    )
    text_normalization_mode: str = Field(
        default=DEFAULT_ELEVENLABS_TEXT_NORMALIZATION_MODE,
        min_length=1,
    )
    max_attempts: int = Field(
        default=DEFAULT_ELEVENLABS_MAX_ATTEMPTS,
        ge=1,
    )
    initial_retry_delay_seconds: float = Field(
        default=DEFAULT_ELEVENLABS_INITIAL_RETRY_DELAY_SECONDS,
        ge=0,
    )
    retry_backoff_multiplier: float = Field(
        default=DEFAULT_ELEVENLABS_RETRY_BACKOFF_MULTIPLIER,
        gt=0,
    )
    max_retry_delay_seconds: float = Field(
        default=DEFAULT_ELEVENLABS_MAX_RETRY_DELAY_SECONDS,
        ge=0,
    )
