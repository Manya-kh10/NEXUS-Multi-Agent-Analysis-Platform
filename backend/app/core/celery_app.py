from celery import Celery
import os
import ssl

# Dynamically resolve REDIS_URL from environment or default to local development instance
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Render secure Redis (rediss://) needs ssl_cert_reqs=none to trust self-signed certs
if redis_url.startswith("rediss://") and "ssl_cert_reqs" not in redis_url:
    if "?" in redis_url:
        redis_url += "&ssl_cert_reqs=none"
    else:
        redis_url += "?ssl_cert_reqs=none"

celery_app = Celery(
    "nexus",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks"]
)

# Standardize Celery configuration settings for cloud production environments
ssl_options = None
if redis_url.startswith("rediss://"):
    ssl_options = {
        "ssl_cert_reqs": ssl.CERT_NONE
    }

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl=ssl_options,
    redis_backend_use_ssl=ssl_options,
    broker_transport_options={
        "visibility_timeout": 3600,
        "socket_keepalive": True,
        "retry_on_timeout": True
    },
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0
        }
    }
)
