"""
Kwork AI PM - Scheduler Service
Avtomatik skanerlash: Kwork → AI tahlil → Telegram xabarnoma
"""
import json
import re
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from models.job import Job, JobStatus
from models.settings import Settings
from services.kwork_service import KworkService
from services.ai_service import AIService
from services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


async def _get_setting(db: AsyncSession, key: str) -> Optional[str]:
    result = await db.execute(select(Settings).where(Settings.key == key))
    s = result.scalar_one_or_none()
    return s.value if s else None


def _extract_json(text: str) -> Optional[dict]:
    """AI javobidan JSON ni ajratib olish"""
    # Markdown code block ichidan
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()

    # Birinchi { ... } blokni olish
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


async def _send_telegram_notification(
    telegram: TelegramService, job: Job, ai_data: dict
):
    """Telegram ga loyiha haqida xabar yuborish"""
    reason_ru = ai_data.get("reason", {}).get("ru", "") if isinstance(ai_data.get("reason"), dict) else str(ai_data.get("reason", ""))
    proposal_ru = ai_data.get("proposal_text", {}).get("ru", "") if isinstance(ai_data.get("proposal_text"), dict) else ""

    price = ai_data.get("estimated_price_rub", "")
    time_h = ai_data.get("estimated_time_human", "")
    confidence = ai_data.get("confidence_score", 0)
    risk = ai_data.get("risk_score", 0)

    text = (
        f"🟢 <b>Yangi loyiha qabul qilindi!</b>\n\n"
        f"📌 <b>{job.title}</b>\n"
        f"💰 Byudjet: {job.budget or '—'}\n"
        f"📂 Kategoriya: {job.category or '—'}\n\n"
        f"🤖 <b>AI tahlil:</b>\n"
        f"  • Ishonch: {round(confidence * 100)}%\n"
        f"  • Risk: {round(risk * 100)}%\n"
        f"  • Narx: {price} RUB\n"
        f"  • Muddat: {time_h}\n\n"
        f"💬 <b>Sabab:</b> {reason_ru}\n\n"
        f"✍️ <b>Taklif:</b>\n{proposal_ru}\n\n"
        f"🔗 <a href='{job.url if hasattr(job, 'url') else f'https://kwork.ru/projects/{job.kwork_id}'}'>Kwork'da ko'rish</a>"
    )

    result = await telegram.send_message(text)
    if result.get("ok"):
        msg_id = result.get("result", {}).get("message_id")
        job.telegram_message_id = str(msg_id) if msg_id else None
        job.telegram_sent = True
    else:
        logger.warning(f"Telegram yuborishda xato: {result}")


async def scan_and_process():
    """
    Asosiy cron vazifasi:
    1. Kwork dan loyihalarni olish
    2. Yangilarini DB ga saqlash
    3. AI tahlil qilish
    4. Telegram ga yuborish
    """
    async with async_session() as db:
        try:
            # Auto-respond yoqilganmi?
            auto = await _get_setting(db, "auto_respond")
            ai_enabled = await _get_setting(db, "ai_enabled")

            # Kwork scan har doim ishlaydi; AI + Telegram — faqat yoqilsa
            kwork = KworkService(db)
            logged_in = await kwork.load_session()

            if not logged_in:
                logger.info("Kwork: login yo'q, scan o'tkazib yuborildi")
                return

            result = await kwork.fetch_projects()
            if not result.get("success"):
                logger.warning(f"Kwork fetch xatosi: {result.get('error')}")
                return

            wants = result.get("wants", [])
            logger.info(f"Kwork: {len(wants)} ta e'lon topildi")

            # AI va Telegram servislarini tayyorlash
            ai_service = None
            telegram = None

            if ai_enabled == "true":
                ai_service = await AIService.from_db(db)

            telegram_enabled = await _get_setting(db, "telegram_enabled")
            if telegram_enabled == "true":
                telegram = await TelegramService.from_db(db)

            new_count = 0

            for want in wants:
                kwork_id = str(want.get("id", ""))
                if not kwork_id:
                    continue

                # Allaqachon bazada bormi?
                existing = await db.execute(
                    select(Job).where(Job.kwork_id == kwork_id)
                )
                if existing.scalar_one_or_none():
                    continue

                # Yangi loyiha — parse va saqlash
                parsed = kwork.parse_project(want)
                job = Job(**{k: v for k, v in parsed.items() if hasattr(Job, k)})
                job.status = JobStatus.PENDING
                db.add(job)
                await db.flush()  # id olish uchun
                new_count += 1

                # AI tahlil
                if ai_service and auto == "true":
                    try:
                        ai_result = await ai_service.generate_response(
                            job.description or job.title, str(job.budget or "")
                        )

                        if ai_result.get("success"):
                            raw_text = ai_result["text"]
                            job.ai_response = raw_text
                            ai_data = _extract_json(raw_text) or {}
                            job.ai_json = json.dumps(ai_data, ensure_ascii=False)

                            job.can_take = bool(ai_data.get("can_take", False))
                            job.confidence_score = float(ai_data.get("confidence_score", 0))
                            job.risk_score = float(ai_data.get("risk_score", 0))
                            job.estimated_price = str(ai_data.get("estimated_price_rub", ""))
                            job.estimated_time = ai_data.get("estimated_time_human", "")

                            reason = ai_data.get("reason", {})
                            if isinstance(reason, dict):
                                job.ai_reason = reason.get("ru", "")
                            else:
                                job.ai_reason = str(reason)

                            proposal = ai_data.get("proposal_text", {})
                            if isinstance(proposal, dict):
                                job.proposal_text_ru = proposal.get("ru", "")
                                job.proposal_text_uz = proposal.get("uz", "")

                            job.status = JobStatus.RESPONDED if job.can_take else JobStatus.SKIPPED

                            # Telegram
                            if job.can_take and telegram:
                                await _send_telegram_notification(telegram, job, ai_data)
                        else:
                            job.status = JobStatus.FAILED
                            job.ai_reason = ai_result.get("error", "AI xatosi")

                    except Exception as e:
                        logger.error(f"AI tahlil xatosi ({kwork_id}): {e}")
                        job.status = JobStatus.FAILED
                        job.ai_reason = str(e)

            await db.commit()
            if new_count:
                logger.info(f"Scan tugadi: {new_count} ta yangi loyiha saqlandi")

        except Exception as e:
            logger.error(f"Scan xatosi: {e}")
            await db.rollback()


async def get_scan_interval() -> int:
    """DB dan scan intervalini olish (sekund)"""
    async with async_session() as db:
        val = await _get_setting(db, "scan_interval")
        try:
            return max(30, int(val or 60))
        except (ValueError, TypeError):
            return 60
