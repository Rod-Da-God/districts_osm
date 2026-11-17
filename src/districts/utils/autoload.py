import asyncio
import logging
from datetime import datetime

from shapely import wkt

from database.repository.city_repository import CityRepository
from database.repository.district_repository import DistrictRepository
from database.schemas.internal import CityCreate, DistrictCreate
from districts.config import settings
from districts.exc import OsmLoadFailedError
from districts.utils.fetcher import (
    fetch_city_boundary,
    fetch_districts_geometry,
    fetch_districts_metadata,
)


logger = logging.getLogger(__name__)


_failed_attempts: dict[str, datetime] = {}

_city_locks: dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def _get_city_lock(city_code: str) -> asyncio.Lock:
    """
    Получить или создать блокировку для конкретного города.

    Args:
        city_code: код города

    Returns:
        asyncio.Lock для этого города
    """
    async with _locks_lock:
        if city_code not in _city_locks:
            _city_locks[city_code] = asyncio.Lock()
        return _city_locks[city_code]


def _check_cooldown(city_code: str) -> bool:
    """
    Проверить cooldown для города.

    Returns:
        True если можно повторить попытку, False если еще рано
    """
    if city_code not in _failed_attempts:
        return True

    last_attempt = _failed_attempts[city_code]
    elapsed = (datetime.now() - last_attempt).total_seconds()
    cooldown = settings.autoload_cooldown_seconds

    if elapsed < cooldown:
        logger.warning(
            "Город '%s' в cooldown: осталось %.0f сек",
            city_code,
            cooldown - elapsed,
        )
        return False

    del _failed_attempts[city_code]
    return True


def _calculate_center_wkt(geometry_wkt: str) -> str:
    """
    Вычислить центр (centroid) из WKT геометрии.

    Args:
        geometry_wkt: WKT строка (MULTIPOLYGON или POLYGON)

    Returns:
        WKT строка POINT
    """
    geom = wkt.loads(geometry_wkt)
    return geom.centroid.wkt


def _normalize_district_name(name: str, city_name: str) -> tuple[str, bool]:
    """
    Нормализовать название района и проверить валидность.

    1. Убирает суффиксы типа "район", "административный округ" и т.д.
    2. Проверяет что название не совпадает с городом

    Args:
        name: исходное название района
        city_name: название города

    Returns:
        tuple: (normalized_name, is_valid)
            - normalized_name: нормализованное название
            - is_valid: True если район валиден, False если нужно пропустить
    """
    normalized = name

    suffixes_to_remove = [
        " административный округ",
        " Административный округ",
        " муниципальный округ",
        " Муниципальный округ",
        " район",
        " Район",
    ]

    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            logger.debug(
                "Нормализация названия: '%s' -> '%s'", name, normalized
            )
            break

    if normalized.lower().strip() == city_name.lower().strip():
        logger.warning(
            "Пропуск района '%s': совпадает с названием города '%s'",
            name,
            city_name,
        )
        return normalized, False

    return normalized, True


async def autoload_city_districts(city_code: str, city_name: str) -> None:
    """
    Автозагрузка города и районов из OSM с защитой от дублирования.

    Использует asyncio.Lock чтобы гарантировать что только один запрос
    загружает конкретный город в конкретный момент времени.

    Args:
        city_code: код города (khabarovsk)
        city_name: название города (Хабаровск)

    Raises:
        OsmLoadFailedError: если загрузка провалилась
    """
    city_lock = await _get_city_lock(city_code)

    async with city_lock:
        logger.debug("Получена блокировка для города '%s'", city_code)

        city = await CityRepository.get_by_code(code=city_code)
        if city is not None:
            districts_count = await DistrictRepository.count_by_city(
                city_id=city.id
            )
            if districts_count > 0:
                logger.info(
                    "Город '%s' уже загружен другим запросом (районов: %d),"
                    " пропускаем",
                    city_code,
                    districts_count,
                )
                return

        if not _check_cooldown(city_code):
            raise OsmLoadFailedError(
                city_code=city_code,
                reason=(
                    "Cooldown active, retry after"
                    f" {settings.autoload_cooldown_seconds}s"
                ),
            )

        try:
            logger.info(
                "Запуск автозагрузки для города '%s' (%s)",
                city_name,
                city_code,
            )

            districts_meta = await fetch_districts_metadata(city_name)

            if not districts_meta:
                logger.info(
                    "Районы не найдены для '%s', включаем фолбек:"
                    " загрузка границ города",
                    city_name,
                )
                city_boundary = await fetch_city_boundary(city_name)

                if not city_boundary:
                    _failed_attempts[city_code] = datetime.now()
                    raise OsmLoadFailedError(
                        city_code=city_code,
                        reason=(
                            "No districts found and city boundary"
                            " fallback failed"
                        ),
                    )

                center_wkt: str | None = _calculate_center_wkt(
                    city_boundary["geometry"]
                )

                city = await CityRepository.get_by_code(code=city_code)

                if city is None:
                    city_data = CityCreate(
                        code=city_code,
                        name=city_name,
                        center=center_wkt,
                        source="osm",
                    )
                    rows_created = await CityRepository.create(city_data)
                    logger.info(
                        "Создан город '%s': %d записей, center=%s",
                        city_code,
                        rows_created,
                        center_wkt,
                    )

                    city = await CityRepository.get_by_code(code=city_code)
                    if city is None:
                        raise OsmLoadFailedError(
                            city_code=city_code,
                            reason="Failed to retrieve city after creation",
                        )
                else:
                    logger.info(
                        "Город '%s' уже существует в БД (id=%s)",
                        city_code,
                        city.id,
                    )

                district_data = DistrictCreate(
                    city_id=city.id,
                    name=city_name,
                    osm_relation_id=city_boundary["osm_relation_id"],
                    polygon=city_boundary["geometry"],
                    center=center_wkt,
                    source="osm",
                )

                await DistrictRepository.create(district_data)
                logger.info(
                    "Город '%s' сохранен как единый район (фолбек):"
                    " osm_relation_id=%d",
                    city_name,
                    city_boundary["osm_relation_id"],
                )
                return

            relation_ids = [
                district["osm_relation_id"] for district in districts_meta
            ]
            geometries = await fetch_districts_geometry(relation_ids)

            if not geometries:
                _failed_attempts[city_code] = datetime.now()
                raise OsmLoadFailedError(
                    city_code=city_code,
                    reason="Failed to fetch geometries from OSM",
                )

            first_geom = next(iter(geometries.values()), None)
            center_wkt = (
                _calculate_center_wkt(first_geom) if first_geom else None
            )

            logger.info(
                "Сохранение города '%s' и %d районов в БД",
                city_code,
                len(geometries),
            )

            city = await CityRepository.get_by_code(code=city_code)

            if city is None:
                city_data = CityCreate(
                    code=city_code,
                    name=city_name,
                    center=center_wkt,
                    source="osm",
                )
                rows_created = await CityRepository.create(city_data)
                logger.info(
                    "Создан город '%s': %d записей, center=%s",
                    city_code,
                    rows_created,
                    center_wkt,
                )

                city = await CityRepository.get_by_code(code=city_code)
                if city is None:
                    raise OsmLoadFailedError(
                        city_code=city_code,
                        reason="Failed to retrieve city after creation",
                    )
            else:
                logger.info(
                    "Город '%s' уже существует в БД (id=%s)",
                    city_code,
                    city.id,
                )

            logger.info("Город загружен: %s (id=%s)", city.name, city.id)

            districts_created = 0
            districts_skipped = 0

            for meta in districts_meta:
                rel_id = meta["osm_relation_id"]
                if rel_id not in geometries:
                    logger.warning(
                        "Пропуск района '%s': нет геометрии", meta["name"]
                    )
                    districts_skipped += 1
                    continue

                normalized_name, is_valid = _normalize_district_name(
                    meta["name"], city_name
                )

                if not is_valid:
                    districts_skipped += 1
                    continue

                district_center = _calculate_center_wkt(geometries[rel_id])

                district_data = DistrictCreate(
                    city_id=city.id,
                    name=normalized_name,
                    osm_relation_id=rel_id,
                    polygon=geometries[rel_id],
                    center=district_center,
                    source="osm",
                )

                await DistrictRepository.create(district_data)
                districts_created += 1
                logger.debug("Создан район: %s", normalized_name)

            if districts_created == 0:
                _failed_attempts[city_code] = datetime.now()
                raise OsmLoadFailedError(
                    city_code=city_code,
                    reason="Failed to save districts to database",
                )

            logger.info(
                "Успешно загружен город '%s': %d/%d районов сохранено,"
                " %d пропущено",
                city_code,
                districts_created,
                len(districts_meta),
                districts_skipped,
            )

        except OsmLoadFailedError:
            raise
        finally:
            logger.debug("Освобождена блокировка для города '%s'", city_code)
