from celery import Celery
import os

# Dynamically resolve REDIS_URL from environment or default to local development instance
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "nexus",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks"]
)

# Standardize Celery configuration settings for cloud production environments
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
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
