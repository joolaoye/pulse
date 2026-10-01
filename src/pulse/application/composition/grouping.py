from pulse.agents import ThemeExtractionAgent
from pulse.agents.theme_extraction import (
    THEME_EXTRACTION_MAX_TOKENS,
    THEME_EXTRACTION_MODEL,
    THEME_EXTRACTION_TEMPERATURE,
)
from pulse.infrastructure.llm.anthropic import (
    AnthropicModelConfig,
    AnthropicProvider,
)
from pulse.services.grouping import (
    SignalClusterer,
    SignalGroupBuilder,
)


def create_signal_group_builder(
    *,
    anthropic_provider: AnthropicProvider,
) -> SignalGroupBuilder:
    theme_extraction_agent = ThemeExtractionAgent(
        llm=anthropic_provider.create_model(
            model_config=AnthropicModelConfig(
                model=THEME_EXTRACTION_MODEL,
                temperature=THEME_EXTRACTION_TEMPERATURE,
                max_tokens=THEME_EXTRACTION_MAX_TOKENS,
            )
        )
    )

    return SignalGroupBuilder(
        signal_clusterer=SignalClusterer(),
        theme_extraction_agent=theme_extraction_agent,
    )
