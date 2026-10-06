import asyncio
import math
import time
from collections.abc import Callable


class InMemoryRateLimiter:
    """Fixed-window counter for a single process."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock: Callable[[], float] = clock
        self._windows: dict[str, tuple[float, int]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        async with self._lock:
            current = self._clock()
            started, count = self._windows.get(key, (current, 0))
            if current - started >= window_seconds:
                started, count = current, 0
            count += 1
            self._windows[key] = (started, count)
            if count > limit:
                return max(1, math.ceil(started + window_seconds - current))
            return None
