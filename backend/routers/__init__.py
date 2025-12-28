"""
Kwork AI PM - Routers Package
"""
from routers.auth import router as auth_router
from routers.jobs import router as jobs_router
from routers.settings import router as settings_router
from routers.kwork import router as kwork_router
from routers.webhook import router as webhook_router
from routers.telegram_callback import router as telegram_callback_router

__all__ = [
    "auth_router", 
    "jobs_router", 
    "settings_router",
    "kwork_router",
    "webhook_router",
    "telegram_callback_router"
]

