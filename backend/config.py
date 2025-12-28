"""
Kwork AI Project Manager - Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Kwork AI PM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DOMAIN: str = "https://haldmp-ip-95-214-211-174.tunnelmole.net"
    
    # Security
    SECRET_KEY: str = "kwork-ai-pm-super-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/kwork_pm.db"
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # Default admin credentials
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_EMAIL: str = "admin@kwork-pm.local"
    
    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
