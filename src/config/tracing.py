import logging
import os
from abc import ABC, abstractmethod

from config import TempoSettings
from config.registry import settings


logger = logging.getLogger(__name__)


class Instrumentor(ABC):
    name: str

    def enabled(self, cfg: TempoSettings) -> bool:
        return True

    @abstractmethod
    def instrument(self, cfg: TempoSettings) -> None: ...


class FastAPIInstrumentor(Instrumentor):
    name = "fastapi"

    def instrument(self, cfg: TempoSettings) -> None:
        from opentelemetry.instrumentation.fastapi import (
            FastAPIInstrumentor as _Instrumentor,
        )

        _Instrumentor().instrument(
            excluded_urls=cfg.otel_python_fastapi_excluded_urls,
            exclude_spans=["receive", "send"],
        )


class HTTPXInstrumentor(Instrumentor):
    name = "httpx"

    def instrument(self, cfg: TempoSettings) -> None:
        from opentelemetry.instrumentation.httpx import (
            HTTPXClientInstrumentor as _Instrumentor,
        )

        _Instrumentor().instrument()


INSTRUMENTORS: tuple[Instrumentor, ...] = (
    FastAPIInstrumentor(),
    HTTPXInstrumentor(),
)


def _export_env(cfg: TempoSettings) -> None:
    """
    SDK читает настройки из os.environ,
    а pydantic кладёт env только в свой объект.
    """
    for key, value in cfg.model_dump().items():
        os.environ[key.upper()] = str(value)


def setup_tracing() -> None:
    cfg = settings.tempo
    if cfg.otel_sdk_disabled:
        return

    try:
        _export_env(cfg)

        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create())

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
    except (ImportError, ValueError):
        # ImportError - не установлены пакеты opentelemetry-*,
        # ValueError - некорректное значение OTEL_*
        # (например, таймаут или sampler arg)
        logger.exception("Трассировка не запущена, сервис работает без неё %s")

    for instrumentor in INSTRUMENTORS:
        if not instrumentor.enabled(cfg):
            continue
        try:
            instrumentor.instrument(cfg)
            logger.info("Трассировка: %s подключён", instrumentor.name)
        except (ImportError, TypeError):
            # ImportError - нет пакета инструментации,
            # TypeError - версия пакета не поддерживает переданный параметр
            logger.exception("Трассировка: %s не подключён", instrumentor.name)
