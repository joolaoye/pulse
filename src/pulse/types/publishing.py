from datetime import datetime, timezone

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
)

from pulse.types.audio import StoredEpisodeAudio

IDENTIFIER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
AUDIO_CONTENT_TYPE_PATTERN = r"^audio/[A-Za-z0-9.+-]+$"


class EpisodeMetadata(BaseModel):
    title: str
    description: str

    @field_validator("title", "description")
    @classmethod
    def validate_nonblank_text(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Episode metadata text must not be blank.")

        return value


class EpisodePublicationRequest(BaseModel):
    episode_id: str = Field(
        ...,
        min_length=1,
        pattern=IDENTIFIER_PATTERN,
    )
    show_id: str = Field(
        ...,
        min_length=1,
        pattern=IDENTIFIER_PATTERN,
    )
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    published_at: AwareDatetime
    stored_audio: StoredEpisodeAudio


class EpisodePublication(BaseModel):
    episode_id: str = Field(
        ...,
        min_length=1,
        pattern=IDENTIFIER_PATTERN,
    )
    show_id: str = Field(
        ...,
        min_length=1,
        pattern=IDENTIFIER_PATTERN,
    )
    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    published_at: AwareDatetime
    duration_seconds: float = Field(..., gt=0)
    audio_object_key: str = Field(..., min_length=1)
    audio_size_bytes: int = Field(..., gt=0)
    audio_content_type: str = Field(
        ...,
        pattern=AUDIO_CONTENT_TYPE_PATTERN,
    )
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("audio_object_key")
    @classmethod
    def validate_audio_object_key(cls, value: str) -> str:
        if value.startswith("/"):
            raise ValueError("The episode audio object key cannot begin with a forward slash.")

        if value.endswith("/"):
            raise ValueError(
                "The episode audio object key must identify a file rather than a directory."
            )

        return value


class PublicationResult(BaseModel):
    episode_id: str = Field(
        ...,
        min_length=1,
        pattern=IDENTIFIER_PATTERN,
    )
    show_id: str = Field(
        ...,
        min_length=1,
        pattern=IDENTIFIER_PATTERN,
    )
    guid: str = Field(..., min_length=1)
    audio_url: HttpUrl
    feed_url: HttpUrl
    published_at: AwareDatetime

    @field_serializer(
        "audio_url",
        "feed_url",
    )
    def serialize_url(self, value: HttpUrl) -> str:
        return str(value)
