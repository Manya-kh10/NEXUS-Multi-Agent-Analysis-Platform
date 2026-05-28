import redis
import json
import hashlib
from app.config import settings

redis_client = redis.from_url(settings.redis_url)
CACHE_TTL = 3600  # 1 hour

def get_cache_key(csv_data: str) -> str:
    return f"nexus:analysis:{hashlib.md5(csv_data.encode()).hexdigest()}"

def get_cached_result(csv_data: str):
    key = get_cache_key(csv_data)
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None

def set_cached_result(csv_data: str, result: dict):
    key = get_cache_key(csv_data)
    redis_client.setex(key, CACHE_TTL, json.dumps(result))

def clear_cache():
    keys = redis_client.keys("nexus:analysis:*")
    if keys:
        redis_client.delete(*keys)
    return len(keys)