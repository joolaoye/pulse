from typing import List

from pulse.services.scripting.conversation_polisher import ConversationPolisher
from pulse.services.scripting.turn_generator import TurnGenerator
from pulse.types import (
    EpisodeScript,
    PodcastProfile,
    ProcessedSignal,
    SpeakerProfile,
    TurnPlan,
)


class ScriptGenerator:
    def __init__(
        self,
        *,
        turn_generator: TurnGenerator,
        conversation_polisher: ConversationPolisher,
    ) -> None:
        self.turn_generator = turn_generator
        self.conversation_polisher = conversation_polisher

    async def generate(
        self,
        *,
        turn_plan: TurnPlan,
        speakers: List[SpeakerProfile],
        signals: List[ProcessedSignal],
        podcast_profile: PodcastProfile,
    ) -> EpisodeScript:
        episode_script = await self.turn_generator.generate(
            turn_plan=turn_plan,
            speakers=speakers,
            signals=signals,
            podcast_profile=podcast_profile,
        )

        return await self.conversation_polisher.polish(
            episode_script=episode_script,
            speakers=speakers,
        )
