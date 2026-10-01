import subprocess

import pytest

from pulse.application.deployment import wrangler
from pulse.application.deployment.errors import (
    DeploymentError,
)


def test_deploy_worker_uses_expected_paths(
    deployment_inputs,
    tmp_path,
    monkeypatch,
) -> None:
    wrangler_path = tmp_path / "wrangler"
    wrangler_path.touch()

    config_path = deployment_inputs.wrangler_config_path
    config_path.touch()

    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text("{}")

    monkeypatch.setattr(
        wrangler,
        "_resolve_project_wrangler",
        lambda: wrangler_path,
    )

    captured = {}

    def fake_run(
        command,
        *,
        env,
        check,
    ) -> None:
        captured["command"] = command
        captured["env"] = env
        captured["check"] = check

    monkeypatch.setattr(
        wrangler.subprocess,
        "run",
        fake_run,
    )

    wrangler.deploy_worker(
        inputs=deployment_inputs,
        secrets_path=secrets_path,
    )

    assert captured["command"] == [
        str(wrangler_path),
        "deploy",
        "--config",
        str(config_path),
        "--secrets-file",
        str(secrets_path),
    ]

    assert captured["env"]["CLOUDFLARE_API_TOKEN"] == "cloudflare-secret"
    assert captured["check"] is True

    assert "cloudflare-secret" not in (captured["command"])


def test_deploy_worker_propagates_clean_failure(
    deployment_inputs,
    tmp_path,
    monkeypatch,
) -> None:
    wrangler_path = tmp_path / "wrangler"
    wrangler_path.touch()

    deployment_inputs.wrangler_config_path.touch()

    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text("{}")

    monkeypatch.setattr(
        wrangler,
        "_resolve_project_wrangler",
        lambda: wrangler_path,
    )

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["wrangler", "deploy"],
        )

    monkeypatch.setattr(
        wrangler.subprocess,
        "run",
        fail,
    )

    with pytest.raises(
        DeploymentError,
        match="exit code 1",
    ) as error:
        wrangler.deploy_worker(
            inputs=deployment_inputs,
            secrets_path=secrets_path,
        )

    assert "cloudflare-secret" not in str(error.value)
