from pathlib import Path
import shutil
import subprocess
from zipfile import BadZipFile, ZipFile

from pulse.application.deployment.errors import (
    DeploymentBuildError,
)

_DIST_PATH = Path("dist")
_WORKER_PYTHON_MODULES_PATH = Path("workers/cloudflare/python_modules")

_PULSE_WHEEL_PATTERN = "pulse-*.whl"

_REQUIRED_WHEEL_MEMBERS = (
    "pulse/__init__.py",
    "pulse/application/execution/run_manager.py",
    "pulse/application/runtime/podcast_pipeline_runtime_factory.py",
    "pulse/application/workflow_factory.py",
)


def clean_build_state() -> None:
    _remove_pulse_wheels()
    _recreate_worker_python_modules()


def build_pulse_wheel() -> Path:
    existing_wheels = _find_pulse_wheels()

    if existing_wheels:
        raise DeploymentBuildError(
            "Pulse wheel build started with existing Pulse wheels "
            "in dist. The deployment build must start clean."
        )

    try:
        subprocess.run(
            [
                "uv",
                "build",
                "--wheel",
            ],
            check=True,
        )
    except FileNotFoundError as error:
        raise DeploymentBuildError(
            "Unable to build Pulse wheel because 'uv' was not found."
        ) from error
    except subprocess.CalledProcessError as error:
        raise DeploymentBuildError("Pulse wheel build failed.") from error

    wheels = _find_pulse_wheels()

    if len(wheels) != 1:
        raise DeploymentBuildError(
            f"Expected exactly one newly built Pulse wheel, found {len(wheels)}."
        )

    wheel_path = wheels[0]

    _validate_pulse_wheel(
        wheel_path=wheel_path,
    )

    return wheel_path


def _remove_pulse_wheels() -> None:
    for wheel_path in _find_pulse_wheels():
        wheel_path.unlink()


def _recreate_worker_python_modules() -> None:
    if _WORKER_PYTHON_MODULES_PATH.exists():
        shutil.rmtree(
            _WORKER_PYTHON_MODULES_PATH,
        )

    _WORKER_PYTHON_MODULES_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )


def _find_pulse_wheels() -> list[Path]:
    if not _DIST_PATH.exists():
        return []

    return sorted(_DIST_PATH.glob(_PULSE_WHEEL_PATTERN))


def _validate_pulse_wheel(
    *,
    wheel_path: Path,
) -> None:
    try:
        with ZipFile(wheel_path) as wheel:
            members = set(wheel.namelist())
    except (BadZipFile, OSError) as error:
        raise DeploymentBuildError(f"Unable to inspect Pulse wheel '{wheel_path}'.") from error

    missing = [member for member in _REQUIRED_WHEEL_MEMBERS if member not in members]

    if missing:
        raise DeploymentBuildError(
            "Pulse wheel is missing required package files: " + ", ".join(missing)
        )
