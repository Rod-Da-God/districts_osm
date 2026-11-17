from typing import Any

from database.repository.city_repository import CityRepository
from database.repository.district_repository import DistrictRepository
from districts.config import settings
from districts.exc import DistrictNotFoundError
from districts.utils.cache_manager import get_cached_cities_districts
from districts.utils.city_loader import get_city_with_autoload


async def resolve_district(
    lat: float,
    lon: float,
    city_code: str,
    city_name: str | None = None,
    fallback_nearest: bool = True,
) -> dict[str, Any]:
    """Определить район по координатам."""
    city = await get_city_with_autoload(city_code, city_name)

    district_result = await DistrictRepository.find_district_by_point(
        city_id=city.id,
        lat=lat,
        lon=lon,
    )

    if district_result is not None:
        return {
            "city": {
                "id": str(city.id),
                "code": city.code,
                "name": city.name,
            },
            "district": {
                "id": district_result["id"],
                "name": district_result["name"],
            },
            "match_type": district_result["match_type"],
            "distance_m": district_result.get("distance_m"),
        }

    if fallback_nearest:
        nearest_result = await DistrictRepository.find_nearest_district(
            city_id=city.id,
            lat=lat,
            lon=lon,
            max_distance_m=settings.nearest_max_distance_m,
        )

        if nearest_result is not None:
            return {
                "city": {
                    "id": str(city.id),
                    "code": city.code,
                    "name": city.name,
                },
                "district": {
                    "id": nearest_result["id"],
                    "name": nearest_result["name"],
                },
                "match_type": nearest_result["match_type"],
                "distance_m": nearest_result.get("distance_m"),
            }

    raise DistrictNotFoundError()


async def get_cities_with_districts() -> dict[str, list[dict]]:
    """Получить список городов с районами."""
    return await get_cached_cities_districts()


async def get_all_cities() -> list[dict[str, Any]]:
    """Получить список всех городов с координатами."""
    return await CityRepository.get_all_cities()
