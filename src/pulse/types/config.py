from datetime import (
    datetime,
    time,
    timezone as datetime_timezone,
)
from typing import List, Optional
from zoneinfo import (
    ZoneInfo,
    ZoneInfoNotFoundError,
)

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
    model_validator,
)

MIN_EPISODE_DURATION_SECONDS = 300


class SpeakerVoiceBinding(BaseModel):
    speaker_id: str = Field(..., min_length=1)
    voice_id: str = Field(..., min_length=1)


class PodcastProfile(BaseModel):
    name: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    target_audience: str = Field(..., min_length=1)
    editorial_style: str = Field(..., min_length=1)
    conversational_style: str = Field(..., min_length=1)

    def to_llm_string(self) -> str:
        return (
            "# Podcast Profile\n\n"
            f"## Name\n{self.name}\n\n"
            f"## Purpose\n{self.purpose}\n\n"
            f"## Target Audience\n{self.target_audience}\n\n"
            f"## Editorial Style\n{self.editorial_style}\n\n"
            f"## Conversational Style\n{self.conversational_style}"
        )


class SpeakerProfile(BaseModel):
    speaker_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    display_name: str = Field(..., min_length=1)
    podcast_role: str = Field(..., min_length=1)
    persona: str = Field(..., min_length=1)
    expertise: List[str] = Field(default_factory=list)
    speaking_style: str = Field(..., min_length=1)

    def to_llm_string(self) -> str:
        expertise = (
            "\n".join(f"- {area}" for area in self.expertise) if self.expertise else "- Generalist"
        )

        return (
            "# Speaker Profile\n\n"
            f"Speaker ID:\n{self.speaker_id}\n\n"
            f"Display Name:\n{self.display_name}\n\n"
            f"Podcast Role:\n{self.podcast_role}\n\n"
            f"Persona:\n{self.persona}\n\n"
            f"Expertise:\n{expertise}\n\n"
            f"Speaking Style:\n{self.speaking_style}"
        )


class PodcastShow(BaseModel):
    show_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    website_url: HttpUrl
    artwork_url: HttpUrl
    category: str = Field(..., min_length=1)
    language: str = Field(
        default="en-US",
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    explicit: bool = False
    verification_email: Optional[EmailStr] = None
    public_base_url: HttpUrl
    feed_object_key: str = Field(..., min_length=1)

    @field_serializer(
        "website_url",
        "artwork_url",
        "public_base_url",
    )
    def serialize_url(self, value: HttpUrl) -> str:
        return str(value)

    @field_validator("feed_object_key")
    @classmethod
    def validate_feed_object_key(cls, value: str) -> str:
        if value.startswith("/"):
            raise ValueError("The podcast feed object key cannot begin with a forward slash.")

        if value.endswith("/"):
            raise ValueError(
                "The podcast feed object key must identify a file rather than a directory."
            )

        if not value.lower().endswith(".xml"):
            raise ValueError("The podcast feed object key must identify an XML file.")

        return value

    @model_validator(mode="after")
    def validate_public_base_url(self) -> "PodcastShow":
        if self.public_base_url.query is not None:
            raise ValueError("The podcast public base URL cannot contain query parameters.")

        if self.public_base_url.fragment is not None:
            raise ValueError("The podcast public base URL cannot contain a fragment.")

        return self

    def build_public_url(
        self,
        object_key: str,
    ) -> str:
        if not object_key:
            raise ValueError("A public podcast URL cannot be built from an empty object key.")

        return f"{str(self.public_base_url).rstrip('/')}/{object_key.lstrip('/')}"

    def get_feed_url(self) -> str:
        return self.build_public_url(self.feed_object_key)


class PodcastConfiguration(BaseModel):
    podcast_profile: PodcastProfile
    speakers: List[SpeakerProfile] = Field(..., min_length=1)
    speaker_voice_bindings: List[SpeakerVoiceBinding] = Field(
        ...,
        min_length=1,
    )


class PodcastPipeline(BaseModel):
    pipeline_id: str
    show_id: str
    podcast_profile: PodcastProfile
    speakers: List[SpeakerProfile] = Field(..., min_length=1)
    speaker_voice_bindings: List[SpeakerVoiceBinding] = Field(
        ...,
        min_length=1,
    )
    interest_profile_markdown: str
    x_list_id: str
    target_episode_duration_seconds: int = Field(
        ...,
        ge=MIN_EPISODE_DURATION_SECONDS,
    )
    enabled: bool = True

    @field_validator(
        "pipeline_id",
        "show_id",
        "interest_profile_markdown",
        "x_list_id",
    )
    @classmethod
    def validate_non_empty_string(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty.")

        return value

    @model_validator(mode="after")
    def validate_voice_bindings(self) -> "PodcastPipeline":
        speaker_ids = {speaker.speaker_id for speaker in self.speakers}
        bound_speaker_ids = {binding.speaker_id for binding in self.speaker_voice_bindings}

        unknown_speaker_ids = bound_speaker_ids - speaker_ids

        if unknown_speaker_ids:
            raise ValueError(
                "Speaker voice bindings reference unknown speaker IDs: "
                f"{sorted(unknown_speaker_ids)}"
            )

        return self


class PodcastPipelineSchedule(BaseModel):
    pipeline_id: str
    local_time: time
    timezone: str
    next_run_at: datetime
    last_dispatched_at: Optional[datetime] = None

    @field_validator("pipeline_id")
    @classmethod
    def validate_pipeline_id(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Podcast pipeline ID cannot be empty.")

        return value

    @field_validator("local_time")
    @classmethod
    def validate_local_time(
        cls,
        value: time,
    ) -> time:
        if value.tzinfo is not None:
            raise ValueError("Podcast pipeline schedule time must be a local wall-clock time.")

        if value.second != 0 or value.microsecond != 0:
            raise ValueError("Podcast pipeline schedule time must use minute precision.")

        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Podcast pipeline schedule timezone cannot be empty.")

        try:
            ZoneInfo(value)

        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown podcast pipeline schedule timezone: '{value}'.") from exc

        return value

    @field_validator(
        "next_run_at",
        "last_dispatched_at",
    )
    @classmethod
    def normalize_utc_datetime(
        cls,
        value: Optional[datetime],
    ) -> Optional[datetime]:
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Podcast pipeline schedule timestamps must be timezone-aware.")

        return value.astimezone(datetime_timezone.utc)
