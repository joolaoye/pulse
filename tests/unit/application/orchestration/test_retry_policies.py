import httpx
import pytest

from pulse.application.orchestration.graph.retry_policies import retry_on_transient_error
from pulse.application.orchestration.nodes.errors import MissingNodeInputError


def _http_status(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("request failed", request=request, response=response)


class _StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(status_code)
        self.status_code = status_code


@pytest.mark.parametrize(
    ("error", "retryable"),
    [
        (_http_status(408), True),
        (_http_status(429), True),
        (_http_status(503), True),
        (httpx.ConnectError("connection failed"), True),
        (_StatusError(500), True),
        (_http_status(400), False),
        (_StatusError(404), False),
        (
            MissingNodeInputError(node_name="publish_episode", input_name="episode_id"),
            False,
        ),
    ],
)
def test_transient_provider_failures_are_retryable(error: Exception, retryable: bool) -> None:
    assert retry_on_transient_error(error) is retryable
