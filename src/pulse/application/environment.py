import os

from dotenv import (
    load_dotenv,
)


def load_environment() -> None:
    load_dotenv()


def require_environment_variable(
    *,
    variable_name: str,
) -> str:

    load_environment()

    value = os.getenv(variable_name)

    if value is None or not value.strip():
        raise RuntimeError((f"The required environment variable {variable_name!r} is missing."))

    return value
