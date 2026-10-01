from datetime import datetime, timezone
from io import StringIO
from typing import Any, Optional, cast

import pytest

from pulse.application.orchestration.logging.run_logger import (
    RunLogger,
)
from pulse.application.orchestration.runner.workflow_runner import (
    WorkflowRunner,
)
from pulse.application.orchestration.state import WorkflowState
from pulse.types import (
    NoContentReason,
    WorkflowOutcome,
)


class _FakeCompiledGraph:
    def __init__(
        self,
        *,
        result: Optional[WorkflowState] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self._result = result
        self._error = error

    async def ainvoke(
        self,
        _input_state,
        *,
        config,
    ):
        if self._error is not None:
            raise self._error

        return self._result


class _FakeGraphDefinition:
    def __init__(
        self,
        graph: _FakeCompiledGraph,
    ) -> None:
        self._graph = graph

    def compile(
        self,
        *,
        checkpointer,
    ):
        return self._graph


class _FakeGraphBuilder:
    def __init__(
        self,
        graph: _FakeCompiledGraph,
    ) -> None:
        self._graph = graph

    def build(self):
        return _FakeGraphDefinition(
            self._graph,
        )


def _state(
    *,
    outcome: WorkflowOutcome,
    no_content_reason: Optional[NoContentReason] = None,
) -> WorkflowState:
    return cast(
        WorkflowState,
        {
            "run_id": "run-1",
            "pipeline_id": "pipeline-1",
            "episode_id": "episode-1",
            "published_at": datetime.now(timezone.utc),
            "workflow_outcome": outcome,
            "no_content_reason": no_content_reason,
        },
    )


def _runner(
    *,
    tmp_path,
    stream: StringIO,
    graph: _FakeCompiledGraph,
) -> WorkflowRunner:
    run_logger = RunLogger(
        run_id="run-1",
        pipeline_id="pipeline-1",
        log_directory=tmp_path,
        stream=stream,
    )

    return WorkflowRunner(
        run_id="run-1",
        graph_builder=cast(Any, _FakeGraphBuilder(graph)),
        checkpointer=cast(Any, object()),
        run_logger=run_logger,
    )


@pytest.mark.asyncio
async def test_new_run_logs_published_outcome(
    tmp_path,
) -> None:
    stream = StringIO()
    state = _state(
        outcome=WorkflowOutcome.PUBLISHED,
    )

    runner = _runner(
        tmp_path=tmp_path,
        stream=stream,
        graph=_FakeCompiledGraph(
            result=state,
        ),
    )

    result = await runner.run(
        initial_state=state,
    )
    runner.close()

    assert result == state

    output = stream.getvalue()

    assert "event=run_started" in output
    assert "invocation_mode" in output
    assert "new" in output
    assert "event=run_completed" in output
    assert WorkflowOutcome.PUBLISHED.value in output
    assert "episode-1" in output


@pytest.mark.asyncio
async def test_resume_logs_no_content_outcome(
    tmp_path,
) -> None:
    stream = StringIO()
    state = _state(
        outcome=WorkflowOutcome.NO_CONTENT,
        no_content_reason=(NoContentReason.NO_UNSEEN_SIGNALS),
    )

    runner = _runner(
        tmp_path=tmp_path,
        stream=stream,
        graph=_FakeCompiledGraph(
            result=state,
        ),
    )

    result = await runner.resume()
    runner.close()

    assert result == state

    output = stream.getvalue()

    assert "event=run_started" in output
    assert "resume" in output
    assert "event=run_completed" in output
    assert WorkflowOutcome.NO_CONTENT.value in output
    assert NoContentReason.NO_UNSEEN_SIGNALS.value in output

    completed_log = output.split(
        "event=run_completed",
        maxsplit=1,
    )[1]

    assert "episode-1" not in completed_log


@pytest.mark.asyncio
async def test_run_failure_logs_execution_context(
    tmp_path,
) -> None:
    stream = StringIO()

    runner = _runner(
        tmp_path=tmp_path,
        stream=stream,
        graph=_FakeCompiledGraph(
            error=ValueError("boom"),
        ),
    )

    initial_state = _state(
        outcome=WorkflowOutcome.PUBLISHED,
    )

    with pytest.raises(
        ValueError,
        match="boom",
    ):
        await runner.run(
            initial_state=initial_state,
        )

    runner.close()

    output = stream.getvalue()

    assert "run=run-1" in output
    assert "pipeline=pipeline-1" in output
    assert "event=run_failed" in output
    assert "error_type=ValueError" in output
    assert "error=boom" in output
