from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import Base


if TYPE_CHECKING:
    from .district_model import District


class SourceEnum(StrEnum):
    """Источник данных: ручной ввод или OSM."""

    MANUAL = "manual"
    OSM = "osm"


class City(Base):
    """Город, для которого загружены районы."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, comment="UUID города"
    )
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Код города латиницей (khabarovsk)",
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Название города (Хабаровск)"
    )
    center: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
        comment="Центр города WGS84",
    )
    source: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=SourceEnum.OSM.value,
        comment="Источник: manual | osm",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    districts: Mapped[list[District]] = relationship(
        "District", back_populates="city", cascade="all, delete-orphan"
    )
