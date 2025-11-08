from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.sql import func
from ..db.session import Base
import enum
import uuid


class CallStatus(enum.Enum):
    ONGOING = "ongoing"
    ENDED = "ended"
    MISSED = "missed"


class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    caller_id = Column(String(36), nullable=False, index=True)
    receiver_id = Column(String(36), nullable=False, index=True)
    status = Column(Enum(CallStatus), default=CallStatus.ONGOING, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_call_users', 'caller_id', 'receiver_id'),
    )