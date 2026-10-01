from pulse.application.deployment import build


def test_clean_build_state_removes_stale_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    dist_path = tmp_path / "dist"
    modules_path = tmp_path / "python_modules"

    dist_path.mkdir()
    modules_path.mkdir()

    stale_wheel = dist_path / "pulse-0.1.0-py3-none-any.whl"
    stale_wheel.write_text("old")

    stale_module = modules_path / "stale.py"
    stale_module.write_text("old")

    monkeypatch.setattr(
        build,
        "_DIST_PATH",
        dist_path,
    )
    monkeypatch.setattr(
        build,
        "_WORKER_PYTHON_MODULES_PATH",
        modules_path,
    )

    build.clean_build_state()

    assert not stale_wheel.exists()
    assert modules_path.is_dir()
    assert list(modules_path.iterdir()) == []
