import logging


logger = logging.getLogger(__name__)


SPECIAL_CITIES = {
    "москва": "Москва",
    "санкт-петербург": "Санкт-Петербург",
}

_SPECIAL_ADMIN_LEVEL = "5"
_DEFAULT_ADMIN_LEVEL = "9"


def build_city_area_query(city_name: str) -> str:
    """
    Построить Overpass QL для поиска relations районов города.

    Стратегия:
    - Для Москвы и Санкт-Петербурга: admin_level=5
    - Для остальных городов: admin_level=9

    Args:
        city_name: Название города (Хабаровск, Владивосток, Москва)

    Returns:
        Overpass QL запрос
    """
    city_lower = city_name.lower()

    if city_lower in SPECIAL_CITIES:
        normalized_name = SPECIAL_CITIES[city_lower]
        logger.info(
            "Используется специальный запрос для города: %s", normalized_name
        )

        query = f"""
[out:json][timeout:120];
area["name"="{normalized_name}"]->.city_area;
rel(area.city_area)
  ["boundary"="administrative"]
  ["admin_level"="{_SPECIAL_ADMIN_LEVEL}"]
  ->.districts;
.districts out tags geom;
"""
        return query.strip()

    query = f"""
[out:json][timeout:120];
area["name"="{city_name}"]->.a;
(
  relation(area.a)["boundary"="administrative"]["admin_level"="{_DEFAULT_ADMIN_LEVEL}"];
);
out tags;
"""
    return query.strip()


def build_city_boundary_query(city_name: str) -> str:
    """
    Построить Overpass QL для поиска границ самого города.

    Используется как фолбек для мелких городов без районов.
    Ищет relation с place=city и возвращает его геометрию напрямую.

    Args:
        city_name: Название города (Благовещенск, Магадан)

    Returns:
        Overpass QL запрос
    """
    query = f"""
[out:json][timeout:120];
(
  relation["place"="city"]["name"="{city_name}"];
  relation["boundary"="administrative"]["admin_level"="6"]["name"="{city_name}"];
);
out geom;
"""
    return query.strip()


def build_districts_geometry_query(relation_ids: list[int]) -> str:
    """
    Построить Overpass QL для получения outer ways районов.

    Args:
        relation_ids: Список OSM relation ID районов

    Returns:
        Overpass QL запрос
    """
    ids_str = ",".join(map(str, relation_ids))
    query = f"""
[out:json][timeout:180];
relation(id:{ids_str})->.rels;
way(r.rels:"outer")->.outerWays;
.outerWays out tags geom;
"""
    return query.strip()
