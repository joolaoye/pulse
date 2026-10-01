import os
from pathlib import (
    Path,
)
import shutil
import subprocess
import sys
from typing import (
    List,
)

REPOSITORY_ROOT = Path(__file__).resolve().parent


def main() -> None:
    print()
    print("Bootstrapping Pulse")
    print()

    _ensure_repository_files()

    _install_python_dependencies()

    npm_executable = _require_executable(
        executable_name="npm",
        installation_message=(
            "Node.js and npm are required to install Pulse's pinned Wrangler dependency."
        ),
    )

    _install_node_dependencies(
        npm_executable=(npm_executable),
    )

    _verify_wrangler()

    _print_completion_message()


def _ensure_repository_files() -> None:
    required_paths: List[Path] = [
        REPOSITORY_ROOT / "pyproject.toml",
        REPOSITORY_ROOT / "uv.lock",
        REPOSITORY_ROOT / "package.json",
        REPOSITORY_ROOT / "package-lock.json",
    ]

    missing_paths = [path for path in required_paths if not path.is_file()]

    if not missing_paths:
        return

    formatted_paths = ", ".join(path.name for path in missing_paths)

    raise RuntimeError(
        (f"Pulse bootstrap is missing required repository files: {formatted_paths}.")
    )


def _install_python_dependencies() -> None:
    print("Installing Pulse Python dependencies...")

    uv_executable = _require_executable(
        executable_name="uv",
        installation_message=(
            "uv is required to install Pulse's locked Python dependencies. "
            "Install uv and retry bootstrap."
        ),
    )

    _run_command(
        [
            uv_executable,
            "sync",
        ]
    )


def _install_node_dependencies(
    *,
    npm_executable: str,
) -> None:
    print("Installing Pulse tooling...")

    _run_command(
        [
            npm_executable,
            "ci",
            "--include=dev",
        ]
    )


def _verify_wrangler() -> None:
    print("Verifying Wrangler...")

    wrangler_executable = _resolve_local_wrangler()

    _run_command(
        [
            wrangler_executable,
            "--version",
        ]
    )


def _resolve_local_wrangler() -> str:
    binary_directory = REPOSITORY_ROOT / "node_modules" / ".bin"

    wrangler_executable = shutil.which(
        "wrangler",
        path=str(binary_directory),
    )

    if wrangler_executable is None:
        raise RuntimeError(("The project-local Wrangler installation could not be found."))

    return wrangler_executable


def _require_executable(
    *,
    executable_name: str,
    installation_message: str,
) -> str:
    executable = shutil.which(executable_name)

    if executable is None:
        raise RuntimeError(installation_message)

    return executable


def _run_command(
    command: List[str],
) -> None:
    try:
        subprocess.run(
            command,
            cwd=(REPOSITORY_ROOT),
            check=True,
        )

    except subprocess.CalledProcessError as error:
        raise RuntimeError((f"Bootstrap command failed: {' '.join(command)}")) from error


def _print_completion_message() -> None:
    print()
    print("Pulse bootstrap complete.")
    print()

    if os.name == "nt":
        print("Activate the environment with:")

        print(r"  .\.venv\Scripts\Activate.ps1")

    else:
        print("Activate the environment with:")

        print("  source .venv/bin/activate")

    print()
    print("Then configure Pulse with:")

    print("  pulse init")

    print()


if __name__ == "__main__":
    try:
        main()

    except RuntimeError as error:
        print(
            f"Bootstrap failed: {error}",
            file=sys.stderr,
        )

        sys.exit(1)
