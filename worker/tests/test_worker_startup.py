"""The worker placeholder starts, validates configuration and exits cleanly."""

from __future__ import annotations

import json

import pytest
from app.core.config import LOCAL_DATABASE_URL, Settings

from worker.main import run


def _log_lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [line for line in capsys.readouterr().out.splitlines() if line.strip()]


def _settings() -> Settings:
    return Settings(
        app_env="local",
        log_level="INFO",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
    )


def test_run_exits_successfully() -> None:
    assert run(_settings()) == 0


def test_run_reports_that_no_queue_is_configured(capsys: pytest.CaptureFixture[str]) -> None:
    run(_settings())

    messages = [json.loads(line)["message"] for line in _log_lines(capsys)]
    assert "worker_started" in messages
    assert "worker_idle_no_queue_configured" in messages
    assert "worker_stopped" in messages


def test_worker_logs_are_structured_json(capsys: pytest.CaptureFixture[str]) -> None:
    run(_settings())

    first = json.loads(_log_lines(capsys)[0])
    assert first["level"] == "INFO"
    assert first["logger"] == "worker.main"


def test_run_refuses_a_deployed_environment_without_an_explicit_database_url() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL must be set explicitly"):
        run(Settings(app_env="staging", database_url=LOCAL_DATABASE_URL))
