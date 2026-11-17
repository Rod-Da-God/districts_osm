import logging

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.path import ENV_FILE


logger = logging.getLogger(__name__)


class CacheSettings(BaseSettings):
    """
    Настройки Redis-кеша сервиса районов.

    В кеше хранится один JSON:
      city_code -> [districts...]
    """

    cache_user: str | None = Field(
        default=None, description="Redis username (optional)"
    )
    cache_password: SecretStr | None = Field(
        default=None, description="Redis password (optional)"
    )
    cache_host: str = Field(default="localhost", description="Redis host")
    cache_port: int = Field(default=6379, description="Redis port")
    cache_db: int = Field(default=0, description="Redis database number")

    cache_decode_responses: bool = Field(
        default=True, description="Decode responses to str"
    )
    cache_max_connections: int = Field(
        default=20, description="Connection pool max size"
    )
    cache_socket_timeout: int = Field(
        default=5, description="Read/Write socket timeout (sec)"
    )
    cache_socket_connect_timeout: int = Field(
        default=10, description="Connect timeout (sec)"
    )
    cache_health_check_interval: int = Field(
        default=15, description="Health check interval (sec)"
    )

    cache_key_prefix: str = Field(
        default="geo", description="Prefix for all keys"
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cache_url(self) -> str:
        """
        Собирает redis:// URL с учётом user/password (если заданы).

        Формат:
          redis://user:password@host:port/db
          redis://host:port/db
        """
        user_part = f"{self.cache_user}:" if self.cache_user else ""
        password_part = (
            f"{self.cache_password.get_secret_value()}@"
            if self.cache_password
            else ""
        )
        return (
            f"redis://{user_part}{password_part}"
            f"{self.cache_host}:{self.cache_port}/{self.cache_db}"
        )


cache_settings = CacheSettings()
