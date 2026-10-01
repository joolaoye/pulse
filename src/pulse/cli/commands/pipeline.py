import asyncio
from pathlib import Path
from typing import Dict, Optional

from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
import typer

from pulse.application.configuration import (
    PodcastPipelineUpdate,
    bootstrap_configuration,
)
from pulse.application.configuration.errors import (
    PodcastPipelineAlreadyExistsError,
    PodcastPipelineNotFoundError,
    PodcastShowNotFoundError,
)
from pulse.cli.input.files import (
    load_interest_profile,
    load_podcast_configuration,
)
from pulse.types import PodcastPipeline

console = Console()

app = typer.Typer(
    help="Manage podcast pipelines.",
)


@app.command("list")
def list_pipelines() -> None:
    asyncio.run(_list_pipelines())


async def _list_pipelines() -> None:
    async with bootstrap_configuration() as application:
        pipelines = await application.pipeline_manager.list()

    if not pipelines:
        console.print("No podcast pipelines found.")
        return

    table = Table(
        title="Podcast Pipelines",
    )

    table.add_column("Pipeline ID")
    table.add_column("Show ID")
    table.add_column("X List ID")
    table.add_column("Duration")
    table.add_column("Speakers")
    table.add_column("Enabled")

    for pipeline in pipelines:
        table.add_row(
            pipeline.pipeline_id,
            pipeline.show_id,
            pipeline.x_list_id,
            f"{pipeline.target_episode_duration_seconds}s",
            str(len(pipeline.speakers)),
            "Yes" if pipeline.enabled else "No",
        )

    console.print(table)


@app.command("get")
def get_pipeline(
    pipeline_id: str = typer.Argument(
        ...,
        help="The podcast pipeline ID.",
    ),
) -> None:
    try:
        asyncio.run(
            _get_pipeline(
                pipeline_id=pipeline_id,
            )
        )
    except PodcastPipelineNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error


async def _get_pipeline(
    *,
    pipeline_id: str,
) -> None:
    async with bootstrap_configuration() as application:
        pipeline = await application.pipeline_manager.get(
            pipeline_id=pipeline_id,
        )

    table = Table(
        show_header=False,
    )

    table.add_column(
        "Field",
        style="bold",
    )
    table.add_column("Value")

    table.add_row("Pipeline ID", pipeline.pipeline_id)
    table.add_row("Show ID", pipeline.show_id)
    table.add_row("X List ID", pipeline.x_list_id)
    table.add_row(
        "Target Duration",
        f"{pipeline.target_episode_duration_seconds}s",
    )
    table.add_row(
        "Enabled",
        "Yes" if pipeline.enabled else "No",
    )
    table.add_row(
        "Speakers",
        str(len(pipeline.speakers)),
    )
    table.add_row(
        "Interest Profile",
        pipeline.interest_profile_markdown,
    )

    console.print(table)


@app.command("create")
def create_pipeline(
    interest_profile_path: Path = typer.Argument(
        ...,
        help="Path to the interest profile Markdown file.",
    ),
    podcast_configuration_path: Path = typer.Argument(
        ...,
        help="Path to the podcast configuration JSON file.",
    ),
    pipeline_id: str = typer.Option(
        ...,
        "--pipeline-id",
        prompt="Pipeline ID",
    ),
    show_id: str = typer.Option(
        ...,
        "--show-id",
        prompt="Show ID",
    ),
    x_list_id: str = typer.Option(
        ...,
        "--x-list-id",
        prompt="X List ID",
    ),
    duration: int = typer.Option(
        ...,
        "--duration",
        prompt="Target episode duration in seconds",
        min=1,
    ),
) -> None:
    try:
        podcast_configuration = load_podcast_configuration(
            path=podcast_configuration_path,
        )
        interest_profile_markdown = load_interest_profile(
            path=interest_profile_path,
        )

        pipeline = PodcastPipeline(
            pipeline_id=pipeline_id,
            show_id=show_id,
            podcast_profile=podcast_configuration.podcast_profile,
            speakers=podcast_configuration.speakers,
            speaker_voice_bindings=(podcast_configuration.speaker_voice_bindings),
            interest_profile_markdown=interest_profile_markdown,
            x_list_id=x_list_id,
            target_episode_duration_seconds=duration,
            enabled=True,
        )

        created_pipeline = asyncio.run(
            _create_pipeline(
                pipeline=pipeline,
            )
        )

    except (
        PodcastPipelineAlreadyExistsError,
        PodcastShowNotFoundError,
    ) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    except ValidationError as error:
        console.print("[red]Invalid podcast pipeline configuration.[/red]")
        console.print(str(error))
        raise typer.Exit(code=1) from error

    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Created podcast pipeline '{created_pipeline.pipeline_id}'.[/green]")


async def _create_pipeline(
    *,
    pipeline: PodcastPipeline,
) -> PodcastPipeline:
    async with bootstrap_configuration() as application:
        return await application.pipeline_manager.create(
            pipeline=pipeline,
        )


@app.command("update")
def update_pipeline(
    pipeline_id: str = typer.Argument(
        ...,
        help="The podcast pipeline ID.",
    ),
    show_id: Optional[str] = typer.Option(
        None,
        "--show-id",
        help="Replace the podcast show associated with the pipeline.",
    ),
    interest_profile_path: Optional[Path] = typer.Option(
        None,
        "--interests",
        help=("Path to a Markdown interest profile. The existing profile is replaced completely."),
    ),
    podcast_configuration_path: Optional[Path] = typer.Option(
        None,
        "--podcast-configuration",
        help="Path to the podcast configuration JSON file.",
    ),
    x_list_id: Optional[str] = typer.Option(
        None,
        "--x-list-id",
        help="Replace the X list ID.",
    ),
    duration: Optional[int] = typer.Option(
        None,
        "--duration",
        min=1,
        help="Replace the target episode duration in seconds.",
    ),
) -> None:
    try:
        update_values = _build_pipeline_update_values(
            show_id=show_id,
            interest_profile_path=interest_profile_path,
            podcast_configuration_path=podcast_configuration_path,
            x_list_id=x_list_id,
            duration=duration,
        )

        if not update_values:
            console.print("[yellow]No updates provided.[/yellow]")
            return

        update = PodcastPipelineUpdate.model_validate(update_values)

        updated_pipeline = asyncio.run(
            _update_pipeline(
                pipeline_id=pipeline_id,
                update=update,
            )
        )

    except (
        PodcastPipelineNotFoundError,
        PodcastShowNotFoundError,
    ) as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    except ValidationError as error:
        console.print("[red]Invalid podcast pipeline update.[/red]")
        console.print(str(error))
        raise typer.Exit(code=1) from error

    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Updated podcast pipeline '{updated_pipeline.pipeline_id}'.[/green]")


def _build_pipeline_update_values(
    *,
    show_id: Optional[str],
    interest_profile_path: Optional[Path],
    podcast_configuration_path: Optional[Path],
    x_list_id: Optional[str],
    duration: Optional[int],
) -> Dict[str, object]:
    values: Dict[str, object] = {}

    if show_id is not None:
        values["show_id"] = show_id

    if x_list_id is not None:
        values["x_list_id"] = x_list_id

    if duration is not None:
        values["target_episode_duration_seconds"] = duration

    if interest_profile_path is not None:
        values["interest_profile_markdown"] = load_interest_profile(
            path=interest_profile_path,
        )

    if podcast_configuration_path is not None:
        podcast_configuration = load_podcast_configuration(
            path=podcast_configuration_path,
        )

        values["podcast_profile"] = podcast_configuration.podcast_profile
        values["speakers"] = podcast_configuration.speakers
        values["speaker_voice_bindings"] = podcast_configuration.speaker_voice_bindings

    return values


async def _update_pipeline(
    *,
    pipeline_id: str,
    update: PodcastPipelineUpdate,
) -> PodcastPipeline:
    async with bootstrap_configuration() as application:
        return await application.pipeline_manager.update(
            pipeline_id=pipeline_id,
            update=update,
        )


@app.command("enable")
def enable_pipeline(
    pipeline_id: str = typer.Argument(
        ...,
        help="The podcast pipeline ID.",
    ),
) -> None:
    try:
        pipeline = asyncio.run(
            _enable_pipeline(
                pipeline_id=pipeline_id,
            )
        )
    except PodcastPipelineNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Enabled podcast pipeline '{pipeline.pipeline_id}'.[/green]")


async def _enable_pipeline(
    *,
    pipeline_id: str,
) -> PodcastPipeline:
    async with bootstrap_configuration() as application:
        return await application.pipeline_manager.enable(
            pipeline_id=pipeline_id,
        )


@app.command("disable")
def disable_pipeline(
    pipeline_id: str = typer.Argument(
        ...,
        help="The podcast pipeline ID.",
    ),
) -> None:
    try:
        pipeline = asyncio.run(
            _disable_pipeline(
                pipeline_id=pipeline_id,
            )
        )
    except PodcastPipelineNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Disabled podcast pipeline '{pipeline.pipeline_id}'.[/green]")


async def _disable_pipeline(
    *,
    pipeline_id: str,
) -> PodcastPipeline:
    async with bootstrap_configuration() as application:
        return await application.pipeline_manager.disable(
            pipeline_id=pipeline_id,
        )
