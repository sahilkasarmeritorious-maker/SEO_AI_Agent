from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_PERIOD: int = 3600  # 1 hour
    # App
    APP_NAME: str = "Website Analysis API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = "llama-3.1-70b-versatile"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # 1 hour
    
    # CORS
    ALLOWED_ORIGINS: list = ["*"]
    
    # Dummy User
    DUMMY_USER_EMAIL: str = "demo@example.com"
    DUMMY_USER_PASSWORD: str = "demo123456"
    DUMMY_USER_FULL_NAME: str = "Demo User"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()