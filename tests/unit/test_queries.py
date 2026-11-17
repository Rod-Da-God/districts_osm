import pytest

from external.overpass.utils.queries import (
    build_city_area_query,
    build_city_boundary_query,
    build_districts_geometry_query,
)


pytestmark = pytest.mark.unit


def test_moscow_uses_admin_level_5() -> None:
    query = build_city_area_query("москва")

    assert '["admin_level"="5"]' in query
    assert '["name"="Москва"]' in query


def test_spb_uses_admin_level_5_case_insensitive() -> None:
    query = build_city_area_query("Санкт-Петербург")

    assert '["admin_level"="5"]' in query
    assert '["name"="Санкт-Петербург"]' in query


def test_regular_city_uses_admin_level_9() -> None:
    query = build_city_area_query("Хабаровск")

    assert '["admin_level"="9"]' in query
    assert "area.a" in query


def test_city_boundary_query_looks_for_place_city() -> None:
    query = build_city_boundary_query("Магадан")

    assert '["place"="city"]' in query
    assert '["admin_level"="6"]' in query
    assert "out geom" in query


def test_districts_geometry_query_joins_ids() -> None:
    query = build_districts_geometry_query([1, 2, 3])

    assert "relation(id:1,2,3)" in query
    assert 'way(r.rels:"outer")' in query
