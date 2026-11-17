import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.path import ENV_FILE


logger = logging.getLogger(__name__)


class DistrictsSettings(BaseSettings):
    """Настройки бизнес-логики районов."""

    nearest_max_distance_m: float = Field(
        default=5000.0,
        gt=0,
        description="Максимальное расстояние до района для nearest-фолбека, м",
    )
    autoload_cooldown_seconds: int = Field(
        default=300,
        ge=0,
        description=(
            "Пауза между повторными попытками автозагрузки города, сек"
        ),
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = DistrictsSettings()
