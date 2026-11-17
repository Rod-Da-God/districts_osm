from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import Base


if TYPE_CHECKING:
    from .city_model import City


class District(Base):
    """Район города с границами в WGS84."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, comment="UUID района"
    )
    city_id: Mapped[UUID] = mapped_column(
        ForeignKey("citys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK города",
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Название района"
    )
    osm_relation_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="OSM relation ID"
    )
    polygon: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
        comment="Границы района (MultiPolygon, WGS84)",
    )
    center: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
        comment="Центроид района",
    )
    source: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="osm",
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

    city: Mapped[City] = relationship("City", back_populates="districts")


Index(
    "idx_district_polygon_gist",
    District.polygon,
    postgresql_using="gist",
)
Index("idx_district_city_id", District.city_id)
