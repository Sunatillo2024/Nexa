import logging

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from contextlib import asynccontextmanager
from .redis_client import redis_client
from . import models, schemas, crud, auth
from .database import get_db, init_db
from .config import settings
from .webrtc import webrtc_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Nexa Call API...")
    init_db()
    print("✅ Database initialized")
    yield
    print("👋 Shutting down...")
    redis_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        existing_user = crud.get_user_by_username(db, user.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        existing_email = crud.get_user_by_email(db, user.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        db_user = crud.create_user(db, user)
        return db_user

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Registration error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/api/auth/login", response_model=schemas.Token)
def login(user_login: schemas.UserLogin, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_current_user_info(
        user_id: str = Depends(auth.verify_token),
        db: Session = Depends(get_db)
):
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/api/calls/start", response_model=schemas.CallResponse)
def start_call(
        call: schemas.CallStart,
        db: Session = Depends(get_db),
        user_id: str = Depends(auth.verify_token)
):
    rate_limit_key = f"call_start:{user_id}"
    if not redis_client.check_rate_limit(
            rate_limit_key,
            settings.RATE_LIMIT_CALLS,
            settings.RATE_LIMIT_WINDOW
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many call attempts. Please wait."
        )

    caller = crud.get_user_by_id(db, call.caller_id)
    if not caller:
        raise HTTPException(status_code=404, detail="Caller not found")

    receiver = crud.get_user_by_id(db, call.receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    receiver_status = redis_client.get_user_status(call.receiver_id)
    if receiver_status.get("status") != "online":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receiver is not online"
        )

    webrtc_channel = webrtc_manager.create_channel(call.caller_id, call.receiver_id)

    db_call = crud.create_call(db, call, webrtc_channel)

    return schemas.CallResponse(
        call_id=db_call.id,
        status=db_call.status.value,
        webrtc_channel=db_call.webrtc_channel,
        caller_id=db_call.caller_id,
        receiver_id=db_call.receiver_id,
        started_at=db_call.started_at
    )


@app.post("/api/calls/end", response_model=schemas.CallEndResponse)
def end_call(
        call_end: schemas.CallEnd,
        db: Session = Depends(get_db),
        user_id: str = Depends(auth.verify_token)
):
    db_call = crud.get_call_by_id(db, call_end.call_id)

    if not db_call:
        raise HTTPException(status_code=404, detail="Call not found")

    if user_id not in [db_call.caller_id, db_call.receiver_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not part of this call"
        )

    db_call = crud.end_call(db, call_end.call_id)

    if not db_call:
        raise HTTPException(status_code=400, detail="Call already ended")

    if db_call.ended_at and db_call.started_at:
        duration = db_call.ended_at - db_call.started_at
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    else:
        duration_str = "00:00:00"

    webrtc_manager.close_channel(db_call.webrtc_channel)

    return schemas.CallEndResponse(
        status="ended",
        duration=duration_str,
        ended_at=db_call.ended_at
    )


@app.get("/api/calls/active", response_model=list[schemas.ActiveCall])
def get_active_calls(
        db: Session = Depends(get_db),
        user_id: str = Depends(auth.verify_token)
):
    active_calls = crud.get_active_calls(db, user_id)
    return [
        schemas.ActiveCall(
            call_id=call.id,
            caller_id=call.caller_id,
            receiver_id=call.receiver_id,
            started_at=call.started_at,
            webrtc_channel=call.webrtc_channel,
            status=call.status.value
        )
        for call in active_calls
    ]


@app.get("/api/calls/history")
def get_call_history(
        limit: int = 50,
        offset: int = 0,
        db: Session = Depends(get_db),
        user_id: str = Depends(auth.verify_token)
):
    calls = crud.get_user_call_history(db, user_id, limit, offset)
    return {
        "calls": [
            {
                "call_id": call.id,
                "caller_id": call.caller_id,
                "receiver_id": call.receiver_id,
                "started_at": call.started_at,
                "ended_at": call.ended_at,
                "status": call.status.value,
                "duration": str(call.ended_at - call.started_at) if call.ended_at else None
            }
            for call in calls
        ],
        "total": len(calls),
        "limit": limit,
        "offset": offset
    }


@app.post("/api/presence/update")
def update_presence(
        status: str,
        db: Session = Depends(get_db),
        user_id: str = Depends(auth.verify_token)
):
    valid_statuses = ["online", "offline", "away"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {', '.join(valid_statuses)}"
        )

    presence_status = models.PresenceStatus(status)
    presence = crud.update_user_presence(db, user_id, presence_status)

    if status == "online":
        redis_client.set_user_online(user_id)
    else:
        redis_client.set_user_offline(user_id)

    return {
        "status": "success",
        "user_status": presence.status.value,
        "last_seen": presence.last_seen
    }


@app.get("/api/presence/{target_user_id}")
def get_presence(
        target_user_id: str,
        db: Session = Depends(get_db),
        user_id: str = Depends(auth.verify_token)
):
    redis_status = redis_client.get_user_status(target_user_id)
    if redis_status.get("status") == "online":
        return redis_status

    presence = crud.get_user_presence(db, target_user_id)
    if not presence:
        return {"status": "offline", "last_seen": None}

    return {
        "status": presence.status.value,
        "last_seen": presence.last_seen
    }


@app.get("/api/presence/online/list")
def get_online_users(
        db: Session = Depends(get_db),
        user_id: str = Depends(auth.verify_token)
):
    online_users = crud.get_online_users(db)
    return {
        "online_users": [
            {
                "user_id": presence.user_id,
                "status": presence.status.value,
                "last_seen": presence.last_seen
            }
            for presence in online_users
        ],
        "count": len(online_users)
    }


@app.post("/api/webrtc/signal")
def send_webrtc_signal(
        signal: schemas.WebRTCSignal,
        user_id: str = Depends(auth.verify_token)
):
    success = redis_client.store_webrtc_signal(signal.call_id, {
        "type": signal.signal_type,
        "data": signal.signal_data,
        "from": user_id,
        "timestamp": datetime.utcnow().isoformat()
    })

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to store signaling data"
        )

    return {"status": "success"}


@app.get("/api/webrtc/signal/{call_id}")
def get_webrtc_signals(
        call_id: str,
        user_id: str = Depends(auth.verify_token)
):
    signals = redis_client.get_webrtc_signals(call_id)
    return {"signals": signals}


@app.get("/health", response_model=schemas.HealthCheck)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis
    redis_status = "healthy" if redis_client.is_connected() else "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow(),
        "database": db_status,
        "redis": redis_status
    }


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.utcnow().isoformat()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        },
    )


@app.get("/debug/users")
def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to check users table"""
    try:
        users = db.query(models.User).all()
        return {
            "total_users": len(users),
            "users": [{"id": u.id, "username": u.username} for u in users]
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.DEBUG)
