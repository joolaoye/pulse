from pulse.services.scripting.script_generator import ScriptGenerator
from pulse.types import EpisodeScript, PodcastProfile, ScriptTurn, SpeakerProfile


def _profile() -> PodcastProfile:
    return PodcastProfile(
        name="Pulse",
        purpose="Explain the week's signals",
        target_audience="Builders",
        editorial_style="Specific",
        conversational_style="Direct",
    )


def _speaker() -> SpeakerProfile:
    return SpeakerProfile(
        speaker_id="host",
        display_name="Host",
        podcast_role="Host",
        persona="Curious",
        speaking_style="Direct",
    )


class _TurnGenerator:
    def __init__(self, script: EpisodeScript) -> None:
        self.script = script
        self.calls = []

    async def generate(self, *, turn_plan, speakers, signals, podcast_profile):
        self.calls.append((turn_plan, speakers, signals, podcast_profile))
        return self.script


class _Polisher:
    def __init__(self, script: EpisodeScript) -> None:
        self.script = script
        self.calls = []

    async def polish(self, *, episode_script, speakers):
        self.calls.append((episode_script, speakers))
        return self.script


async def test_script_generator_polishes_the_generated_script() -> None:
    generated = EpisodeScript(turns=[ScriptTurn(speaker_id="host", spoken_text="Draft")])
    polished = EpisodeScript(turns=[ScriptTurn(speaker_id="host", spoken_text="Final")])
    speakers = [_speaker()]
    profile = _profile()
    turn_plan = object()
    signals = [object()]
    generator = _TurnGenerator(generated)
    polisher = _Polisher(polished)

    result = await ScriptGenerator(
        turn_generator=generator,
        conversation_polisher=polisher,
    ).generate(
        turn_plan=turn_plan,
        speakers=speakers,
        signals=signals,
        podcast_profile=profile,
    )

    assert generator.calls == [(turn_plan, speakers, signals, profile)]
    assert polisher.calls == [(generated, speakers)]
    assert result is polished
