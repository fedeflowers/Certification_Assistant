"""
API routes for analytics feature.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.dependencies import get_db
from analytics.schemas import (
    OverallStatsResponse, WeakAreaResponse, ProgressTrendResponse,
    PerformanceByCertResponse, ExamReadinessResponse, RecentActivityResponse
)
from analytics.services import (
    get_overall_stats, get_weak_areas, get_progress_trend,
    get_performance_by_certification, calculate_exam_readiness,
    get_recent_activity
)


router = APIRouter()


@router.get("/overall", response_model=OverallStatsResponse)
async def get_overall_statistics(
    certification_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get overall statistics."""
    return await get_overall_stats(db, certification_id)


@router.get("/weak-areas", response_model=list[WeakAreaResponse])
async def get_weak_area_list(
    certification_id: Optional[uuid.UUID] = Query(None),
    threshold: float = Query(60.0, description="Accuracy threshold (0-100)"),
    db: AsyncSession = Depends(get_db)
):
    """Get topics with accuracy below threshold."""
    return await get_weak_areas(db, certification_id, threshold)


@router.get("/progress-trend", response_model=ProgressTrendResponse)
async def get_progress_trend_data(
    certification_id: Optional[uuid.UUID] = Query(None),
    period: str = Query("30d", pattern="^(7d|30d|all)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get accuracy trend over time."""
    days_map = {"7d": 7, "30d": 30, "all": 365}
    days = days_map.get(period, 30)
    
    trend = await get_progress_trend(db, certification_id, days)
    
    return ProgressTrendResponse(data=trend, period=period)


@router.get("/performance", response_model=PerformanceByCertResponse)
async def get_performance_statistics(
    db: AsyncSession = Depends(get_db)
):
    """Get performance statistics by certification."""
    certifications = await get_performance_by_certification(db)
    
    return PerformanceByCertResponse(certifications=certifications)


@router.get("/exam-readiness/{certification_id}", response_model=ExamReadinessResponse)
async def get_exam_readiness_score(
    certification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get exam readiness score for a certification."""
    result = await calculate_exam_readiness(db, certification_id)
    
    return ExamReadinessResponse(**result)


@router.get("/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity_list(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get recent activity timeline."""
    activities = await get_recent_activity(db, limit)
    
    return RecentActivityResponse(activities=activities)


@router.post("/refresh")
async def refresh_analytics_cache(
    certification_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Force refresh of analytics cache."""
    from analytics.services import refresh_analytics
    await refresh_analytics(db, certification_id)
    
    return {"message": "Analytics refreshed successfully"}
