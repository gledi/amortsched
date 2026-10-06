import asyncio
import math
import time
from collections.abc import Callable


class InMemoryRateLimiter:
    """Fixed-window counter for a single process, with a bounded number of tracked keys."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 10_000) -> None:
        self._clock: Callable[[], float] = clock
        self._max_keys: int = max_keys
        self._windows: dict[str, tuple[float, int, int]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    def _prune(self, current: float) -> None:
        self._windows = {key: window for key, window in self._windows.items() if current - window[0] < window[2]}
        if len(self._windows) >= self._max_keys:
            newest = sorted(self._windows.items(), key=lambda item: item[1][0])[len(self._windows) // 2 :]
            self._windows = dict(newest)

    async def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        async with self._lock:
            current = self._clock()
            if key not in self._windows and len(self._windows) >= self._max_keys:
                self._prune(current)
            started, count, _ = self._windows.get(key, (current, 0, window_seconds))
            if current - started >= window_seconds:
                started, count = current, 0
            count += 1
            self._windows[key] = (started, count, window_seconds)
            if count > limit:
                return max(1, math.ceil(started + window_seconds - current))
            return None

    def __len__(self) -> int:
        return len(self._windows)
