import logging
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from geoalchemy2.functions import (
    ST_Covers,
    ST_Distance,
    ST_MakePoint,
    ST_SetSRID,
)
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.core.connection import connection
from database.models.city_model import City
from database.models.district_model import District
from database.repository.postgre_repo import PostgreRepository


logger = logging.getLogger(__name__)


class DistrictRepository(PostgreRepository[District]):
    """Репозиторий для District."""

    model = District

    @classmethod
    @connection(commit=False)
    async def find_district_by_point(
        cls,
        city_id: UUID,
        lat: float,
        lon: float,
        session: AsyncSession,
    ) -> dict[str, Any] | None:
        """
        Найти район, который содержит точку (ST_Covers).

        Если найдено >1 района (битые границы):
        - выбрать район с минимальным ST_Distance
        - залогировать случай

        Возвращает dict с полями District + match_type или None.
        """
        point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

        stmt = (
            select(District)
            .where(District.city_id == city_id)
            .where(ST_Covers(District.polygon, point))
        )
        result = await session.execute(stmt)
        districts = result.scalars().all()

        if len(districts) == 0:
            return None

        if len(districts) == 1:
            district = districts[0]
            return {
                "id": str(district.id),
                "city_id": str(district.city_id),
                "name": district.name,
                "osm_relation_id": district.osm_relation_id,
                "match_type": "contains",
                "distance_m": None,
            }

        logger.warning(
            "Найдено %d районов для точки lat=%s lon=%s в городе %s"
            " (битые границы)",
            len(districts),
            lat,
            lon,
            city_id,
        )

        min_distance = None
        closest_district = None

        for district in districts:
            distance_stmt = select(
                ST_Distance(
                    cast(District.polygon, Geography),
                    cast(point, Geography),
                )
            ).where(District.id == district.id)

            distance_result = await session.execute(distance_stmt)
            distance = distance_result.scalar()

            if min_distance is None or distance < min_distance:
                min_distance = distance
                closest_district = district

        if closest_district is None:
            return None

        return {
            "id": str(closest_district.id),
            "city_id": str(closest_district.city_id),
            "name": closest_district.name,
            "osm_relation_id": closest_district.osm_relation_id,
            "match_type": "contains",
            "distance_m": min_distance,
        }

    @classmethod
    @connection(commit=False)
    async def find_nearest_district(
        cls,
        city_id: UUID,
        lat: float,
        lon: float,
        max_distance_m: float,
        session: AsyncSession,
    ) -> dict[str, Any] | None:
        """
        Найти ближайший район по расстоянию до границы полигона.

        Возвращает dict с полями District + match_type + distance_m
        или None.
        """
        point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

        stmt = (
            select(
                District,
                ST_Distance(
                    cast(District.polygon, Geography),
                    cast(point, Geography),
                ).label("distance"),
            )
            .where(District.city_id == city_id)
            .order_by("distance")
            .limit(1)
        )

        result = await session.execute(stmt)
        row = result.first()

        if row is None:
            return None

        district, distance = row

        if distance > max_distance_m:
            logger.info(
                "Ближайший район '%s' дальше порога: %.2fm > %.2fm",
                district.name,
                distance,
                max_distance_m,
            )
            return None

        return {
            "id": str(district.id),
            "city_id": str(district.city_id),
            "name": district.name,
            "osm_relation_id": district.osm_relation_id,
            "match_type": "nearest",
            "distance_m": distance,
        }

    @classmethod
    @connection(commit=False)
    async def get_all_cities_with_districts(
        cls,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        Получить все города с их районами.

        Для построения кеша.

        Возвращает список:
        [
          {
            "code": "khabarovsk",
            "districts": [{"id": "...", "name": "..."}]
          },
          ...
        ]
        """
        stmt = (
            select(City)
            .options(selectinload(City.districts))
            .order_by(City.code)
        )
        result = await session.execute(stmt)
        cities = result.scalars().all()

        return [
            {
                "code": city.code,
                "districts": [
                    {"id": str(district.id), "name": district.name}
                    for district in city.districts
                ],
            }
            for city in cities
        ]

    @classmethod
    @connection(commit=False)
    async def count_by_city(
        cls,
        city_id: UUID,
        session: AsyncSession,
    ) -> int:
        """
        Подсчитать количество районов в городе.

        Args:
            city_id: UUID города
            session: асинхронная сессия

        Returns:
            Количество районов
        """
        stmt = select(func.count(District.id)).where(
            District.city_id == city_id
        )
        result = await session.execute(stmt)
        count = result.scalar_one()

        logger.debug("В городе %s найдено %d районов", city_id, count)
        return count
