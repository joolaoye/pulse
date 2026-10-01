from contextlib import contextmanager, suppress
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Iterator

from pulse.application.deployment.models import (
    DeploymentInputs,
)

_WORKER_SECRETS_FILENAME = "worker-secrets.json"

WORKER_SECRET_NAMES = (
    "CLOUDFLARE_API_TOKEN",
    "ANTHROPIC_API_KEY",
    "VOYAGE_API_KEY",
    "X_BEARER_TOKEN",
    "ELEVENLABS_API_KEY",
)


@contextmanager
def deployment_secrets_file(
    *,
    inputs: DeploymentInputs,
) -> Iterator[Path]:
    secrets = _build_worker_secrets(
        inputs=inputs,
    )

    with TemporaryDirectory(prefix="pulse-deploy-") as temporary_directory:
        secrets_path = Path(temporary_directory) / _WORKER_SECRETS_FILENAME

        secrets_path.write_text(
            json.dumps(secrets),
            encoding="utf-8",
        )

        with suppress(OSError):
            secrets_path.chmod(0o600)

        yield secrets_path


def _build_worker_secrets(
    *,
    inputs: DeploymentInputs,
) -> Dict[str, str]:
    return {
        "CLOUDFLARE_API_TOKEN": (inputs.cloudflare.api_token),
        "ANTHROPIC_API_KEY": (inputs.providers.anthropic_api_key),
        "VOYAGE_API_KEY": (inputs.providers.voyage_api_key),
        "X_BEARER_TOKEN": (inputs.providers.x_bearer_token),
        "ELEVENLABS_API_KEY": (inputs.providers.elevenlabs_api_key),
    }
