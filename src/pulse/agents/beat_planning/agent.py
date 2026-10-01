from pulse.agents._base import BaseAgent
from pulse.agents.beat_planning.schemas import (
    BeatPlanningInput,
    BeatPlanningOutput,
)
from pulse.agents.beat_planning.system_prompt import SYSTEM_PROMPT
from pulse.agents.beat_planning.user_prompt import USER_PROMPT
from pulse.infrastructure.llm.anthropic import SONNET_MODEL

BEAT_PLANNING_MODEL = SONNET_MODEL
BEAT_PLANNING_TEMPERATURE = 0.2
BEAT_PLANNING_MAX_TOKENS = 1024


class BeatPlanningAgent(BaseAgent[BeatPlanningInput, BeatPlanningOutput]):
    def __init__(self, llm):
        super().__init__(llm, BeatPlanningOutput)

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        input_data: BeatPlanningInput,
    ) -> str:
        return USER_PROMPT.format(
            planning_context=input_data.to_llm_string(),
        )
