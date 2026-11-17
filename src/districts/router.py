import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from database.schemas.internal import ErrorResponse
from database.schemas.response import (
    CitiesListResponse,
    ResolveDistrictResponse,
)
from districts.dependens import get_districts_service
from districts.exc import (
    CityCodeRequiredError,
    CityNotFoundError,
    DistrictNotFoundError,
    DistrictsBaseException,
    InvalidCoordsError,
    OsmLoadFailedError,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/districts", tags=["districts"])


@router.get(
    "/resolve",
    response_model=ResolveDistrictResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid coordinates or missing city_code",
        },
        404: {
            "model": ErrorResponse,
            "description": "City or district not found",
        },
        502: {"model": ErrorResponse, "description": "OSM load failed"},
    },
)
async def resolve_district(
    svc: Annotated[Any, Depends(get_districts_service)],
    lat: float = Query(..., description="Широта", ge=-90, le=90),
    lon: float = Query(..., description="Долгота", ge=-180, le=180),
    city_code: str = Query(..., description="Код города (khabarovsk)"),
    city_name: str | None = Query(
        None, description="Название города (Хабаровск)"
    ),
    fallback_nearest: bool = Query(
        True,
        description=("Использовать nearest fallback если точка вне районов"),
    ),
) -> Any:
    """
    Определить район по координатам.
    """
    try:
        return await svc.resolve_district(
            lat=lat,
            lon=lon,
            city_code=city_code,
            city_name=city_name,
            fallback_nearest=fallback_nearest,
        )

    except InvalidCoordsError as e:
        logger.warning("Invalid coordinates: %s", e.message)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "invalid_coords", "detail": e.message},
        )

    except CityCodeRequiredError as e:
        logger.warning("City code required: %s", e.message)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "city_code_required", "detail": e.message},
        )

    except CityNotFoundError as e:
        logger.warning("City not found: %s", e.message)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "city_not_found", "detail": e.message},
        )

    except DistrictNotFoundError as e:
        logger.warning("District not found: %s", e.message)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "district_not_found", "detail": e.message},
        )

    except OsmLoadFailedError as e:
        logger.error("OSM load failed: %s", e.message)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "osm_load_failed", "detail": e.message},
        )

    except DistrictsBaseException as e:
        logger.error("Districts exception: %s", e.message)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "error", "detail": e.message},
        )


@router.get(
    "/cities",
    response_model=dict[str, list[dict]],
    status_code=status.HTTP_200_OK,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_cities(
    svc: Annotated[Any, Depends(get_districts_service)],
) -> Any:
    """
    Получить список городов с районами.
    """
    return await svc.get_cities_with_districts()


@router.get(
    "/cities/list",
    response_model=CitiesListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_cities_list(
    svc: Annotated[Any, Depends(get_districts_service)],
) -> Any:
    """
    Получить список всех городов с координатами центра.
    """
    cities = await svc.get_all_cities()
    return {"data": cities}
