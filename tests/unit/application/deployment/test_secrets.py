import json

from pulse.application.deployment.secrets import (
    WORKER_SECRET_NAMES,
    deployment_secrets_file,
)


def test_deployment_secrets_contains_only_worker_secrets(
    deployment_inputs,
) -> None:
    with deployment_secrets_file(
        inputs=deployment_inputs,
    ) as secrets_path:
        secrets = json.loads(secrets_path.read_text())

        assert set(secrets) == set(WORKER_SECRET_NAMES)

        assert secrets["CLOUDFLARE_API_TOKEN"] == "cloudflare-secret"

        assert "PULSE_CLOUDFLARE_API_TOKEN" not in secrets


def test_deployment_secrets_file_is_removed(
    deployment_inputs,
) -> None:
    with deployment_secrets_file(
        inputs=deployment_inputs,
    ) as secrets_path:
        assert secrets_path.is_file()
        saved_path = secrets_path

    assert not saved_path.exists()
