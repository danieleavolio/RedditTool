"""Settings and credentials.

Precedence for settings: ``RPA_*`` environment variables > ``config.toml`` > defaults.
Secrets never live in ``config.toml`` and never appear in ``Settings``: they are read
through :func:`get_credentials` from the environment or the system keyring.
"""

from __future__ import annotations

import os
from pathlib import Path

import platformdirs
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from reddit_analyzer import __version__

APP_NAME = "reddit-post-analyzer"
KEYRING_SERVICE = APP_NAME
ENV_PREFIX = "RPA_"
DB_FILENAME = "reddit.db"
CREDENTIALS_DOC = "docs/reddit-credentials.md"


def config_file_path() -> Path:
    """Location of ``config.toml`` (override with ``RPA_CONFIG_FILE``)."""
    override = os.environ.get("RPA_CONFIG_FILE")
    if override:
        return Path(override)
    return Path(platformdirs.user_config_dir(APP_NAME, appauthor=False)) / "config.toml"


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PathsConfig(_Section):
    data_dir: Path | None = None  # None = platformdirs user data dir


class RedditConfig(_Section):
    client_id: str = ""
    redirect_uri: str = "http://localhost:8080"


class CollectConfig(_Section):
    comments_depth: int = Field(2, ge=1)
    comments_max_per_post: int = Field(50, ge=1)
    morechildren_cap: int = Field(20, ge=0)  # max /api/morechildren calls per post
    ratelimit_reserve: int = Field(5, ge=0)  # slow down when remaining quota drops below this
    max_retries: int = Field(4, ge=0)
    timeout_seconds: float = Field(30.0, gt=0)


class LoggingConfig(_Section):
    level: str = "INFO"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX, env_nested_delimiter="__", extra="forbid", frozen=True
    )

    paths: PathsConfig = PathsConfig()
    reddit: RedditConfig = RedditConfig()
    collect: CollectConfig = CollectConfig()
    logging: LoggingConfig = LoggingConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml = TomlConfigSettingsSource(settings_cls, toml_file=config_file_path())
        return init_settings, env_settings, toml

    @property
    def data_dir(self) -> Path:
        return self.paths.data_dir or Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))

    @property
    def db_path(self) -> Path:
        return self.data_dir / DB_FILENAME


def load_settings() -> Settings:
    """Load settings, honouring the flat env vars documented in the credentials guide.

    ``RPA_CLIENT_ID``, ``RPA_REDIRECT_URI`` and ``RPA_DATA_DIR`` are shorthands for the
    nested ``RPA_REDDIT__CLIENT_ID`` etc. They are passed as init values, which merge
    with (and win over) the TOML file.
    """
    flat = {
        "reddit": {
            "client_id": os.environ.get("RPA_CLIENT_ID"),
            "redirect_uri": os.environ.get("RPA_REDIRECT_URI"),
        },
        "paths": {"data_dir": os.environ.get("RPA_DATA_DIR")},
    }
    overrides = {
        section: {k: v for k, v in values.items() if v}
        for section, values in flat.items()
        if any(values.values())
    }
    return Settings(**overrides)


class MissingCredentialsError(RuntimeError):
    pass


class Credentials(BaseModel):
    model_config = ConfigDict(frozen=True)

    client_id: str
    client_secret: SecretStr
    refresh_token: SecretStr | None = None  # None until `rpa auth login` has run
    username: str | None = None  # read from /api/v1/me at login, never typed by hand


def _keyring_get(key: str) -> str | None:
    try:
        import keyring
        from keyring.errors import KeyringError

        try:
            return keyring.get_password(KEYRING_SERVICE, key)
        except KeyringError:
            return None  # no usable backend (e.g. headless Linux): fall back to env vars
    except ImportError:  # pragma: no cover - keyring is a hard dependency
        return None


def get_credentials(settings: Settings | None = None) -> Credentials:
    """Resolve credentials: env vars first, then the system keyring."""
    settings = settings or load_settings()
    client_id = settings.reddit.client_id
    client_secret = os.environ.get("RPA_CLIENT_SECRET") or _keyring_get("client_secret")
    refresh_token = os.environ.get("RPA_REFRESH_TOKEN") or _keyring_get("refresh_token")
    if not client_id or not client_secret:
        raise MissingCredentialsError(
            "Reddit credentials not found. Run `rpa auth login`, or set RPA_CLIENT_ID and "
            f"RPA_CLIENT_SECRET. See {CREDENTIALS_DOC}."
        )
    return Credentials(
        client_id=client_id,
        client_secret=SecretStr(client_secret),
        refresh_token=SecretStr(refresh_token) if refresh_token else None,
        username=_keyring_get("username"),
    )


def build_user_agent(username: str | None) -> str:
    """User-Agent in the format Reddit requires."""
    return f"python:{APP_NAME}:{__version__} (by /u/{username or 'unknown'})"
