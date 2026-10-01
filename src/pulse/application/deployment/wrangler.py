import os
from pathlib import Path
import subprocess

from pulse.application.deployment.errors import (
    DeploymentError,
    DeploymentPreflightError,
)
from pulse.application.deployment.models import (
    DeploymentInputs,
)
from pulse.infrastructure.cloudflare.wrangler_config import (
    WRANGLER_CONFIG_PATH,
    render_wrangler_config,
)


def validate_wrangler_configuration(
    inputs: DeploymentInputs,
) -> None:
    actual = WRANGLER_CONFIG_PATH.read_text()

    expected = render_wrangler_config(
        account_id=inputs.cloudflare.account_id,
        d1_database_name=inputs.d1_database_name,
        d1_database_id=inputs.cloudflare.d1_database_id,
        vectorize_index_name=(inputs.resources.vectorize_index_name),
        podcast_bucket_name=(inputs.resources.podcast_bucket_name),
    )

    if actual != expected:
        raise DeploymentPreflightError(
            "Wrangler configuration is out of sync with "
            "wrangler.jsonc.template. Run 'pulse init' "
            "to regenerate it."
        )

    _validate_no_secret_values(
        config=actual,
        inputs=inputs,
    )


def _validate_no_secret_values(
    *,
    config: str,
    inputs: DeploymentInputs,
) -> None:
    secrets = (
        inputs.cloudflare.api_token,
        inputs.providers.anthropic_api_key,
        inputs.providers.voyage_api_key,
        inputs.providers.x_bearer_token,
        inputs.providers.elevenlabs_api_key,
    )

    if any(secret and secret in config for secret in secrets):
        raise DeploymentPreflightError(
            "Wrangler configuration contains a secret value. Secrets must be deployed separately."
        )


def deploy_worker(
    *,
    inputs: DeploymentInputs,
    secrets_path: Path,
) -> None:
    if not secrets_path.is_file():
        raise DeploymentPreflightError(f"Worker secrets file does not exist: {secrets_path}")

    wrangler_path = _resolve_project_wrangler()

    environment = os.environ.copy()

    environment["CLOUDFLARE_API_TOKEN"] = inputs.cloudflare.api_token

    command = [
        str(wrangler_path),
        "deploy",
        "--config",
        str(inputs.wrangler_config_path),
        "--secrets-file",
        str(secrets_path),
    ]

    try:
        subprocess.run(
            command,
            env=environment,
            check=True,
        )
    except FileNotFoundError as error:
        raise DeploymentPreflightError(
            "Unable to deploy Pulse because the project-local "
            "Wrangler executable could not be started."
        ) from error
    except subprocess.CalledProcessError as error:
        raise DeploymentError(
            f"Wrangler deployment failed with exit code {error.returncode}."
        ) from error


def _resolve_project_wrangler() -> Path:
    candidates = (
        Path("node_modules/.bin/wrangler"),
        Path("node_modules/.bin/wrangler.cmd"),
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise DeploymentPreflightError(
        "Project-local Wrangler was not found in node_modules/.bin. "
        "Install the project Node dependencies before deploying."
    )
