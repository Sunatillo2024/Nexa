from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CallStart(BaseModel):
    receiver_id: str


class CallEnd(BaseModel):
    call_id: str


class CallResponse(BaseModel):
    call_id: str
    status: str
    caller_id: str
    receiver_id: str
    started_at: datetime


class CallHistory(BaseModel):
    call_id: str
    caller_id: str
    receiver_id: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration: Optional[str] = None