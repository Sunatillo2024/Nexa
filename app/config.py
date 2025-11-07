from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_DB: str = "nexa_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "1111"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: str = "postgresql://postgres:1111@localhost:5432/nexa_db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: str = "redis://localhost:6379"
    CORS_ORIGINS: list = ["*"]
    RATE_LIMIT_CALLS: int = 5
    RATE_LIMIT_WINDOW: int = 60
    APP_NAME: str = "Nexa Call API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
