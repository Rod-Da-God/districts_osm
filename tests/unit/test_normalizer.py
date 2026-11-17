import pytest
from shapely.geometry import LineString, MultiPolygon, Polygon

from external.overpass.utils.normalizer import normalize_geometry


pytestmark = pytest.mark.unit


def test_polygon_becomes_multipolygon_wkt() -> None:
    result = normalize_geometry(Polygon([(0, 0), (0, 1), (1, 1), (0, 0)]))

    assert result is not None
    assert result.startswith("MULTIPOLYGON")


def test_multipolygon_kept_as_is() -> None:
    polygon = Polygon([(0, 0), (0, 1), (1, 1), (0, 0)])

    result = normalize_geometry(MultiPolygon([polygon]))

    assert result is not None
    assert result.startswith("MULTIPOLYGON")


def test_non_polygon_returns_none() -> None:
    assert normalize_geometry(LineString([(0, 0), (1, 1)])) is None
