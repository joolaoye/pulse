from pydantic import ValidationError
import pytest

from pulse.types import PodcastPipeline, PodcastProfile, SpeakerProfile, SpeakerVoiceBinding


def test_voice_binding_must_reference_a_configured_speaker() -> None:
    with pytest.raises(ValidationError):
        PodcastPipeline(
            pipeline_id="pipeline-alpha",
            show_id="show-alpha",
            podcast_profile=PodcastProfile(
                name="Nightly Pulse",
                purpose="Explain rate moves.",
                target_audience="Operators",
                editorial_style="Specific",
                conversational_style="Direct",
            ),
            speakers=[
                SpeakerProfile(
                    speaker_id="host",
                    display_name="Mina Cho",
                    podcast_role="Host",
                    persona="Curious",
                    speaking_style="Direct",
                )
            ],
            speaker_voice_bindings=[
                SpeakerVoiceBinding(speaker_id="guest", voice_id="voice-guest"),
            ],
            interest_profile_markdown="# Rates\n\nWhat changed.",
            x_list_id="list-1842",
            target_episode_duration_seconds=900,
        )
