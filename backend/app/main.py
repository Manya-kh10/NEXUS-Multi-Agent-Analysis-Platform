from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import pipeline, agents, tasks, history, chat, health, ml, report, auth
from app.middleware import LoggingMiddleware, FileSizeMiddleware

app = FastAPI(title="NEXUS API", version="3.0.0")

# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(FileSizeMiddleware)

import os
origins = [
    "http://localhost",
    "http://localhost:8501",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8000",
    "https://nexus-multi-agent-intelligence-analysis-platform.vercel.app",
    "https://nexus-multi-agent-analysis-platform-lsdgvx4t6.vercel.app"
]

frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

# Strip '*' to prevent FastAPI exceptions when allow_credentials=True
if "*" in origins:
    origins.remove("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="https://.*\\.vercel\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
app.include_router(report.router, prefix="/api/report", tags=["report"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "NEXUS", "version": "3.0.0"}