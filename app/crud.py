from sqlalchemy.orm import Session
from . import models, schemas
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