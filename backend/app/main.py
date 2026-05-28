from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import pipeline, agents, tasks, history, chat, health, ml, report, auth
from app.middleware import LoggingMiddleware, FileSizeMiddleware

# Standardized Routing Configuration (redirect_slashes=True set explicitly)
app = FastAPI(title="NEXUS API", version="3.0.0", redirect_slashes=True)

# CORS Middleware (First operation after app initialization)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nexus-multi-agent-analysis-platform-5nddujzap.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Other Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(FileSizeMiddleware)

# Root Path Handler
@app.get("/")
async def root_path():
    return {"status": "online"}

# Routers (All requests cleanly map under /api prefix)
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
app.include_router(report.router, prefix="/api/report", tags=["report"])

# Explicit OPTIONS Handler for CORS Preflight Requests
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return {}
@app.get("/debug/routes")
async def get_routes():
    return [{"path": route.path, "name": route.name} for route in app.routes]