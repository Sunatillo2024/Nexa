from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import time

from starlette.responses import JSONResponse

from . import models, schemas, crud, database, webrtc, auth
from .database import engine

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nexa Call API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting storage (in-memory for MVP)
rate_limit_storage = {}


def rate_limit(key: str, limit: int = 10, window: int = 60):
    """Simple rate limiting"""
    current_time = time.time()
    window_start = current_time - window

    # Clean old entries
    rate_limit_storage[key] = [
        timestamp for timestamp in rate_limit_storage.get(key, [])
        if timestamp > window_start
    ]

    if len(rate_limit_storage[key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )

    rate_limit_storage[key].append(current_time)


@app.post("/api/calls/start", response_model=schemas.CallResponse)
def start_call(
        call: schemas.CallStart,
        db: Session = Depends(database.get_db),
        user_id: str = Depends(auth.verify_token)
):
    # Rate limiting
    rate_limit(f"start_call:{user_id}", limit=5, window=60)

    # Create WebRTC channel
    webrtc_channel = webrtc.webrtc_manager.create_channel(
        call.caller_id, call.receiver_id
    )

    # Create call in database
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
        db: Session = Depends(database.get_db),
        user_id: str = Depends(auth.verify_token)
):
    db_call = crud.end_call(db, call_end.call_id)

    if not db_call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Calculate duration
    if db_call.ended_at and db_call.started_at:
        duration = db_call.ended_at - db_call.started_at
        duration_str = str(duration)
    else:
        duration_str = "00:00:00"

    # Close WebRTC channel
    webrtc.webrtc_manager.close_channel(db_call.webrtc_channel)

    return schemas.CallEndResponse(
        status="ended",
        duration=duration_str
    )


@app.get("/api/calls/active", response_model=list[schemas.ActiveCall])
def get_active_calls(
        db: Session = Depends(database.get_db),
        user_id: str = Depends(auth.verify_token)
):
    active_calls = crud.get_active_calls(db)
    return [
        schemas.ActiveCall(
            call_id=call.id,
            caller_id=call.caller_id,
            receiver_id=call.receiver_id,
            started_at=call.started_at,
            webrtc_channel=call.webrtc_channel
        )
        for call in active_calls
    ]


@app.post("/api/presence/{user_id}/{status}")
def update_presence(
        user_id: str,
        status: str,
        db: Session = Depends(database.get_db),
        auth_user_id: str = Depends(auth.verify_token)
):
    if status not in ["online", "offline"]:
        raise HTTPException(status_code=400, detail="Status must be 'online' or 'offline'")

    presence = crud.update_user_presence(db, user_id, status)
    return {"status": "success", "user_status": presence.status}


@app.get("/api/presence/{user_id}")
def get_presence(
        user_id: str,
        db: Session = Depends(database.get_db),
        auth_user_id: str = Depends(auth.verify_token)
):
    presence = crud.get_user_presence(db, user_id)
    if not presence:
        return {"status": "offline"}
    return {"status": presence.status, "last_seen": presence.last_seen}


# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Error handling middleware
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)