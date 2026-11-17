import pytest

from districts.utils.autoload import _normalize_district_name


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Центральный район", "Центральный"),
        ("Кировский Район", "Кировский"),
        ("Северный административный округ", "Северный"),
        ("Северный муниципальный округ", "Северный"),
        ("Без суффикса", "Без суффикса"),
    ],
)
def test_suffixes_are_removed(raw: str, expected: str) -> None:
    name, is_valid = _normalize_district_name(raw, "Хабаровск")

    assert name == expected
    assert is_valid is True


def test_district_equal_to_city_is_rejected() -> None:
    name, is_valid = _normalize_district_name("Хабаровск район", "Хабаровск")

    assert name == "Хабаровск"
    assert is_valid is False
