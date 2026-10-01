import pytest

from pulse.application.composition.cloud import ProviderCredentials
from pulse.application.deployment.errors import (
    DeploymentPreflightError,
    PulseNotInitializedError,
)
from pulse.application.deployment.models import (
    DeploymentInputs,
)
from pulse.application.deployment.preflight import (
    validate_deployment_preflight,
)


def test_preflight_rejects_missing_initialization(
    deployment_inputs: DeploymentInputs,
) -> None:
    with pytest.raises(
        PulseNotInitializedError,
    ) as error:
        validate_deployment_preflight(
            deployment_inputs,
        )

    assert str(error.value) == (
        "Pulse has not been initialized. Run 'pulse init' before 'pulse deploy'."
    )


def test_preflight_reports_missing_credential(
    deployment_inputs: DeploymentInputs,
) -> None:
    deployment_inputs.wrangler_config_path.touch()

    inputs = DeploymentInputs(
        wrangler_config_path=(deployment_inputs.wrangler_config_path),
        cloudflare=deployment_inputs.cloudflare,
        providers=ProviderCredentials(
            anthropic_api_key="",
            voyage_api_key=(deployment_inputs.providers.voyage_api_key),
            x_bearer_token=(deployment_inputs.providers.x_bearer_token),
            elevenlabs_api_key=(deployment_inputs.providers.elevenlabs_api_key),
        ),
        resources=deployment_inputs.resources,
        d1_database_name=(deployment_inputs.d1_database_name),
    )

    with pytest.raises(
        DeploymentPreflightError,
    ) as error:
        validate_deployment_preflight(
            inputs,
        )

    message = str(error.value)

    assert "ANTHROPIC_API_KEY" in message
    assert "Run 'pulse init'" in message
