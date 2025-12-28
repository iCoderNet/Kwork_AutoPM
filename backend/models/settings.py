"""
Kwork AI PM - Settings Model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)  # ai, telegram, kwork, system
    description = Column(String(255), nullable=True)
    is_secret = Column(Integer, default=0)  # 1 = encrypted/hidden
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Settings {self.key}>"


# Default settings keys
DEFAULT_SETTINGS = [
    # Kwork
    {"key": "kwork_username", "value": "", "category": "kwork", "description": "Kwork login", "is_secret": 0},
    {"key": "kwork_password", "value": "", "category": "kwork", "description": "Kwork parol", "is_secret": 1},
    
    # AI
    {"key": "ai_enabled", "value": "false", "category": "ai", "description": "AI PM yoqilgan", "is_secret": 0},
    {"key": "ai_model", "value": "gpt-4", "category": "ai", "description": "AI model nomi", "is_secret": 0},
    {"key": "ai_api_key", "value": "", "category": "ai", "description": "AI API kaliti", "is_secret": 1},
    {"key": "ai_prompt", "value": "", "category": "ai", "description": "AI uchun prompt", "is_secret": 0},
    
    # Telegram
    {"key": "telegram_bot_token", "value": "", "category": "telegram", "description": "Telegram bot token", "is_secret": 1},
    {"key": "telegram_group_id", "value": "", "category": "telegram", "description": "Telegram guruh ID", "is_secret": 0},
    {"key": "telegram_enabled", "value": "false", "category": "telegram", "description": "Telegram xabarnoma yoqilgan", "is_secret": 0},
    
    # System
    {"key": "scan_interval", "value": "60", "category": "system", "description": "Kwork skanerlash intervali (sekund)", "is_secret": 0},
    {"key": "auto_respond", "value": "false", "category": "system", "description": "Avtomatik javob berish", "is_secret": 0},
]
