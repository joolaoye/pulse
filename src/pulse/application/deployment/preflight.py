from typing import Dict

from pulse.application.deployment.errors import (
    DeploymentPreflightError,
    PulseNotInitializedError,
)
from pulse.application.deployment.models import (
    DeploymentInputs,
)


def validate_deployment_preflight(
    inputs: DeploymentInputs,
) -> None:
    if not inputs.wrangler_config_path.is_file():
        raise PulseNotInitializedError(
            "Pulse has not been initialized. Run 'pulse init' before 'pulse deploy'."
        )

    required: Dict[str, str] = {
        "CLOUDFLARE_ACCOUNT_ID": inputs.cloudflare.account_id,
        "PULSE_CLOUDFLARE_API_TOKEN": inputs.cloudflare.api_token,
        "CLOUDFLARE_D1_DATABASE_ID": inputs.cloudflare.d1_database_id,
        "PULSE_VECTORIZE_INDEX_NAME": inputs.resources.vectorize_index_name,
        "PULSE_PODCAST_BUCKET_NAME": inputs.resources.podcast_bucket_name,
        "ANTHROPIC_API_KEY": inputs.providers.anthropic_api_key,
        "VOYAGE_API_KEY": inputs.providers.voyage_api_key,
        "X_BEARER_TOKEN": inputs.providers.x_bearer_token,
        "ELEVENLABS_API_KEY": inputs.providers.elevenlabs_api_key,
    }

    missing = [name for name, value in required.items() if not value or not value.strip()]

    if missing:
        raise DeploymentPreflightError(
            "Pulse initialization is incomplete. "
            "Missing required deployment values: "
            + ", ".join(missing)
            + ". Run 'pulse init' to repair the installation."
        )
