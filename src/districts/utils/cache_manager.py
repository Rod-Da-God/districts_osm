import json
import logging

from database.repository.district_repository import DistrictRepository
from external.cache.cache import Cache


logger = logging.getLogger(__name__)


async def get_cached_cities_districts() -> dict[str, list[dict]]:
    """
    Получить города с районами с кешированием.

    Returns:
        Dict[city_code -> [{"id": "...", "name": "..."}]]
    """
    cached = await Cache.get_cities_districts_json()

    if cached is not None:
        logger.debug("Возврат данных из кеша")
        return json.loads(cached)

    logger.debug("Кеш пуст, загрузка из БД")
    cities_data = await DistrictRepository.get_all_cities_with_districts()

    result = {city["code"]: city["districts"] for city in cities_data}

    await Cache.set_cities_districts_json(
        json.dumps(result, ensure_ascii=False)
    )

    return result
