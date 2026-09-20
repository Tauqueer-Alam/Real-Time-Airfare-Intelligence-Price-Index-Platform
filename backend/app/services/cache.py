import json
import os

import redis
from redis.exceptions import RedisError

SEARCH_CACHE_TTL_SECONDS = 60
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def build_search_cache_key(
    source: str,
    destination: str,
    page: int,
    limit: int,
    sort: str,
    order: str,
) -> str:
    return (
        f"flight-search:{source}:{destination}:page={page}:limit={limit}:"
        f"sort={sort}:order={order}"
    )


def get_cached_search_result(cache_key: str) -> dict | None:
    try:
        cached_value = redis_client.get(cache_key)
        return json.loads(cached_value) if cached_value else None
    except (RedisError, json.JSONDecodeError):
        return None


def cache_search_result(cache_key: str, result: dict) -> None:
    try:
        redis_client.set(cache_key, json.dumps(result), ex=SEARCH_CACHE_TTL_SECONDS)
    except RedisError:
        # Redis is an optional performance layer; PostgreSQL remains available.
        pass
