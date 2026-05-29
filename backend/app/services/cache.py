import redis
import json
import hashlib
import logging
from app.config import settings

logger = logging.getLogger("nexus.cache")
redis_client = redis.from_url(settings.redis_url)
CACHE_TTL = 3600  # 1 hour

def get_cache_key(csv_data: str) -> str:
    return f"nexus:analysis:{hashlib.md5(csv_data.encode()).hexdigest()}"

def get_cached_result(csv_data: str):
    try:
        key = get_cache_key(csv_data)
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except redis.RedisError as e:
        logger.warning(f"Redis cache read error: {e}")
    return None

def set_cached_result(csv_data: str, result: dict):
    try:
        key = get_cache_key(csv_data)
        redis_client.setex(key, CACHE_TTL, json.dumps(result))
    except redis.RedisError as e:
        logger.warning(f"Redis cache write error: {e}")

def clear_cache():
    try:
        keys = redis_client.keys("nexus:analysis:*")
        if keys:
            redis_client.delete(*keys)
        return len(keys)
    except redis.RedisError as e:
        logger.warning(f"Redis cache clear error: {e}")
        return 0