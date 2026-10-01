import pytest

from pulse.services.planning.duration import allocate_weighted_durations


def test_remainder_seconds_go_to_the_largest_fractional_shares() -> None:
    assert allocate_weighted_durations(weights=[1, 2], target_duration_seconds=10) == [3, 7]


def test_equal_fractional_shares_award_the_remainder_to_the_earlier_weight() -> None:
    assert allocate_weighted_durations(weights=[1, 1], target_duration_seconds=5) == [3, 2]


@pytest.mark.parametrize(
    ("weights", "target_duration_seconds"),
    [
        ([], 10),
        ([1], 0),
        ([0, 1], 10),
    ],
)
def test_invalid_duration_allocation_is_rejected(
    weights: list[int],
    target_duration_seconds: int,
) -> None:
    with pytest.raises(ValueError):
        allocate_weighted_durations(
            weights=weights,
            target_duration_seconds=target_duration_seconds,
        )
