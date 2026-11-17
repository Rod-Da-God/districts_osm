import asyncio
import logging
from datetime import datetime

from external.overpass.config import overpass_settings


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Простой rate limiter для Overpass API.

    Один общий лимитер на процесс: перед каждым запросом ждёт,
    пока не пройдёт минимальный интервал между запросами.
    """

    def __init__(self, rps: float | None = None) -> None:
        """
        Args:
            rps: запросов в секунду (requests per second).
                По умолчанию берётся OVERPASS_RPS_LIMIT.
        """
        self._rps = (
            rps if rps is not None else overpass_settings.overpass_rps_limit
        )
        if self._rps <= 0:
            raise ValueError("rps must be greater than zero")
        self._min_interval = 1.0 / self._rps
        self._last_request: datetime | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Ждать перед следующим запросом если нужно."""
        async with self._lock:
            if self._last_request is not None:
                elapsed = (datetime.now() - self._last_request).total_seconds()
                wait_time = self._min_interval - elapsed
                if wait_time > 0:
                    logger.debug("Rate limit: ожидание %.2f сек", wait_time)
                    await asyncio.sleep(wait_time)

            self._last_request = datetime.now()


rate_limiter = RateLimiter()
