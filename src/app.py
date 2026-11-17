import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database.core.connection import init_db
from exc_handler import setup_exception_handlers
from external.cache.cache import Cache
from external.overpass.client import OverpassClient
from middleware import setup_middlewares
from routers import setup_routers


logger = logging.getLogger(__name__)


async def startup() -> None:
    logger.info("START Application")

    await init_db(use_create_all=True)
    logger.info("Database initialized")

    await OverpassClient.init()
    logger.info("OverpassClient initialized")

    await Cache.init()
    logger.info("Cache initialized")

    logger.info("START Completed")


async def shutdown() -> None:
    await OverpassClient.close()
    await Cache.close()
    logger.info("FINISH Application")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup()
    yield
    await shutdown()


def create_app() -> FastAPI:
    """
    Фабрика приложения. Модуль импортируется uvicorn-ом после setup_tracing(),
    поэтому FastAPI и SQLAlchemy здесь уже инструментированы.
    """
    app = FastAPI(lifespan=lifespan, redirect_slashes=False)
    setup_routers(app=app)
    setup_exception_handlers(app=app)
    setup_middlewares(app=app)
    return app
