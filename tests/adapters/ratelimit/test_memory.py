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


@pytest.mark.anyio
async def test_tracked_keys_stay_bounded():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock, max_keys=100)

    for index in range(1000):
        await limiter.hit(f"key-{index}", limit=5, window_seconds=60)

    assert len(limiter) <= 100


@pytest.mark.anyio
async def test_expired_windows_are_dropped_before_live_ones():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock, max_keys=3)
    await limiter.hit("live", limit=1, window_seconds=600)
    await limiter.hit("stale-1", limit=1, window_seconds=10)
    await limiter.hit("stale-2", limit=1, window_seconds=10)
    clock.now += 20

    await limiter.hit("new", limit=1, window_seconds=10)

    assert await limiter.hit("live", limit=1, window_seconds=600) is not None
