from pydantic import BaseModel, Field


class ResolveDistrictRequest(BaseModel):
    """Query параметры для GET /districts/resolve."""

    lat: float = Field(..., description="Широта")
    lon: float = Field(..., description="Долгота")
    city_code: str | None = Field(..., description="Код города (khabarovsk)")
    city_name: str | None = Field(
        ..., description="Название города (Хабаровск)"
    )
    fallback_nearest: bool = Field(
        default=True,
        description="Использовать nearest fallback если точка вне районов",
    )
