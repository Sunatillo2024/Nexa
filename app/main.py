import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import socketio

# Local imports
from app.core.config import settings
from app.db.session import init_db, get_db
from app.api.routes import auth, calls, sessions, users
from app.services.session_manager import session_manager

# ─────────────────────────────
# Socket.IO setup
# ─────────────────────────────
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio)

# ─────────────────────────────
# Logging
# ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("nexa-call")


# ─────────────────────────────
# Lifespan (startup/shutdown)
# ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Nexa Call API...")
    init_db()
    logger.info("✅ Database initialized")

    async def cleanup_task():
        while True:
            await asyncio.sleep(60)
            session_manager.cleanup_expired_sessions(timeout_minutes=5)

    cleanup = asyncio.create_task(cleanup_task())
    yield
    cleanup.cancel()
    logger.info("👋 Shutting down Nexa Call...")


# ─────────────────────────────
# FastAPI application
# ─────────────────────────────
app = FastAPI(
    title="Nexa Call - Audio Calling Platform",
    version="2.0.0",
    description="Real-time audio calling system with WebRTC and Socket.IO",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO
app.mount("/socket.io", socket_app)

# ─────────────────────────────
# Include routers (REST APIs)
# ─────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(users.router, prefix="/api")


# ─────────────────────────────
# Routes
# ─────────────────────────────
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Nexa Call - Audio Platform",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "socket_io": "/socket.io",
            "audio_client": "/audio-call",
            "health": "/health"
        }
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Database health check"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/audio-call", response_class=HTMLResponse)
async def audio_call_page():
    """Serve the WebRTC audio call HTML client"""
    with open("template/audio_call.html", "r") as f:
        return f.read()


# ─────────────────────────────
# Socket.IO event handlers
# ─────────────────────────────
@sio.event
async def connect(sid, environ):
    logger.info(f"User connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.info(f"User disconnected: {sid}")


@sio.event
async def offer(sid, data):
    logger.info(f"Offer received from {sid}")
    await sio.emit("offer", data, skip_sid=sid)


@sio.event
async def answer(sid, data):
    logger.info(f"Answer received from {sid}")
    await sio.emit("answer", data, skip_sid=sid)


@sio.event
async def candidate(sid, data):
    await sio.emit("candidate", data, skip_sid=sid)


# ─────────────────────────────
# Entry point
# ─────────────────────────────
if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Nexa Call Audio Platform...")
    logger.info("📡 Socket.IO signaling server enabled")
    logger.info("🎙️ WebRTC audio calls ready")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
