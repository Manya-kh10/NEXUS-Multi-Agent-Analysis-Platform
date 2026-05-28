from fastapi import APIRouter
from app.database import engine
from app.config import settings
import redis
import httpx

router = APIRouter()

@router.get("/")
async def health_check():
    status = {
        "service": "NEXUS",
        "version": "2.0.0",
        "status": "ok",
        "components": {}
    }

    # Check PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        status["components"]["postgres"] = "ok"
    except Exception as e:
        status["components"]["postgres"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        status["components"]["redis"] = "ok"
    except Exception as e:
        status["components"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check Groq
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get("https://api.groq.com")
            status["components"]["groq"] = "ok" if res.status_code < 500 else "degraded"
    except Exception:
        status["components"]["groq"] = "unreachable"

    return status