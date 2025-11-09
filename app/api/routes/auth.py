from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...services.auth_service import AuthService
from ...core.security import create_access_token, decode_token
from ... import schemas
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    new_user = AuthService.create_user(db, user.username, user.email, user.password)
    return new_user


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = AuthService.authenticate(db, credentials.username, credentials.password)
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user"""
    user_id = decode_token(credentials.credentials)
    return AuthService.get_user_by_id(db, user_id)