from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status
import hashlib

from .config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    # Pre-hash with SHA-256 to handle any length and ensure consistent length
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    # Convert to bytes for bcrypt
    password_bytes = sha256_hash.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')

    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        return False


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with SHA-256 pre-hashing"""
    # Pre-hash with SHA-256 to:
    # 1. Handle any password length
    # 2. Create uniform length input (64 hex chars = 64 bytes, under bcrypt's 72 byte limit)
    sha256_hash = hashlib.sha256(password.encode()).hexdigest()

    # Convert to bytes
    password_bytes = sha256_hash.encode('utf-8')

    # Generate salt and hash with bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode('utf-8')


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