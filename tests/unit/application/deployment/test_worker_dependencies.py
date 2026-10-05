import subprocess

import pytest

from pulse.application.deployment import (
    worker_dependencies,
)
from pulse.application.deployment.errors import (
    DeploymentBuildError,
)


def test_download_wheel_succeeds_when_downloader_is_available(
    tmp_path,
    monkeypatch,
) -> None:
    wheels_path = tmp_path / "wheels"
    wheels_path.mkdir()

    monkeypatch.setattr(
        worker_dependencies,
        "_TEMP_WHEELS_PATH",
        wheels_path,
    )

    captured = {}

    def succeed(command, *, cwd, check, capture_output, text):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        (wheels_path / "langchain_core-1.6.1-py3-none-any.whl").write_bytes(b"wheel")
        return subprocess.CompletedProcess(
            command,
            0,
        )

    monkeypatch.setattr(
        worker_dependencies.subprocess,
        "run",
        succeed,
    )

    wheel_path = worker_dependencies._download_wheel(
        package="langchain-core",
        version="1.6.1",
    )

    assert wheel_path == wheels_path / "langchain_core-1.6.1-py3-none-any.whl"
    assert captured["command"] == [
        "uv",
        "tool",
        "run",
        "--from",
        "pip",
        "pip",
        "download",
        "--no-deps",
        "--python-version",
        "3.12",
        "--platform",
        "any",
        "--only-binary=:all:",
        "langchain-core==1.6.1",
    ]
    assert captured["cwd"] == wheels_path
    assert captured["check"] is True


def test_download_wheel_reports_missing_pip_without_blaming_the_package(
    tmp_path,
    monkeypatch,
) -> None:
    wheels_path = tmp_path / "wheels"
    wheels_path.mkdir()

    monkeypatch.setattr(
        worker_dependencies,
        "_TEMP_WHEELS_PATH",
        wheels_path,
    )

    def missing_pip(command, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=command,
            stderr=".venv/bin/python: No module named pip",
        )

    monkeypatch.setattr(
        worker_dependencies.subprocess,
        "run",
        missing_pip,
    )

    with pytest.raises(DeploymentBuildError) as error:
        worker_dependencies._download_wheel(
            package="langchain-core",
            version="1.6.1",
        )

    message = str(error.value)

    assert "pip is not installed in the current environment" in message
    assert "uv tool run --from pip" in message
    assert "langchain-core" not in message


def test_download_wheel_reports_missing_uv_without_blaming_the_package(
    tmp_path,
    monkeypatch,
) -> None:
    wheels_path = tmp_path / "wheels"
    wheels_path.mkdir()

    monkeypatch.setattr(
        worker_dependencies,
        "_TEMP_WHEELS_PATH",
        wheels_path,
    )

    def missing_uv(*args, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(
        worker_dependencies.subprocess,
        "run",
        missing_uv,
    )

    with pytest.raises(DeploymentBuildError) as error:
        worker_dependencies._download_wheel(
            package="langchain-core",
            version="1.6.1",
        )

    message = str(error.value)

    assert "pip is not installed in the current environment" in message
    assert "langchain-core" not in message


def test_download_wheel_reports_genuine_package_download_failure(
    tmp_path,
    monkeypatch,
) -> None:
    wheels_path = tmp_path / "wheels"
    wheels_path.mkdir()

    monkeypatch.setattr(
        worker_dependencies,
        "_TEMP_WHEELS_PATH",
        wheels_path,
    )

    def package_missing(command, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=command,
            stderr=(
                "ERROR: Could not find a version that satisfies the requirement "
                "langchain-core==1.6.1 (from versions: none)\n"
                "ERROR: No matching distribution found for langchain-core==1.6.1"
            ),
        )

    monkeypatch.setattr(
        worker_dependencies.subprocess,
        "run",
        package_missing,
    )

    with pytest.raises(DeploymentBuildError) as error:
        worker_dependencies._download_wheel(
            package="langchain-core",
            version="1.6.1",
        )

    message = str(error.value)

    assert message == "Failed to download pure-Python wheel for langchain-core 1.6.1."
    assert "pip is not installed" not in message
