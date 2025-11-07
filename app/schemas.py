from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CallStart(BaseModel):
    caller_id: str
    receiver_id: str

class CallEnd(BaseModel):
    call_id: str

class CallResponse(BaseModel):
    call_id: str
    status: str
    webrtc_channel: str
    caller_id: str
    receiver_id: str
    started_at: datetime

class CallEndResponse(BaseModel):
    status: str
    duration: str

class ActiveCall(BaseModel):
    call_id: str
    caller_id: str
    receiver_id: str
    started_at: datetime
    webrtc_channel: str

class UserPresenceUpdate(BaseModel):
    user_id: str
    status: str

class TokenData(BaseModel):
    user_id: Optional[str] = None