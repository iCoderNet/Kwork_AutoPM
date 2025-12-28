"""
Kwork AI PM - Settings Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from database import get_db
from models.settings import Settings, DEFAULT_SETTINGS
from routers.auth import get_current_user
from services.telegram_service import TelegramService

router = APIRouter(prefix="/api/settings", tags=["Settings"])


# Pydantic Models
class SettingItem(BaseModel):
    key: str
    value: Optional[str]
    category: str
    description: Optional[str]
    is_secret: bool
    
    class Config:
        from_attributes = True


class SettingsResponse(BaseModel):
    settings: Dict[str, Dict[str, Any]]


class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, str]


class AIStatusResponse(BaseModel):
    enabled: bool
    model: Optional[str]
    has_api_key: bool
    has_prompt: bool


class TelegramStatusResponse(BaseModel):
    enabled: bool
    has_token: bool
    has_group_id: bool


class TestTelegramResponse(BaseModel):
    success: bool
    message: str
    bot_info: Optional[dict] = None


# Helper functions
async def get_setting_value(db: AsyncSession, key: str) -> Optional[str]:
    """Get setting value by key"""
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting_value(db: AsyncSession, key: str, value: str):
    """Set setting value"""
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = value
    else:
        # Find default setting info
        default = next((s for s in DEFAULT_SETTINGS if s["key"] == key), None)
        if default:
            new_setting = Settings(
                key=key,
                value=value,
                category=default.get("category", "system"),
                description=default.get("description", ""),
                is_secret=default.get("is_secret", 0)
            )
            db.add(new_setting)


async def init_default_settings(db: AsyncSession):
    """Initialize default settings if not exist"""
    for default in DEFAULT_SETTINGS:
        result = await db.execute(
            select(Settings).where(Settings.key == default["key"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            setting = Settings(
                key=default["key"],
                value=default["value"],
                category=default["category"],
                description=default.get("description", ""),
                is_secret=default.get("is_secret", 0)
            )
            db.add(setting)
    
    await db.commit()


# Routes
@router.get("", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all settings grouped by category"""
    result = await db.execute(select(Settings))
    all_settings = result.scalars().all()
    
    # Group by category
    grouped: Dict[str, Dict[str, Any]] = {}
    
    for setting in all_settings:
        if setting.category not in grouped:
            grouped[setting.category] = {}
        
        # Hide secret values, just indicate they exist
        value = setting.value
        if setting.is_secret and value:
            value = "••••••••"
        
        grouped[setting.category][setting.key] = {
            "value": value,
            "description": setting.description,
            "is_secret": bool(setting.is_secret),
            "has_value": bool(setting.value)
        }
    
    return SettingsResponse(settings=grouped)


@router.put("")
async def update_settings(
    request: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update multiple settings"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can update settings"
        )
    
    for key, value in request.settings.items():
        # Skip empty secret updates (user didn't change them)
        if value == "••••••••":
            continue
        await set_setting_value(db, key, value)
    
    await db.commit()
    return {"message": "Settings updated successfully", "success": True}


@router.get("/ai-status", response_model=AIStatusResponse)
async def get_ai_status(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get AI PM status"""
    enabled = await get_setting_value(db, "ai_enabled")
    model = await get_setting_value(db, "ai_model")
    api_key = await get_setting_value(db, "ai_api_key")
    prompt = await get_setting_value(db, "ai_prompt")
    
    return AIStatusResponse(
        enabled=enabled == "true",
        model=model,
        has_api_key=bool(api_key),
        has_prompt=bool(prompt)
    )


@router.post("/ai-toggle")
async def toggle_ai(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Toggle AI PM on/off"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can toggle AI"
        )
    
    current = await get_setting_value(db, "ai_enabled")
    new_value = "false" if current == "true" else "true"
    
    await set_setting_value(db, "ai_enabled", new_value)
    await db.commit()
    
    status_msg = "yoqildi" if new_value == "true" else "o'chirildi"
    return {
        "message": f"AI PM {status_msg}",
        "enabled": new_value == "true"
    }


@router.get("/telegram-status", response_model=TelegramStatusResponse)
async def get_telegram_status(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get Telegram integration status"""
    enabled = await get_setting_value(db, "telegram_enabled")
    token = await get_setting_value(db, "telegram_bot_token")
    group_id = await get_setting_value(db, "telegram_group_id")
    
    return TelegramStatusResponse(
        enabled=enabled == "true",
        has_token=bool(token),
        has_group_id=bool(group_id)
    )


@router.post("/test-telegram", response_model=TestTelegramResponse)
async def test_telegram(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Test Telegram bot connection"""
    telegram_service = await TelegramService.from_db(db)
    
    if not telegram_service:
        return TestTelegramResponse(
            success=False,
            message="Telegram sozlamalari to'liq emas. Bot token va Group ID ni kiriting."
        )
    
    try:
        result = await telegram_service.test_connection()
        
        if result.get("ok"):
            bot_info = result.get("result", {})
            
            # Try to send test message
            test_result = await telegram_service.send_message(
                "✅ <b>Test xabar</b>\n\nKwork AI PM Telegram integratsiyasi muvaffaqiyatli ishlayapti!"
            )
            
            if test_result.get("ok"):
                return TestTelegramResponse(
                    success=True,
                    message="Telegram bot muvaffaqiyatli ulandi va test xabar yuborildi!",
                    bot_info={
                        "username": bot_info.get("username"),
                        "first_name": bot_info.get("first_name")
                    }
                )
            else:
                return TestTelegramResponse(
                    success=False,
                    message=f"Bot ulandi, lekin xabar yuborib bo'lmadi: {test_result.get('description', 'Unknown error')}"
                )
        else:
            return TestTelegramResponse(
                success=False,
                message=f"Bot ulanmadi: {result.get('description', 'Unknown error')}"
            )
    except Exception as e:
        return TestTelegramResponse(
            success=False,
            message=f"Xatolik yuz berdi: {str(e)}"
        )


class AITestRequest(BaseModel):
    job_description: str


class AITestResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None


@router.post("/test-ai", response_model=AITestResponse)
async def test_ai(
    request: AITestRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Test AI with a job description"""
    from services.ai_service import AIService
    
    ai_service = await AIService.from_db(db)
    
    if not ai_service:
        return AITestResponse(
            success=False,
            error="AI sozlamalari to'liq emas. Model va API key ni o'rnating."
        )
    
    try:
        result = await ai_service.generate_response(request.job_description, "")
        
        if result.get("success"):
            return AITestResponse(
                success=True,
                text=result.get("text"),
                model=result.get("model")
            )
        else:
            return AITestResponse(
                success=False,
                error=result.get("error", "Noma'lum xato")
            )
    except Exception as e:
        return AITestResponse(
            success=False,
            error=f"Xatolik yuz berdi: {str(e)}"
        )


class WebhookResponse(BaseModel):
    success: bool
    message: str
    webhook_url: Optional[str] = None


@router.post("/setup-webhook", response_model=WebhookResponse)
async def setup_telegram_webhook(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Setup Telegram webhook for callback buttons"""
    from config import settings
    
    telegram_service = await TelegramService.from_db(db)
    
    if not telegram_service:
        return WebhookResponse(
            success=False,
            message="Telegram sozlamalari to'liq emas. Bot token va Group ID ni kiriting."
        )
    
    try:
        # Webhook URL - DOMAIN + /api/telegram/callback
        webhook_url = f"{settings.DOMAIN}/api/telegram/callback"
        
        result = await telegram_service.set_webhook(webhook_url)
        
        if result.get("ok"):
            return WebhookResponse(
                success=True,
                message="Telegram webhook muvaffaqiyatli o'rnatildi!",
                webhook_url=webhook_url
            )
        else:
            return WebhookResponse(
                success=False,
                message=f"Webhook o'rnatib bo'lmadi: {result.get('description', 'Unknown error')}"
            )
    except Exception as e:
        return WebhookResponse(
            success=False,
            message=f"Xatolik yuz berdi: {str(e)}"
        )


@router.get("/webhook-info", response_model=WebhookResponse)
async def get_webhook_info(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current Telegram webhook info"""
    telegram_service = await TelegramService.from_db(db)
    
    if not telegram_service:
        return WebhookResponse(
            success=False,
            message="Telegram sozlamalari to'liq emas."
        )
    
    try:
        result = await telegram_service.get_webhook_info()
        
        if result.get("ok"):
            info = result.get("result", {})
            url = info.get("url", "")
            
            if url:
                return WebhookResponse(
                    success=True,
                    message=f"Webhook faol. Pending updates: {info.get('pending_update_count', 0)}",
                    webhook_url=url
                )
            else:
                return WebhookResponse(
                    success=False,
                    message="Webhook o'rnatilmagan"
                )
        else:
            return WebhookResponse(
                success=False,
                message=f"Webhook ma'lumotini olish imkoni bo'lmadi: {result.get('description', 'Unknown error')}"
            )
    except Exception as e:
        return WebhookResponse(
            success=False,
            message=f"Xatolik yuz berdi: {str(e)}"
        )
