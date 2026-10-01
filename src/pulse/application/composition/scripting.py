from pulse.agents import (
    ConversationPolishAgent,
    EpisodeMetadataGenerationAgent,
    TurnScriptingAgent,
)
from pulse.agents.conversation_polish import (
    CONVERSATION_POLISH_MAX_TOKENS,
    CONVERSATION_POLISH_MODEL,
    CONVERSATION_POLISH_TEMPERATURE,
)
from pulse.agents.conversation_polish.runtime.elevenlabs import (
    ELEVENLABS_RUNTIME_DELIVERY_EXAMPLES,
    ELEVENLABS_RUNTIME_DELIVERY_INSTRUCTIONS,
)
from pulse.agents.episode_metadata import (
    EPISODE_METADATA_GENERATION_MAX_TOKENS,
    EPISODE_METADATA_GENERATION_MODEL,
    EPISODE_METADATA_GENERATION_TEMPERATURE,
)
from pulse.agents.turn_scripting import (
    TURN_SCRIPTING_MAX_TOKENS,
    TURN_SCRIPTING_MODEL,
    TURN_SCRIPTING_TEMPERATURE,
)
from pulse.infrastructure.llm.anthropic import (
    AnthropicModelConfig,
    AnthropicProvider,
)
from pulse.services.episode_metadata import EpisodeMetadataGenerator
from pulse.services.scripting import (
    ConversationPolisher,
    ScriptGenerator,
    TurnGenerator,
)


def create_script_generator(
    *,
    anthropic_provider: AnthropicProvider,
) -> ScriptGenerator:
    turn_scripting_agent = TurnScriptingAgent(
        llm=anthropic_provider.create_model(
            model_config=AnthropicModelConfig(
                model=TURN_SCRIPTING_MODEL,
                temperature=TURN_SCRIPTING_TEMPERATURE,
                max_tokens=TURN_SCRIPTING_MAX_TOKENS,
            )
        )
    )

    conversation_polish_agent = ConversationPolishAgent(
        llm=anthropic_provider.create_model(
            model_config=AnthropicModelConfig(
                model=CONVERSATION_POLISH_MODEL,
                temperature=CONVERSATION_POLISH_TEMPERATURE,
                max_tokens=CONVERSATION_POLISH_MAX_TOKENS,
            )
        ),
        runtime_delivery_instructions=ELEVENLABS_RUNTIME_DELIVERY_INSTRUCTIONS,
        runtime_delivery_examples=ELEVENLABS_RUNTIME_DELIVERY_EXAMPLES,
    )

    return ScriptGenerator(
        turn_generator=TurnGenerator(
            turn_scripting_agent=turn_scripting_agent,
        ),
        conversation_polisher=ConversationPolisher(
            conversation_polish_agent=conversation_polish_agent,
        ),
    )


def create_episode_metadata_generator(
    *,
    anthropic_provider: AnthropicProvider,
) -> EpisodeMetadataGenerator:
    agent = EpisodeMetadataGenerationAgent(
        llm=anthropic_provider.create_model(
            model_config=AnthropicModelConfig(
                model=EPISODE_METADATA_GENERATION_MODEL,
                temperature=EPISODE_METADATA_GENERATION_TEMPERATURE,
                max_tokens=EPISODE_METADATA_GENERATION_MAX_TOKENS,
            )
        )
    )

    return EpisodeMetadataGenerator(
        episode_metadata_generation_agent=agent,
    )
