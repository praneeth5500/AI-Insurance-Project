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


def _deployed(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "staging",
        "database_url": "postgresql+asyncpg://u:p@db.internal:5432/insurance",
        "cors_allowed_origins": "https://app.example.com",
        "frontend_base_url": "https://app.example.com",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_a_deployed_environment_must_name_its_app_origin() -> None:
    """The API sends credentials, so the origin list is an access list."""
    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        _deployed(cors_allowed_origins="http://localhost:3000").validate_for_environment()

    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        _deployed(cors_allowed_origins="").validate_for_environment()


def test_a_wildcard_cors_origin_is_refused() -> None:
    with pytest.raises(RuntimeError, match="cannot be"):
        _deployed(cors_allowed_origins="*").validate_for_environment()


def test_a_plain_http_cors_origin_is_refused() -> None:
    """A Secure cookie is never sent to http, so listing one only misleads."""
    with pytest.raises(RuntimeError, match="not https"):
        _deployed(
            cors_allowed_origins="https://app.example.com,http://staging.example.com"
        ).validate_for_environment()


def test_sign_in_links_cannot_still_point_at_localhost() -> None:
    with pytest.raises(RuntimeError, match="FRONTEND_BASE_URL"):
        _deployed(frontend_base_url="http://localhost:3000").validate_for_environment()


def test_a_correctly_configured_deployment_validates() -> None:
    _deployed().validate_for_environment()


def test_local_development_keeps_its_defaults() -> None:
    """None of the above may make `make dev` require configuration."""
    Settings(app_env="local").validate_for_environment()
