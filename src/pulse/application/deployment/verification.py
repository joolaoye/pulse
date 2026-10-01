from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from pulse.application.deployment.errors import (
    DeploymentError,
)
from pulse.application.deployment.models import (
    DeploymentInputs,
)
from pulse.application.deployment.secrets import (
    WORKER_SECRET_NAMES,
)
from pulse.infrastructure.cloudflare.worker_state import (
    CloudflareWorkerState,
)
from pulse.infrastructure.cloudflare.wrangler_config import (
    D1_BINDING,
    SCHEDULER_CRON,
    WORKER_NAME,
    WORKFLOW_BINDING,
    WORKFLOW_CLASS,
    WORKFLOW_NAME,
)


@dataclass(frozen=True)
class DeploymentVerification:
    worker_name: str
    version_id: Optional[str]


async def verify_deployment(
    *,
    inputs: DeploymentInputs,
    worker_state: CloudflareWorkerState,
) -> DeploymentVerification:
    settings = await worker_state.get_settings(
        worker_name=WORKER_NAME,
    )

    bindings = settings.get("bindings")

    if not isinstance(bindings, list):
        raise DeploymentError("Deployed Worker did not return valid bindings.")

    _verify_workflow_binding(
        bindings=bindings,
    )
    _verify_d1_binding(
        bindings=bindings,
        database_id=inputs.cloudflare.d1_database_id,
    )

    schedules = await worker_state.get_schedules(
        worker_name=WORKER_NAME,
    )
    _verify_scheduler_cron(
        schedules=schedules,
    )

    secrets = await worker_state.list_secrets(
        worker_name=WORKER_NAME,
    )
    _verify_secrets(
        secrets=secrets,
    )

    deployments = await worker_state.list_deployments(
        worker_name=WORKER_NAME,
    )

    return DeploymentVerification(
        worker_name=WORKER_NAME,
        version_id=_resolve_version_id(
            deployments=deployments,
        ),
    )


def _verify_workflow_binding(
    *,
    bindings: List[Dict[str, Any]],
) -> None:
    for binding in bindings:
        if (
            binding.get("type") == "workflow"
            and binding.get("name") == WORKFLOW_BINDING
            and binding.get("workflow_name") == WORKFLOW_NAME
            and binding.get("class_name") == WORKFLOW_CLASS
        ):
            return

    raise DeploymentError(
        f"Deployed Worker is missing required Workflow binding '{WORKFLOW_BINDING}'."
    )


def _verify_d1_binding(
    *,
    bindings: List[Dict[str, Any]],
    database_id: str,
) -> None:
    for binding in bindings:
        if (
            binding.get("type") == "d1"
            and binding.get("name") == D1_BINDING
            and binding.get("database_id") == database_id
        ):
            return

    raise DeploymentError(f"Deployed Worker is missing required D1 binding '{D1_BINDING}'.")


def _verify_scheduler_cron(
    *,
    schedules: List[Dict[str, Any]],
) -> None:
    deployed_crons = {
        schedule.get("cron")
        for schedule in schedules
        if isinstance(
            schedule.get("cron"),
            str,
        )
    }

    if deployed_crons != {SCHEDULER_CRON}:
        raise DeploymentError(
            f"Deployed Worker has unexpected Cron Triggers. Expected only '{SCHEDULER_CRON}'."
        )


def _verify_secrets(
    *,
    secrets: List[Dict[str, Any]],
) -> None:
    deployed_names: Set[str] = {
        secret["name"]
        for secret in secrets
        if isinstance(
            secret.get("name"),
            str,
        )
    }

    missing = [
        secret_name for secret_name in WORKER_SECRET_NAMES if secret_name not in deployed_names
    ]

    if missing:
        raise DeploymentError("Deployed Worker is missing required secrets: " + ", ".join(missing))


def _resolve_version_id(
    *,
    deployments: List[Dict[str, Any]],
) -> Optional[str]:
    if not deployments:
        raise DeploymentError("Deployed Worker has no active deployment.")

    versions = deployments[0].get("versions")

    if not isinstance(versions, list):
        return None

    for version in versions:
        version_id = version.get("version_id")

        if isinstance(version_id, str):
            return version_id

    return None
