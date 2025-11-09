from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import hashlib

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(sha256_hash, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Сначала хешируем SHA-256, затем берем первые 72 байта
    # Это безопасно, т.к. SHA-256 уже создает криптографически стойкий хеш
    sha256_hash = hashlib.sha256(password.encode()).hexdigest()
    # Обрезаем до 72 байт (bcrypt лимит)
    truncated = sha256_hash[:72]
    return pwd_context.hash(truncated)


def create_access_token(user_id: str) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str:
    """Decode JWT token and return user_id"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
