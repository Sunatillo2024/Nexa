from sqlalchemy import Column, String, DateTime, Integer, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class CallStatus(enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    MISSED = "missed"

class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, index=True)
    caller_id = Column(String(36), nullable=False, index=True)
    receiver_id = Column(String(36), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(CallStatus), default=CallStatus.ACTIVE)
    webrtc_channel = Column(String(255), nullable=True)

class UserPresence(Base):
    __tablename__ = "user_presence"

    user_id = Column(String(36), primary_key=True, index=True)
    status = Column(String(20), default="offline")  # online, offline
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    socket_id = Column(String(255), nullable=True)