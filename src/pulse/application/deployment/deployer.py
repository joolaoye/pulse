from pulse.application.deployment.build import (
    build_pulse_wheel,
    clean_build_state,
)
from pulse.application.deployment.models import (
    DeploymentInputs,
)
from pulse.application.deployment.preflight import (
    validate_deployment_preflight,
)
from pulse.application.deployment.secrets import (
    deployment_secrets_file,
)
from pulse.application.deployment.verification import (
    DeploymentVerification,
    verify_deployment,
)
from pulse.application.deployment.worker_bundle import (
    validate_worker_bundle,
)
from pulse.application.deployment.worker_dependencies import (
    assemble_worker_dependencies,
)
from pulse.application.deployment.wrangler import (
    deploy_worker,
    validate_wrangler_configuration,
)
from pulse.infrastructure.cloudflare.client import (
    CloudflareClient,
)
from pulse.infrastructure.cloudflare.config import (
    CloudflareConfig,
)
from pulse.infrastructure.cloudflare.worker_state import (
    CloudflareWorkerState,
)


async def deploy_application(
    inputs: DeploymentInputs,
) -> DeploymentVerification:
    validate_deployment_preflight(
        inputs,
    )
    validate_wrangler_configuration(
        inputs,
    )

    clean_build_state()

    pulse_wheel_path = build_pulse_wheel()

    assemble_worker_dependencies(
        pulse_wheel_path=pulse_wheel_path,
    )
    validate_worker_bundle()

    with deployment_secrets_file(
        inputs=inputs,
    ) as secrets_path:
        deploy_worker(
            inputs=inputs,
            secrets_path=secrets_path,
        )

    return await _verify_deployment(
        inputs=inputs,
    )


async def _verify_deployment(
    *,
    inputs: DeploymentInputs,
) -> DeploymentVerification:
    cloudflare_client = CloudflareClient(
        config=CloudflareConfig(
            api_token=inputs.cloudflare.api_token,
            account_id=inputs.cloudflare.account_id,
        ),
    )

    try:
        return await verify_deployment(
            inputs=inputs,
            worker_state=CloudflareWorkerState(
                cloudflare_client=cloudflare_client,
            ),
        )
    finally:
        await cloudflare_client.aclose()
