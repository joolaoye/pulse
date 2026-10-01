from langchain_anthropic import (
    ChatAnthropic,
)

from pulse.infrastructure.llm.anthropic.config import AnthropicModelConfig, AnthropicProviderConfig


class AnthropicProvider:
    def __init__(
        self,
        config: (AnthropicProviderConfig),
    ):
        self.config = config

    def create_model(
        self,
        *,
        model_config: AnthropicModelConfig,
    ) -> ChatAnthropic:
        return ChatAnthropic(
            api_key=self.config.api_key,
            model=model_config.model,  # type: ignore
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,  # type: ignore
        )  # pyright: ignore[reportCallIssue]
