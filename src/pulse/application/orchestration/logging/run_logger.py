import logging
from pathlib import Path
from typing import (
    Dict,
    Optional,
    TextIO,
)

from pulse.application.orchestration.logging.node_logger import NodeLogger

DEFAULT_LOG_DIRECTORY = Path("logs/runs")


class _RunLogFormatter(logging.Formatter):
    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        timestamp = self.formatTime(
            record,
            self.datefmt,
        )

        parts = [
            timestamp,
            record.levelname,
        ]

        run_id = getattr(
            record,
            "run_id",
            None,
        )

        if run_id is not None:
            parts.append(f"run={run_id}")

        pipeline_id = getattr(
            record,
            "pipeline_id",
            None,
        )

        if pipeline_id is not None:
            parts.append(f"pipeline={pipeline_id}")

        event = getattr(
            record,
            "event",
            None,
        )

        if event is not None:
            parts.append(f"event={event}")

        node_name = getattr(
            record,
            "node_name",
            None,
        )

        if node_name is not None:
            parts.append(f"node={node_name}")

        attempt = getattr(
            record,
            "attempt",
            None,
        )

        if attempt is not None:
            parts.append(f"attempt={attempt}")

        elapsed_ms = getattr(
            record,
            "elapsed_ms",
            None,
        )

        if elapsed_ms is not None:
            parts.append(f"elapsed_ms={elapsed_ms:.2f}")

        input_summary = getattr(
            record,
            "input_summary",
            None,
        )

        if input_summary:
            parts.append(f"input={input_summary}")

        result_summary = getattr(
            record,
            "result_summary",
            None,
        )

        if result_summary:
            parts.append(f"result={result_summary}")

        error_type = getattr(
            record,
            "error_type",
            None,
        )

        if error_type is not None:
            parts.append(f"error_type={error_type}")

        error_message = getattr(
            record,
            "error_message",
            None,
        )

        if error_message is not None:
            parts.append(f"error={error_message}")

        formatted = " ".join(parts)

        if record.exc_info:
            formatted = f"{formatted}\n{self.formatException(record.exc_info)}"

        return formatted


class RunLogger:
    def __init__(
        self,
        *,
        run_id: str,
        pipeline_id: str,
        log_directory: Path = DEFAULT_LOG_DIRECTORY,
        level: int = logging.INFO,
        stream: Optional[TextIO] = None,
    ) -> None:
        self._run_id = run_id
        self._pipeline_id = pipeline_id

        log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._log_path = log_directory / f"{run_id}.log"

        self._logger = logging.Logger(
            name=f"pulse.run.{run_id}",
            level=level,
        )

        self._logger.propagate = False

        formatter = _RunLogFormatter(
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

        self._file_handler = logging.FileHandler(
            self._log_path,
            encoding="utf-8",
        )
        self._file_handler.setLevel(level)
        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(
            self._file_handler,
        )

        self._stream_handler: Optional[logging.StreamHandler] = None

        if stream is not None:
            self._stream_handler = logging.StreamHandler(
                stream,
            )
            self._stream_handler.setLevel(level)
            self._stream_handler.setFormatter(formatter)
            self._logger.addHandler(
                self._stream_handler,
            )

        self._node_logger = NodeLogger(
            logger=self._logger,
            run_id=self._run_id,
            pipeline_id=self._pipeline_id,
        )

        self._closed = False

    @property
    def run_id(
        self,
    ) -> str:
        return self._run_id

    @property
    def log_path(
        self,
    ) -> Path:
        return self._log_path

    @property
    def node_logger(
        self,
    ) -> NodeLogger:
        return self._node_logger

    def run_started(
        self,
        *,
        run_summary: Optional[Dict[str, object]] = None,
    ) -> None:
        self._logger.info(
            "run_started",
            extra=self._build_log_context(
                event="run_started",
                input_summary=(run_summary or {}),
            ),
        )

    def run_completed(
        self,
        *,
        elapsed_ms: float,
        result_summary: Optional[Dict[str, object]] = None,
    ) -> None:
        self._logger.info(
            "run_completed",
            extra=self._build_log_context(
                event="run_completed",
                elapsed_ms=elapsed_ms,
                result_summary=(result_summary or {}),
            ),
        )

    def run_failed(
        self,
        *,
        elapsed_ms: float,
        error: Exception,
    ) -> None:
        self._logger.error(
            "run_failed",
            extra=self._build_log_context(
                event="run_failed",
                elapsed_ms=elapsed_ms,
                error_type=(error.__class__.__name__),
                error_message=str(error),
            ),
            exc_info=(
                error.__class__,
                error,
                error.__traceback__,
            ),
        )

    def close(
        self,
    ) -> None:
        if self._closed:
            return

        self._file_handler.flush()
        self._file_handler.close()
        self._logger.removeHandler(
            self._file_handler,
        )

        if self._stream_handler is not None:
            self._stream_handler.flush()
            self._logger.removeHandler(
                self._stream_handler,
            )
            self._stream_handler.close()

        self._closed = True

    def _build_log_context(
        self,
        *,
        event: str,
        elapsed_ms: Optional[float] = None,
        input_summary: Optional[Dict[str, object]] = None,
        result_summary: Optional[Dict[str, object]] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, object]:
        return {
            "run_id": self._run_id,
            "pipeline_id": self._pipeline_id,
            "event": event,
            "elapsed_ms": elapsed_ms,
            "input_summary": (input_summary or {}),
            "result_summary": (result_summary or {}),
            "error_type": error_type,
            "error_message": (error_message),
        }

    def __enter__(
        self,
    ) -> "RunLogger":
        return self

    def __exit__(
        self,
        *args: object,
    ) -> None:
        self.close()
