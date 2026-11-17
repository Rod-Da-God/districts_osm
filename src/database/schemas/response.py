from typing import Literal

from pydantic import BaseModel, Field, RootModel


class CityResponse(BaseModel):
    """Информация о городе в ответе."""

    id: str = Field(..., description="UUID города")
    code: str = Field(..., description="Код города (khabarovsk)")
    name: str = Field(..., description="Название города (Хабаровск)")


class DistrictResponse(BaseModel):
    """Информация о районе в ответе."""

    id: str = Field(..., description="UUID района")
    name: str = Field(..., description="Название района")


class ResolveDistrictResponse(BaseModel):
    """Ответ 200 для /districts/resolve."""

    city: CityResponse
    district: DistrictResponse
    match_type: Literal["contains", "nearest"] = Field(
        ...,
        description=(
            "Тип определения: contains (внутри) или nearest (ближайший)"
        ),
    )
    distance_m: float | None = Field(
        None,
        description="Расстояние до границы района (метры), только для nearest",
    )


class DistrictListItem(BaseModel):
    """Элемент списка районов для /cities."""

    id: str = Field(..., description="UUID района")
    name: str = Field(..., description="Название района")


CitiesResponse = RootModel[dict[str, list[DistrictListItem]]]


class CityListItem(BaseModel):
    """Элемент списка городов для GET /cities/list."""

    id: str = Field(..., description="UUID города")
    name: str = Field(..., description="Название города (Хабаровск)")
    code: str = Field(..., description="Код города (khabarovsk)")
    coordinates: list[float] | None = Field(
        None, description="Координаты центра города [lon, lat]"
    )


class CitiesListResponse(BaseModel):
    """Ответ для GET /cities/list."""

    data: list[CityListItem] = Field(..., description="Список всех городов")
