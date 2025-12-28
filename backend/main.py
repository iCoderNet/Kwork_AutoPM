"""
Kwork AI Project Manager - Main Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from config import settings
from database import init_db, async_session
from routers import auth_router, jobs_router, settings_router, kwork_router, webhook_router, telegram_callback_router
from routers.settings import init_default_settings
from services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    print("🚀 Starting Kwork AI PM...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Initialize default settings and admin user
    async with async_session() as db:
        await init_default_settings(db)
        await AuthService.create_default_admin(db)
        print("✅ Default settings and admin user ready")
    
    print(f"🌐 Server running at {settings.DOMAIN}")
    print(f"📚 API Docs: {settings.DOMAIN}/docs")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Kwork AI PM...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Project Manager for Kwork freelance platform",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(settings_router)
app.include_router(kwork_router)
app.include_router(webhook_router)
app.include_router(telegram_callback_router)

# Serve static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# Root routes - serve frontend
@app.get("/")
async def serve_index():
    """Serve login page"""
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.get("/dashboard")
async def serve_dashboard():
    """Serve dashboard page"""
    return FileResponse(os.path.join(frontend_path, "dashboard.html"))


@app.get("/job-detail")
async def serve_job_detail():
    """Serve job detail page"""
    return FileResponse(os.path.join(frontend_path, "job-detail.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
