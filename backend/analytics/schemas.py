"""
Pydantic schemas for analytics feature.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel


class OverallStatsResponse(BaseModel):
    """Schema for overall statistics."""
    total_questions_answered: int
    correct_answers: int
    accuracy: float
    study_streak: int
    total_time_spent_minutes: int
    questions_today: int
    trend: Optional[str] = None  # "up", "down", or "stable"
    trend_value: Optional[float] = None
    exam_readiness_score: Optional[float] = None


class WeakAreaResponse(BaseModel):
    """Schema for weak area."""
    topic: str
    total_questions: int
    correct: int
    accuracy: float
    certification_id: UUID
    certification_name: str


class ProgressTrendItem(BaseModel):
    """Schema for progress trend data point."""
    date: date
    accuracy: float
    questions_answered: int
    correct: int


class ProgressTrendResponse(BaseModel):
    """Schema for progress trend."""
    data: List[ProgressTrendItem]
    period: str  # "7d", "30d", "all"


class CertificationPerformance(BaseModel):
    """Schema for certification performance."""
    certification_id: UUID
    certification_name: str
    total_questions: int
    answered: int
    correct: int
    accuracy: float


class PerformanceByCertResponse(BaseModel):
    """Schema for performance by certification."""
    certifications: List[CertificationPerformance]


class TopicReadiness(BaseModel):
    """Schema for topic readiness."""
    topic: str
    total: int
    answered: int
    coverage: float
    accuracy: Optional[float] = None
    mastered: bool = False


class TopicStats(BaseModel):
    """Schema for topic statistics."""
    total: int
    covered: int
    mastered: int


class ExamReadinessResponse(BaseModel):
    """Schema for exam readiness score."""
    certification_id: UUID
    certification_name: str
    readiness_score: float  # 0-100
    components: Dict[str, float]  # Breakdown of score components
    topic_stats: Optional[TopicStats] = None
    topics: Optional[List[TopicReadiness]] = None
    recommendation: str


class RecentActivityItem(BaseModel):
    """Schema for recent activity item."""
    type: str  # "quiz_completed", "certification_added", "milestone"
    title: str
    description: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


class RecentActivityResponse(BaseModel):
    """Schema for recent activity."""
    activities: List[RecentActivityItem]
