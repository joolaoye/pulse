import pytest

from pulse.application.deployment import (
    worker_bundle,
)
from pulse.application.deployment.errors import (
    DeploymentBuildError,
)

_REQUIRED_MODULES = (
    "pulse",
    "langgraph_checkpoint_cloudflare_d1",
    "requests",
    "msgpack",
    "xxhash",
    "ormsgpack",
    "uuid_utils",
    "websockets",
    "langsmith",
    "orjson",
)


def test_worker_bundle_reports_missing_module(
    tmp_path,
    monkeypatch,
) -> None:
    modules_path = tmp_path / "python_modules"
    modules_path.mkdir()

    for module_name in _REQUIRED_MODULES:
        if module_name == "msgpack":
            continue

        (modules_path / module_name).mkdir()

    monkeypatch.setattr(
        worker_bundle,
        "_WORKER_PYTHON_MODULES_PATH",
        modules_path,
    )

    with pytest.raises(
        DeploymentBuildError,
        match="msgpack",
    ):
        worker_bundle.validate_worker_bundle()
