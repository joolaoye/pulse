from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceNames:
    vectorize_index_name: str
    podcast_bucket_name: str


@dataclass(frozen=True)
class CloudflareRestCredentials:
    api_token: str
    account_id: str
    d1_database_id: str


@dataclass(frozen=True)
class ProviderCredentials:
    anthropic_api_key: str
    voyage_api_key: str
    x_bearer_token: str
    elevenlabs_api_key: str
