from pydantic import BaseModel, Field

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-5-20250929"
OPUS_MODEL = "claude-opus-4-20250514"

DEFAULT_MODEL = HAIKU_MODEL
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 4096


class AnthropicModelConfig(BaseModel):
    model: str = Field(default=DEFAULT_MODEL, min_length=1)
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, gt=0)


class AnthropicProviderConfig(BaseModel):
    api_key: str = Field(..., min_length=1)
