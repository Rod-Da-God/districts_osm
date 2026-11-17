from __future__ import annotations

import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.path import ENV_FILE


logger = logging.getLogger(__name__)


class OverpassSettings(BaseSettings):
    """
    Настройки клиента Overpass API.

    Используется для:
    - выполнения Overpass QL запросов к /api/interpreter
    - первичной/ленивой загрузки городов и районов из OSM
    """

    overpass_base_url: str = Field(
        default="https://overpass-api.de",
        description="Base URL Overpass API (without trailing slash)",
    )

    overpass_timeout_s: float = Field(
        default=120.0,
        description="HTTP client timeout in seconds for Overpass queries",
    )

    overpass_user_agent: str = Field(
        default="districts-osm/1.0",
        description="User-Agent for Overpass requests (required by API)",
    )

    overpass_rps_limit: float = Field(
        default=1.0,
        gt=0,
        description="Max Overpass requests per second (global limiter)",
    )

    overpass_retry_attempts: int = Field(
        default=3,
        ge=1,
        description="How many attempts on timeout/connection/5xx errors",
    )

    overpass_retry_backoff_s: float = Field(
        default=2.0,
        ge=0,
        description="Base backoff seconds between retries",
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


overpass_settings = OverpassSettings()
