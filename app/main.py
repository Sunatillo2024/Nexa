from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import text  # Добавляем импорт text

from .core.config import settings
from .db.session import init_db, get_db
from .api.routes import auth, calls
from .api import routes as api_routes
from .api.websocket import websocket_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("🚀 Starting Nexa Call API...")
    init_db()
    print("✅ Database initialized")

    # Import here to avoid circular imports
    from .services.session_manager import session_manager

    # Cleanup task for expired sessions
    import asyncio
    async def cleanup_task():
        while True:
            await asyncio.sleep(60)  # Every minute
            session_manager.cleanup_expired_sessions(timeout_minutes=5)

    cleanup = asyncio.create_task(cleanup_task())

    yield

    cleanup.cancel()
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(calls.router, prefix="/api")

# Import sessions router
from .api.routes import sessions

app.include_router(sessions.router, prefix="/api")

# WebSocket endpoint
app.add_api_websocket_route("/ws/{user_id}", websocket_endpoint)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # ИСПРАВЛЕНО: используем text() для сырого SQL
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.DEBUG)