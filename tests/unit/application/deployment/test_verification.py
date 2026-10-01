import pytest

from pulse.application.deployment.errors import DeploymentError
from pulse.application.deployment.models import DeploymentInputs
from pulse.application.deployment.secrets import WORKER_SECRET_NAMES
from pulse.application.deployment.verification import verify_deployment
from pulse.infrastructure.cloudflare.wrangler_config import (
    D1_BINDING,
    SCHEDULER_CRON,
    WORKER_NAME,
    WORKFLOW_BINDING,
    WORKFLOW_CLASS,
    WORKFLOW_NAME,
)


class _WorkerState:
    def __init__(self, *, database_id: str) -> None:
        self.database_id = database_id

    async def get_settings(self, *, worker_name: str) -> dict:
        del worker_name
        return {
            "bindings": [
                {
                    "type": "workflow",
                    "name": WORKFLOW_BINDING,
                    "workflow_name": WORKFLOW_NAME,
                    "class_name": WORKFLOW_CLASS,
                },
                {
                    "type": "d1",
                    "name": D1_BINDING,
                    "database_id": self.database_id,
                },
            ]
        }

    async def get_schedules(self, *, worker_name: str) -> list[dict]:
        del worker_name
        return [{"cron": SCHEDULER_CRON}]

    async def list_secrets(self, *, worker_name: str) -> list[dict]:
        del worker_name
        return [{"name": name} for name in WORKER_SECRET_NAMES]

    async def list_deployments(self, *, worker_name: str) -> list[dict]:
        del worker_name
        return [{"versions": [{"version_id": "version-1"}]}]


async def test_expected_worker_state_passes_verification(
    deployment_inputs: DeploymentInputs,
) -> None:
    verification = await verify_deployment(
        inputs=deployment_inputs,
        worker_state=_WorkerState(database_id=deployment_inputs.cloudflare.d1_database_id),
    )

    assert verification.worker_name == WORKER_NAME
    assert verification.version_id == "version-1"


async def test_wrong_d1_database_fails_verification(
    deployment_inputs: DeploymentInputs,
) -> None:
    with pytest.raises(DeploymentError):
        await verify_deployment(
            inputs=deployment_inputs,
            worker_state=_WorkerState(database_id="other-database"),
        )
