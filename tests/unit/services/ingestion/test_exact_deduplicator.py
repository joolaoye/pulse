from typing import Any, cast

import pytest

from pulse.services.ingestion.exact_deduplicator import ExactDeduplicator
from pulse.types import Signal


class FakeD1Client:
    def __init__(
        self,
        results: list[dict[str, Any]] | None = None,
    ) -> None:
        self.results = results or []
        self.calls: list[dict[str, Any]] = []

    async def query(
        self,
        sql: str,
        params: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "sql": sql,
                "params": list(params or []),
            }
        )

        return self.results


def _normalized_sql(sql: str) -> str:
    return " ".join(sql.split())


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([], False),
        ([{"1": 1}], True),
    ],
)
async def test_exists_matches_persisted_pipeline_signal(
    rows: list[dict[str, Any]],
    expected: bool,
) -> None:
    client = FakeD1Client(rows)
    deduplicator = ExactDeduplicator(
        d1_client=cast(Any, client),
        pipeline_id="pipeline-1",
    )
    signal = Signal(
        id="signal-1",
        source="x",
        content="Launch notes",
    )

    assert await deduplicator.exists(signal=signal) is expected

    assert len(client.calls) == 1
    assert _normalized_sql(client.calls[0]["sql"]) == (
        "SELECT 1 FROM signals WHERE pipeline_id = ? AND source = ? AND signal_id = ? LIMIT 1"
    )
    assert client.calls[0]["params"] == [
        "pipeline-1",
        "x",
        "signal-1",
    ]
