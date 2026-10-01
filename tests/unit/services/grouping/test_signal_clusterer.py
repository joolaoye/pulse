import pytest

from pulse.services.grouping.signal_clusterer import SignalClusterer
from pulse.types import EmbeddedSignal, SignalCluster


def _embedded(
    signal_id: str,
    embedding: list[float],
) -> EmbeddedSignal:
    return EmbeddedSignal(
        signal_id=signal_id,
        embedding=embedding,
        embedding_version="test",
    )


def test_similar_embeddings_group_and_every_signal_is_kept_once() -> None:
    signals = [
        _embedded("a", [1.0, 0.0]),
        _embedded("b", [0.99, 0.01]),
        _embedded("c", [0.0, 1.0]),
    ]
    clusterer = SignalClusterer()

    first = clusterer.cluster(signals)
    second = clusterer.cluster(signals)

    assert first == second
    assert [(cluster.cluster_id, cluster.signal_ids) for cluster in first] == [
        (0, ["a", "b"]),
        (1, ["c"]),
    ]


def test_single_signal_forms_one_group() -> None:
    result = SignalClusterer().cluster(
        [_embedded("only", [1.0, 0.0])],
    )

    assert result == [
        SignalCluster(
            cluster_id=0,
            signal_ids=["only"],
        )
    ]


def test_empty_input_returns_no_groups() -> None:
    assert SignalClusterer().cluster([]) == []


@pytest.mark.parametrize(
    ("distance_threshold", "group_count"),
    [
        (1.0, 2),
        (1.01, 1),
    ],
)
def test_distance_threshold_boundary(
    distance_threshold: float,
    group_count: int,
) -> None:
    result = SignalClusterer(
        distance_threshold=distance_threshold,
    ).cluster(
        [
            _embedded("a", [1.0, 0.0]),
            _embedded("c", [0.0, 1.0]),
        ]
    )

    assert len(result) == group_count
    assert sorted(signal_id for cluster in result for signal_id in cluster.signal_ids) == [
        "a",
        "c",
    ]


@pytest.mark.parametrize(
    ("linkage", "expected_groups"),
    [
        ("single", [["a", "b", "c", "d"]]),
        ("complete", [["a", "b"], ["c", "d"]]),
        ("average", [["a", "b"], ["c", "d"]]),
    ],
)
def test_linkage_decides_whether_a_chain_merges(
    linkage: str,
    expected_groups: list[list[str]],
) -> None:
    # Euclidean gaps: a-b and c-d are 1, while the nearest gap between those
    # pairs is 2. Single linkage follows that bridge; complete and average do not.
    result = SignalClusterer(
        metric="euclidean",
        linkage=linkage,
        distance_threshold=2.5,
    ).cluster(
        [
            _embedded("a", [0.0]),
            _embedded("b", [1.0]),
            _embedded("c", [3.0]),
            _embedded("d", [4.0]),
        ]
    )

    assert [cluster.signal_ids for cluster in result] == expected_groups
