from pydantic import BaseModel, EmailStr, Field, validator, field_validator
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)

    @field_validator('password')
    def validate_password_length(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password too long (maximum 72 bytes)')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# Call schemas
class CallStart(BaseModel):
    caller_id: str = Field(..., description="ID of the user starting the call")
    receiver_id: str = Field(..., description="ID of the user receiving the call")

    @validator('receiver_id')
    def validate_receiver(cls, v, values):
        if 'caller_id' in values and v == values['caller_id']:
            raise ValueError('Cannot call yourself')
        return v


class CallEnd(BaseModel):
    call_id: str = Field(..., description="ID of the call to end")


class CallResponse(BaseModel):
    call_id: str
    status: str
    webrtc_channel: str
    caller_id: str
    receiver_id: str
    started_at: datetime

    class Config:
        from_attributes = True


class CallEndResponse(BaseModel):
    status: str
    duration: str
    ended_at: Optional[datetime] = None


class ActiveCall(BaseModel):
    call_id: str
    caller_id: str
    receiver_id: str
    started_at: datetime
    webrtc_channel: str
    status: str

    class Config:
        from_attributes = True


class UserPresenceUpdate(BaseModel):
    user_id: str
    status: str = Field(..., pattern="^(online|offline|away)$")


class PresenceResponse(BaseModel):
    user_id: str
    status: str
    last_seen: datetime

    class Config:
        from_attributes = True


class WebRTCSignal(BaseModel):
    call_id: str
    signal_type: str = Field(..., pattern="^(offer|answer|ice-candidate)$")
    signal_data: dict


class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    database: str
    redis: str
