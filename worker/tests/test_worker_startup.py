"""The worker starts, validates configuration and exits cleanly."""

from __future__ import annotations

import json
import os

import pytest
from app.core.config import LOCAL_DATABASE_URL, Settings

from worker.main import run


def _log_lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [line for line in capsys.readouterr().out.splitlines() if line.strip()]


def _settings() -> Settings:
    """Point at the real test database.

    The worker now opens a connection as soon as it starts, so a placeholder
    URL would only test that an unreachable host fails.
    """
    return Settings(
        app_env="local",
        log_level="INFO",
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql+asyncpg://insurance:insurance@127.0.0.1:5432/insurance_test"
        ),
    )


def test_run_exits_successfully() -> None:
    assert run(_settings(), max_jobs=1) == 0


def test_run_starts_and_stops_cleanly_with_an_empty_queue(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`max_jobs` makes the loop finite so it can be tested at all.

    With nothing to claim the worker returns immediately rather than
    blocking, which is also what a scale-to-zero deployment needs.
    """
    run(_settings(), max_jobs=1)

    messages = [json.loads(line)["message"] for line in _log_lines(capsys)]
    assert "worker_started" in messages
    assert "worker_stopped" in messages


def test_worker_logs_are_structured_json(capsys: pytest.CaptureFixture[str]) -> None:
    run(_settings(), max_jobs=1)

    first = json.loads(_log_lines(capsys)[0])
    assert first["level"] == "INFO"
    assert first["logger"] == "worker.main"


def test_run_refuses_a_deployed_environment_without_an_explicit_database_url() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL must be set explicitly"):
        run(Settings(app_env="staging", database_url=LOCAL_DATABASE_URL), max_jobs=1)
