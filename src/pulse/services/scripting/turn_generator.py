from typing import Dict, List, Optional

from pulse.agents import TurnScriptingAgent, TurnScriptingInput
from pulse.types import (
    EpisodeScript,
    PodcastProfile,
    ProcessedSignal,
    ScriptTurn,
    SpeakerProfile,
    Turn,
    TurnPlan,
)


class TurnGenerator:
    def __init__(
        self,
        *,
        turn_scripting_agent: TurnScriptingAgent,
    ) -> None:
        self.turn_scripting_agent = turn_scripting_agent

    async def generate(
        self,
        *,
        turn_plan: TurnPlan,
        speakers: List[SpeakerProfile],
        signals: List[ProcessedSignal],
        podcast_profile: PodcastProfile,
    ) -> EpisodeScript:
        speaker_by_id = {speaker.speaker_id: speaker for speaker in speakers}
        signal_by_id = {signal.signal_id: signal for signal in signals}

        script_turns: List[ScriptTurn] = []

        await self._generate_turns(
            turns=turn_plan.opening.turns,
            speaker_by_id=speaker_by_id,
            podcast_profile=podcast_profile,
            planning_context=turn_plan.opening.episode_opening.to_llm_string(),
            source_context=[],
            script_turns=script_turns,
        )

        for segment_turn_plan in turn_plan.body.segment_turn_plans:
            for beat_turn_plan in segment_turn_plan.beat_turn_plans:
                beat = beat_turn_plan.beat

                await self._generate_turns(
                    turns=beat_turn_plan.turns,
                    speaker_by_id=speaker_by_id,
                    podcast_profile=podcast_profile,
                    planning_context=beat.to_llm_string(),
                    source_context=self._resolve_beat_signals(
                        primary_signal_id=beat.primary_signal_id,
                        supporting_signal_ids=beat.supporting_signal_ids,
                        signal_by_id=signal_by_id,
                    ),
                    script_turns=script_turns,
                )

        await self._generate_turns(
            turns=turn_plan.closing.turns,
            speaker_by_id=speaker_by_id,
            podcast_profile=podcast_profile,
            planning_context=turn_plan.closing.episode_closing.to_llm_string(),
            source_context=[],
            script_turns=script_turns,
        )

        return EpisodeScript(
            turns=script_turns,
        )

    async def _generate_turns(
        self,
        *,
        turns: List[Turn],
        speaker_by_id: Dict[str, SpeakerProfile],
        podcast_profile: PodcastProfile,
        planning_context: str,
        source_context: List[ProcessedSignal],
        script_turns: List[ScriptTurn],
    ) -> None:
        for turn in turns:
            script_turns.append(
                await self._generate_turn(
                    turn=turn,
                    speaker_by_id=speaker_by_id,
                    podcast_profile=podcast_profile,
                    planning_context=planning_context,
                    source_context=source_context,
                    previous_script_turn=(script_turns[-1] if script_turns else None),
                )
            )

    async def _generate_turn(
        self,
        *,
        turn: Turn,
        speaker_by_id: Dict[str, SpeakerProfile],
        podcast_profile: PodcastProfile,
        planning_context: str,
        source_context: List[ProcessedSignal],
        previous_script_turn: Optional[ScriptTurn],
    ) -> ScriptTurn:
        speaker = speaker_by_id.get(turn.speaker_id)

        if speaker is None:
            raise ValueError(f"Turn scripting could not resolve speaker_id {turn.speaker_id!r}.")

        output = await self.turn_scripting_agent.arun(
            input_data=TurnScriptingInput(
                turn=turn,
                speaker=speaker,
                podcast_profile=podcast_profile,
                planning_context=planning_context,
                source_context=source_context,
                previous_script_turn=previous_script_turn,
            )
        )

        return ScriptTurn(
            speaker_id=turn.speaker_id,
            spoken_text=output.spoken_text,
        )

    @staticmethod
    def _resolve_beat_signals(
        *,
        primary_signal_id: str,
        supporting_signal_ids: List[str],
        signal_by_id: Dict[str, ProcessedSignal],
    ) -> List[ProcessedSignal]:
        signal_ids = [
            primary_signal_id,
            *supporting_signal_ids,
        ]

        resolved_signals: List[ProcessedSignal] = []

        for signal_id in signal_ids:
            signal = signal_by_id.get(signal_id)

            if signal is None:
                raise ValueError(f"Turn scripting could not resolve signal_id {signal_id!r}.")

            resolved_signals.append(signal)

        return resolved_signals
