import pytest
from typer.testing import CliRunner

from pulse.cli.main import app

runner = CliRunner()


@pytest.mark.parametrize(
    "arguments",
    [
        ["run", "pipeline-1", "run-1"],
        ["run", "pipeline-1", "--pipeline-id", "pipeline-2"],
    ],
)
def test_fresh_run_rejects_resume_arguments(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    started: list[str] = []
    monkeypatch.setattr(
        "pulse.cli.commands.run._execute_run",
        lambda **kwargs: started.append("run"),
    )
    monkeypatch.setattr(
        "pulse.cli.commands.run._execute_resume",
        lambda **kwargs: started.append("resume"),
    )

    result = runner.invoke(app, arguments)

    assert result.exit_code == 1
    assert started == []


@pytest.mark.parametrize(
    "arguments",
    [
        ["run", "resume"],
        ["run", "resume", "run-1"],
    ],
)
def test_resume_requires_run_and_pipeline_identity(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    started: list[str] = []
    monkeypatch.setattr(
        "pulse.cli.commands.run._execute_run",
        lambda **kwargs: started.append("run"),
    )
    monkeypatch.setattr(
        "pulse.cli.commands.run._execute_resume",
        lambda **kwargs: started.append("resume"),
    )

    result = runner.invoke(app, arguments)

    assert result.exit_code == 1
    assert started == []
