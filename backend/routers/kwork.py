"""
Kwork AI PM - Kwork Router
Kwork login/logout va status uchun API endpointlar
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from database import get_db
from routers.auth import get_current_user
from services.kwork_service import KworkService


router = APIRouter(prefix="/api/kwork", tags=["Kwork"])


class KworkLoginRequest(BaseModel):
    username: str
    password: str


class KworkLoginResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    user_id: Optional[str] = None


class KworkStatusResponse(BaseModel):
    logged_in: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    last_check: Optional[str] = None


@router.post("/login", response_model=KworkLoginResponse)
async def kwork_login(
    request: KworkLoginRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Kwork ga kirish"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat admin login qila oladi"
        )
    
    service = KworkService(db)
    result = await service.login(request.username, request.password)
    
    return KworkLoginResponse(**result)


@router.post("/logout")
async def kwork_logout(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Kwork dan chiqish"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat admin chiqishi mumkin"
        )
    
    service = KworkService(db)
    result = await service.logout()
    
    return result


@router.get("/status", response_model=KworkStatusResponse)
async def kwork_status(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Kwork holati"""
    service = KworkService(db)
    result = await service.get_status()
    
    return KworkStatusResponse(**result)


@router.post("/check-projects")
async def check_projects(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """E'lonlarni tekshirish (manual)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat admin tekshira oladi"
        )
    
    service = KworkService(db)
    result = await service.fetch_projects()
    
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error"),
            "count": 0
        }
    
    return {
        "success": True,
        "count": result.get("count", 0),
        "message": f"{result.get('count', 0)} ta e'lon topildi"
    }
