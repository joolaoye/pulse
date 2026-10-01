import pytest

from pulse.application import environment
from pulse.application.deployment.inputs import (
    load_deployment_inputs,
)

_REQUIRED_ENVIRONMENT = {
    "PULSE_CLOUDFLARE_API_TOKEN": "cloudflare-secret",
    "CLOUDFLARE_ACCOUNT_ID": "account-id",
    "CLOUDFLARE_D1_DATABASE_ID": "database-id",
    "ANTHROPIC_API_KEY": "anthropic-secret",
    "VOYAGE_API_KEY": "voyage-secret",
    "X_BEARER_TOKEN": "x-secret",
    "ELEVENLABS_API_KEY": "elevenlabs-secret",
    "PULSE_VECTORIZE_INDEX_NAME": "pulse-signals",
    "PULSE_PODCAST_BUCKET_NAME": "pulse-podcasts",
    "PULSE_D1_DATABASE_NAME": "pulse",
}


def test_missing_deployment_credential_fails_clearly(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        environment,
        "load_dotenv",
        lambda: None,
    )

    for name, value in _REQUIRED_ENVIRONMENT.items():
        monkeypatch.setenv(
            name,
            value,
        )

    monkeypatch.delenv(
        "ANTHROPIC_API_KEY",
        raising=False,
    )

    with pytest.raises(RuntimeError) as error:
        load_deployment_inputs()

    assert str(error.value) == ("The required environment variable 'ANTHROPIC_API_KEY' is missing.")
