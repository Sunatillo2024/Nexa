from fastapi import APIRouter, Depends, HTTPException
from ...services.session_manager import session_manager
from ...core.security import decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/sessions", tags=["Sessions"])
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from token"""
    return decode_token(credentials.credentials)


@router.get("/my")
def get_my_session(user_id: str = Depends(get_current_user_id)):
    """Get user's current active session"""
    session = session_manager.get_user_session(user_id)

    if not session:
        return {
            "active": False,
            "session": None
        }

    return {
        "active": True,
        "session": session_manager.get_session_info(session.session_id)
    }


@router.get("/{session_id}")
def get_session_info(
        session_id: str,
        user_id: str = Depends(get_current_user_id)
):
    """Get session information"""
    session_info = session_manager.get_session_info(session_id)

    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if user is part of session
    if user_id not in [session_info["user1_id"], session_info["user2_id"]]:
        raise HTTPException(status_code=403, detail="Not part of this session")

    return session_info


@router.get("/")
def get_all_sessions(user_id: str = Depends(get_current_user_id)):
    """Get all active sessions (admin only - for debugging)"""
    # In production, add admin check here
    return {
        "total": len(session_manager.sessions),
        "sessions": [
            session_manager.get_session_info(sid)
            for sid in session_manager.sessions.keys()
        ]
    }


@router.post("/{session_id}/end")
def force_end_session(
        session_id: str,
        user_id: str = Depends(get_current_user_id)
):
    """Force end a session"""
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if user is part of session
    if user_id not in [session.user1_id, session.user2_id]:
        raise HTTPException(status_code=403, detail="Not part of this session")

    session_manager.end_session(session_id)

    return {
        "success": True,
        "message": f"Session {session_id} ended"
    }