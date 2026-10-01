from pathlib import (
    Path,
)

from pulse.types import PodcastConfiguration


def load_interest_profile(
    *,
    path: Path,
) -> str:
    if path.suffix.lower() != ".md":
        raise ValueError(("Interest profile must be a Markdown (.md) file."))

    if not path.is_file():
        raise ValueError(f"File '{path}' does not exist.")

    markdown = path.read_text(
        encoding="utf-8",
    )

    if not markdown.strip():
        raise ValueError("Interest profile cannot be empty.")

    return markdown


def load_podcast_configuration(
    *,
    path: Path,
) -> PodcastConfiguration:
    if path.suffix.lower() != ".json":
        raise ValueError(("Podcast configuration must be a JSON (.json) file."))

    if not path.is_file():
        raise ValueError(f"File '{path}' does not exist.")

    return PodcastConfiguration.model_validate_json(
        path.read_text(
            encoding="utf-8",
        )
    )
