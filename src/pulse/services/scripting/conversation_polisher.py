from typing import Dict, List

from pulse.agents import (
    ConversationPolishAgent,
    ConversationPolishInput,
)
from pulse.types import (
    EpisodeScript,
    ScriptTurn,
    SpeakerProfile,
)


class ConversationPolisher:
    def __init__(
        self,
        *,
        conversation_polish_agent: ConversationPolishAgent,
    ) -> None:
        self.conversation_polish_agent = conversation_polish_agent

    async def polish(
        self,
        *,
        episode_script: EpisodeScript,
        speakers: List[SpeakerProfile],
    ) -> EpisodeScript:
        speaker_by_id = self._build_speaker_lookup(
            speakers=speakers,
        )

        polished_turns: List[ScriptTurn] = []

        for script_turn in episode_script.turns:
            speaker = speaker_by_id.get(script_turn.speaker_id)

            if speaker is None:
                raise ValueError(
                    f"Conversation polish could not resolve speaker_id {script_turn.speaker_id!r}."
                )

            output = await self.conversation_polish_agent.arun(
                input_data=ConversationPolishInput(
                    script_turn=script_turn,
                    speaker=speaker,
                    previous_polished_script_turn=(polished_turns[-1] if polished_turns else None),
                )
            )

            polished_turns.append(
                ScriptTurn(
                    speaker_id=script_turn.speaker_id,
                    spoken_text=output.spoken_text,
                )
            )

        return EpisodeScript(
            turns=polished_turns,
        )

    @staticmethod
    def _build_speaker_lookup(
        *,
        speakers: List[SpeakerProfile],
    ) -> Dict[str, SpeakerProfile]:
        speaker_by_id: Dict[str, SpeakerProfile] = {}

        for speaker in speakers:
            if speaker.speaker_id in speaker_by_id:
                raise ValueError(
                    "Conversation polish received multiple speaker "
                    f"profiles for {speaker.speaker_id!r}."
                )

            speaker_by_id[speaker.speaker_id] = speaker

        return speaker_by_id
