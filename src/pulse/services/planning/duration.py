from typing import List


def allocate_weighted_durations(
    *,
    weights: List[int],
    target_duration_seconds: int,
) -> List[int]:
    if not weights:
        raise ValueError("At least one duration weight is required.")

    if target_duration_seconds <= 0:
        raise ValueError(("Target duration must be greater than zero."))

    if any(weight <= 0 for weight in weights):
        raise ValueError(("Duration weights must all be greater than zero."))

    total_weight = sum(weights)

    raw_durations = [(target_duration_seconds * weight / total_weight) for weight in weights]

    allocated_durations = [int(duration) for duration in raw_durations]

    remaining_seconds = target_duration_seconds - sum(allocated_durations)

    remainder_order = sorted(
        range(len(raw_durations)),
        key=lambda index: raw_durations[index] - allocated_durations[index],
        reverse=True,
    )

    for index in remainder_order[:remaining_seconds]:
        allocated_durations[index] += 1

    return allocated_durations
