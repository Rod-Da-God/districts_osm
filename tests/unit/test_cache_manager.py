import json

import pytest

from districts.utils import cache_manager
from external.cache.cache import Cache


pytestmark = pytest.mark.unit


async def test_returns_cached_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"khabarovsk": [{"id": "1", "name": "Центральный"}]}

    async def fake_get() -> str:
        return json.dumps(payload, ensure_ascii=False)

    async def fail_db() -> list[dict]:
        raise AssertionError("БД не должна читаться при заполненном кеше")

    monkeypatch.setattr(Cache, "get_cities_districts_json", fake_get)
    monkeypatch.setattr(
        cache_manager.DistrictRepository,
        "get_all_cities_with_districts",
        fail_db,
    )

    assert await cache_manager.get_cached_cities_districts() == payload


async def test_loads_from_db_and_fills_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_rows = [
        {
            "code": "khabarovsk",
            "districts": [{"id": "1", "name": "Центральный"}],
        }
    ]
    saved: dict[str, str] = {}

    async def fake_get() -> None:
        return None

    async def fake_db() -> list[dict]:
        return db_rows

    async def fake_set(json_str: str) -> None:
        saved["value"] = json_str

    monkeypatch.setattr(Cache, "get_cities_districts_json", fake_get)
    monkeypatch.setattr(
        cache_manager.DistrictRepository,
        "get_all_cities_with_districts",
        fake_db,
    )
    monkeypatch.setattr(Cache, "set_cities_districts_json", fake_set)

    result = await cache_manager.get_cached_cities_districts()

    assert result == {"khabarovsk": [{"id": "1", "name": "Центральный"}]}
    assert json.loads(saved["value"]) == result
