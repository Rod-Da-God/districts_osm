import logging

from districts.utils.rate_limiter import rate_limiter
from external.overpass.client import OverpassClient
from external.overpass.utils import (
    build_city_area_query,
    build_city_boundary_query,
    normalize_geometry,
    parse_districts_metadata,
    parse_ways_to_geometry,
)


logger = logging.getLogger(__name__)


SPECIAL_CITY_NAMES = {"москва", "санкт-петербург"}


async def fetch_districts_metadata(city_name: str) -> list[dict]:
    """
    Получить metadata районов (relation IDs и names).

    Для Москвы и Санкт-Петербурга использует admin_level=5,
    для остальных городов - admin_level=9.

    Args:
        city_name: название города (Хабаровск, Владивосток, Москва)

    Returns:
        Список районов с полями: osm_relation_id, osm_type, name
    """
    await rate_limiter.acquire()

    query = build_city_area_query(city_name)
    logger.info("Получение метаданных районов для города '%s'", city_name)

    data = await OverpassClient.execute(query=query)

    if city_name.lower() in SPECIAL_CITY_NAMES:
        elements = data.get("elements", [])
        districts = []

        logger.info(
            "Обработка специального запроса для города '%s':"
            " получено %d elements",
            city_name,
            len(elements),
        )

        for elem in elements:
            elem_type = elem.get("type")
            elem_id = elem.get("id")
            tags = elem.get("tags", {})

            if elem_type != "relation":
                continue

            if tags.get("boundary") != "administrative":
                continue

            if tags.get("admin_level") != "5":
                continue

            name = (
                tags.get("name")
                or tags.get("name:ru")
                or tags.get("official_name")
                or tags.get("alt_name")
            )

            if not name:
                logger.debug("Relation %s без name, теги: %s", elem_id, tags)
                continue

            districts.append(
                {
                    "osm_relation_id": elem_id,
                    "osm_type": elem_type,
                    "name": name,
                }
            )

        logger.info(
            "Найдено %d районов для '%s' (admin_level=5)",
            len(districts),
            city_name,
        )
        return districts

    districts = parse_districts_metadata(data)

    if not districts:
        logger.warning("Районы не найдены для города '%s'", city_name)
        return []

    logger.info("Найдено %d районов для '%s'", len(districts), city_name)
    return districts


async def fetch_city_boundary(city_name: str) -> dict | None:
    """
    Получить границы города как фолбек для мелких городов.

    Ищет relation с place=city или admin_level=6 и возвращает
    его метаданные и геометрию. Использует 'out geom' для получения
    геометрии напрямую в members.

    Args:
        city_name: название города (Благовещенск, Магадан)

    Returns:
        dict с полями: osm_relation_id, name, geometry (WKT) или None
    """
    await rate_limiter.acquire()

    query = build_city_boundary_query(city_name)
    logger.info("Получение границ города '%s' (фолбек)", city_name)

    data = await OverpassClient.execute(query=query)
    elements = data.get("elements", [])

    if not elements:
        logger.warning("Границы города '%s' не найдены", city_name)
        return None

    logger.info(
        "Найдено %d элементов для города '%s'", len(elements), city_name
    )

    city_relation = None
    for elem in elements:
        if elem.get("type") != "relation":
            continue

        tags = elem.get("tags", {})
        members = elem.get("members", [])

        is_city = tags.get("place") == "city"
        is_admin = (
            tags.get("boundary") == "administrative"
            and tags.get("admin_level") == "6"
        )

        if not (is_city or is_admin):
            continue

        outer_with_geom = [
            member
            for member in members
            if member.get("type") == "way"
            and member.get("role") == "outer"
            and member.get("geometry")
        ]

        if outer_with_geom:
            city_relation = elem
            logger.info(
                "Найден relation %d: place=%s, admin_level=%s, outer_ways=%d",
                elem.get("id"),
                tags.get("place"),
                tags.get("admin_level"),
                len(outer_with_geom),
            )
            break

    if not city_relation:
        logger.warning(
            "Не найден подходящий relation для '%s' из %d элементов",
            city_name,
            len(elements),
        )
        return None

    rel_id = city_relation.get("id")
    tags = city_relation.get("tags", {})
    name = tags.get("name") or tags.get("name:ru") or city_name

    logger.info("Используем relation %d: %s", rel_id, name)

    members = city_relation.get("members", [])

    outer_members = [
        member
        for member in members
        if member.get("type") == "way"
        and member.get("role") == "outer"
        and member.get("geometry")
    ]

    logger.info(
        "Найдено %d outer ways для города '%s'", len(outer_members), city_name
    )

    ways = [
        {
            "type": "way",
            "id": member.get("ref"),
            "geometry": member.get("geometry", []),
        }
        for member in outer_members
    ]

    geom = parse_ways_to_geometry(ways)
    if geom is None:
        logger.warning(
            "Не удалось построить геометрию для города '%s'", city_name
        )
        return None

    wkt = normalize_geometry(geom)
    if wkt is None:
        logger.warning(
            "Не удалось нормализовать геометрию для города '%s'", city_name
        )
        return None

    logger.info("Геометрия города '%s' успешно построена", city_name)

    return {
        "osm_relation_id": rel_id,
        "name": name,
        "geometry": wkt,
    }


async def fetch_districts_geometry(relation_ids: list[int]) -> dict[int, str]:
    """
    Получить геометрию районов (outer ways) - БАТЧ версия.

    Использует специальный запрос который возвращает:
    1. Relations с members (список way IDs)
    2. Ways с геометрией

    Затем группирует ways по relation_id через members.

    Args:
        relation_ids: список OSM relation ID

    Returns:
        Dict[osm_relation_id -> WKT MultiPolygon]
    """
    await rate_limiter.acquire()

    ids_str = ",".join(map(str, relation_ids))
    query = f"""
[out:json][timeout:180];

relation(id:{ids_str})->.rels;

.rels out tags;
.rels out body;

way(r.rels:"outer")->.ways;
.ways out geom;
"""

    logger.info("Получение геометрии для %d районов (батч)", len(relation_ids))

    data = await OverpassClient.execute(query=query)
    elements = data.get("elements", [])

    relations: dict[int, dict] = {}
    ways: dict[int, dict] = {}

    for elem in elements:
        if elem.get("type") == "relation":
            rel_id = elem.get("id")
            relations[rel_id] = {
                "tags": elem.get("tags", {}),
                "members": elem.get("members", []),
            }
        elif elem.get("type") == "way":
            way_id = elem.get("id")
            ways[way_id] = elem

    logger.info("Получено %d relations и %d ways", len(relations), len(ways))

    result: dict[int, str] = {}

    for rel_id in relation_ids:
        if rel_id not in relations:
            logger.warning("Relation %d не найдена в ответе", rel_id)
            continue

        members = relations[rel_id].get("members", [])

        outer_way_ids = [
            member["ref"]
            for member in members
            if member.get("type") == "way" and member.get("role") == "outer"
        ]

        if not outer_way_ids:
            logger.warning("Relation %d не имеет outer ways", rel_id)
            continue

        relation_ways = []
        for way_id in outer_way_ids:
            if way_id in ways:
                relation_ways.append(ways[way_id])
            else:
                logger.debug(
                    "Way %d из relation %d не найден в ответе", way_id, rel_id
                )

        if not relation_ways:
            logger.warning("Не найдены ways для relation %d", rel_id)
            continue

        logger.debug("Relation %d: %d outer ways", rel_id, len(relation_ways))

        geom = parse_ways_to_geometry(relation_ways)

        if geom is None:
            logger.warning(
                "Не удалось построить геометрию для relation %d", rel_id
            )
            continue

        wkt = normalize_geometry(geom)

        if wkt is None:
            logger.warning(
                "Не удалось нормализовать геометрию для relation %d", rel_id
            )
            continue

        result[rel_id] = wkt
        logger.debug("Геометрия для relation %d построена", rel_id)

    logger.info(
        "Успешно построена геометрия для %d/%d районов",
        len(result),
        len(relation_ids),
    )
    return result
