import json
from typing import (
    Any,
)


def dumps(
    value: Any,
    *,
    default=None,
    option=None,
) -> bytes:
    return json.dumps(
        value,
        default=default,
        separators=(
            ",",
            ":",
        ),
    ).encode("utf-8")


def loads(
    value,
):
    if isinstance(
        value,
        bytes,
    ):
        value = value.decode("utf-8")

    return json.loads(value)
