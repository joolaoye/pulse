import asyncio
from typing import Never, Optional

from rich.console import Console
import typer

from pulse.application.composition.local import bootstrap_local
from pulse.application.execution.errors import (
    WorkflowRunFailedError,
    WorkflowRunNotFoundError,
    WorkflowRunPipelineMismatchError,
)
from pulse.application.execution.run_manager import RunManager
from pulse.application.orchestration.state import WorkflowState
from pulse.types import WorkflowOutcome

console = Console()


def run(
    target: str = typer.Argument(
        ...,
        help="Podcast pipeline ID, or 'resume' to resume an existing run.",
    ),
    run_id: Optional[str] = typer.Argument(
        None,
        help="Run ID when resuming an existing workflow.",
    ),
    pipeline_id: Optional[str] = typer.Option(
        None,
        "--pipeline-id",
        help="Podcast pipeline ID associated with the run being resumed.",
    ),
) -> None:
    if target == "resume":
        _handle_resume_command(
            run_id=run_id,
            pipeline_id=pipeline_id,
        )
        return

    _handle_fresh_run_command(
        pipeline_id=target,
        run_id=run_id,
        resume_pipeline_id=pipeline_id,
    )


def _handle_fresh_run_command(
    *,
    pipeline_id: str,
    run_id: Optional[str],
    resume_pipeline_id: Optional[str],
) -> None:
    if run_id is not None:
        _exit_with_error("Unexpected run ID for a fresh workflow run.")

    if resume_pipeline_id is not None:
        _exit_with_error("--pipeline-id is only valid when resuming a workflow.")

    _execute_run(
        pipeline_id=pipeline_id,
    )


def _handle_resume_command(
    *,
    run_id: Optional[str],
    pipeline_id: Optional[str],
) -> None:
    if run_id is None:
        _exit_with_error("A run ID is required when resuming a workflow.")

    if pipeline_id is None:
        _exit_with_error("--pipeline-id is required when resuming a workflow.")

    _execute_resume(
        run_id=run_id,
        pipeline_id=pipeline_id,
    )


def _execute_run(
    *,
    pipeline_id: str,
) -> None:
    try:
        result = asyncio.run(
            _run_pipeline(
                pipeline_id=pipeline_id,
            )
        )
    except WorkflowRunFailedError as error:
        _render_run_failure(error=error)
        raise typer.Exit(code=1) from error
    except ValueError as error:
        _exit_with_error(
            str(error),
            cause=error,
        )

    _render_run_result(
        result=result,
    )


def _execute_resume(
    *,
    run_id: str,
    pipeline_id: str,
) -> None:
    try:
        result = asyncio.run(
            _resume_pipeline(
                run_id=run_id,
                pipeline_id=pipeline_id,
            )
        )
    except (
        WorkflowRunNotFoundError,
        WorkflowRunPipelineMismatchError,
    ) as error:
        _exit_with_error(
            str(error),
            cause=error,
        )
    except WorkflowRunFailedError as error:
        _render_run_failure(error=error)
        raise typer.Exit(code=1) from error
    except ValueError as error:
        _exit_with_error(
            str(error),
            cause=error,
        )

    _render_run_result(
        result=result,
    )


async def _run_pipeline(
    *,
    pipeline_id: str,
) -> WorkflowState:
    async with bootstrap_local() as application:
        return await RunManager(
            application=application,
        ).run(
            pipeline_id=pipeline_id,
        )


async def _resume_pipeline(
    *,
    run_id: str,
    pipeline_id: str,
) -> WorkflowState:
    async with bootstrap_local() as application:
        return await RunManager(
            application=application,
        ).resume(
            run_id=run_id,
            pipeline_id=pipeline_id,
        )


def _render_run_failure(
    *,
    error: WorkflowRunFailedError,
) -> None:
    console.print("[red]Workflow run failed.[/red]")
    console.print(f"Pipeline ID: {error.pipeline_id}")
    console.print(f"Run ID: {error.run_id}")
    console.print(f"Error: {error.error}")
    console.print()
    console.print(
        "[yellow]Keep the Run ID above. It can be used to resume this workflow run.[/yellow]"
    )


def _render_run_result(
    *,
    result: WorkflowState,
) -> None:
    outcome = result.get("workflow_outcome")

    if outcome == WorkflowOutcome.NO_CONTENT:
        _render_no_content_result(
            result=result,
        )
        return

    if outcome == WorkflowOutcome.PUBLISHED:
        _render_published_result(
            result=result,
        )
        return

    raise RuntimeError("Workflow completed without a valid terminal outcome.")


def _render_no_content_result(
    *,
    result: WorkflowState,
) -> None:
    console.print("[green]Workflow completed successfully.[/green]")
    console.print("No episode was produced.")

    reason = result.get("no_content_reason")

    if reason is not None:
        console.print(f"Reason: {reason.value}")

    console.print(f"Run ID: {result['run_id']}")


def _render_published_result(
    *,
    result: WorkflowState,
) -> None:
    console.print("[green]Episode published successfully.[/green]")
    console.print(f"Run ID: {result['run_id']}")
    console.print(f"Episode ID: {result['episode_id']}")

    episode_metadata = result.get("episode_metadata")

    if episode_metadata is not None:
        console.print(f"Title: {episode_metadata.title}")

    publication_result = result.get("publication_result")

    if publication_result is None:
        return

    console.print(f"Audio URL: {publication_result.audio_url}")
    console.print(f"Feed URL: {publication_result.feed_url}")


def _exit_with_error(
    message: str,
    *,
    cause: Optional[Exception] = None,
) -> Never:
    console.print(f"[red]Error:[/red] {message}")

    if cause is not None:
        raise typer.Exit(code=1) from cause

    raise typer.Exit(code=1)
