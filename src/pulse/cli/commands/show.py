import asyncio
from typing import Dict, Optional

from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
import typer

from pulse.application.configuration import (
    PodcastShowUpdate,
    bootstrap_configuration,
)
from pulse.application.configuration.errors import (
    PodcastShowAlreadyExistsError,
    PodcastShowNotFoundError,
)
from pulse.types import PodcastShow

console = Console()

app = typer.Typer(
    help="Manage podcast shows.",
)


@app.command("list")
def list_shows() -> None:
    asyncio.run(_list_shows())


async def _list_shows() -> None:
    async with bootstrap_configuration() as application:
        podcast_shows = await application.show_manager.list()

    if not podcast_shows:
        console.print("No podcast shows found.")
        return

    table = Table(
        title="Podcast Shows",
    )

    table.add_column("Show ID")
    table.add_column("Title")
    table.add_column("Author")
    table.add_column("Language")
    table.add_column("Feed URL")

    for podcast_show in podcast_shows:
        table.add_row(
            podcast_show.show_id,
            podcast_show.title,
            podcast_show.author,
            podcast_show.language,
            podcast_show.get_feed_url(),
        )

    console.print(table)


@app.command("get")
def get_show(
    show_id: str = typer.Argument(
        ...,
        help="The podcast show ID.",
    ),
) -> None:
    try:
        asyncio.run(
            _get_show(
                show_id=show_id,
            )
        )
    except PodcastShowNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error


async def _get_show(
    *,
    show_id: str,
) -> None:
    async with bootstrap_configuration() as application:
        podcast_show = await application.show_manager.get(
            show_id=show_id,
        )

    table = Table(
        show_header=False,
    )

    table.add_column(
        "Field",
        style="bold",
    )
    table.add_column("Value")

    table.add_row("Show ID", podcast_show.show_id)
    table.add_row("Title", podcast_show.title)
    table.add_row("Description", podcast_show.description)
    table.add_row("Author", podcast_show.author)
    table.add_row("Website", str(podcast_show.website_url))
    table.add_row("Artwork", str(podcast_show.artwork_url))
    table.add_row("Category", podcast_show.category)
    table.add_row("Language", podcast_show.language)
    table.add_row(
        "Explicit",
        "Yes" if podcast_show.explicit else "No",
    )
    table.add_row(
        "Verification Email",
        (
            str(podcast_show.verification_email)
            if podcast_show.verification_email is not None
            else "-"
        ),
    )
    table.add_row(
        "Public Base URL",
        str(podcast_show.public_base_url),
    )
    table.add_row(
        "Feed Object Key",
        podcast_show.feed_object_key,
    )
    table.add_row(
        "Feed URL",
        podcast_show.get_feed_url(),
    )

    console.print(table)


@app.command("create")
def create_show(
    show_id: str = typer.Option(
        ...,
        "--show-id",
        prompt="Show ID",
        help="Stable identifier for the podcast show.",
    ),
    title: str = typer.Option(
        ...,
        "--title",
        prompt="Title",
        help="Public title of the podcast show.",
    ),
    description: str = typer.Option(
        ...,
        "--description",
        prompt="Description",
        help="Public description of the podcast show.",
    ),
    author: str = typer.Option(
        ...,
        "--author",
        prompt="Author",
        help="Public author or creator of the podcast show.",
    ),
    website_url: str = typer.Option(
        ...,
        "--website-url",
        prompt="Website URL",
        help="Public website URL for the podcast show.",
    ),
    artwork_url: str = typer.Option(
        ...,
        "--artwork-url",
        prompt="Artwork URL",
        help="Permanent public artwork URL.",
    ),
    category: str = typer.Option(
        ...,
        "--category",
        prompt="Category",
        help="Primary podcast category.",
    ),
    language: str = typer.Option(
        "en-US",
        "--language",
        help="Podcast language tag.",
    ),
    explicit: bool = typer.Option(
        False,
        "--explicit/--not-explicit",
        help="Whether the podcast contains explicit content.",
    ),
    verification_email: Optional[str] = typer.Option(
        None,
        "--verification-email",
        help="Optional podcast-directory verification email.",
    ),
    public_base_url: str = typer.Option(
        ...,
        "--public-base-url",
        prompt="Public base URL",
        help="Public base URL for feed and media objects.",
    ),
    feed_object_key: str = typer.Option(
        ...,
        "--feed-object-key",
        prompt="Feed object key",
        help="Object-storage key for the RSS feed.",
    ),
) -> None:
    try:
        podcast_show = PodcastShow.model_validate(
            {
                "show_id": show_id,
                "title": title,
                "description": description,
                "author": author,
                "website_url": website_url,
                "artwork_url": artwork_url,
                "category": category,
                "language": language,
                "explicit": explicit,
                "verification_email": verification_email,
                "public_base_url": public_base_url,
                "feed_object_key": feed_object_key,
            }
        )

        created_show = asyncio.run(
            _create_show(
                podcast_show=podcast_show,
            )
        )

    except ValidationError as error:
        console.print("[red]Invalid podcast show configuration.[/red]")
        console.print(str(error))
        raise typer.Exit(code=1) from error

    except PodcastShowAlreadyExistsError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Created podcast show '{created_show.show_id}'.[/green]")
    console.print(f"Feed URL: {created_show.get_feed_url()}")


async def _create_show(
    *,
    podcast_show: PodcastShow,
) -> PodcastShow:
    async with bootstrap_configuration() as application:
        return await application.show_manager.create(
            podcast_show=podcast_show,
        )


@app.command("update")
def update_show(
    show_id: str = typer.Argument(
        ...,
        help="The podcast show ID.",
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
    ),
    author: Optional[str] = typer.Option(
        None,
        "--author",
    ),
    website_url: Optional[str] = typer.Option(
        None,
        "--website-url",
    ),
    artwork_url: Optional[str] = typer.Option(
        None,
        "--artwork-url",
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
    ),
    explicit: Optional[bool] = typer.Option(
        None,
        "--explicit/--not-explicit",
    ),
    verification_email: Optional[str] = typer.Option(
        None,
        "--verification-email",
    ),
    clear_verification_email: bool = typer.Option(
        False,
        "--clear-verification-email",
        help="Remove the current verification email.",
    ),
    public_base_url: Optional[str] = typer.Option(
        None,
        "--public-base-url",
    ),
    feed_object_key: Optional[str] = typer.Option(
        None,
        "--feed-object-key",
    ),
) -> None:
    if verification_email is not None and clear_verification_email:
        console.print(
            "[red]Error:[/red] --verification-email and "
            "--clear-verification-email cannot be used together."
        )
        raise typer.Exit(code=1)

    update_values = _build_show_update_values(
        title=title,
        description=description,
        author=author,
        website_url=website_url,
        artwork_url=artwork_url,
        category=category,
        language=language,
        explicit=explicit,
        verification_email=verification_email,
        clear_verification_email=clear_verification_email,
        public_base_url=public_base_url,
        feed_object_key=feed_object_key,
    )

    if not update_values:
        console.print("[yellow]No updates provided.[/yellow]")
        return

    try:
        update = PodcastShowUpdate.model_validate(update_values)

        updated_show = asyncio.run(
            _update_show(
                show_id=show_id,
                update=update,
            )
        )

    except ValidationError as error:
        console.print("[red]Invalid podcast show update.[/red]")
        console.print(str(error))
        raise typer.Exit(code=1) from error

    except PodcastShowNotFoundError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Updated podcast show '{updated_show.show_id}'.[/green]")


def _build_show_update_values(
    *,
    title: Optional[str],
    description: Optional[str],
    author: Optional[str],
    website_url: Optional[str],
    artwork_url: Optional[str],
    category: Optional[str],
    language: Optional[str],
    explicit: Optional[bool],
    verification_email: Optional[str],
    clear_verification_email: bool,
    public_base_url: Optional[str],
    feed_object_key: Optional[str],
) -> Dict[str, object]:
    values: Dict[str, object] = {
        key: value
        for key, value in {
            "title": title,
            "description": description,
            "author": author,
            "website_url": website_url,
            "artwork_url": artwork_url,
            "category": category,
            "language": language,
            "explicit": explicit,
            "verification_email": verification_email,
            "public_base_url": public_base_url,
            "feed_object_key": feed_object_key,
        }.items()
        if value is not None
    }

    if clear_verification_email:
        values["verification_email"] = None

    return values


async def _update_show(
    *,
    show_id: str,
    update: PodcastShowUpdate,
) -> PodcastShow:
    async with bootstrap_configuration() as application:
        return await application.show_manager.update(
            show_id=show_id,
            update=update,
        )
