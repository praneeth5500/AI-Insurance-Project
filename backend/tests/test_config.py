"""Configuration guards."""

from __future__ import annotations

import pytest

from app.core.config import LOCAL_DATABASE_URL, AppEnv, Settings


def test_local_environment_may_use_the_development_database() -> None:
    settings = Settings(app_env="local", database_url=LOCAL_DATABASE_URL)

    settings.validate_for_environment()

    assert settings.is_local is True


@pytest.mark.parametrize("app_env", ["preview", "staging", "production-beta"])
def test_deployed_environments_refuse_the_local_database_default(app_env: AppEnv) -> None:
    settings = Settings(app_env=app_env, database_url=LOCAL_DATABASE_URL)

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set explicitly"):
        settings.validate_for_environment()


def test_cors_origins_are_parsed_from_a_comma_separated_list() -> None:
    settings = Settings(cors_allowed_origins="http://localhost:3000, https://beta.example.com")

    assert settings.cors_origins == ["http://localhost:3000", "https://beta.example.com"]


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="log_level must be one of"):
        Settings(log_level="chatty")


def test_create_app_enforces_the_environment_guard_on_injected_settings() -> None:
    from app.main import create_app

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set explicitly"):
        create_app(Settings(app_env="production-beta", database_url=LOCAL_DATABASE_URL))
