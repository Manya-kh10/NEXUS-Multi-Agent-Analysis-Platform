from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import pipeline, agents, tasks, history, chat, health, ml, report, auth
from app.middleware import LoggingMiddleware, FileSizeMiddleware

app = FastAPI(title="NEXUS API", version="3.0.0")

# CORS Middleware (First operation after app initialization)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nexus-multi-agent-analysis-platform-5nddujzap.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Other Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(FileSizeMiddleware)

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