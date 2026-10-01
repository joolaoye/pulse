import logging
from typing import (
    Dict,
    Optional,
)


class NodeLogger:
    def __init__(
        self,
        logger: logging.Logger,
        run_id: str,
        pipeline_id: str,
    ) -> None:
        self._logger = logger
        self._run_id = run_id
        self._pipeline_id = pipeline_id

    def node_started(
        self,
        *,
        node_name: str,
        input_summary: Dict[str, object],
        attempt: Optional[int] = None,
    ) -> None:
        self._logger.info(
            "node_started",
            extra=self._build_log_context(
                event="node_started",
                node_name=node_name,
                attempt=attempt,
                input_summary=input_summary,
            ),
        )

    def node_completed(
        self,
        *,
        node_name: str,
        elapsed_ms: float,
        result_summary: Dict[str, object],
        attempt: Optional[int] = None,
    ) -> None:
        self._logger.info(
            "node_completed",
            extra=self._build_log_context(
                event="node_completed",
                node_name=node_name,
                attempt=attempt,
                elapsed_ms=elapsed_ms,
                result_summary=result_summary,
            ),
        )

    def node_failed(
        self,
        *,
        node_name: str,
        elapsed_ms: float,
        error: Exception,
        attempt: Optional[int] = None,
    ) -> None:
        self._logger.error(
            "node_failed",
            extra=self._build_log_context(
                event="node_failed",
                node_name=node_name,
                attempt=attempt,
                elapsed_ms=elapsed_ms,
                error_type=error.__class__.__name__,
                error_message=str(error),
            ),
            exc_info=(
                error.__class__,
                error,
                error.__traceback__,
            ),
        )

    def _build_log_context(
        self,
        *,
        event: str,
        node_name: str,
        attempt: Optional[int] = None,
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
            "node_name": node_name,
            "attempt": attempt,
            "elapsed_ms": elapsed_ms,
            "input_summary": (input_summary or {}),
            "result_summary": (result_summary or {}),
            "error_type": error_type,
            "error_message": error_message,
        }
