import asyncio

from rich.console import Console
import typer

from pulse.application.deployment import (
    deploy_application,
)
from pulse.application.deployment.inputs import (
    load_deployment_inputs,
)

console = Console()


def deploy() -> None:
    try:
        asyncio.run(_deploy())
    except Exception as error:
        console.print(f"[red]Deployment failed:[/red] {error}")
        raise typer.Exit(code=1) from error


async def _deploy() -> None:
    inputs = load_deployment_inputs()

    await deploy_application(
        inputs=inputs,
    )
