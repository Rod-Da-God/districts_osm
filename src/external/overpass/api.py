from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, cast

import httpx
from httpx import AsyncClient, ConnectError, HTTPError, TimeoutException

from .config import overpass_settings


logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def api_endpoint(
    path: str, method: str = "POST"
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Декоратор для методов OverpassApiClient.

    - не создаёт клиент
    - проверяет init()
    - делает HTTP запрос
    - передает json-ответ в метод через data=
    - повторяет запрос при таймауте/сетевой ошибке/5xx
    - логирует и пробрасывает ошибки
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not args:
                raise RuntimeError("api_endpoint expects bound method")

            self_obj = args[0]
            client = getattr(self_obj, "_client", None)
            base_url: str | None = getattr(self_obj, "_base_url", None)
            if client is None or base_url is None:
                raise RuntimeError(
                    f"{self_obj.__class__.__name__} not initialized:"
                    " call init() first"
                )

            url = base_url.rstrip("/") + path

            # Извлекаем query из kwargs и формируем form data.
            # Делаем это один раз: на повторных попытках kwargs те же.
            query_str = kwargs.pop("query", None)

            attempts = max(1, overpass_settings.overpass_retry_attempts)
            backoff = overpass_settings.overpass_retry_backoff_s
            last_error: Exception | None = None

            for attempt in range(1, attempts + 1):
                try:
                    logger.debug(
                        "HTTP %s %s (попытка %d/%d)",
                        method.upper(),
                        url,
                        attempt,
                        attempts,
                    )

                    if query_str:
                        # Overpass API ожидает query в form data
                        resp = await client.post(url, data={"data": query_str})
                    else:
                        resp = await client.request(
                            method.upper(), url, **kwargs
                        )

                    resp.raise_for_status()
                    data = resp.json()

                    logger.debug(
                        "HTTP %s %s -> %s",
                        method.upper(),
                        url,
                        resp.status_code,
                    )
                    # ВАЖНО: передаём query обратно в метод вместе с data
                    caller = cast(Callable[..., Awaitable[R]], fn)
                    return await caller(*args, query=query_str, data=data)

                except (TimeoutException, ConnectError) as e:
                    last_error = e
                    logger.warning(
                        "Overpass connection/timeout error"
                        " (попытка %d/%d): %s",
                        attempt,
                        attempts,
                        e,
                    )

                except HTTPError as e:
                    last_error = e
                    response = getattr(e, "response", None)
                    status = getattr(response, "status_code", None)
                    body = getattr(response, "text", "")
                    logger.warning(
                        "Overpass HTTP error (попытка %d/%d):"
                        " %s %s -> status=%s body=%s err=%s",
                        attempt,
                        attempts,
                        method,
                        url,
                        status,
                        body[:500],
                        e,
                    )
                    # 4xx повторять бессмысленно, 5xx — можно
                    if status is None or status < 500:
                        raise

                if attempt < attempts:
                    delay = backoff * (2 ** (attempt - 1))
                    if delay > 0:
                        logger.info(
                            "Повтор запроса к Overpass через %.1f сек", delay
                        )
                        await asyncio.sleep(delay)

            if last_error is None:
                raise RuntimeError("Overpass request failed without error")
            logger.exception("Overpass request failed: %s", last_error)
            raise last_error

        return cast(Callable[P, Awaitable[R]], wrapper)

    return decorator


class OverpassApiClient:
    """
    Реальный HTTP-клиент Overpass API.

    Отвечает за:
    - управление AsyncClient (init/close)
    - выполнение запросов к /api/interpreter
    - обработку ошибок и повторные попытки
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        self._base_url = base_url or overpass_settings.overpass_base_url
        self._timeout_s = timeout_s or overpass_settings.overpass_timeout_s

        self._client: AsyncClient | None = None

    async def init(self) -> None:
        if self._client is not None:
            logger.warning(
                "OverpassApiClient.init() called but already initialized"
            )
            return

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout_s),
            headers={"User-Agent": overpass_settings.overpass_user_agent},
        )
        logger.info(
            "OverpassApiClient initialized: base_url=%s timeout=%s",
            self._base_url,
            self._timeout_s,
        )

    async def close(self) -> None:
        if self._client is None:
            logger.warning(
                "OverpassApiClient.close() called but not initialized"
            )
            return
        await self._client.aclose()
        self._client = None
        logger.info("OverpassApiClient closed")

    @api_endpoint("/api/interpreter", method="POST")
    async def execute(self, *, query: str, data: Any = None) -> dict:
        """
        Выполнить Overpass QL запрос.

        query — строка overpass QL.
        Возвращает сырой JSON dict.
        """
        # Декоратор уже сделал request и передал data=resp.json()
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict from Overpass, got {type(data)}")
        return data
