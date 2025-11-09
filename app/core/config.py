from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Nexa Call API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:1111@localhost:5432/nexa_db"

    # Добавляем отдельные поля для PostgreSQL (опционально)
    POSTGRES_DB: str = "nexa_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "1111"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Rate Limiting
    RATE_LIMIT_CALLS: int = 5
    RATE_LIMIT_WINDOW: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Разрешаем дополнительные поля (если не хотите их явно определять)
        extra = "ignore"


settings = Settings()