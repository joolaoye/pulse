import pytest

from pulse.services.audio.batcher import DialogueBatcher
from pulse.types import EpisodeScript, ScriptTurn, SpeakerVoiceBinding


def _script(*turns: tuple[str, str]) -> EpisodeScript:
    return EpisodeScript(
        turns=[
            ScriptTurn(speaker_id=speaker_id, spoken_text=spoken_text)
            for speaker_id, spoken_text in turns
        ]
    )


def _bindings(*speaker_ids: str) -> list[SpeakerVoiceBinding]:
    return [
        SpeakerVoiceBinding(speaker_id=speaker_id, voice_id=f"voice-{speaker_id}")
        for speaker_id in speaker_ids
    ]


def test_turns_stay_together_until_the_character_limit_is_exceeded() -> None:
    batches = DialogueBatcher(max_characters_per_batch=10).batch(
        episode_script=_script(("host", "aaaa"), ("analyst", "bbbbbb"), ("host", "cc")),
        speaker_voice_bindings=_bindings("host", "analyst"),
    )

    assert [
        (
            batch.batch_index,
            batch.character_count,
            [
                (turn.script_turn_index, turn.speaker_id, turn.voice_id, turn.spoken_text)
                for turn in batch.turns
            ],
        )
        for batch in batches
    ] == [
        (
            0,
            10,
            [
                (0, "host", "voice-host", "aaaa"),
                (1, "analyst", "voice-analyst", "bbbbbb"),
            ],
        ),
        (1, 2, [(2, "host", "voice-host", "cc")]),
    ]


@pytest.mark.parametrize("max_characters_per_batch", [0, -5])
def test_batch_limit_must_be_positive(max_characters_per_batch: int) -> None:
    with pytest.raises(ValueError):
        DialogueBatcher(max_characters_per_batch=max_characters_per_batch)


@pytest.mark.parametrize(
    ("bindings", "spoken_text"),
    [
        (_bindings("host"), "aaaa"),
        (_bindings("host", "host"), "aaaa"),
        ([], "aaaa"),
        (_bindings("host", "analyst"), "abcdefghijk"),
    ],
)
def test_invalid_dialogue_is_rejected(
    bindings: list[SpeakerVoiceBinding],
    spoken_text: str,
) -> None:
    with pytest.raises(ValueError):
        DialogueBatcher(max_characters_per_batch=10).batch(
            episode_script=_script(("host", "ok"), ("analyst", spoken_text)),
            speaker_voice_bindings=bindings,
        )
