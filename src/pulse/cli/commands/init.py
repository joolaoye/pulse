import asyncio
from pathlib import Path
from typing import Dict, Optional

from dotenv import dotenv_values
from pydantic import ValidationError
from rich.console import Console
import typer

from pulse.application.setup import (
    DEFAULT_CHECKPOINT_DATABASE_PATH,
    DEFAULT_D1_DATABASE_NAME,
    DEFAULT_PUBLIC_PODCAST_BUCKET_NAME,
    DEFAULT_VECTORIZE_INDEX_NAME,
    PulseInitializationConfig,
    bootstrap_setup,
)
from pulse.application.setup.errors import (
    PulseResourceCollisionError,
    PulseResourceCompatibilityError,
)

Environment = Dict[str, Optional[str]]

_ENV_PATH = Path(".env")

console = Console()


def initialize() -> None:
    try:
        existing_environment = _load_existing_environment()

        console.print("[bold]Initializing Pulse[/bold]")
        console.print()

        config = _build_initialization_config(
            existing_environment=existing_environment,
        )

        _run_initialization(
            config=config,
            existing_environment=existing_environment,
        )

    except typer.Exit:
        raise

    except PulseResourceCompatibilityError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    except ValidationError as error:
        console.print("[red]Invalid Pulse configuration.[/red]")
        console.print(str(error))
        raise typer.Exit(code=1) from error

    except (OSError, RuntimeError) as error:
        console.print(f"[red]Failed to initialize Pulse:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print()
    console.print("[green]Pulse initialized successfully.[/green]")


def _build_initialization_config(
    *,
    existing_environment: Environment,
) -> PulseInitializationConfig:
    return PulseInitializationConfig(
        x_bearer_token=_prompt_required(
            existing_environment=existing_environment,
            variable_name="X_BEARER_TOKEN",
            prompt="X bearer token",
            hide_input=True,
        ),
        voyage_api_key=_prompt_required(
            existing_environment=existing_environment,
            variable_name="VOYAGE_API_KEY",
            prompt="Voyage API key",
            hide_input=True,
        ),
        anthropic_api_key=_prompt_required(
            existing_environment=existing_environment,
            variable_name="ANTHROPIC_API_KEY",
            prompt="Anthropic API key",
            hide_input=True,
        ),
        elevenlabs_api_key=_prompt_required(
            existing_environment=existing_environment,
            variable_name="ELEVENLABS_API_KEY",
            prompt="ElevenLabs API key",
            hide_input=True,
        ),
        cloudflare_account_id=_prompt_required(
            existing_environment=existing_environment,
            variable_name="CLOUDFLARE_ACCOUNT_ID",
            prompt="Cloudflare account ID",
        ),
        cloudflare_api_token=_prompt_required(
            existing_environment=existing_environment,
            variable_name="PULSE_CLOUDFLARE_API_TOKEN",
            prompt="Cloudflare API token",
            hide_input=True,
        ),
        d1_database_name=_prompt_value(
            existing_environment=existing_environment,
            variable_name="PULSE_D1_DATABASE_NAME",
            prompt="D1 database name",
            default=DEFAULT_D1_DATABASE_NAME,
        ),
        vectorize_index_name=_prompt_value(
            existing_environment=existing_environment,
            variable_name="PULSE_VECTORIZE_INDEX_NAME",
            prompt="Vectorize index name",
            default=DEFAULT_VECTORIZE_INDEX_NAME,
        ),
        checkpoint_database_path=_prompt_path(
            existing_environment=existing_environment,
            variable_name="PULSE_CHECKPOINT_DATABASE_PATH",
            prompt="Checkpoint database path",
            default=DEFAULT_CHECKPOINT_DATABASE_PATH,
        ),
        podcast_bucket_name=_prompt_value(
            existing_environment=existing_environment,
            variable_name="PULSE_PODCAST_BUCKET_NAME",
            prompt="Public podcast bucket name",
            default=DEFAULT_PUBLIC_PODCAST_BUCKET_NAME,
        ),
    )


def _run_initialization(
    *,
    config: PulseInitializationConfig,
    existing_environment: Environment,
) -> None:
    reuse_existing_resources = _is_existing_pulse_installation(
        existing_environment=existing_environment,
    )

    try:
        asyncio.run(
            _initialize(
                config=config,
                reuse_existing_resources=reuse_existing_resources,
            )
        )

    except PulseResourceCollisionError as error:
        _render_resource_collisions(error=error)

        if not typer.confirm(
            "Use these existing resources?",
            default=False,
        ):
            console.print()
            console.print(
                "[yellow]Initialization cancelled. "
                "Choose different resource names and run "
                "'pulse init' again.[/yellow]"
            )
            raise typer.Exit(code=1) from None

        asyncio.run(
            _initialize(
                config=config,
                reuse_existing_resources=True,
            )
        )


async def _initialize(
    *,
    config: PulseInitializationConfig,
    reuse_existing_resources: bool,
) -> None:
    async with bootstrap_setup(
        config=config,
        reuse_existing_cloudflare_resources=reuse_existing_resources,
    ) as initializer:
        await initializer.initialize(
            config=config,
        )


def _render_resource_collisions(
    *,
    error: PulseResourceCollisionError,
) -> None:
    console.print()
    console.print("[yellow]Existing Cloudflare resources were found:[/yellow]")

    for resource in error.resources:
        console.print(f"  - {resource}")

    console.print()


def _load_existing_environment() -> Environment:
    if not _ENV_PATH.is_file():
        return {}

    return dict(
        dotenv_values(
            dotenv_path=_ENV_PATH,
        )
    )


def _get_existing_value(
    *,
    existing_environment: Environment,
    variable_name: str,
) -> Optional[str]:
    value = existing_environment.get(variable_name)

    if value is None:
        return None

    value = value.strip()

    return value or None


def _prompt_required(
    *,
    existing_environment: Environment,
    variable_name: str,
    prompt: str,
    hide_input: bool = False,
) -> str:
    existing_value = _get_existing_value(
        existing_environment=existing_environment,
        variable_name=variable_name,
    )

    if existing_value is not None:
        return existing_value

    return typer.prompt(
        prompt,
        hide_input=hide_input,
    )


def _prompt_value(
    *,
    existing_environment: Environment,
    variable_name: str,
    prompt: str,
    default: str,
) -> str:
    existing_value = _get_existing_value(
        existing_environment=existing_environment,
        variable_name=variable_name,
    )

    if existing_value is not None:
        return existing_value

    return typer.prompt(
        prompt,
        default=default,
    )


def _prompt_path(
    *,
    existing_environment: Environment,
    variable_name: str,
    prompt: str,
    default: Path,
) -> Path:
    return Path(
        _prompt_value(
            existing_environment=existing_environment,
            variable_name=variable_name,
            prompt=prompt,
            default=str(default),
        )
    )


def _is_existing_pulse_installation(
    *,
    existing_environment: Environment,
) -> bool:
    return (
        _get_existing_value(
            existing_environment=existing_environment,
            variable_name="CLOUDFLARE_D1_DATABASE_ID",
        )
        is not None
    )
