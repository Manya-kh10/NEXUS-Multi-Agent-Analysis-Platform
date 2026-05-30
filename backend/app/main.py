# ==============================================================================
# TEAM EXPLANATION / ROOT CAUSE POST-MORTEM:
# A 404 manifests as a CORS error because the browser sends a preflight OPTIONS 
# request first. When FastAPI returns 404 for OPTIONS (no route match), the response 
# has no CORS headers. The browser interprets the missing headers as a CORS 
# violation and blocks the actual request before it even fires. The real bug is 
# the 404, not CORS.
# ==============================================================================

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
import os
from contextlib import asynccontextmanager
from app.config import settings
from app.services.storage_service import initialize_storage
from alembic.config import Config
from alembic import command
import logging

logger = logging.getLogger("nexus.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== NEXUS STARTUP INITIALIZATION & VALIDATION ===")
    
    # 1. Environment & Config Validation
    logger.info("Verifying environment configurations...")
    if not settings.database_url:
        logger.error("CRITICAL CONFIGURATION ERROR: DATABASE_URL is missing!")
    elif not ("postgresql" in settings.database_url or "postgres" in settings.database_url):
        logger.warning(f"DATABASE_URL does not specify standard postgresql driver: {settings.database_url}")
        
    if not settings.redis_url:
        logger.warning("REDIS_URL environment variable is missing! Caching and task queues will be disabled.")
        
    # Check Supabase keys
    from app.services.storage_service import get_supabase_key, is_supabase_enabled
    supabase_key = get_supabase_key()
    if not settings.supabase_url:
        logger.warning("SUPABASE_URL is missing. Falling back to persistent local volume storage.")
    elif not supabase_key:
        logger.warning("Supabase authentication keys (anon/service-role) are missing. Falling back to local storage.")
    else:
        logger.info(f"Supabase credentials configured. Bucket: {settings.supabase_bucket}")

    # 2. Programmatic database migrations
    try:
        logger.info("Running pending database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed.")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)

    # 3. PostgreSQL Connectivity Validation
    logger.info("Verifying PostgreSQL database connection...")
    try:
        from app.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL database connection successfully validated.")
    except Exception as e:
        logger.warning(f"PostgreSQL database connection failed: {e}")

    # 4. Redis Connectivity Validation
    if settings.redis_url:
        logger.info("Verifying Redis connection...")
        try:
            import redis
            r = redis.from_url(settings.redis_url, socket_timeout=3)
            r.ping()
            logger.info("Redis server connection successfully validated.")
        except Exception as e:
            logger.warning(f"Redis server connection failed: {e}. Asynchronous queueing and cache features may be degraded.")
    else:
        logger.warning("Skipping Redis connection validation because REDIS_URL is missing.")

    # 5. Initialize Storage buckets/directories
    logger.info("Initializing storage systems...")
    try:
        await initialize_storage()
        logger.info("Storage initialization completed.")
    except Exception as e:
        logger.warning(f"Storage systems initialization failed: {e}. Falling back to default filesystem paths.")

    logger.info("=== NEXUS SYSTEM READY ===")
    yield

app = FastAPI(
    title="NEXUS API",
    version="3.0.0",
    redirect_slashes=False,
    lifespan=lifespan
)

def make_cors_error_response(request: Request, content: dict, status_code: int) -> JSONResponse:
    response = JSONResponse(content=jsonable_encoder(content), status_code=status_code)
    
    # Standardize CORS response injection
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
        
    return response

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled backend exception occurred: {exc}")
    return make_cors_error_response(
        request=request,
        content={"detail": "Internal Server Error", "message": str(exc)},
        status_code=500
    )

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException raised: {exc.status_code} - {exc.detail}")
    return make_cors_error_response(
        request=request,
        content={"detail": exc.detail},
        status_code=exc.status_code
    )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    logger.error(f"RequestValidationError raised: {exc.errors()}")
    return make_cors_error_response(
        request=request,
        content={"detail": "Validation error", "errors": exc.errors()},
        status_code=422
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

@app.get("/debug/config")
async def debug_config():
    from app.config import settings
    
    redis_masked = settings.redis_url
    if "@" in redis_masked:
        parts = redis_masked.split("@", 1)
        scheme_and_user = parts[0].split(":", 2)
        redis_masked = f"{scheme_and_user[0]}://****:****@{parts[1]}"
        
    db_masked = settings.database_url
    if "@" in db_masked:
        parts = db_masked.split("@", 1)
        scheme_and_user = parts[0].split(":", 2)
        db_masked = f"{scheme_and_user[0]}://****:****@{parts[1]}"
        
    return {
        "redis_url_masked": redis_masked,
        "database_url_masked": db_masked,
        "supabase_url": settings.supabase_url,
        "supabase_bucket": settings.supabase_bucket,
        "has_groq_key": bool(settings.groq_api_key)
    }

@app.get("/debug/celery")
async def debug_celery():
    from app.core.celery_app import celery_app
    try:
        insp = celery_app.control.inspect(timeout=5.0)
        return {
            "ping": insp.ping(),
            "active": insp.active(),
            "reserved": insp.reserved(),
            "registered": insp.registered(),
            "stats": insp.stats()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/analyses")
async def debug_analyses():
    from app.database import AsyncSessionLocal
    from app.models.analysis import Analysis
    from sqlalchemy import select
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Analysis).order_by(Analysis.created_at.desc()).limit(15)
            res = await db.execute(stmt)
            analyses = res.scalars().all()
            return [
                {
                    "id": a.id,
                    "task_id": a.task_id,
                    "filename": a.filename,
                    "status": a.status,
                    "original_rows": a.original_rows,
                    "original_cols": a.original_cols,
                    "cached": a.cached,
                    "created_at": str(a.created_at),
                    "completed_at": str(a.completed_at)
                }
                for a in analyses
            ]
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/celery-log")
async def debug_celery_log():
    log_path = "/app/celery_startup.log"
    if not os.path.exists(log_path):
        log_path = "celery_startup.log"
    if not os.path.exists(log_path):
        return {"error": f"Log file not found at {os.path.abspath(log_path)} or /app/celery_startup.log."}
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
        return {"log_path": os.path.abspath(log_path), "lines": lines[-150:]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/task-state/{task_id}")
async def debug_task_state(task_id: str):
    from celery.result import AsyncResult
    task = AsyncResult(task_id)
    try:
        state = task.state
        info_type = str(type(task.info))
        info_str = str(task.info)
        result_type = str(type(task.result))
        result_str = str(task.result)
        return {
            "task_id": task_id,
            "state": state,
            "info_type": info_type,
            "info_str": info_str,
            "result_type": result_type,
            "result_str": result_str
        }
    except Exception as e:
        return {"error": str(e)}


# Step 3.5: Root GET and HEAD for Render Health Check
@app.get("/")
async def root():
    return {"status": "ok"}

@app.head("/")
async def root_head():
    return {}

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

@app.get("/health/redis")
async def health_redis():
    import redis
    try:
        r = redis.from_url(settings.redis_url, socket_timeout=3)
        r.ping()
        return {"status": "healthy", "redis": "online"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {str(e)}")

@app.get("/health/celery")
async def health_celery():
    from app.core.celery_app import celery_app
    try:
        insp = celery_app.control.inspect(timeout=1.0)
        ping_res = insp.ping()
        if not ping_res:
            raise HTTPException(status_code=503, detail="No active Celery workers found.")
        return {"status": "healthy", "workers": ping_res}
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Celery inspection failed: {str(e)}")

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