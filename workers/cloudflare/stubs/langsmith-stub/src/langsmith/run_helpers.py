from contextvars import (
    ContextVar,
)
from typing import (
    Any,
    Dict,
    Optional,
)

_DEFAULT_CONTEXT: Dict[
    str,
    Any,
] = {
    "parent": None,
    "project_name": None,
    "tags": None,
    "metadata": None,
    "enabled": False,
    "client": None,
    "replicas": None,
    "distributed_parent_id": None,
}


_TRACING_CONTEXT: ContextVar[
    Optional[
        Dict[
            str,
            Any,
        ]
    ]
] = ContextVar(
    "langsmith_tracing_context",
    default=None,
)


def get_tracing_context() -> Dict[
    str,
    Any,
]:
    context = _TRACING_CONTEXT.get()

    if context is None:
        return dict(_DEFAULT_CONTEXT)

    return {
        **_DEFAULT_CONTEXT,
        **context,
        "enabled": False,
    }


def _set_tracing_context(
    context: Dict[
        str,
        Any,
    ],
) -> None:
    _TRACING_CONTEXT.set(
        {
            **context,
            "enabled": False,
        }
    )


def get_current_run_tree():
    return get_tracing_context().get("parent")
