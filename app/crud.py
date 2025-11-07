from sqlalchemy.orm import Session
from . import models, schemas, auth
import uuid
from datetime import datetime
from typing import List


def create_call(db: Session, call: schemas.CallStart, webrtc_channel: str):
    db_call = models.Call(
        id=str(uuid.uuid4()),
        caller_id=call.caller_id,
        receiver_id=call.receiver_id,
        webrtc_channel=webrtc_channel,
        status=models.CallStatus.ACTIVE
    )
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    return db_call


def end_call(db: Session, call_id: str):
    db_call = db.query(models.Call).filter(models.Call.id == call_id).first()
    if db_call:
        db_call.status = models.CallStatus.ENDED
        db_call.ended_at = datetime.utcnow()
        db.commit()
        db.refresh(db_call)
    return db_call


def get_active_calls(db: Session) -> List[models.Call]:
    return db.query(models.Call).filter(models.Call.status == models.CallStatus.ACTIVE).all()


def get_call_by_id(db: Session, call_id: str):
    return db.query(models.Call).filter(models.Call.id == call_id).first()


def update_user_presence(db: Session, user_id: str, status: str, socket_id: str = None):
    db_presence = db.query(models.UserPresence).filter(models.UserPresence.user_id == user_id).first()
    if db_presence:
        db_presence.status = status
        db_presence.socket_id = socket_id
        db_presence.last_seen = datetime.utcnow()
    else:
        db_presence = models.UserPresence(
            user_id=user_id,
            status=status,
            socket_id=socket_id
        )
        db.add(db_presence)
    db.commit()
    return db_presence


def get_user_presence(db: Session, user_id: str):
    return db.query(models.UserPresence).filter(models.UserPresence.user_id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    try:
        hashed_password = auth.get_password_hash(user.password)
        db_user = models.User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Return user without password
        return db_user
    except Exception as e:
        db.rollback()
        print(f"Error creating user: {str(e)}")
        raise e


def get_active_calls_for_user(db: Session, user_id: str):
    return db.query(models.Call).filter(
        (models.Call.caller_id == user_id) | (models.Call.receiver_id == user_id),
        models.Call.status == models.CallStatus.ACTIVE
    ).all()


def get_user_call_history(db: Session, user_id: str, limit: int = 50, offset: int = 0):
    return db.query(models.Call).filter(
        (models.Call.caller_id == user_id) | (models.Call.receiver_id == user_id)
    ).order_by(models.Call.started_at.desc()).offset(offset).limit(limit).all()


def get_online_users(db: Session):
    return db.query(models.UserPresence).filter(
        models.UserPresence.status == models.PresenceStatus.ONLINE
    ).all()
