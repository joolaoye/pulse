from datetime import time
from pathlib import Path

import pytest

from pulse.cli.commands.schedule import _parse_local_time
from pulse.cli.input.files import load_interest_profile, load_podcast_configuration


@pytest.mark.parametrize(
    ("name", "content", "accepted"),
    [
        ("profile.md", "# Rates\n\nWhat changed this week.\n", True),
        ("empty.md", " \n\t", False),
        ("profile.txt", "# Rates\n\nWhat changed this week.\n", False),
    ],
)
def test_interest_profile_must_be_non_empty_markdown(
    tmp_path: Path,
    name: str,
    content: str,
    accepted: bool,
) -> None:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")

    if accepted:
        assert load_interest_profile(path=path) == content
        return

    with pytest.raises(ValueError):
        load_interest_profile(path=path)


def test_podcast_configuration_must_be_json(tmp_path: Path) -> None:
    path = tmp_path / "podcast.yaml"
    path.write_text("name: Pulse\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_podcast_configuration(path=path)


@pytest.mark.parametrize(
    ("value", "parsed"),
    [
        ("09:30", time(9, 30)),
        ("24:00", None),
        ("09:60", None),
    ],
)
def test_schedule_time_uses_twenty_four_hour_hh_mm(value: str, parsed: time | None) -> None:
    if parsed is None:
        with pytest.raises(ValueError):
            _parse_local_time(value=value)
        return

    assert _parse_local_time(value=value) == parsed
