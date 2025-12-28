"""
Kwork AI PM - Jobs Router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models.job import Job, JobStatus
from routers.auth import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# Pydantic Models
class JobResponse(BaseModel):
    id: int
    kwork_id: str
    title: str
    description: Optional[str]
    budget: Optional[str]
    category: Optional[str]
    client_name: Optional[str]
    status: str
    ai_response: Optional[str]
    confidence_score: Optional[float]
    risk_score: Optional[float]
    ai_reason: Optional[str]
    estimated_price: Optional[str]
    estimated_time: Optional[str]
    telegram_sent: bool
    created_at: datetime
    responded_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class JobStatsResponse(BaseModel):
    total: int
    pending: int
    responded: int
    skipped: int
    failed: int
    telegram_sent: int
    avg_confidence: Optional[float]
    avg_risk: Optional[float]


class JobStatusUpdate(BaseModel):
    status: str


# Routes
@router.get("", response_model=JobListResponse)
async def get_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    telegram_sent: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get paginated list of jobs with filters"""
    # Base query
    query = select(Job)
    count_query = select(func.count(Job.id))
    
    # Apply filters
    if status and status != "all":
        try:
            job_status = JobStatus(status)
            query = query.where(Job.status == job_status)
            count_query = count_query.where(Job.status == job_status)
        except ValueError:
            pass
    
    if telegram_sent is not None:
        query = query.where(Job.telegram_sent == telegram_sent)
        count_query = count_query.where(Job.telegram_sent == telegram_sent)
    
    if search:
        search_filter = or_(
            Job.title.ilike(f"%{search}%"),
            Job.description.ilike(f"%{search}%"),
            Job.kwork_id.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    offset = (page - 1) * per_page
    query = query.order_by(desc(Job.created_at)).offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    total_pages = (total + per_page - 1) // per_page
    
    return JobListResponse(
        items=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get job statistics for dashboard"""
    # Total count
    total_result = await db.execute(select(func.count(Job.id)))
    total = total_result.scalar() or 0
    
    # Status counts
    pending_result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.PENDING)
    )
    pending = pending_result.scalar() or 0
    
    responded_result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.RESPONDED)
    )
    responded = responded_result.scalar() or 0
    
    skipped_result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.SKIPPED)
    )
    skipped = skipped_result.scalar() or 0
    
    failed_result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.FAILED)
    )
    failed = failed_result.scalar() or 0
    
    # Telegram sent count
    telegram_result = await db.execute(
        select(func.count(Job.id)).where(Job.telegram_sent == True)
    )
    telegram_sent = telegram_result.scalar() or 0
    
    # Average scores
    avg_confidence_result = await db.execute(
        select(func.avg(Job.confidence_score)).where(Job.confidence_score.isnot(None))
    )
    avg_confidence = avg_confidence_result.scalar()
    
    avg_risk_result = await db.execute(
        select(func.avg(Job.risk_score)).where(Job.risk_score.isnot(None))
    )
    avg_risk = avg_risk_result.scalar()
    
    return JobStatsResponse(
        total=total,
        pending=pending,
        responded=responded,
        skipped=skipped,
        failed=failed,
        telegram_sent=telegram_sent,
        avg_confidence=round(avg_confidence, 2) if avg_confidence else None,
        avg_risk=round(avg_risk, 2) if avg_risk else None
    )


@router.get("/{job_id}")
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get single job by ID with all details"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job.to_dict()


@router.put("/{job_id}/status")
async def update_job_status(
    job_id: int,
    update: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update job status"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    try:
        new_status = JobStatus(update.status)
        job.status = new_status
        if new_status == JobStatus.RESPONDED:
            job.responded_at = datetime.utcnow()
        await db.commit()
        
        return {"message": "Status updated", "status": new_status.value}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {update.status}"
        )
