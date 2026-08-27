"""Application configuration.

Settings come from the environment only. Nothing here carries a real
credential default, and the application refuses to start in a non-local
environment without an explicit DATABASE_URL
(docs/09_AWS_DEPLOYMENT.md section 7).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "preview", "staging", "production-beta"]

LOCAL_DATABASE_URL = "postgresql+asyncpg://insurance:insurance@localhost:5432/insurance_local"
LOCAL_FRONTEND_ORIGIN = "http://localhost:3000"


class Settings(BaseSettings):
    """Runtime settings for the API and worker."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = "local"
    log_level: str = "INFO"

    database_url: str = LOCAL_DATABASE_URL

    api_host: str = "0.0.0.0"  # noqa: S104 — containers bind all interfaces
    api_port: int = 8000

    cors_allowed_origins: str = LOCAL_FRONTEND_ORIGIN

    #: Requests slower than this are logged at WARNING so latency stays visible.
    slow_request_threshold_ms: int = Field(default=1000, ge=1)

    # ---------------------------------------------------------------- auth --
    # Where the magic link should send the user. The link is built by the API
    # but opened in the frontend.
    frontend_base_url: str = LOCAL_FRONTEND_ORIGIN

    #: Comma-separated emails seeded into the beta allowlist by
    #: `make seed-allowlist`. Empty by default: nobody has access until an
    #: invite is issued deliberately.
    beta_allowlist_emails: str = ""

    session_cookie_name: str = "insurance_session"
    #: Set in deployed environments when the API and app are on different
    #: subdomains of the same site (e.g. ".example.com"). Unset locally.
    session_cookie_domain: str | None = None

    #: Lifetimes are configurable rather than hard-coded: neither value is
    #: fixed by the specification, so both are flagged in
    #: docs/PHASE_2_NOTES.md for founder confirmation.
    magic_link_ttl_minutes: int = Field(default=15, ge=1, le=60)
    session_ttl_days: int = Field(default=14, ge=1, le=90)

    # ------------------------------------------------------------ features --
    # A destination is advertised as available only when it actually works.
    # docs/12_BETA_CHECKLIST.md requires "no dead buttons", so each flag stays
    # false until the phase that builds the flow turns it on.
    #
    # The health questionnaire is built and usable (Phase 4), so its entry
    # point is on by default. Matched options are a separate flag: the review
    # screen must not promise results the engine cannot yet produce.
    # The policy decoder arrives in Phases 10-13. Motor is architecturally
    # supported but must not be enabled until the health engine and motor data
    # are ready (docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 8).
    feature_health_recommendation: bool = True
    feature_motor_recommendation: bool = False
    feature_policy_decoder: bool = False

    # ------------------------------------------------------------ uploads --
    # docs/09_AWS_DEPLOYMENT.md section 5: block public access, encrypt at
    # rest, separate by environment, signed temporary URLs, a lifecycle
    # policy, a deletion path, and MIME validation before processing. The
    # bucket itself is not chosen yet, so storage sits behind an interface and
    # local development writes to a private directory instead.
    #
    # The directory is deliberately *outside* the repository and outside
    # anything the web server serves: an uploaded policy is a private document
    # and CLAUDE.md forbids exposing one publicly.
    # Defaults under the developer's home directory rather than a shared
    # temp directory: /tmp and /var/tmp are readable by every account on the
    # machine, which is not where a private policy document belongs even in
    # development. Deployed environments set this or, better, configure an
    # object-storage adapter instead.
    upload_storage_dir: str = str(Path.home() / ".insurance-local-uploads")

    #: Largest file accepted, in bytes. Not fixed by the specification;
    #: 20 MB comfortably holds a scanned policy booklet.
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1024)

    #: Most pages a document may have. A PDF is a container: a small file can
    #: declare thousands of pages, and the worker walks every one. Refusing at
    #: upload is cheaper than discovering it in extraction, and a real policy
    #: booklet is far below this.
    max_document_pages: int = Field(default=400, ge=1)

    #: How many documents one policy may carry. A policy wording is sometimes
    #: split across a few files (wording, schedule, endorsements).
    max_documents_per_policy: int = Field(default=5, ge=1, le=20)

    #: Serve clearly-labelled synthetic modules on the returning-user home so
    #: the layout can be reviewed before the real data exists
    #: (docs/11_BUILD_PLAN.md Phase 3: "Use mock data first"). Refused outside
    #: local and preview: demo data must never look like a real record.
    home_demo_data: bool = False

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @property
    def allowlist_seed_emails(self) -> list[str]:
        return [
            email.strip().lower()
            for email in self.beta_allowlist_emails.split(",")
            if email.strip()
        ]

    @property
    def session_cookie_secure(self) -> bool:
        """Only local development may send the session cookie over plain HTTP."""
        return not self.is_local

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def validate_for_environment(self) -> None:
        """Fail loudly rather than silently running a deployed env on local defaults."""
        if not self.is_local and self.database_url == LOCAL_DATABASE_URL:
            raise RuntimeError(
                f"DATABASE_URL must be set explicitly when APP_ENV={self.app_env}; "
                "the local development default is not usable outside APP_ENV=local."
            )
        # Credentialed CORS: the browser sends the session cookie to any origin
        # named here, so a wildcard or a stale localhost entry is an open door
        # rather than a misconfiguration. Nothing is guessed — a deployed
        # environment must say what its app origin is.
        if not self.is_local:
            origins = self.cors_origins
            if not origins or origins == [LOCAL_FRONTEND_ORIGIN]:
                raise RuntimeError(
                    f"CORS_ALLOWED_ORIGINS must name this environment's app origin when "
                    f"APP_ENV={self.app_env}; the local development default is not usable."
                )
            for origin in origins:
                if origin == "*":
                    raise RuntimeError(
                        "CORS_ALLOWED_ORIGINS cannot be '*': the API sends credentials, "
                        "so every listed origin can read a signed-in user's data."
                    )
                if not origin.startswith("https://"):
                    raise RuntimeError(
                        f"CORS origin {origin!r} is not https. A session cookie is "
                        f"Secure, so a plain-http origin cannot work and must not be listed."
                    )
            if self.frontend_base_url == LOCAL_FRONTEND_ORIGIN:
                raise RuntimeError(
                    f"FRONTEND_BASE_URL must be set when APP_ENV={self.app_env}; "
                    "sign-in links would otherwise point at localhost."
                )

        if self.home_demo_data and self.app_env not in ("local", "preview"):
            raise RuntimeError(
                f"HOME_DEMO_DATA cannot be enabled when APP_ENV={self.app_env}. "
                "Synthetic modules are for layout review only and must never be "
                "shown to beta users as though they were real records."
            )


@lru_cache
def get_settings() -> Settings:
    """Return process-wide settings (cached)."""
    settings = Settings()
    settings.validate_for_environment()
    return settings
