import redis
from app.core.config import settings

try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
    redis_client.ping()
except Exception as e:
    print(f"Redis connection failed: {e}. Running without Redis.")
    redis_client = None


def get_redis():
    return redis_client

