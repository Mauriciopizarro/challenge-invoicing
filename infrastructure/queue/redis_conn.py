from redis import Redis

from config import settings


def build_redis_connection() -> Redis:
    # RQ requires the synchronous redis client (not redis.asyncio).
    return Redis.from_url(settings.REDIS_URL)
