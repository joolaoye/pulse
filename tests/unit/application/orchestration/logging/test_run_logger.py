from io import StringIO

from pulse.application.orchestration.logging.run_logger import (
    RunLogger,
)


def test_run_logger_writes_run_events_to_file_and_stream(
    tmp_path,
) -> None:
    stream = StringIO()

    logger = RunLogger(
        run_id="run-1",
        pipeline_id="pipeline-1",
        log_directory=tmp_path,
        stream=stream,
    )

    logger.run_started(
        run_summary={
            "invocation_mode": "new",
        }
    )
    logger.run_completed(
        elapsed_ms=125.5,
        result_summary={
            "workflow_outcome": "PUBLISHED",
            "episode_id": "episode-1",
        },
    )

    logger.close()

    stream_output = stream.getvalue()
    file_output = (tmp_path / "run-1.log").read_text()

    for output in (
        stream_output,
        file_output,
    ):
        assert "run=run-1" in output
        assert "pipeline=pipeline-1" in output
        assert "event=run_started" in output
        assert "event=run_completed" in output
        assert "elapsed_ms=125.50" in output
        assert "PUBLISHED" in output
        assert "episode-1" in output


def test_node_logger_writes_events_to_run_stream(
    tmp_path,
) -> None:
    stream = StringIO()

    logger = RunLogger(
        run_id="run-1",
        pipeline_id="pipeline-1",
        log_directory=tmp_path,
        stream=stream,
    )

    logger.node_logger.node_started(
        node_name="retrieve_sources",
        input_summary={
            "source": "x",
        },
    )

    logger.node_logger.node_completed(
        node_name="retrieve_sources",
        elapsed_ms=42.25,
        result_summary={
            "discourse_count": 10,
        },
    )

    logger.close()

    output = stream.getvalue()

    assert "run=run-1" in output
    assert "pipeline=pipeline-1" in output
    assert "event=node_started" in output
    assert "event=node_completed" in output
    assert "node=retrieve_sources" in output
    assert "elapsed_ms=42.25" in output
    assert "discourse_count" in output


def test_node_logger_writes_failure_to_stream(
    tmp_path,
) -> None:
    stream = StringIO()

    logger = RunLogger(
        run_id="run-1",
        pipeline_id="pipeline-1",
        log_directory=tmp_path,
        stream=stream,
    )

    error = ValueError("boom")

    logger.node_logger.node_failed(
        node_name="process_semantics",
        elapsed_ms=15.0,
        error=error,
    )

    logger.close()

    output = stream.getvalue()

    assert "run=run-1" in output
    assert "pipeline=pipeline-1" in output
    assert "event=node_failed" in output
    assert "node=process_semantics" in output
    assert "error_type=ValueError" in output
    assert "error=boom" in output
