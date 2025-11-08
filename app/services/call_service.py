from sqlalchemy.orm import Session
from ..models.call import Call, CallStatus
from datetime import datetime


class CallService:
    @staticmethod
    def create_call(db: Session, caller_id: str, receiver_id: str) -> Call:
        """Create new call"""
        call = Call(
            caller_id=caller_id,
            receiver_id=receiver_id,
            status=CallStatus.ONGOING
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call

    @staticmethod
    def end_call(db: Session, call_id: str) -> Call:
        """End call"""
        call = db.query(Call).filter(Call.id == call_id).first()
        if call:
            call.status = CallStatus.ENDED
            call.ended_at = datetime.utcnow()
            db.commit()
            db.refresh(call)
        return call

    @staticmethod
    def get_call(db: Session, call_id: str) -> Call:
        """Get call by ID"""
        return db.query(Call).filter(Call.id == call_id).first()

    @staticmethod
    def get_user_calls(db: Session, user_id: str, limit: int = 50):
        """Get user's call history"""
        return db.query(Call).filter(
            (Call.caller_id == user_id) | (Call.receiver_id == user_id)
        ).order_by(Call.started_at.desc()).limit(limit).all()

    @staticmethod
    def get_active_calls(db: Session, user_id: str):
        """Get user's active calls"""
        return db.query(Call).filter(
            (Call.caller_id == user_id) | (Call.receiver_id == user_id),
            Call.status == CallStatus.ONGOING
        ).all()