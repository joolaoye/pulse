from importlib.metadata import (
    PackageNotFoundError,
    version,
)

from rich.console import (
    Console,
)
import typer

from pulse.cli.commands.deploy import deploy
from pulse.cli.commands.init import initialize
from pulse.cli.commands.pipeline import app as pipeline_app
from pulse.cli.commands.run import run
from pulse.cli.commands.schedule import app as schedule_app
from pulse.cli.commands.show import app as show_app

PACKAGE_NAME = "pulse"

console = Console()

app = typer.Typer(
    help=("Pulse is an automated personalized podcast pipeline."),
    no_args_is_help=True,
)

app.add_typer(
    show_app,
    name="show",
)

app.add_typer(
    pipeline_app,
    name="pipeline",
)

app.add_typer(
    schedule_app,
    name="schedule",
)

app.command(
    "run",
)(run)

app.command(
    "init",
)(initialize)

app.command(
    "deploy",
)(deploy)


def _get_version() -> str:
    try:
        return version(PACKAGE_NAME)

    except PackageNotFoundError:
        return "unknown"


def _version_callback(
    value: bool,
) -> None:
    if not value:
        return

    console.print(f"Pulse {_get_version()}")

    raise typer.Exit()


@app.callback()
def main(
    version_requested: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help=("Show the installed Pulse version and exit."),
    ),
) -> None:
    pass


if __name__ == "__main__":
    app()
