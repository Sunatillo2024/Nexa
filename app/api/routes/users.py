from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...services.websocket_manager import manager as ws_manager
from ...services.session_manager import session_manager
from ...services.auth_service import AuthService
from ...core.security import decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict

router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from token"""
    return decode_token(credentials.credentials)


@router.get("/online")
def get_online_users(
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    """Get all online users with their status"""
    online_user_ids = ws_manager.get_online_users()

    users_info = []
    for uid in online_user_ids:
        # Skip current user
        if uid == user_id:
            continue

        try:
            user = AuthService.get_user_by_id(db, uid)

            # Check if user is in a call
            session = session_manager.get_user_session(uid)
            in_call = session is not None and session.status == "active"

            users_info.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "status": "in_call" if in_call else "online",
                "in_call": in_call
            })
        except:
            # User might be deleted but still connected
            continue

    return {
        "total": len(users_info),
        "users": users_info
    }


@router.get("/all")
def get_all_users(
        user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    """Get all users (online and offline)"""
    from ...models.user import User

    # Get all users from database
    all_users = db.query(User).all()
    online_user_ids = ws_manager.get_online_users()

    users_info = []
    for user in all_users:
        # Skip current user
        if user.id == user_id:
            continue

        is_online = user.id in online_user_ids

        # Check if user is in a call
        in_call = False
        if is_online:
            session = session_manager.get_user_session(user.id)
            in_call = session is not None and session.status == "active"

        users_info.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "status": "in_call" if in_call else ("online" if is_online else "offline"),
            "online": is_online,
            "in_call": in_call,
            "created_at": user.created_at.isoformat()
        })

    # Sort: online first, then by username
    users_info.sort(key=lambda x: (not x["online"], x["username"]))

    return {
        "total": len(users_info),
        "online_count": sum(1 for u in users_info if u["online"]),
        "offline_count": sum(1 for u in users_info if not u["online"]),
        "users": users_info
    }


@router.get("/{user_id}")
def get_user_info(
        user_id: str,
        current_user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    """Get specific user information"""
    user = AuthService.get_user_by_id(db, user_id)

    is_online = ws_manager.is_user_online(user_id)

    # Check if user is in a call
    in_call = False
    session_info = None
    if is_online:
        session = session_manager.get_user_session(user_id)
        if session and session.status == "active":
            in_call = True
            session_info = {
                "session_id": session.session_id,
                "with_user": session.user2_id if session.user1_id == user_id else session.user1_id
            }

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "status": "in_call" if in_call else ("online" if is_online else "offline"),
        "online": is_online,
        "in_call": in_call,
        "session": session_info,
        "created_at": user.created_at.isoformat()
    }


@router.get("/search/{username}")
def search_users(
        username: str,
        current_user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    """Search users by username"""
    from ...models.user import User

    # Search users (case-insensitive)
    users = db.query(User).filter(
        User.username.ilike(f"%{username}%"),
        User.id != current_user_id
    ).limit(20).all()

    online_user_ids = ws_manager.get_online_users()

    users_info = []
    for user in users:
        is_online = user.id in online_user_ids

        in_call = False
        if is_online:
            session = session_manager.get_user_session(user.id)
            in_call = session is not None and session.status == "active"

        users_info.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "status": "in_call" if in_call else ("online" if is_online else "offline"),
            "online": is_online,
            "in_call": in_call
        })

    return {
        "query": username,
        "total": len(users_info),
        "users": users_info
    }