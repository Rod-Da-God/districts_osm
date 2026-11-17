import logging
from typing import Any

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.core.connection import connection
from database.models.city_model import City
from database.repository.postgre_repo import PostgreRepository


logger = logging.getLogger(__name__)


class CityRepository(PostgreRepository[City]):
    """Репозиторий для City."""

    model = City

    @classmethod
    @connection(commit=False)
    async def get_by_code(
        cls,
        code: str,
        session: AsyncSession,
    ) -> City | None:
        """
        Получить город по коду.

        Args:
            code: код города (khabarovsk)
            session: асинхронная сессия

        Returns:
            City или None если не найден
        """
        stmt = select(City).where(City.code == code)
        result = await session.execute(stmt)
        city = result.scalar_one_or_none()

        if city:
            logger.debug(
                "Город '%s' найден: id=%s name=%s", code, city.id, city.name
            )
        else:
            logger.debug("Город '%s' не найден в БД", code)

        return city

    @classmethod
    @connection(commit=False)
    async def get_all_cities(
        cls,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        Получить все города с координатами центра.

        Returns:
            Список городов с полями: id, name, code, coordinates [lon, lat]
        """
        stmt = select(
            City.id,
            City.name,
            City.code,
            ST_X(City.center).label("lon"),
            ST_Y(City.center).label("lat"),
        ).order_by(City.name)

        result = await session.execute(stmt)
        rows = result.all()

        cities = []
        for row in rows:
            city_dict: dict[str, Any] = {
                "id": str(row.id),
                "name": row.name,
                "code": row.code,
            }

            if row.lon is not None and row.lat is not None:
                city_dict["coordinates"] = [row.lon, row.lat]
            else:
                city_dict["coordinates"] = None

            cities.append(city_dict)

        logger.debug("Получено %d городов из БД", len(cities))
        return cities
