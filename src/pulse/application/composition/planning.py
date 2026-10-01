"""
Shared planning composition.

Receives already-created providers. Never reads os.environ.
"""

from pulse.agents import (
    BEAT_PLANNING_MAX_TOKENS,
    BEAT_PLANNING_MODEL,
    BEAT_PLANNING_TEMPERATURE,
    BODY_OUTLINE_PLANNING_MAX_TOKENS,
    BODY_OUTLINE_PLANNING_MODEL,
    BODY_OUTLINE_PLANNING_TEMPERATURE,
    BODY_TURN_PLANNING_MAX_TOKENS,
    BODY_TURN_PLANNING_MODEL,
    BODY_TURN_PLANNING_TEMPERATURE,
    CLOSING_PLANNING_MAX_TOKENS,
    CLOSING_PLANNING_MODEL,
    CLOSING_PLANNING_TEMPERATURE,
    CLOSING_TURN_PLANNING_MAX_TOKENS,
    CLOSING_TURN_PLANNING_MODEL,
    CLOSING_TURN_PLANNING_TEMPERATURE,
    CONVERSATION_ANGLE_MAX_TOKENS,
    CONVERSATION_ANGLE_MODEL,
    CONVERSATION_ANGLE_TEMPERATURE,
    OPENING_PLANNING_MAX_TOKENS,
    OPENING_PLANNING_MODEL,
    OPENING_PLANNING_TEMPERATURE,
    OPENING_TURN_PLANNING_MAX_TOKENS,
    OPENING_TURN_PLANNING_MODEL,
    OPENING_TURN_PLANNING_TEMPERATURE,
    QUESTION_PLANNING_MAX_TOKENS,
    QUESTION_PLANNING_MODEL,
    QUESTION_PLANNING_TEMPERATURE,
    SHORTLIST_PLANNING_MAX_TOKENS,
    SHORTLIST_PLANNING_MODEL,
    SHORTLIST_PLANNING_TEMPERATURE,
    BeatPlanningAgent,
    BodyOutlinePlanningAgent,
    BodyTurnPlanningAgent,
    ClosingPlanningAgent,
    ClosingTurnPlanningAgent,
    ConversationAnglePlanningAgent,
    OpeningPlanningAgent,
    OpeningTurnPlanningAgent,
    QuestionPlanningAgent,
    ShortlistPlanningAgent,
)
from pulse.infrastructure.llm.anthropic import (
    AnthropicModelConfig,
    AnthropicProvider,
)
from pulse.services.planning import (
    BeatPlanner,
    BodyOutlinePlanner,
    BodyPlanner,
    BodyTurnPlanner,
    ClosingPlanner,
    ClosingTurnPlanner,
    ConversationAnglePlanner,
    EpisodePlanner,
    OpeningPlanner,
    OpeningTurnPlanner,
    Planner,
    QuestionPlanner,
    SegmentPlanner,
    ShortlistPlanner,
    TurnPlanner,
)


def _create_llm(
    *,
    anthropic_provider: AnthropicProvider,
    model: str,
    temperature: float,
    max_tokens: int,
):
    return anthropic_provider.create_model(
        model_config=AnthropicModelConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )


def _create_body_outline_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> BodyOutlinePlanner:
    return BodyOutlinePlanner(
        body_outline_planning_agent=BodyOutlinePlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=BODY_OUTLINE_PLANNING_MODEL,
                temperature=BODY_OUTLINE_PLANNING_TEMPERATURE,
                max_tokens=BODY_OUTLINE_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_shortlist_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> ShortlistPlanner:
    return ShortlistPlanner(
        shortlist_planning_agent=ShortlistPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=SHORTLIST_PLANNING_MODEL,
                temperature=SHORTLIST_PLANNING_TEMPERATURE,
                max_tokens=SHORTLIST_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_conversation_angle_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> ConversationAnglePlanner:
    return ConversationAnglePlanner(
        conversation_angle_planning_agent=ConversationAnglePlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=CONVERSATION_ANGLE_MODEL,
                temperature=CONVERSATION_ANGLE_TEMPERATURE,
                max_tokens=CONVERSATION_ANGLE_MAX_TOKENS,
            )
        )
    )


def _create_question_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> QuestionPlanner:
    return QuestionPlanner(
        question_planning_agent=QuestionPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=QUESTION_PLANNING_MODEL,
                temperature=QUESTION_PLANNING_TEMPERATURE,
                max_tokens=QUESTION_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_beat_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> BeatPlanner:
    return BeatPlanner(
        beat_planning_agent=BeatPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=BEAT_PLANNING_MODEL,
                temperature=BEAT_PLANNING_TEMPERATURE,
                max_tokens=BEAT_PLANNING_MAX_TOKENS,
            )
        ),
        conversation_angle_planner=_create_conversation_angle_planner(
            anthropic_provider=anthropic_provider,
        ),
        question_planner=_create_question_planner(
            anthropic_provider=anthropic_provider,
        ),
    )


def _create_segment_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> SegmentPlanner:
    return SegmentPlanner(
        shortlist_planner=_create_shortlist_planner(
            anthropic_provider=anthropic_provider,
        ),
        beat_planner=_create_beat_planner(
            anthropic_provider=anthropic_provider,
        ),
    )


def _create_body_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> BodyPlanner:
    return BodyPlanner(
        body_outline_planner=_create_body_outline_planner(
            anthropic_provider=anthropic_provider,
        ),
        segment_planner=_create_segment_planner(
            anthropic_provider=anthropic_provider,
        ),
    )


def _create_opening_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> OpeningPlanner:
    return OpeningPlanner(
        opening_planning_agent=OpeningPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=OPENING_PLANNING_MODEL,
                temperature=OPENING_PLANNING_TEMPERATURE,
                max_tokens=OPENING_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_closing_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> ClosingPlanner:
    return ClosingPlanner(
        closing_planning_agent=ClosingPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=CLOSING_PLANNING_MODEL,
                temperature=CLOSING_PLANNING_TEMPERATURE,
                max_tokens=CLOSING_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_episode_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> EpisodePlanner:
    return EpisodePlanner(
        body_planner=_create_body_planner(
            anthropic_provider=anthropic_provider,
        ),
        opening_planner=_create_opening_planner(
            anthropic_provider=anthropic_provider,
        ),
        closing_planner=_create_closing_planner(
            anthropic_provider=anthropic_provider,
        ),
    )


def _create_opening_turn_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> OpeningTurnPlanner:
    return OpeningTurnPlanner(
        opening_turn_planning_agent=OpeningTurnPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=OPENING_TURN_PLANNING_MODEL,
                temperature=OPENING_TURN_PLANNING_TEMPERATURE,
                max_tokens=OPENING_TURN_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_body_turn_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> BodyTurnPlanner:
    return BodyTurnPlanner(
        body_turn_planning_agent=BodyTurnPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=BODY_TURN_PLANNING_MODEL,
                temperature=BODY_TURN_PLANNING_TEMPERATURE,
                max_tokens=BODY_TURN_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_closing_turn_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> ClosingTurnPlanner:
    return ClosingTurnPlanner(
        closing_turn_planning_agent=ClosingTurnPlanningAgent(
            llm=_create_llm(
                anthropic_provider=anthropic_provider,
                model=CLOSING_TURN_PLANNING_MODEL,
                temperature=CLOSING_TURN_PLANNING_TEMPERATURE,
                max_tokens=CLOSING_TURN_PLANNING_MAX_TOKENS,
            )
        )
    )


def _create_turn_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> TurnPlanner:
    return TurnPlanner(
        opening_turn_planner=_create_opening_turn_planner(
            anthropic_provider=anthropic_provider,
        ),
        body_turn_planner=_create_body_turn_planner(
            anthropic_provider=anthropic_provider,
        ),
        closing_turn_planner=_create_closing_turn_planner(
            anthropic_provider=anthropic_provider,
        ),
    )


def create_planner(
    *,
    anthropic_provider: AnthropicProvider,
) -> Planner:
    return Planner(
        episode_planner=_create_episode_planner(
            anthropic_provider=anthropic_provider,
        ),
        turn_planner=_create_turn_planner(
            anthropic_provider=anthropic_provider,
        ),
    )
