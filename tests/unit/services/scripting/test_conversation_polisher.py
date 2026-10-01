import pytest

from pulse.agents.conversation_polish.schemas import ConversationPolishOutput
from pulse.services.scripting.conversation_polisher import ConversationPolisher
from pulse.types import EpisodeScript, ScriptTurn, SpeakerProfile


def _speaker(speaker_id: str) -> SpeakerProfile:
    return SpeakerProfile(
        speaker_id=speaker_id,
        display_name=speaker_id,
        podcast_role=speaker_id,
        persona="Curious",
        speaking_style="Direct",
    )


class _PolishAgent:
    def __init__(self) -> None:
        self.inputs = []

    async def arun(self, *, input_data):
        self.inputs.append(input_data)
        return ConversationPolishOutput(spoken_text=f"polished-{len(self.inputs)}")


async def test_polished_script_keeps_speaker_identity_and_turn_order() -> None:
    script = EpisodeScript(
        turns=[
            ScriptTurn(speaker_id="host", spoken_text="Opening"),
            ScriptTurn(speaker_id="guest", spoken_text="Response"),
        ]
    )
    speakers = [_speaker("guest"), _speaker("host")]
    agent = _PolishAgent()

    polished = await ConversationPolisher(conversation_polish_agent=agent).polish(
        episode_script=script,
        speakers=speakers,
    )

    assert agent.inputs[0].script_turn is script.turns[0]
    assert agent.inputs[0].speaker.speaker_id == "host"
    assert agent.inputs[0].previous_polished_script_turn is None
    assert agent.inputs[1].previous_polished_script_turn.spoken_text == "polished-1"
    assert [(turn.speaker_id, turn.spoken_text) for turn in polished.turns] == [
        ("host", "polished-1"),
        ("guest", "polished-2"),
    ]


async def test_polish_rejects_an_unknown_speaker() -> None:
    with pytest.raises(ValueError):
        await ConversationPolisher(conversation_polish_agent=_PolishAgent()).polish(
            episode_script=EpisodeScript(
                turns=[ScriptTurn(speaker_id="stranger", spoken_text="Hello")]
            ),
            speakers=[_speaker("host")],
        )


async def test_polish_rejects_duplicate_speaker_profiles() -> None:
    with pytest.raises(ValueError):
        await ConversationPolisher(conversation_polish_agent=_PolishAgent()).polish(
            episode_script=EpisodeScript(
                turns=[ScriptTurn(speaker_id="host", spoken_text="Hello")]
            ),
            speakers=[_speaker("host"), _speaker("host")],
        )
