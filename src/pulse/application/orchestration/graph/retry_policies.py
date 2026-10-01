import httpx
from langgraph.types import (
    RetryPolicy,
    default_retry_on,  # type: ignore
)

from pulse.application.orchestration.nodes.errors import (
    MissingNodeInputError,
)


def retry_on_transient_error(
    error: Exception,
) -> bool:
    if isinstance(
        error,
        MissingNodeInputError,
    ):
        return False

    if isinstance(
        error,
        httpx.HTTPStatusError,
    ):
        status_code = error.response.status_code

        return status_code == 408 or status_code == 429 or status_code >= 500

    if isinstance(
        error,
        httpx.TransportError,
    ):
        return True

    status_code = getattr(
        error,
        "status_code",
        None,
    )

    if isinstance(
        status_code,
        int,
    ):
        return status_code == 408 or status_code == 429 or status_code >= 500

    return default_retry_on(error)


TRANSIENT_RETRY_POLICY = RetryPolicy(
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=8.0,
    max_attempts=2,
    jitter=True,
    retry_on=(retry_on_transient_error),
)


PUBLICATION_RETRY_POLICY = RetryPolicy(
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=8.0,
    max_attempts=3,
    jitter=True,
    retry_on=(retry_on_transient_error),
)
