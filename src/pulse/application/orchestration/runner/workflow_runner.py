from time import perf_counter
from typing import Dict, Optional, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from pulse.application.orchestration.graph.builder import PulseGraphBuilder
from pulse.application.orchestration.logging.run_logger import RunLogger
from pulse.application.orchestration.state import WorkflowState


class WorkflowRunner:
    def __init__(
        self,
        *,
        run_id: str,
        graph_builder: PulseGraphBuilder,
        checkpointer: BaseCheckpointSaver,
        run_logger: RunLogger,
    ) -> None:
        if not run_id.strip():
            raise ValueError("Workflow run ID cannot be empty.")

        self._run_id = run_id
        self._graph: CompiledStateGraph = graph_builder.build().compile(
            checkpointer=checkpointer,
        )
        self._run_logger = run_logger

    async def run(
        self,
        *,
        initial_state: WorkflowState,
    ) -> WorkflowState:
        self._validate_initial_state(initial_state)

        return await self._invoke(
            input_state=initial_state,
            invocation_mode="new",
        )

    async def resume(self) -> WorkflowState:
        return await self._invoke(
            input_state=None,
            invocation_mode="resume",
        )

    async def get_state(self) -> WorkflowState:
        snapshot = await self._graph.aget_state(self._build_config())
        return cast(WorkflowState, snapshot.values)

    def close(self) -> None:
        self._run_logger.close()

    async def _invoke(
        self,
        input_state: Optional[WorkflowState],
        invocation_mode: str,
    ) -> WorkflowState:
        self._run_logger.run_started(
            run_summary={
                "invocation_mode": invocation_mode,
            }
        )
        started_at = perf_counter()

        try:
            result = await self._graph.ainvoke(
                input_state,
                config=self._build_config(),
            )
        except Exception as error:
            self._run_logger.run_failed(
                elapsed_ms=self._elapsed_ms(started_at),
                error=error,
            )
            raise

        result_state = cast(
            WorkflowState,
            result,
        )

        self._run_logger.run_completed(
            elapsed_ms=self._elapsed_ms(started_at),
            result_summary=self._summarize_result(
                state=result_state,
            ),
        )

        return result_state

    def _build_config(self) -> RunnableConfig:
        return {
            "configurable": {
                "thread_id": self._run_id,
            },
        }

    def _validate_initial_state(
        self,
        initial_state: WorkflowState,
    ) -> None:
        if "run_id" not in initial_state:
            raise ValueError("Initial workflow state must contain run_id.")

        state_run_id = initial_state["run_id"]

        if state_run_id != self._run_id:
            raise ValueError(
                "Workflow state run ID must match the WorkflowRunner run ID. "
                f"Runner: {self._run_id}. "
                f"State: {state_run_id}."
            )

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return (perf_counter() - started_at) * 1000

    @staticmethod
    def _summarize_result(
        *,
        state: WorkflowState,
    ) -> Dict[str, object]:
        summary: Dict[str, object] = {}

        workflow_outcome = state.get("workflow_outcome")
        no_content_reason = state.get("no_content_reason")

        if workflow_outcome is not None:
            summary["workflow_outcome"] = workflow_outcome.value

        if no_content_reason is not None:
            summary["no_content_reason"] = no_content_reason.value
        elif workflow_outcome is not None:
            summary["episode_id"] = state["episode_id"]

        return summary
