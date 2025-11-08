from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...services.call_service import CallService
from ...core.security import decode_token
from ... import schemas
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/calls", tags=["Calls"])
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from token"""
    return decode_token(credentials.credentials)


@router.get("/history")
def get_call_history(
        limit: int = 50,
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    """Get user's call history"""
    calls = CallService.get_user_calls(db, user_id, limit)

    return {
        "calls": [
            schemas.CallHistory(
                call_id=call.id,
                caller_id=call.caller_id,
                receiver_id=call.receiver_id,
                status=call.status.value,
                started_at=call.started_at,
                ended_at=call.ended_at,
                duration=str(call.ended_at - call.started_at) if call.ended_at else None
            )
            for call in calls
        ],
        "total": len(calls)
    }


@router.get("/active")
def get_active_calls(
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    """Get user's active calls"""
    calls = CallService.get_active_calls(db, user_id)

    return {
        "calls": [
            schemas.CallResponse(
                call_id=call.id,
                status=call.status.value,
                caller_id=call.caller_id,
                receiver_id=call.receiver_id,
                started_at=call.started_at
            )
            for call in calls
        ],
        "count": len(calls)
    }