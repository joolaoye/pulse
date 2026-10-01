import pytest

from pulse.application.composition.cloud import (
    CloudflareRestCredentials,
    ProviderCredentials,
    ResourceNames,
)
from pulse.application.deployment.models import (
    DeploymentInputs,
)


@pytest.fixture
def deployment_inputs(
    tmp_path,
) -> DeploymentInputs:
    return DeploymentInputs(
        wrangler_config_path=(tmp_path / "wrangler.jsonc"),
        cloudflare=CloudflareRestCredentials(
            api_token="cloudflare-secret",
            account_id="account-id",
            d1_database_id="database-id",
        ),
        providers=ProviderCredentials(
            anthropic_api_key="anthropic-secret",
            voyage_api_key="voyage-secret",
            x_bearer_token="x-secret",
            elevenlabs_api_key="elevenlabs-secret",
        ),
        resources=ResourceNames(
            vectorize_index_name="pulse-signals",
            podcast_bucket_name="pulse-podcasts",
        ),
        d1_database_name="pulse",
    )
