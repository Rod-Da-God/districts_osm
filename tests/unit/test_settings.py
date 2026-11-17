import pytest

from database.core.config import DatabaseSettings
from external.cache.config import CacheSettings


pytestmark = pytest.mark.unit


def test_database_url_with_password() -> None:
    settings = DatabaseSettings(
        DB_USER="postgres",
        DB_PASSWORD="secret",
        DB_HOST="db",
        DB_PORT=5433,
        DB_NAME="districts",
    )

    assert (
        settings.sqlalchemy_url
        == "postgresql+asyncpg://postgres:secret@db:5433/districts"
    )


def test_database_url_without_password_does_not_fail() -> None:
    settings = DatabaseSettings(
        DB_USER="postgres",
        DB_PASSWORD=None,
        DB_HOST="db",
        DB_PORT=5432,
        DB_NAME="districts",
    )

    assert settings.sqlalchemy_url == "postgresql+asyncpg://postgres:@db:5432/districts"


def test_cache_url_without_credentials() -> None:
    settings = CacheSettings(
        cache_user=None,
        cache_password=None,
        cache_host="redis",
        cache_port=6380,
        cache_db=2,
    )

    assert settings.cache_url == "redis://redis:6380/2"


def test_cache_url_with_credentials() -> None:
    settings = CacheSettings(
        cache_user="user",
        cache_password="pass",
        cache_host="redis",
        cache_port=6379,
        cache_db=0,
    )

    assert settings.cache_url == "redis://user:pass@redis:6379/0"
