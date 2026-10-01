from dataclasses import dataclass

from pulse.application.composition.models import (
    CloudflareRestCredentials,
    ProviderCredentials,
)
from pulse.infrastructure.cloudflare import (
    CloudflareClient,
    CloudflareConfig,
)
from pulse.infrastructure.db.d1 import (
    D1Client,
    D1Config,
)
from pulse.infrastructure.embeddings.voyage import (
    VoyageConfig,
    VoyageEmbeddingProvider,
)
from pulse.infrastructure.llm.anthropic import (
    AnthropicProvider,
    AnthropicProviderConfig,
)
from pulse.infrastructure.storage.r2 import R2Client
from pulse.infrastructure.tts.elevenlabs import (
    ElevenLabsConfig,
    ElevenLabsDialogueProvider,
)
from pulse.infrastructure.vector.vectorize import VectorizeClient
from pulse.infrastructure.x import ClientConfig, XClient


@dataclass
class WorkflowInfrastructure:
    cloudflare_client: CloudflareClient
    x_client: XClient
    d1_client: D1Client
    r2_client: R2Client
    vectorize_client: VectorizeClient
    anthropic_provider: AnthropicProvider
    embedding_provider: VoyageEmbeddingProvider
    elevenlabs_dialogue_provider: ElevenLabsDialogueProvider

    async def aclose(self) -> None:
        await self.elevenlabs_dialogue_provider.aclose()
        await self.x_client.aclose()
        await self.cloudflare_client.aclose()


def create_rest_infrastructure(
    *,
    cloudflare: CloudflareRestCredentials,
    providers: ProviderCredentials,
) -> WorkflowInfrastructure:
    cloudflare_client = CloudflareClient(
        config=CloudflareConfig(
            api_token=cloudflare.api_token,
            account_id=cloudflare.account_id,
        ),
    )

    x_client = XClient(
        bearer_token=providers.x_bearer_token,
        config=ClientConfig(),
    )

    d1_client = D1Client(
        cloudflare_client=cloudflare_client,
        config=D1Config(
            database_id=cloudflare.d1_database_id,
        ),
    )

    r2_client = R2Client(
        cloudflare_client=cloudflare_client,
    )

    vectorize_client = VectorizeClient(
        cloudflare_client=cloudflare_client,
    )

    anthropic_provider = AnthropicProvider(
        config=AnthropicProviderConfig(
            api_key=providers.anthropic_api_key,
        ),
    )

    embedding_provider = VoyageEmbeddingProvider(
        config=VoyageConfig(
            api_key=providers.voyage_api_key,
        ),
    )

    elevenlabs_dialogue_provider = ElevenLabsDialogueProvider(
        config=ElevenLabsConfig(
            api_key=providers.elevenlabs_api_key,
        ),
    )

    return WorkflowInfrastructure(
        cloudflare_client=cloudflare_client,
        x_client=x_client,
        d1_client=d1_client,
        r2_client=r2_client,
        vectorize_client=vectorize_client,
        anthropic_provider=anthropic_provider,
        embedding_provider=embedding_provider,
        elevenlabs_dialogue_provider=elevenlabs_dialogue_provider,
    )
