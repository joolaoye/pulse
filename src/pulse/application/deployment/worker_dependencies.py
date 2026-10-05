import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Tuple
from zipfile import BadZipFile, ZipFile

from pulse.application.deployment.errors import (
    DeploymentBuildError,
)

_WORKER_PATH = Path("workers/cloudflare")
_PYTHON_MODULES_PATH = _WORKER_PATH / "python_modules"
_STUBS_PATH = _WORKER_PATH / "stubs"
_TEMP_WHEELS_PATH = _WORKER_PATH / ".wheels_temp"


_WORKER_TOOL_ENV_PATH = Path(".venv-workers")


_PYWRANGLER_ENV_PATH = _WORKER_PATH / ".venv-workers"


_MANUAL_WHEELS: Tuple[
    Tuple[str, str],
    ...,
] = (
    ("langchain-core", "1.6.1"),
    ("langchain-protocol", "0.0.19"),
    ("langchain-anthropic", "1.7.0"),
    ("langgraph-checkpoint-cloudflare-d1", "0.1.6"),
    ("langgraph", "1.2.11"),
    ("langgraph-sdk", "0.4.4"),
    ("langgraph-checkpoint", "4.2.0"),
    ("langgraph-prebuilt", "1.1.0"),
    ("sqlalchemy-cloudflare-d1", "0.3.11"),
    ("sqlalchemy", "2.0.43"),
)

WORKER_COMPATIBILITY_STUBS: Tuple[
    str,
    ...,
] = (
    "xxhash",
    "ormsgpack",
    "uuid_utils",
    "websockets",
    "langsmith",
    "orjson",
)

_OVERRIDDEN_PACKAGE_PATTERNS: Tuple[
    str,
    ...,
] = (
    "langchain",
    "langchain-*.dist-info",
    "langchain_core",
    "langchain_core-*.dist-info",
    "langchain_anthropic",
    "langchain_anthropic-*.dist-info",
    "langchain_protocol",
    "langchain_protocol-*.dist-info",
    "langgraph",
    "langgraph-*.dist-info",
    "langgraph_sdk",
    "langgraph_sdk-*.dist-info",
    "langgraph_checkpoint",
    "langgraph_checkpoint-*.dist-info",
    "langgraph_prebuilt",
    "langgraph_prebuilt-*.dist-info",
    "langgraph_checkpoint_cloudflare_d1",
    "langgraph_checkpoint_cloudflare_d1-*.dist-info",
    "sqlalchemy",
    "sqlalchemy-*.dist-info",
    "sqlalchemy_cloudflare_d1",
    "sqlalchemy_cloudflare_d1-*.dist-info",
)


def assemble_worker_dependencies(
    *,
    pulse_wheel_path: Path,
) -> None:
    _validate_assembly_inputs(
        pulse_wheel_path=pulse_wheel_path,
    )

    _reset_temp_wheels()

    try:
        _sync_pyodide_dependencies()
        _remove_overridden_packages()
        _install_manual_wheels()
        _fix_langgraph_namespace_packages()
        _apply_compatibility_stubs()
        _extract_wheel(
            wheel_path=pulse_wheel_path,
        )
    finally:
        _cleanup_temporary_state()


def _validate_assembly_inputs(
    *,
    pulse_wheel_path: Path,
) -> None:
    if not pulse_wheel_path.is_file():
        raise DeploymentBuildError(f"Pulse wheel does not exist: {pulse_wheel_path}")

    if not _PYTHON_MODULES_PATH.is_dir():
        raise DeploymentBuildError("Worker python_modules does not exist.")

    if not _STUBS_PATH.is_dir():
        raise DeploymentBuildError(f"Worker stubs directory does not exist: {_STUBS_PATH}")


def _sync_pyodide_dependencies() -> None:
    environment = os.environ.copy()
    environment["UV_PROJECT_ENVIRONMENT"] = str(_WORKER_TOOL_ENV_PATH.resolve())

    _run_command(
        [
            "uv",
            "run",
            "pywrangler",
            "sync",
        ],
        cwd=_WORKER_PATH,
        environment=environment,
        description=("sync Pyodide-compatible Worker dependencies"),
    )


def _remove_overridden_packages() -> None:
    for pattern in _OVERRIDDEN_PACKAGE_PATTERNS:
        _remove_matches(
            pattern=pattern,
        )


def _install_manual_wheels() -> None:
    for package, version in _MANUAL_WHEELS:
        wheel_path = _download_wheel(
            package=package,
            version=version,
        )

        _extract_wheel(
            wheel_path=wheel_path,
        )

        wheel_path.unlink()


def _download_wheel(
    *,
    package: str,
    version: str,
) -> Path:
    command = _pure_python_wheel_download_command(
        package=package,
        version=version,
    )

    try:
        subprocess.run(
            command,
            cwd=_TEMP_WHEELS_PATH,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise DeploymentBuildError(_missing_wheel_downloader_message()) from error
    except subprocess.CalledProcessError as error:
        if _is_wheel_downloader_failure(error):
            raise DeploymentBuildError(_missing_wheel_downloader_message()) from error

        raise DeploymentBuildError(
            f"Failed to download pure-Python wheel for {package} {version}."
        ) from error

    return _resolve_downloaded_wheel(
        package=package,
    )


def _pure_python_wheel_download_command(
    *,
    package: str,
    version: str,
) -> List[str]:
    return [
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
        f"{package}=={version}",
    ]


def _missing_wheel_downloader_message() -> str:
    return (
        "Deployment requires pip to download Python wheels, but pip is not "
        "installed in the current environment. Install uv, then retry "
        "deployment. Pulse downloads these wheels with `uv tool run --from pip`."
    )


def _is_wheel_downloader_failure(
    error: subprocess.CalledProcessError,
) -> bool:
    output = f"{error.stdout or ''}\n{error.stderr or ''}"

    return any(
        marker in output
        for marker in (
            "No module named pip",
            "Failed to spawn `pip`",
            "Failed to install tool",
        )
    )


def _resolve_downloaded_wheel(
    *,
    package: str,
) -> Path:
    prefix = package.replace(
        "-",
        "_",
    )

    wheels: List[Path] = sorted(_TEMP_WHEELS_PATH.glob(f"{prefix}-*.whl"))

    if len(wheels) != 1:
        raise DeploymentBuildError(
            f"Expected exactly one downloaded wheel for '{package}', found {len(wheels)}."
        )

    return wheels[0]


def _extract_wheel(
    *,
    wheel_path: Path,
) -> None:
    try:
        with ZipFile(wheel_path) as wheel:
            wheel.extractall(_PYTHON_MODULES_PATH)
    except (BadZipFile, OSError) as error:
        raise DeploymentBuildError(f"Failed to extract wheel '{wheel_path}'.") from error


def _fix_langgraph_namespace_packages() -> None:
    langgraph_path = _PYTHON_MODULES_PATH / "langgraph"

    if not langgraph_path.is_dir():
        raise DeploymentBuildError("langgraph package was not installed.")

    directories = [
        langgraph_path,
        *[path for path in langgraph_path.rglob("*") if path.is_dir()],
    ]

    for directory in directories:
        relative_parts = directory.relative_to(langgraph_path).parts

        if any(part.startswith(".") for part in relative_parts):
            continue

        init_path = directory / "__init__.py"

        if not init_path.exists():
            init_path.touch()


def _apply_compatibility_stubs() -> None:
    for stub_name in WORKER_COMPATIBILITY_STUBS:
        _remove_matches(
            pattern=stub_name,
        )
        _remove_matches(
            pattern=(f"{stub_name}-*.dist-info"),
        )

        _copy_stub(
            stub_name=stub_name,
        )


def _copy_stub(
    *,
    stub_name: str,
) -> None:
    source_path = _STUBS_PATH / f"{stub_name}-stub" / "src" / stub_name

    if not source_path.is_dir():
        raise DeploymentBuildError(f"Stub package not found: {source_path}")

    destination_path = _PYTHON_MODULES_PATH / stub_name

    if destination_path.exists():
        shutil.rmtree(
            destination_path,
        )

    shutil.copytree(
        source_path,
        destination_path,
    )


def _remove_matches(
    *,
    pattern: str,
) -> None:
    for path in _PYTHON_MODULES_PATH.glob(pattern):
        if path.is_dir():
            shutil.rmtree(
                path,
            )
        else:
            path.unlink()


def _run_command(
    command: List[str],
    *,
    cwd: Path,
    environment: dict,
    description: str,
) -> None:
    try:
        subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=True,
        )
    except FileNotFoundError as error:
        raise DeploymentBuildError(
            f"Unable to {description} because '{command[0]}' was not found."
        ) from error
    except subprocess.CalledProcessError as error:
        raise DeploymentBuildError(f"Failed to {description}.") from error


def _reset_temp_wheels() -> None:
    shutil.rmtree(
        _TEMP_WHEELS_PATH,
        ignore_errors=True,
    )

    _TEMP_WHEELS_PATH.mkdir(
        parents=True,
    )


def _cleanup_temporary_state() -> None:
    shutil.rmtree(
        _TEMP_WHEELS_PATH,
        ignore_errors=True,
    )

    shutil.rmtree(
        _PYWRANGLER_ENV_PATH,
        ignore_errors=True,
    )
