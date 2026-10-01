from datetime import datetime, timezone
from typing import Optional, TextIO
from uuid import uuid4

from pulse.application.composition.assemble import PulseApplication
from pulse.application.execution.errors import (
    WorkflowRunFailedError,
    WorkflowRunNotFoundError,
    WorkflowRunPipelineMismatchError,
)
from pulse.application.orchestration.runner import WorkflowRunner
from pulse.application.orchestration.state.initial_state import (
    build_initial_workflow_state,
)
from pulse.application.orchestration.state.workflow_state import (
    WorkflowState,
)
from pulse.application.workflow_factory import PulseWorkflowFactory


class RunManager:
    def __init__(
        self,
        *,
        application: PulseApplication,
        run_log_stream: Optional[TextIO] = None,
    ) -> None:
        self._application = application
        self._workflow_factory = PulseWorkflowFactory(
            application=application,
            run_log_stream=run_log_stream,
        )

    async def run(
        self,
        *,
        pipeline_id: str,
        run_id: Optional[str] = None,
    ) -> WorkflowState:
        pipeline_id = self._validate_non_empty_identifier(
            name="Podcast pipeline ID",
            value=pipeline_id,
        )

        if run_id is None:
            run_id = self._create_identifier()
        else:
            run_id = self._validate_non_empty_identifier(
                name="Workflow run ID",
                value=run_id,
            )

        runtime = await self._application.podcast_pipeline_runtime_factory.create(
            pipeline_id=pipeline_id,
        )

        runner = self._workflow_factory.create(
            run_id=run_id,
            runtime=runtime,
        )

        initial_state = build_initial_workflow_state(
            runtime=runtime,
            run_id=run_id,
            episode_id=self._create_identifier(),
            published_at=datetime.now(timezone.utc),
        )

        try:
            return await self._run_workflow(
                runner=runner,
                initial_state=initial_state,
                run_id=run_id,
                pipeline_id=pipeline_id,
            )
        finally:
            runner.close()

    async def resume(
        self,
        *,
        run_id: str,
        pipeline_id: str,
    ) -> WorkflowState:
        run_id = self._validate_non_empty_identifier(
            name="Workflow run ID",
            value=run_id,
        )
        pipeline_id = self._validate_non_empty_identifier(
            name="Podcast pipeline ID",
            value=pipeline_id,
        )

        runtime = await self._application.podcast_pipeline_runtime_factory.create(
            pipeline_id=pipeline_id,
        )

        runner = self._workflow_factory.create(
            run_id=run_id,
            runtime=runtime,
        )

        try:
            checkpoint_state = await runner.get_state()

            self._validate_resume_state(
                checkpoint_state=checkpoint_state,
                run_id=run_id,
                pipeline_id=pipeline_id,
            )

            if self._is_terminal(
                checkpoint_state=checkpoint_state,
            ):
                return checkpoint_state

            return await self._resume_workflow(
                runner=runner,
                run_id=run_id,
                pipeline_id=pipeline_id,
            )
        finally:
            runner.close()

    async def run_or_resume(
        self,
        *,
        run_id: str,
        pipeline_id: str,
    ) -> WorkflowState:
        run_id = self._validate_non_empty_identifier(
            name="Workflow run ID",
            value=run_id,
        )
        pipeline_id = self._validate_non_empty_identifier(
            name="Podcast pipeline ID",
            value=pipeline_id,
        )

        runtime = await self._application.podcast_pipeline_runtime_factory.create(
            pipeline_id=pipeline_id,
        )

        runner = self._workflow_factory.create(
            run_id=run_id,
            runtime=runtime,
        )

        try:
            checkpoint_state = await runner.get_state()

            if not checkpoint_state:
                initial_state = build_initial_workflow_state(
                    runtime=runtime,
                    run_id=run_id,
                    episode_id=self._create_identifier(),
                    published_at=datetime.now(timezone.utc),
                )

                return await self._run_workflow(
                    runner=runner,
                    initial_state=initial_state,
                    run_id=run_id,
                    pipeline_id=pipeline_id,
                )

            self._validate_resume_state(
                checkpoint_state=checkpoint_state,
                run_id=run_id,
                pipeline_id=pipeline_id,
            )

            if self._is_terminal(
                checkpoint_state=checkpoint_state,
            ):
                return checkpoint_state

            return await self._resume_workflow(
                runner=runner,
                run_id=run_id,
                pipeline_id=pipeline_id,
            )
        finally:
            runner.close()

    @staticmethod
    async def _run_workflow(
        *,
        runner: WorkflowRunner,
        initial_state: WorkflowState,
        run_id: str,
        pipeline_id: str,
    ) -> WorkflowState:
        try:
            return await runner.run(
                initial_state=initial_state,
            )
        except Exception as error:
            raise WorkflowRunFailedError(
                run_id=run_id,
                pipeline_id=pipeline_id,
                error=error,
            ) from error

    @staticmethod
    async def _resume_workflow(
        *,
        runner: WorkflowRunner,
        run_id: str,
        pipeline_id: str,
    ) -> WorkflowState:
        try:
            return await runner.resume()
        except Exception as error:
            raise WorkflowRunFailedError(
                run_id=run_id,
                pipeline_id=pipeline_id,
                error=error,
            ) from error

    @staticmethod
    def _is_terminal(
        *,
        checkpoint_state: WorkflowState,
    ) -> bool:
        return checkpoint_state.get("workflow_outcome") is not None

    @staticmethod
    def _validate_resume_state(
        *,
        checkpoint_state: WorkflowState,
        run_id: str,
        pipeline_id: str,
    ) -> None:
        if (
            not checkpoint_state
            or "run_id" not in checkpoint_state
            or "pipeline_id" not in checkpoint_state
        ):
            raise WorkflowRunNotFoundError(f"Workflow run '{run_id}' does not exist.")

        checkpoint_run_id = checkpoint_state["run_id"]

        if checkpoint_run_id != run_id:
            raise RuntimeError(
                "Checkpoint state run ID does not match "
                "the requested workflow run ID. "
                f"Requested: '{run_id}'. "
                f"Checkpoint: '{checkpoint_run_id}'."
            )

        checkpoint_pipeline_id = checkpoint_state["pipeline_id"]

        if checkpoint_pipeline_id != pipeline_id:
            raise WorkflowRunPipelineMismatchError(
                "Workflow run "
                f"'{run_id}' belongs to podcast pipeline "
                f"'{checkpoint_pipeline_id}', not "
                f"'{pipeline_id}'."
            )

    @staticmethod
    def _create_identifier() -> str:
        return str(uuid4())

    @staticmethod
    def _validate_non_empty_identifier(
        *,
        name: str,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(f"{name} cannot be empty.")

        return value
