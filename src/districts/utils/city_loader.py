import logging

from database.models.city_model import City
from database.repository.city_repository import CityRepository
from database.repository.district_repository import DistrictRepository
from districts.exc import CityNotFoundError
from districts.utils.autoload import autoload_city_districts
from external.cache.cache import Cache


logger = logging.getLogger(__name__)


async def get_city_with_autoload(
    city_code: str,
    city_name: str | None = None,
) -> City:
    """
    Получить город с автозагрузкой если нужно.

    Логика:
    1. Попытаться найти город по коду через репозиторий
    2. Если не найден -> запустить автозагрузку
    3. Проверить что у города есть районы через репозиторий
    4. Если районов нет -> запустить автозагрузку
    5. Инвалидировать кеш после автозагрузки

    Args:
        city_code: код города (khabarovsk)
        city_name: название города (Хабаровск), опционально

    Returns:
        City объект

    Raises:
        CityNotFoundError: если город не найден и автозагрузка не удалась
    """
    city = await CityRepository.get_by_code(code=city_code)

    if city is None:
        logger.info(
            "Город '%s' не найден в БД, запуск автозагрузки", city_code
        )

        if city_name is None:
            raise CityNotFoundError(city_code)

        await autoload_city_districts(city_code, city_name)

        await Cache.delete_cities_districts_json()

        city = await CityRepository.get_by_code(code=city_code)

        if city is None:
            raise CityNotFoundError(city_code)

    districts_count = await DistrictRepository.count_by_city(city_id=city.id)

    if districts_count == 0:
        logger.info(
            "У города '%s' нет районов, запуск автозагрузки", city_code
        )

        if city_name is None:
            city_name = city.name

        await autoload_city_districts(city_code, city_name)

        await Cache.delete_cities_districts_json()

    return city
