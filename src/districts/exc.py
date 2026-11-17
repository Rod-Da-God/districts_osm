from fastapi import status


class DistrictsBaseException(Exception):
    """Базовое исключение для districts модуля."""

    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidCoordsError(DistrictsBaseException):
    """400 - Невалидные координаты."""

    def __init__(self, message: str = "Invalid coordinates provided") -> None:
        super().__init__(
            message=message, status_code=status.HTTP_400_BAD_REQUEST
        )


class CityCodeRequiredError(DistrictsBaseException):
    """400 - city_code обязателен."""

    def __init__(self, message: str = "city_code is required") -> None:
        super().__init__(
            message=message, status_code=status.HTTP_400_BAD_REQUEST
        )


class CityNotFoundError(DistrictsBaseException):
    """404 - Город не найден (автозагрузка не удалась)."""

    def __init__(self, city_code: str) -> None:
        super().__init__(
            message=f"City '{city_code}' not found and autoload failed",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DistrictNotFoundError(DistrictsBaseException):
    """404 - Район не найден для указанных координат."""

    def __init__(
        self, message: str = "District not found for given coordinates"
    ) -> None:
        super().__init__(
            message=message, status_code=status.HTTP_404_NOT_FOUND
        )


class OsmLoadFailedError(DistrictsBaseException):
    """502 - Ошибка загрузки из OSM."""

    def __init__(self, city_code: str, reason: str = "Unknown error") -> None:
        super().__init__(
            message=(
                "Failed to load data from OSM for city"
                f" '{city_code}': {reason}"
            ),
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
