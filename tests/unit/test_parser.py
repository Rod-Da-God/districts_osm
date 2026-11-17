import pytest

from external.overpass.utils.parser import (
    parse_districts_metadata,
    parse_ways_to_geometry,
)


pytestmark = pytest.mark.unit


def test_parse_districts_metadata_filters_levels_and_names() -> None:
    data = {
        "elements": [
            {
                "type": "relation",
                "id": 1,
                "tags": {
                    "boundary": "administrative",
                    "admin_level": "9",
                    "name": "Центральный район",
                },
            },
            {
                "type": "relation",
                "id": 2,
                "tags": {
                    "boundary": "administrative",
                    "admin_level": "10",
                    "name:ru": "Кировский",
                },
            },
            {
                "type": "relation",
                "id": 3,
                "tags": {
                    "boundary": "administrative",
                    "admin_level": "4",
                    "name": "Область",
                },
            },
            {
                "type": "relation",
                "id": 4,
                "tags": {"admin_level": "9", "name": "Без boundary"},
            },
            {
                "type": "relation",
                "id": 5,
                "tags": {
                    "boundary": "administrative",
                    "admin_level": "9",
                },
            },
            {
                "type": "way",
                "id": 6,
                "tags": {
                    "boundary": "administrative",
                    "admin_level": "9",
                    "name": "Не relation",
                },
            },
        ]
    }

    districts = parse_districts_metadata(data)

    assert districts == [
        {
            "osm_relation_id": 1,
            "osm_type": "relation",
            "name": "Центральный район",
        },
        {"osm_relation_id": 2, "osm_type": "relation", "name": "Кировский"},
    ]


def test_parse_ways_to_geometry_builds_polygon_from_ring() -> None:
    ways = [
        {
            "type": "way",
            "id": 10,
            "geometry": [
                {"lat": 0.0, "lon": 0.0},
                {"lat": 0.0, "lon": 1.0},
                {"lat": 1.0, "lon": 1.0},
                {"lat": 1.0, "lon": 0.0},
                {"lat": 0.0, "lon": 0.0},
            ],
        }
    ]

    geom = parse_ways_to_geometry(ways)

    assert geom is not None
    assert geom.area == pytest.approx(1.0)


def test_parse_ways_to_geometry_returns_none_for_empty_input() -> None:
    assert parse_ways_to_geometry([]) is None


def test_parse_ways_to_geometry_skips_short_ways() -> None:
    ways = [
        {
            "type": "way",
            "id": 11,
            "geometry": [{"lat": 0.0, "lon": 0.0}],
        }
    ]

    assert parse_ways_to_geometry(ways) is None
