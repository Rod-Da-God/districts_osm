import pytest

from districts.exc import (
    CityNotFoundError,
    DistrictNotFoundError,
    InvalidCoordsError,
    OsmLoadFailedError,
)


pytestmark = pytest.mark.unit


def test_invalid_coords_is_400() -> None:
    error = InvalidCoordsError()

    assert error.status_code == 400
    assert error.message == "Invalid coordinates provided"


def test_city_not_found_is_404_with_code() -> None:
    error = CityNotFoundError("khabarovsk")

    assert error.status_code == 404
    assert "khabarovsk" in error.message


def test_district_not_found_is_404() -> None:
    assert DistrictNotFoundError().status_code == 404


def test_osm_load_failed_is_502_with_reason() -> None:
    error = OsmLoadFailedError("magadan", "timeout")

    assert error.status_code == 502
    assert "magadan" in error.message
    assert "timeout" in error.message
