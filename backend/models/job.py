"""
Kwork AI PM - Job Model (E'lonlar)
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, Enum
from sqlalchemy.sql import func
from database import Base
import enum


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    RESPONDED = "responded"
    SKIPPED = "skipped"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    kwork_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # ========== Asosiy ma'lumotlar ==========
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    budget = Column(String(100), nullable=True)
    category = Column(String(200), nullable=True)
    category_id = Column(String(50), nullable=True)
    
    # ========== To'liq JSON saqlash ==========
    kwork_json = Column(Text, nullable=True)  # Kwork dan kelgan to'liq JSON
    ai_json = Column(Text, nullable=True)     # AI dan qaytgan to'liq JSON
    
    # ========== Buyurtmachi ma'lumotlari ==========
    client_id = Column(String(50), nullable=True)
    client_name = Column(String(200), nullable=True)
    client_avatar = Column(String(500), nullable=True)
    client_profile_url = Column(String(500), nullable=True)
    client_wants_count = Column(Integer, nullable=True)      # Nechta e'lon bergan
    client_hired_percent = Column(Integer, nullable=True)    # Necha % yollagan
    
    # ========== E'lon detallari ==========
    max_days = Column(Integer, nullable=True)         # Maksimum kun
    price_limit = Column(String(50), nullable=True)   # Narx limiti
    views_count = Column(Integer, nullable=True)      # Ko'rishlar soni
    kwork_status = Column(String(50), nullable=True)  # active/archive
    time_left = Column(String(50), nullable=True)     # Qolgan vaqt
    
    # ========== Sanalar ==========
    date_expire = Column(DateTime(timezone=True), nullable=True)
    date_active = Column(DateTime(timezone=True), nullable=True)
    date_create_kwork = Column(DateTime(timezone=True), nullable=True)
    
    # ========== Status ==========
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    
    # ========== AI Response ==========
    ai_response = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    ai_reason = Column(Text, nullable=True)
    estimated_price = Column(String(50), nullable=True)
    estimated_time = Column(String(100), nullable=True)
    
    # AI optimized fields
    can_take = Column(Boolean, nullable=True)         # AI: olsa bo'ladimi
    proposal_text_ru = Column(Text, nullable=True)    # Taklif matni (rus)
    proposal_text_uz = Column(Text, nullable=True)    # Taklif matni (o'zbek)
    
    # ========== Notification ==========
    telegram_sent = Column(Boolean, default=False)
    telegram_message_id = Column(String(50), nullable=True)
    
    # ========== Timestamps ==========
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Job {self.kwork_id}: {self.title[:50]}>"
    
    def to_dict(self):
        """Job ni dictionary ga aylantirish"""
        return {
            "id": self.id,
            "kwork_id": self.kwork_id,
            "title": self.title,
            "description": self.description,
            "budget": self.budget,
            "category": self.category,
            "category_id": self.category_id,
            "kwork_json": self.kwork_json,
            "ai_json": self.ai_json,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "client_avatar": self.client_avatar,
            "client_profile_url": self.client_profile_url,
            "client_wants_count": self.client_wants_count,
            "client_hired_percent": self.client_hired_percent,
            "max_days": self.max_days,
            "price_limit": self.price_limit,
            "views_count": self.views_count,
            "kwork_status": self.kwork_status,
            "time_left": self.time_left,
            "date_expire": self.date_expire.isoformat() if self.date_expire else None,
            "date_active": self.date_active.isoformat() if self.date_active else None,
            "status": self.status.value if self.status else None,
            "ai_response": self.ai_response,
            "confidence_score": self.confidence_score,
            "risk_score": self.risk_score,
            "ai_reason": self.ai_reason,
            "estimated_price": self.estimated_price,
            "estimated_time": self.estimated_time,
            "can_take": self.can_take,
            "proposal_text_ru": self.proposal_text_ru,
            "proposal_text_uz": self.proposal_text_uz,
            "telegram_sent": self.telegram_sent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }

