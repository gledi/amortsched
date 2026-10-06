from redis.asyncio import Redis


class RedisRateLimiter:
    """Fixed-window counter shared across processes."""

    def __init__(self, client: Redis, prefix: str = "ratelimit:") -> None:
        self._client: Redis = client
        self._prefix: str = prefix

    async def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        redis_key = f"{self._prefix}{key}"
        async with self._client.pipeline(transaction=True) as pipe:
            _ = pipe.incr(redis_key)
            _ = pipe.expire(redis_key, window_seconds, nx=True)
            _ = pipe.ttl(redis_key)
            count, _, ttl = await pipe.execute()  # pyright: ignore[reportAny]
        if int(count) > limit:  # pyright: ignore[reportAny]
            return max(1, int(ttl))  # pyright: ignore[reportAny]
        return None
