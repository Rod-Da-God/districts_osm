import logging
from collections.abc import Callable
from time import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CollectorRegistry,
    GCCollector,
    PlatformCollector,
    ProcessCollector,
)
from prometheus_fastapi_instrumentator import Instrumentator, metrics


logger = logging.getLogger(__name__)


def setup_metrics(app: FastAPI) -> None:
    """
    Подключает prometheus-метрики и маршрут /metrics.
    """
    # Свой реестр на приложение: глобальный REGISTRY не даёт создать второе
    # приложение в одном процессе (DuplicateTimeseries).
    registry = CollectorRegistry()
    ProcessCollector(registry=registry)
    GCCollector(registry=registry)
    PlatformCollector(registry=registry)
    Instrumentator(
        excluded_handlers=["/metrics", "/health"],
        should_instrument_requests_inprogress=False,
        inprogress_labels=True,
        registry=registry,
    ).add(
        metrics.default(
            latency_lowr_buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1,
                2.5,
            ),
            registry=registry,
        )
    ).instrument(app).expose(app)


def add_cors_middleware(app: FastAPI) -> None:
    """
    Добавляет CORS middleware к приложению FastAPI.
    """
    origins = ["http://localhost:5173", "https://tkp-pipeline.whatchlee.ru"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["retry-after"],
    )


async def log_requests(request: Request, call_next: Callable) -> None:
    """
    Middleware для логирования HTTP-запросов.
    """
    start_time = time()
    response = await call_next(request)
    process_time = time() - start_time
    logger.info(
        f'"{request.method} {request.url.path}'
        f' HTTP/{request.scope["http_version"]}" '
        f'"from {getattr(request.client, "host", "unknown")} '
        f'"status - {response.status_code} time - {process_time:.3f}s"'
    )
    return response


def setup_middlewares(app: FastAPI) -> None:
    """
    Настраивает все middleware для приложения.
    """
    setup_metrics(app)
    add_cors_middleware(app)
    app.middleware("http")(log_requests)
