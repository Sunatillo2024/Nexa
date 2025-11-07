from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.sql import func
from .database import Base
import enum
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class CallStatus(enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    MISSED = "missed"


class PresenceStatus(enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"


class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    caller_id = Column(String(36), nullable=False, index=True)
    receiver_id = Column(String(36), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(CallStatus), default=CallStatus.ACTIVE, nullable=False)
    webrtc_channel = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_caller_receiver', 'caller_id', 'receiver_id'),
        Index('idx_status_started', 'status', 'started_at'),
    )


class UserPresence(Base):
    __tablename__ = "user_presence"

    user_id = Column(String(36), primary_key=True, index=True)
    status = Column(Enum(PresenceStatus), default=PresenceStatus.OFFLINE, nullable=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    socket_id = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(String(10), default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
