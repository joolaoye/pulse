import math
from typing import List


def cosine_similarity(
    left: List[float],
    right: List[float],
) -> float:
    if len(left) != len(right):
        raise ValueError("Cosine similarity requires vectors with equal dimensions.")

    dot_product = sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=True)
    )

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    denominator = left_norm * right_norm

    if denominator == 0:
        return 0.0

    return dot_product / denominator
