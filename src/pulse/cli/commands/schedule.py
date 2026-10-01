import asyncio
from datetime import (
    datetime,
    time,
    timezone as datetime_timezone,
)
import re

from rich.console import Console
from rich.table import Table
import typer

from pulse.application.configuration import (
    bootstrap_configuration,
)
from pulse.application.configuration.errors import (
    PodcastPipelineNotFoundError,
    PodcastPipelineScheduleNotFoundError,
)
from pulse.types import (
    PodcastPipelineSchedule,
)

console = Console()

app = typer.Typer(
    help="Manage podcast pipeline schedules.",
)


@app.command("set")
def set_schedule(
    pipeline_id: str = typer.Argument(
        ...,
        help="The podcast pipeline ID.",
    ),
    local_time: str = typer.Option(
        ...,
        "--time",
        prompt="Daily local time",
        help="Daily local time in 24-hour HH:MM format.",
    ),
    timezone_name: str = typer.Option(
        ...,
        "--timezone",
        prompt="Timezone",
        help="IANA timezone name, such as America/Chicago.",
    ),
) -> None:
    try:
        parsed_time = _parse_local_time(
            value=local_time,
        )

        schedule = asyncio.run(
            _set_schedule(
                pipeline_id=pipeline_id,
                local_time=parsed_time,
                timezone_name=timezone_name,
            )
        )

    except PodcastPipelineNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Set schedule for podcast pipeline '{schedule.pipeline_id}'.[/green]")

    _print_schedule(
        schedule=schedule,
    )


async def _set_schedule(
    *,
    pipeline_id: str,
    local_time: time,
    timezone_name: str,
) -> PodcastPipelineSchedule:
    async with bootstrap_configuration() as application:
        return await application.schedule_manager.set(
            pipeline_id=pipeline_id,
            local_time=local_time,
            timezone_name=timezone_name,
        )


@app.command("get")
def get_schedule(
    pipeline_id: str = typer.Argument(
        ...,
        help="The podcast pipeline ID.",
    ),
) -> None:
    try:
        schedule = asyncio.run(
            _get_schedule(
                pipeline_id=pipeline_id,
            )
        )

    except PodcastPipelineScheduleNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    _print_schedule(
        schedule=schedule,
    )


async def _get_schedule(
    *,
    pipeline_id: str,
) -> PodcastPipelineSchedule:
    async with bootstrap_configuration() as application:
        return await application.schedule_manager.get(
            pipeline_id=pipeline_id,
        )


@app.command("remove")
def remove_schedule(
    pipeline_id: str = typer.Argument(
        ...,
        help="The podcast pipeline ID.",
    ),
) -> None:
    try:
        asyncio.run(
            _remove_schedule(
                pipeline_id=pipeline_id,
            )
        )

    except PodcastPipelineScheduleNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Removed schedule for podcast pipeline '{pipeline_id}'.[/green]")


async def _remove_schedule(
    *,
    pipeline_id: str,
) -> None:
    async with bootstrap_configuration() as application:
        await application.schedule_manager.remove(
            pipeline_id=pipeline_id,
        )


def _print_schedule(
    *,
    schedule: PodcastPipelineSchedule,
) -> None:
    table = Table(
        show_header=False,
    )

    table.add_column(
        "Field",
        style="bold",
    )

    table.add_column(
        "Value",
    )

    table.add_row(
        "Pipeline ID",
        schedule.pipeline_id,
    )

    table.add_row(
        "Local Time",
        schedule.local_time.strftime("%H:%M"),
    )

    table.add_row(
        "Timezone",
        schedule.timezone,
    )

    table.add_row(
        "Next Run",
        _format_utc_datetime(
            value=schedule.next_run_at,
        ),
    )

    table.add_row(
        "Last Dispatched",
        (
            _format_utc_datetime(
                value=schedule.last_dispatched_at,
            )
            if schedule.last_dispatched_at is not None
            else "Never"
        ),
    )

    console.print(table)


def _parse_local_time(
    *,
    value: str,
) -> time:
    value = value.strip()

    if (
        re.fullmatch(
            r"(?:[01]\d|2[0-3]):[0-5]\d",
            value,
        )
        is None
    ):
        raise ValueError("Schedule time must use 24-hour HH:MM format.")

    hour, minute = (int(part) for part in value.split(":"))

    return time(
        hour=hour,
        minute=minute,
    )


def _format_utc_datetime(
    *,
    value: datetime,
) -> str:
    return (
        value.astimezone(datetime_timezone.utc)
        .isoformat(timespec="seconds")
        .replace(
            "+00:00",
            "Z",
        )
    )
