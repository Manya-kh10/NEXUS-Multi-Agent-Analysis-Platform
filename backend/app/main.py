# ==============================================================================
# TEAM EXPLANATION / ROOT CAUSE POST-MORTEM:
# A 404 manifests as a CORS error because the browser sends a preflight OPTIONS 
# request first. When FastAPI returns 404 for OPTIONS (no route match), the response 
# has no CORS headers. The browser interprets the missing headers as a CORS 
# violation and blocks the actual request before it even fires. The real bug is 
# the 404, not CORS.
# ==============================================================================

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

app = FastAPI(
    title="NEXUS API",
    version="3.0.0",
    redirect_slashes=False
)

# Step 1: CORS first, before everything else
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]
ALLOWED_ORIGINS += [
    "http://localhost:5173", 
    "http://localhost:3000",
    "https://nexus-multi-agent-analysis-platform.vercel.app",
    "https://nexus-multi-agent-analysis-platform-5nddujzap.vercel.app",
    "https://nexus-multi-agent-analysis-platform-9qtdz56i.vercel.app",
    "https://nexus-multi-agent-analysis-git-3e127b-manyas-projects-ee68bfc4.vercel.app",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Step 2: Explicit OPTIONS handler (nuclear option - catches everything)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return JSONResponse(content={}, status_code=200)

# Step 3: Debug route (keep until deployment confirmed working)
@app.get("/debug/routes")
async def debug_routes():
    return {"routes": [r.path for r in app.routes]}

# Step 4: Health check at root level (no prefix)
@app.get("/health")
@app.get("/api/health")
async def health():
    from app.database import engine
    from app.config import settings
    import redis
    import httpx
    
    postgres_status = "error"
    redis_status = "error"
    groq_status = "error"
    
    # Check PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        postgres_status = "ok"
    except Exception:
        pass

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        redis_status = "ok"
    except Exception:
        pass

    # Check Groq
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            res = await client.get("https://api.groq.com")
            groq_status = "ok" if res.status_code < 500 else "degraded"
    except Exception:
        pass
        
    status_overall = "healthy" if (postgres_status == "ok" and redis_status == "ok") else "degraded"
    
    return {
        "status": status_overall,
        "service": "NEXUS",
        "postgres": {
            "status": "healthy" if postgres_status == "ok" else "offline"
        },
        "redis": {
            "status": "healthy" if redis_status == "ok" else "offline"
        },
        "groq": {
            "status": "healthy" if groq_status == "ok" else "offline"
        },
        "components": {
            "postgres": postgres_status,
            "redis": redis_status,
            "groq": groq_status
        }
    }

# Step 5: Include all routers AFTER middleware
from app.routers import pipeline, agents, tasks, history, chat, health as health_router, ml, report, auth
from app.middleware import LoggingMiddleware, FileSizeMiddleware

app.add_middleware(LoggingMiddleware)
app.add_middleware(FileSizeMiddleware)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(health_router.router, prefix="/api/health", tags=["health"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
app.include_router(report.router, prefix="/api/report", tags=["report"])