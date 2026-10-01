import pytest


def pytest_addoption(parser) -> None:
    group = parser.getgroup("pulse-e2e")

    group.addoption(
        "--x-list-id",
        action="store",
        default=None,
        help="X list used by the live Pulse E2E pipeline.",
    )

    group.addoption(
        "--public-podcast-base-url",
        action="store",
        default=None,
        help=("Public R2/custom-domain base URL used for published podcast assets."),
    )

    group.addoption(
        "--resume-run-id",
        action="store",
        default=None,
        help="Resume a previously failed Pulse E2E run.",
    )


@pytest.fixture
def x_list_id(request) -> str:
    value = request.config.getoption("--x-list-id")

    if value is None or not value.strip():
        pytest.fail(
            "--x-list-id is required for the live E2E test.",
        )

    return value.strip()


@pytest.fixture
def public_podcast_base_url(request) -> str:
    value = request.config.getoption(
        "--public-podcast-base-url",
    )

    if value is None or not value.strip():
        pytest.fail(
            "--public-podcast-base-url is required for the live E2E test.",
        )

    return value.strip().rstrip("/")


@pytest.fixture
def resume_run_id(request):
    value = request.config.getoption("--resume-run-id")

    if value is None:
        return None

    value = value.strip()

    return value or None
