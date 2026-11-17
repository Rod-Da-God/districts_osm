from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CityCreate(BaseModel):
    """Схема создания города."""

    code: str
    name: str
    center: str | None = None
    source: Literal["manual", "osm"] = "osm"


class DistrictCreate(BaseModel):
    """Схема создания района."""

    city_id: UUID
    name: str
    osm_relation_id: int | None = None
    polygon: str
    center: str | None = None
    source: Literal["manual", "osm"] = "osm"


class ErrorResponse(BaseModel):
    """Стандартный формат ошибки."""

    error: str = Field(..., description="Тип ошибки")
    detail: str | None = Field(None, description="Детали ошибки")
