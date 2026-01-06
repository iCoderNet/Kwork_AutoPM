"""
Kwork AI PM - Telegram Service
"""
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config import settings

from models.settings import Settings


class TelegramService:
    """Service for sending Telegram notifications"""
    
    BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(self, bot_token: str, group_id: str):
        self.bot_token = bot_token
        self.group_id = group_id
    
    @classmethod
    async def from_db(cls, db: AsyncSession) -> Optional["TelegramService"]:
        """Create TelegramService instance from database settings"""
        # Get bot token
        result = await db.execute(
            select(Settings).where(Settings.key == "telegram_bot_token")
        )
        token_setting = result.scalar_one_or_none()
        
        # Get group ID
        result = await db.execute(
            select(Settings).where(Settings.key == "telegram_group_id")
        )
        group_setting = result.scalar_one_or_none()
        
        if not token_setting or not group_setting:
            return None
        
        if not token_setting.value or not group_setting.value:
            return None
        
        return cls(token_setting.value, group_setting.value)
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> dict:
        """Send message to Telegram group"""
        url = f"{self.BASE_URL}{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.group_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30)
            return response.json()
    
    async def test_connection(self) -> dict:
        """Test Telegram bot connection"""
        url = f"{self.BASE_URL}{self.bot_token}/getMe"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            return response.json()
    
    async def set_webhook(self, webhook_url: str) -> dict:
        """Set Telegram webhook URL"""
        url = f"{self.BASE_URL}{self.bot_token}/setWebhook"
        
        payload = {
            "url": webhook_url,
            "allowed_updates": ["callback_query", "message"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30)
            return response.json()
    
    async def delete_webhook(self) -> dict:
        """Delete Telegram webhook"""
        url = f"{self.BASE_URL}{self.bot_token}/deleteWebhook"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, timeout=30)
            return response.json()
    
    async def get_webhook_info(self) -> dict:
        """Get current webhook info"""
        url = f"{self.BASE_URL}{self.bot_token}/getWebhookInfo"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            return response.json()
    
    @staticmethod
    def format_job_notification(job_data: dict) -> str:
        """Format job notification message for Telegram"""
        status_emoji = "✅" if job_data.get("can_take") else "❌"
        
        message = f"""
{status_emoji} <b>Yangi loyiha topildi!</b>

📋 <b>Sarlavha:</b> {job_data.get('title', 'N/A')}

💰 <b>Byudjet:</b> {job_data.get('budget', 'Belgilanmagan')}

📊 <b>AI Baholash:</b>
• Ishonch darajasi: {job_data.get('confidence_score', 0):.0%}
• Risk darajasi: {job_data.get('risk_score', 0):.0%}
• Taxminiy narx: {job_data.get('estimated_price', 'N/A')} RUB
• Taxminiy muddat: {job_data.get('estimated_time', 'N/A')}

📝 <b>Sabab:</b> {job_data.get('reason', 'N/A')}

🔗 <a href="{job_data.get('url', '#')}">Kwork'da ko'rish</a>
"""
        return message.strip()
    
    @staticmethod
    def format_response_notification(job_data: dict, response_text: str) -> str:
        """Format response sent notification"""
        message = f"""
📤 <b>Otklik yuborildi!</b>

📋 <b>Loyiha:</b> {job_data.get('title', 'N/A')}

💬 <b>Yuborilgan javob:</b>
<i>{response_text}</i>

🔗 <a href="{job_data.get('url', '#')}">Kwork'da ko'rish</a>
"""
        return message.strip()
    
    async def send_message_with_buttons(
        self, 
        text: str, 
        buttons: list,
        parse_mode: str = "HTML"
    ) -> dict:
        """Send message with inline keyboard buttons"""
        url = f"{self.BASE_URL}{self.bot_token}/sendMessage"
        
        # Build inline keyboard
        inline_keyboard = []
        for row in buttons:
            keyboard_row = []
            for btn in row:
                if btn.get("url"):
                    keyboard_row.append({
                        "text": btn["text"],
                        "url": btn["url"]
                    })
                elif btn.get("callback_data"):
                    keyboard_row.append({
                        "text": btn["text"],
                        "callback_data": btn["callback_data"]
                    })
            if keyboard_row:
                inline_keyboard.append(keyboard_row)
        
        payload = {
            "chat_id": self.group_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
            "reply_markup": {
                "inline_keyboard": inline_keyboard
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30)
            return response.json()
    
    async def delete_message(self, chat_id: int, message_id: int) -> dict:
        """Delete a message from chat"""
        url = f"{self.BASE_URL}{self.bot_token}/deleteMessage"
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30)
            return response.json()
    
    async def send_job_notification(self, job, ai_data: dict) -> dict:
        """
        E'lon haqida Telegram guruhga xabar yuborish
        Barcha loyihalar yuboriladi (mos va mos emas)
        """
        import json
        
        # AI ma'lumotlarini olish
        can_take = ai_data.get("can_take", False)
        confidence = ai_data.get("confidence_score", 0)
        risk = ai_data.get("risk_score", 0)
        
        # Confidence va risk qiymatlarini foizga aylantirish
        if confidence <= 1:
            confidence = confidence * 100
        if risk <= 1:
            risk = risk * 100
        
        # Reason olish
        reason = ai_data.get("reason", {})
        if isinstance(reason, dict):
            reason_text = reason.get("uz", reason.get("ru", "N/A"))
        else:
            reason_text = str(reason)
        
        # Kategoriya - job.category yoki kwork_json dan olish
        category_name = job.category
        if not category_name or category_name == "N/A":
            try:
                if job.kwork_json:
                    kwork_data = json.loads(job.kwork_json)
                    category_name = kwork_data.get("parent_category_name") or kwork_data.get("category_name") or "N/A"
            except:
                category_name = "N/A"
        
        # Client info
        client_name = job.client_name or "N/A"
        client_link = f'<a href="https://kwork.ru/user/{client_name}">{client_name}</a>' if client_name != "N/A" else "N/A"
        
        # Vazifa sharti - ikki tilda
        full_task = ai_data.get("full_task_text", {})
        task_ru = ""
        task_uz = ""
        if isinstance(full_task, dict):
            task_ru = full_task.get("ru", "")[:500] if full_task.get("ru") else ""
            task_uz = full_task.get("uz", "")[:500] if full_task.get("uz") else ""
        elif isinstance(full_task, str):
            task_ru = full_task[:500]
        
        # Vazifa sharti matni
        task_text = ""
        if task_ru or task_uz:
            task_text = "\n\n<blockquote>📄 <b>Vazifa sharti:</b>\n"
            if task_ru:
                task_text += f"🇷🇺 {task_ru}\n"
            if task_uz:
                task_text += f"🇺🇿 {task_uz}</blockquote>"
        
        # Status emoji va matn
        if can_take:
            status_emoji = "✅"
            status_text = "Mos loyiha"
        else:
            status_emoji = "❌"
            status_text = "Mos emas"
        
        # Xabar matni
        message = f"""
{status_emoji} <b>Yangi loyiha: {status_text}</b>

📋 <b>Sarlavha:</b>
{job.title[:200]}

💰 <b>Byudjet:</b> {int(float(job.budget)) if job.budget else 'Belgilanmagan'} ₽
👤 <b>Buyurtmachi:</b> {client_link}

📊 <b>AI Baholash:</b>
• Ishonch: <b>{confidence:.0f}%</b>
• Xavf: <b>{risk:.0f}%</b>
• Tavsiya narxi: <b>{ai_data.get('estimated_price_rub', 'N/A')} ₽</b>
• Tavsiya muddati: <b>{ai_data.get('estimated_time_human', 'N/A')}</b>

📝 <b>Sabab:</b> {reason_text[:300]}{task_text}
"""
        
        # Tugmalar
        job_url = f"https://kwork.ru/projects/{job.kwork_id}"
        detail_url = f"{settings.DOMAIN}/job-detail?id={job.id}"
        
        buttons = [
            [
                {"text": "📋 To'liq tanishish", "url": detail_url}
            ],
            [
                {"text": "🔗 Kworkda ochish", "url": job_url}
            ],
            [
                {"text": "❌ O'tkazib yuborish", "callback_data": f"skip_{job.id}"}
            ]
        ]
        
        result = await self.send_message_with_buttons(message.strip(), buttons)
        
        # Message ID ni saqlash uchun qaytarish
        if result.get("ok") and result.get("result"):
            return {
                "success": True,
                "message_id": result["result"].get("message_id")
            }
        
        return {
            "success": False,
            "error": result.get("description", "Xatolik")
        }
    
    async def send_simple_job_notification(self, job) -> dict:
        """
        AI tahlilisiz oddiy e'lon xabarini yuborish
        API limit tugaganda yoki AI ishlamay qolganda ishlatiladi
        """
        import json
        
        # Kategoriya olish
        category_name = job.category
        if not category_name or category_name == "N/A":
            try:
                if job.kwork_json:
                    kwork_data = json.loads(job.kwork_json)
                    category_name = kwork_data.get("parent_category_name") or kwork_data.get("category_name") or "N/A"
            except:
                category_name = "N/A"
        
        # Client info
        client_name = job.client_name or "N/A"
        client_link = f'<a href="https://kwork.ru/user/{client_name}">{client_name}</a>' if client_name != "N/A" else "N/A"
        
        # Buyurtmachi statistikasi
        client_stats = ""
        if job.client_wants_count:
            client_stats += f"• Buyurtmalar: {job.client_wants_count} ta\n"
        if job.client_hired_percent:
            client_stats += f"• Yollash foizi: {job.client_hired_percent}%\n"
        
        # Description (qisqartirilgan)
        description = job.description or ""
        if len(description) > 500:
            description = description[:500] + "..."
        
        # Vaqt haqida ma'lumot
        time_info = ""
        if job.max_days:
            time_info = f"⏰ <b>Muddat:</b> {job.max_days} kun\n"
        if job.time_left:
            time_info += f"⏳ <b>Qolgan vaqt:</b> {job.time_left}\n"
        
        # Xabar matni
        message = f"""
🆕 <b>Yangi loyiha (AI tahlilsiz)</b>

📋 <b>Sarlavha:</b>
{job.title[:200]}

📁 <b>Kategoriya:</b> {category_name}

💰 <b>Byudjet:</b> {int(float(job.budget)) if job.budget else 'Belgilanmagan'} ₽
👤 <b>Buyurtmachi:</b> {client_link}
{client_stats}
{time_info}
<blockquote>📄 <b>Tavsif:</b>
{description}</blockquote>

⚠️ <i>AI tahlili hozircha mavjud emas (API limit)</i>
"""
        
        # Tugmalar
        job_url = f"https://kwork.ru/projects/{job.kwork_id}"
        detail_url = f"{settings.DOMAIN}/job-detail?id={job.id}"
        
        buttons = [
            [
                {"text": "📋 To'liq tanishish", "url": detail_url}
            ],
            [
                {"text": "🔗 Kworkda ochish", "url": job_url}
            ],
            [
                {"text": "❌ O'tkazib yuborish", "callback_data": f"skip_{job.id}"}
            ]
        ]
        
        result = await self.send_message_with_buttons(message.strip(), buttons)
        
        # Message ID ni saqlash uchun qaytarish
        if result.get("ok") and result.get("result"):
            return {
                "success": True,
                "message_id": result["result"].get("message_id")
            }
        
        return {
            "success": False,
            "error": result.get("description", "Xatolik")
        }
