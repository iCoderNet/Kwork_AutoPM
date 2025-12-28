"""
Kwork AI PM - Webhook Router
Cron job uchun webhook endpoint - yangi e'lonlarni tekshirish
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from typing import List
import json
import asyncio
import logging
from datetime import datetime

from database import get_db
from config import settings
from models.job import Job, JobStatus
from services.kwork_service import KworkService
from services.ai_service import AIService
from services.telegram_service import TelegramService


# Logger sozlash
logger = logging.getLogger("webhook")
logger.setLevel(logging.DEBUG)

# Logs papkasini yaratish
import os
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(logs_dir, exist_ok=True)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler (rotating log - max 5MB, 5 backup files)
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(
    os.path.join(logs_dir, "webhook.log"),
    maxBytes=5*1024*1024,  # 5MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


router = APIRouter(prefix="/api/webhook", tags=["Webhook"])


async def process_jobs_background(job_ids: List[int]):
    """Background da e'lonlarni AI bilan tahlil qilish"""
    logger.info("=" * 60)
    logger.info(f"🚀 BACKGROUND TASK BOSHLANDI - {len(job_ids)} ta job")
    logger.info("=" * 60)
    
    # Yangi database session yaratish (background task uchun)
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # AI service olish
            logger.info("📡 AI service yuklanmoqda...")
            ai_service = await AIService.from_db(db)
            
            if ai_service:
                logger.info("✅ AI service tayyor")
            else:
                logger.warning("⚠️ AI service TOPILMADI! Dashboard'dan sozlang")
            
            logger.info("📡 Telegram service yuklanmoqda...")
            telegram_service = await TelegramService.from_db(db)
            
            if telegram_service:
                logger.info("✅ Telegram service tayyor")
            else:
                logger.warning("⚠️ Telegram service TOPILMADI! Dashboard'dan sozlang")
            
            for i, job_id in enumerate(job_ids, 1):
                logger.info("-" * 40)
                logger.info(f"📋 Job #{job_id} qayta ishlanmoqda ({i}/{len(job_ids)})")
                
                try:
                    # Job ni olish
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job = result.scalar_one_or_none()
                    
                    if not job:
                        logger.warning(f"⚠️ Job #{job_id} bazada topilmadi")
                        continue
                    
                    logger.info(f"   📝 Title: {job.title[:50]}...")
                    logger.info(f"   💰 Budget: {job.budget}")
                    logger.info(f"   📄 Description uzunligi: {len(job.description or '')} belgi")
                    
                    # AI tahlil
                    ai_data = None
                    ai_response_text = None
                    
                    if ai_service:
                        logger.info(f"   🤖 AI tahlil boshlanmoqda...")
                        start_time = datetime.now()
                        
                        try:
                            ai_result = await ai_service.generate_response(job.description or "", job.budget or "")
                            elapsed = (datetime.now() - start_time).total_seconds()
                            logger.info(f"   ⏱️ AI javob olindi: {elapsed:.2f} soniya")
                            
                            # Success tekshirish
                            if not ai_result.get("success", False):
                                error_msg = ai_result.get("error", "Noma'lum xato")
                                logger.error(f"   ❌ AI xato: {error_msg}")
                                continue
                            
                            # TEXT keyni olish (response emas!)
                            ai_response_text = ai_result.get("text", "")
                            logger.debug(f"   📊 AI Raw response uzunligi: {len(ai_response_text)} belgi")
                            
                            if not ai_response_text:
                                logger.error(f"   ❌ AI javob bo'sh!")
                                continue
                            
                            # JSON ni parse qilish
                            clean_text = ai_response_text.replace("```json", "").replace("```", "").strip()
                            ai_data = json.loads(clean_text)
                            
                            logger.info(f"   ✅ JSON parse qilindi")
                            logger.info(f"   📊 can_take: {ai_data.get('can_take')}")
                            logger.info(f"   📊 confidence_score: {ai_data.get('confidence_score')}")
                            logger.info(f"   📊 risk_score: {ai_data.get('risk_score')}")
                            logger.info(f"   💵 estimated_price: {ai_data.get('estimated_price_rub')} RUB")
                            logger.info(f"   ⏰ estimated_time: {ai_data.get('estimated_time_human')}")
                            
                            # Job ni yangilash
                            job.ai_response = ai_response_text
                            job.ai_json = json.dumps(ai_data, ensure_ascii=False)
                            job.confidence_score = ai_data.get("confidence_score")
                            job.risk_score = ai_data.get("risk_score")
                            job.ai_reason = json.dumps(ai_data.get("reason", {}), ensure_ascii=False)
                            job.estimated_price = str(ai_data.get("estimated_price_rub", ""))
                            job.estimated_time = ai_data.get("estimated_time_human", "")
                            job.can_take = ai_data.get("can_take")
                            
                            # Status ni AI baholashiga qarab o'zgartirish
                            if ai_data.get("can_take"):
                                job.status = "accepted"
                                logger.info(f"   ✅ Status: ACCEPTED (can_take=true)")
                            else:
                                job.status = "skipped"
                                logger.info(f"   ⏭️ Status: SKIPPED (can_take=false)")
                            
                            if isinstance(ai_data.get("proposal_text"), dict):
                                job.proposal_text_ru = ai_data.get("proposal_text", {}).get("ru")
                                job.proposal_text_uz = ai_data.get("proposal_text", {}).get("uz")
                                logger.debug(f"   📝 Proposal text RU: {len(job.proposal_text_ru or '')} belgi")
                                logger.debug(f"   📝 Proposal text UZ: {len(job.proposal_text_uz or '')} belgi")
                            
                            await db.commit()
                            logger.info(f"   💾 Job #{job_id} bazaga saqlandi")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"   ❌ JSON parse xato: {e}")
                            logger.error(f"   📄 Raw response: {ai_response_text[:200]}...")
                        except Exception as e:
                            logger.error(f"   ❌ AI xato: {type(e).__name__}: {e}")
                    else:
                        logger.warning(f"   ⚠️ AI service yo'q - tahlil o'tkazib yuborildi")
                    
                    # Telegram ga yuborish (barcha joblar yuboriladi)
                    if telegram_service and ai_data:
                        logger.info(f"   📨 Telegram ga yuborilmoqda...")
                        try:
                            tg_result = await telegram_service.send_job_notification(job, ai_data)
                            logger.debug(f"   📬 Telegram response: {tg_result}")
                            
                            if tg_result.get("success"):
                                job.telegram_sent = True
                                job.telegram_message_id = tg_result.get("message_id")
                                await db.commit()
                                logger.info(f"   ✅ Job #{job_id} Telegram ga yuborildi (msg_id: {tg_result.get('message_id')})")
                            else:
                                logger.error(f"   ❌ Telegram xato: {tg_result.get('error')}")
                        except Exception as e:
                            logger.error(f"   ❌ Telegram exception: {type(e).__name__}: {e}")
                    elif not telegram_service:
                        logger.warning(f"   ⚠️ Telegram service yo'q")
                    elif not ai_data:
                        logger.warning(f"   ⚠️ AI data yo'q - Telegram yuborilmadi")
                            
                except Exception as e:
                    logger.error(f"   ❌ Job #{job_id} umumiy xato: {type(e).__name__}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Background task umumiy xato: {type(e).__name__}: {e}")
        finally:
            await engine.dispose()
            logger.info("=" * 60)
            logger.info(f"🏁 BACKGROUND TASK YAKUNLANDI")
            logger.info("=" * 60)


@router.post("/check")
async def webhook_check(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Cron webhook - yangi e'lonlarni tekshirish (ASYNC)
    
    Flow:
    1. Kwork dan e'lonlarni olish
    2. Yangi e'lonlarni bazaga saqlash (AI siz)
    3. TEZKOR javob qaytarish
    4. Background da AI tahlil + Telegram
    """
    logger.info("=" * 60)
    logger.info("🔔 WEBHOOK /check CHAQIRILDI")
    logger.info("=" * 60)
    
    # Kwork dan e'lonlarni olish
    logger.info("📡 Kwork dan e'lonlar olinmoqda...")
    kwork_service = KworkService(db)
    result = await kwork_service.fetch_projects()
    
    if not result.get("success"):
        logger.error(f"❌ Kwork xato: {result.get('error')}")
        return {
            "success": False,
            "error": result.get("error"),
            "new_jobs": 0
        }
    
    wants = result.get("wants", [])
    logger.info(f"✅ Kwork dan {len(wants)} ta e'lon olindi")
    
    new_job_ids = []
    
    for i, want in enumerate(wants, 1):
        # Parse qilish
        job_data = kwork_service.parse_project(want)
        kwork_id = job_data["kwork_id"]
        
        # Bazada bor-yo'qligini tekshirish
        existing = await db.execute(
            select(Job).where(Job.kwork_id == kwork_id)
        )
        existing_job = existing.scalar_one_or_none()
        
        if existing_job:
            logger.debug(f"   ⏭️ #{kwork_id} allaqachon bor")
            continue
        
        logger.info(f"   ➕ #{kwork_id} yangi e'lon: {job_data['title'][:40]}...")
        
        # Yangi job yaratish (AI SIFOTIZ - tez saqlash)
        new_job = Job(
            # Asosiy
            kwork_id=job_data["kwork_id"],
            title=job_data["title"],
            description=job_data["description"],
            budget=job_data["budget"],
            category=job_data["category"],
            category_id=job_data.get("category_id"),
            
            # To'liq Kwork JSON
            kwork_json=job_data.get("kwork_json"),
            
            # Buyurtmachi
            client_id=job_data.get("client_id"),
            client_name=job_data.get("client_name"),
            client_avatar=job_data.get("client_avatar"),
            client_profile_url=job_data.get("client_profile_url"),
            client_wants_count=job_data.get("client_wants_count"),
            client_hired_percent=job_data.get("client_hired_percent"),
            
            # E'lon detallari
            max_days=job_data.get("max_days"),
            price_limit=job_data.get("price_limit"),
            views_count=job_data.get("views_count"),
            kwork_status=job_data.get("kwork_status"),
            time_left=job_data.get("time_left"),
            
            # Sanalar
            date_expire=job_data.get("date_expire"),
            date_active=job_data.get("date_active"),
            date_create_kwork=job_data.get("date_create_kwork"),
            
            # Status
            status=JobStatus.PENDING,
        )
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
        
        new_job_ids.append(new_job.id)
        logger.info(f"   💾 Job #{new_job.id} bazaga saqlandi")
    
    logger.info(f"📊 Jami: {len(wants)} ta tekshirildi, {len(new_job_ids)} ta yangi")
    
    # Background da AI tahlil qilish
    if new_job_ids:
        logger.info(f"🚀 Background task ishga tushirilmoqda: {new_job_ids}")
        background_tasks.add_task(process_jobs_background, new_job_ids)
    else:
        logger.info("ℹ️ Yangi job yo'q - background task kerak emas")
    
    logger.info("=" * 60)
    logger.info("✅ WEBHOOK RESPONSE - client ga javob yuborilmoqda")
    logger.info("=" * 60)
    
    return {
        "success": True,
        "total_checked": len(wants),
        "new_jobs": len(new_job_ids),
        "message": f"{len(new_job_ids)} ta yangi e'lon topildi. AI tahlil background da davom etmoqda..."
    }
