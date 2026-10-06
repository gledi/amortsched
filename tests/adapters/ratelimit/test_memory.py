import pytest

from amortsched.adapters.ratelimit.memory import InMemoryRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.anyio
async def test_allows_up_to_limit_then_reports_retry_after():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)

    assert [await limiter.hit("k", limit=2, window_seconds=60) for _ in range(2)] == [None, None]
    clock.now += 15
    assert await limiter.hit("k", limit=2, window_seconds=60) == 45


@pytest.mark.anyio
async def test_window_resets_and_keys_are_independent():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)

    assert await limiter.hit("a", limit=1, window_seconds=10) is None
    assert await limiter.hit("a", limit=1, window_seconds=10) == 10
    assert await limiter.hit("b", limit=1, window_seconds=10) is None

    clock.now += 10
    assert await limiter.hit("a", limit=1, window_seconds=10) is None
