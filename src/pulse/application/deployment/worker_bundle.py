from pathlib import Path
from typing import Tuple

from pulse.application.deployment.errors import (
    DeploymentBuildError,
)
from pulse.application.deployment.worker_dependencies import (
    WORKER_COMPATIBILITY_STUBS,
)

_WORKER_PYTHON_MODULES_PATH = Path("workers/cloudflare/python_modules")

_REQUIRED_WORKER_MODULES: Tuple[str, ...] = (
    "pulse",
    "langgraph_checkpoint_cloudflare_d1",
    "requests",
    "msgpack",
    *WORKER_COMPATIBILITY_STUBS,
)


def validate_worker_bundle() -> None:
    if not _WORKER_PYTHON_MODULES_PATH.is_dir():
        raise DeploymentBuildError(f"Worker bundle does not exist: {_WORKER_PYTHON_MODULES_PATH}")

    missing_modules = [
        module_name
        for module_name in _REQUIRED_WORKER_MODULES
        if not _worker_module_exists(
            module_name=module_name,
        )
    ]

    if missing_modules:
        raise DeploymentBuildError(
            "Worker bundle is missing required modules: " + ", ".join(missing_modules)
        )


def _worker_module_exists(
    *,
    module_name: str,
) -> bool:
    module_path = _WORKER_PYTHON_MODULES_PATH / module_name.replace(".", "/")

    return module_path.is_dir() or module_path.with_suffix(".py").is_file()
