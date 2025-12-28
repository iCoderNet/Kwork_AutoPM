"""
Kwork AI PM - Telegram Callback Router
Telegram tugmalari callback handler
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json

from database import async_session
from models.job import Job, JobStatus
from services.telegram_service import TelegramService


router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


class TelegramUpdate(BaseModel):
    """Telegram webhook update model"""
    update_id: int
    callback_query: Optional[dict] = None
    message: Optional[dict] = None


@router.post("/callback")
async def telegram_callback(request: Request):
    """
    Telegram callback query handler
    Tugmalar bosilganda ishlaydi
    """
    try:
        data = await request.json()
    except:
        return {"ok": True}
    
    callback_query = data.get("callback_query")
    
    if not callback_query:
        return {"ok": True}
    
    callback_id = callback_query.get("id")
    callback_data = callback_query.get("data", "")
    from_user = callback_query.get("from", {})
    message = callback_query.get("message", {})
    
    async with async_session() as db:
        telegram_service = await TelegramService.from_db(db)
        
        if not telegram_service:
            return {"ok": True}
        
        # Accept callback
        if callback_data.startswith("accept_"):
            job_id = callback_data.replace("accept_", "")
            
            try:
                job_id = int(job_id)
            except:
                await answer_callback(telegram_service, callback_id, "❌ Noto'g'ri ID")
                return {"ok": True}
            
            # Job ni olish
            result = await db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                await answer_callback(telegram_service, callback_id, "❌ E'lon topilmadi")
                return {"ok": True}
            
            # Status yangilash
            job.status = JobStatus.RESPONDED
            await db.commit()
            
            # Callback javob
            await answer_callback(
                telegram_service, 
                callback_id, 
                "✅ Qabul qilindi! Otklik yuborish tayyorlanmoqda..."
            )
            
            # Xabarni yangilash
            await edit_message_status(
                telegram_service,
                message.get("chat", {}).get("id"),
                message.get("message_id"),
                job,
                "✅ QABUL QILINDI"
            )
            
            return {"ok": True}
        
        # Skip callback
        elif callback_data.startswith("skip_"):
            job_id = callback_data.replace("skip_", "")
            
            try:
                job_id = int(job_id)
            except:
                await answer_callback(telegram_service, callback_id, "❌ Noto'g'ri ID")
                return {"ok": True}
            
            # Job ni olish
            result = await db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                await answer_callback(telegram_service, callback_id, "❌ E'lon topilmadi")
                return {"ok": True}
            
            # Status yangilash
            job.status = JobStatus.SKIPPED
            await db.commit()
            
            # Callback javob
            await answer_callback(
                telegram_service, 
                callback_id, 
                "🗑 Xabar o'chirildi"
            )
            
            # Xabarni O'CHIRISH
            chat_id = message.get("chat", {}).get("id")
            message_id = message.get("message_id")
            await telegram_service.delete_message(chat_id, message_id)
            
            return {"ok": True}
    
    return {"ok": True}


async def answer_callback(service: TelegramService, callback_id: str, text: str):
    """Callback query ni javoblash"""
    import httpx
    
    url = f"{service.BASE_URL}{service.bot_token}/answerCallbackQuery"
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "callback_query_id": callback_id,
            "text": text,
            "show_alert": False
        })


async def edit_message_status(
    service: TelegramService, 
    chat_id: int, 
    message_id: int, 
    job: Job,
    status_text: str
):
    """Xabardagi tugmalarni olib tashlab status qo'shish"""
    import httpx
    
    url = f"{service.BASE_URL}{service.bot_token}/editMessageReplyMarkup"
    
    # Tugmalarni olib tashlash
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": f"🔗 Kworkda ochish", "url": f"https://kwork.ru/projects/{job.kwork_id}"}],
                    [{"text": status_text, "callback_data": "status_done"}]
                ]
            }
        })
