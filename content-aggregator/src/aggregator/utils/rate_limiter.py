import asyncio
import time
from urllib.parse import urlparse


class RateLimiter:
    """Per-domain token bucket rate limiter."""

    def __init__(self, calls_per_second: float = 1.0) -> None:
        self._interval = 1.0 / calls_per_second
        self._last_call: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc or url

    async def acquire(self, url: str) -> None:
        domain = self._domain(url)
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        async with self._locks[domain]:
            last = self._last_call.get(domain, 0.0)
            wait = self._interval - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call[domain] = time.monotonic()
