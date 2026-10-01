from typing import List, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
)

from pulse.types import (
    MIN_EPISODE_DURATION_SECONDS,
    PodcastProfile,
    SpeakerProfile,
    SpeakerVoiceBinding,
)


class PodcastPipelineUpdate(BaseModel):
    show_id: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    podcast_profile: Optional[PodcastProfile] = None
    speakers: Optional[List[SpeakerProfile]] = None
    speaker_voice_bindings: Optional[List[SpeakerVoiceBinding]] = None
    interest_profile_markdown: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    x_list_id: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    target_episode_duration_seconds: Optional[int] = Field(
        default=None,
        ge=MIN_EPISODE_DURATION_SECONDS,
    )


class PodcastShowUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    description: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    author: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    website_url: Optional[HttpUrl] = None
    artwork_url: Optional[HttpUrl] = None
    category: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    language: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    explicit: Optional[bool] = None
    verification_email: Optional[EmailStr] = None
    public_base_url: Optional[HttpUrl] = None
    feed_object_key: Optional[str] = Field(
        default=None,
        min_length=1,
    )
