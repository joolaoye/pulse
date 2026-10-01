from pathlib import Path

from pydantic import BaseModel, Field, field_validator

DEFAULT_D1_DATABASE_NAME = "pulse"
DEFAULT_VECTORIZE_INDEX_NAME = "pulse-signals"
DEFAULT_CHECKPOINT_DATABASE_PATH = Path("runtime/checkpoints/pulse.sqlite3")
DEFAULT_PUBLIC_PODCAST_BUCKET_NAME = "pulse-public-podcasts"


class PulseInitializationConfig(BaseModel):
    x_bearer_token: str = Field(repr=False)
    voyage_api_key: str = Field(repr=False)
    anthropic_api_key: str = Field(repr=False)
    elevenlabs_api_key: str = Field(repr=False)

    cloudflare_account_id: str
    cloudflare_api_token: str = Field(repr=False)

    d1_database_name: str = DEFAULT_D1_DATABASE_NAME
    vectorize_index_name: str = DEFAULT_VECTORIZE_INDEX_NAME
    checkpoint_database_path: Path = DEFAULT_CHECKPOINT_DATABASE_PATH
    podcast_bucket_name: str = DEFAULT_PUBLIC_PODCAST_BUCKET_NAME

    @field_validator(
        "x_bearer_token",
        "voyage_api_key",
        "anthropic_api_key",
        "elevenlabs_api_key",
        "cloudflare_account_id",
        "cloudflare_api_token",
        "d1_database_name",
        "vectorize_index_name",
        "podcast_bucket_name",
    )
    @classmethod
    def validate_non_empty_string(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty.")

        return value
