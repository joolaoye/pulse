"""Minimal ormsgpack compatibility layer for Pyodide.

Backed by msgpack's pure-Python implementation.
"""

from typing import Any, Callable, Optional

from msgpack.ext import ExtType # type: ignore
from msgpack.fallback import ( # type: ignore
    Packer,
    unpackb as _unpackb,
)


class MsgpackEncodeError(TypeError):
    pass


class MsgpackDecodeError(ValueError):
    pass


Ext = ExtType


OPT_NAIVE_UTC = 1
OPT_NON_STR_KEYS = 2
OPT_OMIT_MICROSECONDS = 4
OPT_PASSTHROUGH_BIG_INT = 8
OPT_PASSTHROUGH_DATACLASS = 16
OPT_PASSTHROUGH_DATETIME = 32
OPT_PASSTHROUGH_SUBCLASS = 64
OPT_PASSTHROUGH_TUPLE = 128
OPT_SERIALIZE_NUMPY = 256
OPT_SERIALIZE_PYDANTIC = 512
OPT_SORT_KEYS = 1024
OPT_UTC_Z = 2048
OPT_PASSTHROUGH_UUID = 4096
OPT_PASSTHROUGH_ENUM = 8192
OPT_DATETIME_AS_TIMESTAMP_EXT = 16384
OPT_REPLACE_SURROGATES = 32768


def packb(
    obj: Any,
    *,
    default: Optional[
        Callable[[Any], Any]
    ] = None,
    option: int = 0,
) -> bytes:
    try:
        packer = Packer(
            default=default,
            use_bin_type=True,
        )

        return packer.pack(
            obj
        )

    except Exception as exc:
        raise MsgpackEncodeError(
            str(exc)
        ) from exc


def unpackb(
    data: bytes,
    *,
    ext_hook: Optional[
        Callable[[int, bytes], Any]
    ] = None,
    option: int = 0,
) -> Any:
    try:
        kwargs = {
            "raw": False,
            "strict_map_key": not bool(
                option
                & OPT_NON_STR_KEYS
            ),
        }

        if ext_hook is not None:
            kwargs[
                "ext_hook"
            ] = ext_hook # type: ignore

        return _unpackb(
            data,
            **kwargs,
        )

    except Exception as exc:
        raise MsgpackDecodeError(
            str(exc)
        ) from exc


__version__ = "1.12.1"