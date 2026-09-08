"""Environment-based configuration, loaded once at startup."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_REQUIRED_VARS = (
    "DISCORD_TOKEN",
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    discord_token: str
    spotify_client_id: str
    spotify_client_secret: str
    soloist_ws_host: str
    soloist_ws_port: int
    pulse_monitor: str
    pulse_server: str | None

    @property
    def soloist_ws_url(self) -> str:
        return f"ws://{self.soloist_ws_host}:{self.soloist_ws_port}"


def load_config(env_file: str | None = ".env") -> Config:
    """Load and validate configuration from the environment.

    Raises ConfigError with a clear message if a required variable is
    missing, so misconfiguration fails fast instead of surfacing as a
    confusing runtime error later.
    """
    if env_file:
        load_dotenv(env_file, override=False)

    missing = [name for name in _REQUIRED_VARS if not os.environ.get(name)]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill them in "
            "(see docs/AUTH.md)."
        )

    try:
        soloist_ws_port = int(os.environ.get("SOLOIST_WS_PORT", "5710"))
    except ValueError as exc:
        raise ConfigError("SOLOIST_WS_PORT must be an integer") from exc

    return Config(
        discord_token=os.environ["DISCORD_TOKEN"],
        spotify_client_id=os.environ["SPOTIFY_CLIENT_ID"],
        spotify_client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        soloist_ws_host=os.environ.get("SOLOIST_WS_HOST", "127.0.0.1"),
        soloist_ws_port=soloist_ws_port,
        pulse_monitor=os.environ.get("SOLOIST_PULSE_MONITOR", "soloist_out.monitor"),
        pulse_server=os.environ.get("PULSE_SERVER") or None,
    )
