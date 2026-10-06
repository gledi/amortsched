import pytest
from redis.asyncio import Redis
from testcontainers.community.redis import RedisContainer

from amortsched.adapters.ratelimit.redis import RedisRateLimiter


@pytest.fixture(scope="module")
def redis_url():
    with RedisContainer("redis:8.10-alpine") as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest.mark.anyio
async def test_redis_limiter_counts_within_window_and_keeps_expiry(redis_url):
    client = Redis.from_url(redis_url)
    try:
        limiter = RedisRateLimiter(client, prefix="test:")
        assert await limiter.hit("k", limit=2, window_seconds=60) is None
        assert await limiter.hit("k", limit=2, window_seconds=60) is None
        retry_after = await limiter.hit("k", limit=2, window_seconds=60)
        assert retry_after is not None and 0 < retry_after <= 60
        assert 0 < await client.ttl("test:k") <= 60
        assert await limiter.hit("other", limit=2, window_seconds=60) is None
    finally:
        await client.aclose()
