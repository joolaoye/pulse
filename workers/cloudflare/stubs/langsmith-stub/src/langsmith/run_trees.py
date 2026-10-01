from contextvars import (
    ContextVar,
)

_CLIENT = ContextVar(
    "langsmith_client",
    default=None,
)


class RunTree:
    pass


def get_cached_client():
    return None


def to_headers(
    *args,
    **kwargs,
):
    return {}
