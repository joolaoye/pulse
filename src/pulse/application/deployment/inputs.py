from pulse.application.composition.cloud import (
    CloudflareRestCredentials,
    ProviderCredentials,
    ResourceNames,
)
from pulse.application.deployment.models import (
    DeploymentInputs,
)
from pulse.application.environment import (
    load_environment,
    require_environment_variable,
)
from pulse.infrastructure.cloudflare.wrangler_config import (
    WRANGLER_CONFIG_PATH,
)


def load_deployment_inputs() -> DeploymentInputs:
    load_environment()

    return DeploymentInputs(
        wrangler_config_path=WRANGLER_CONFIG_PATH,
        cloudflare=CloudflareRestCredentials(
            api_token=require_environment_variable(
                variable_name="PULSE_CLOUDFLARE_API_TOKEN",
            ),
            account_id=require_environment_variable(
                variable_name="CLOUDFLARE_ACCOUNT_ID",
            ),
            d1_database_id=require_environment_variable(
                variable_name="CLOUDFLARE_D1_DATABASE_ID",
            ),
        ),
        providers=ProviderCredentials(
            anthropic_api_key=require_environment_variable(
                variable_name="ANTHROPIC_API_KEY",
            ),
            voyage_api_key=require_environment_variable(
                variable_name="VOYAGE_API_KEY",
            ),
            x_bearer_token=require_environment_variable(
                variable_name="X_BEARER_TOKEN",
            ),
            elevenlabs_api_key=require_environment_variable(
                variable_name="ELEVENLABS_API_KEY",
            ),
        ),
        resources=ResourceNames(
            vectorize_index_name=require_environment_variable(
                variable_name="PULSE_VECTORIZE_INDEX_NAME",
            ),
            podcast_bucket_name=require_environment_variable(
                variable_name="PULSE_PODCAST_BUCKET_NAME",
            ),
        ),
        d1_database_name=require_environment_variable(
            variable_name="PULSE_D1_DATABASE_NAME",
        ),
    )
