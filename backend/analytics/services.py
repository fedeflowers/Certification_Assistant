"""
Business logic for analytics feature.
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_, distinct, case
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Certification, Question, QuizSession, SessionAnswer,
    AnalyticsCache
)
from analytics.schemas import (
    OverallStatsResponse, WeakAreaResponse, ProgressTrendItem,
    CertificationPerformance, RecentActivityItem
)


async def calculate_certification_accuracy(
    db: AsyncSession,
    certification_id: uuid.UUID
) -> Optional[float]:
    """Calculate overall accuracy for a certification."""
    from sqlalchemy import case
    result = await db.execute(
        select(
            func.count(SessionAnswer.id).label("total"),
            func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
        )
        .select_from(SessionAnswer)
        .join(Question, SessionAnswer.question_id == Question.id)
        .where(
            and_(
                Question.certification_id == certification_id,
                SessionAnswer.is_correct.isnot(None)
            )
        )
    )
    
    row = result.one()
    if row.total and row.total > 0:
        return round((row.correct / row.total) * 100, 1)
    return None


async def get_overall_stats(
    db: AsyncSession,
    certification_id: Optional[uuid.UUID] = None
) -> OverallStatsResponse:
    """Get overall statistics."""
    # Base query conditions
    conditions = [SessionAnswer.is_correct.isnot(None)]
    
    if certification_id:
        conditions.append(Question.certification_id == certification_id)
    
    # Total questions answered and correct
    result = await db.execute(
        select(
            func.count(SessionAnswer.id).label("total"),
            func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
        )
        .select_from(SessionAnswer)
        .join(Question, SessionAnswer.question_id == Question.id)
        .where(and_(*conditions))
    )
    
    row = result.one()
    total_answered = row.total or 0
    correct_answers = row.correct or 0
    accuracy = round((correct_answers / total_answered * 100), 1) if total_answered > 0 else 0
    
    # Calculate study streak
    streak = await calculate_study_streak(db)
    
    # Questions answered today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(SessionAnswer.id))
        .where(SessionAnswer.answered_at >= today_start)
    )
    questions_today = today_result.scalar() or 0
    
    # Total time spent (approximate based on sessions)
    time_result = await db.execute(
        select(func.sum(SessionAnswer.time_spent_seconds))
        .where(SessionAnswer.time_spent_seconds.isnot(None))
    )
    total_seconds = time_result.scalar() or 0
    total_minutes = total_seconds // 60
    
    # Calculate trend (compare last 7 days to previous 7 days)
    trend, trend_value = await calculate_accuracy_trend(db, certification_id)
    
    # Calculate exam readiness if certification is specified
    exam_readiness_score = None
    if certification_id:
        try:
            readiness_result = await calculate_exam_readiness(db, certification_id)
            exam_readiness_score = readiness_result.get("readiness_score")
        except Exception:
            pass
    
    return OverallStatsResponse(
        total_questions_answered=total_answered,
        correct_answers=correct_answers,
        accuracy=accuracy,
        study_streak=streak,
        total_time_spent_minutes=total_minutes,
        questions_today=questions_today,
        trend=trend,
        trend_value=trend_value,
        exam_readiness_score=exam_readiness_score
    )


async def calculate_study_streak(db: AsyncSession) -> int:
    """Calculate consecutive days with quiz activity."""
    # Get distinct dates with activity
    result = await db.execute(
        select(func.date(QuizSession.started_at).label("date"))
        .where(QuizSession.status == "completed")
        .group_by(func.date(QuizSession.started_at))
        .order_by(func.date(QuizSession.started_at).desc())
    )
    
    dates = [row.date for row in result]
    
    if not dates:
        return 0
    
    streak = 0
    today = date.today()
    expected_date = today
    
    for d in dates:
        if d == expected_date or d == expected_date - timedelta(days=1):
            streak += 1
            expected_date = d - timedelta(days=1)
        else:
            break
    
    return streak


async def calculate_accuracy_trend(
    db: AsyncSession,
    certification_id: Optional[uuid.UUID] = None
) -> tuple[Optional[str], Optional[float]]:
    """Calculate accuracy trend comparing recent to previous period."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    
    async def get_accuracy_for_period(start: datetime, end: datetime) -> Optional[float]:
        conditions = [
            SessionAnswer.answered_at >= start,
            SessionAnswer.answered_at < end,
            SessionAnswer.is_correct.isnot(None)
        ]
        
        if certification_id:
            conditions.append(Question.certification_id == certification_id)
        
        result = await db.execute(
            select(
                func.count(SessionAnswer.id).label("total"),
                func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
            )
            .select_from(SessionAnswer)
            .join(Question, SessionAnswer.question_id == Question.id)
            .where(and_(*conditions))
        )
        
        row = result.one()
        if row.total and row.total > 0:
            return (row.correct / row.total) * 100
        return None
    
    recent_accuracy = await get_accuracy_for_period(week_ago, now)
    previous_accuracy = await get_accuracy_for_period(two_weeks_ago, week_ago)
    
    if recent_accuracy is None or previous_accuracy is None:
        return None, None
    
    diff = recent_accuracy - previous_accuracy
    
    if diff > 1:
        return "up", round(diff, 1)
    elif diff < -1:
        return "down", round(abs(diff), 1)
    else:
        return "stable", 0


async def get_weak_areas(
    db: AsyncSession,
    certification_id: Optional[uuid.UUID] = None,
    threshold: float = 60.0
) -> List[WeakAreaResponse]:
    """Get topics with accuracy below threshold."""
    conditions = [
        Question.topic.isnot(None),
        SessionAnswer.is_correct.isnot(None)
    ]
    
    if certification_id:
        conditions.append(Question.certification_id == certification_id)
    
    result = await db.execute(
        select(
            Question.certification_id,
            Certification.name.label("cert_name"),
            Question.topic,
            func.count(SessionAnswer.id).label("total"),
            func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
        )
        .select_from(SessionAnswer)
        .join(Question, SessionAnswer.question_id == Question.id)
        .join(Certification, Question.certification_id == Certification.id)
        .where(and_(*conditions))
        .group_by(Question.certification_id, Certification.name, Question.topic)
    )
    
    weak_areas = []
    for row in result:
        if row.total > 0:
            accuracy = (row.correct / row.total) * 100
            if accuracy < threshold:
                weak_areas.append(WeakAreaResponse(
                    topic=row.topic,
                    total_questions=row.total,
                    correct=row.correct or 0,
                    accuracy=round(accuracy, 1),
                    certification_id=row.certification_id,
                    certification_name=row.cert_name
                ))
    
    # Sort by accuracy (lowest first)
    weak_areas.sort(key=lambda x: x.accuracy)
    
    return weak_areas


async def get_progress_trend(
    db: AsyncSession,
    certification_id: Optional[uuid.UUID] = None,
    days: int = 30
) -> List[ProgressTrendItem]:
    """Get accuracy trend over time."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    conditions = [
        SessionAnswer.answered_at >= start_date,
        SessionAnswer.is_correct.isnot(None)
    ]
    
    if certification_id:
        conditions.append(Question.certification_id == certification_id)
    
    result = await db.execute(
        select(
            func.date(SessionAnswer.answered_at).label("date"),
            func.count(SessionAnswer.id).label("total"),
            func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
        )
        .select_from(SessionAnswer)
        .join(Question, SessionAnswer.question_id == Question.id)
        .where(and_(*conditions))
        .group_by(func.date(SessionAnswer.answered_at))
        .order_by(func.date(SessionAnswer.answered_at))
    )
    
    trend = []
    for row in result:
        accuracy = (row.correct / row.total * 100) if row.total > 0 else 0
        trend.append(ProgressTrendItem(
            date=row.date,
            accuracy=round(accuracy, 1),
            questions_answered=row.total,
            correct=row.correct or 0
        ))
    
    return trend


async def get_performance_by_certification(
    db: AsyncSession
) -> List[CertificationPerformance]:
    """Get performance statistics by certification."""
    # Get all certifications with their stats
    result = await db.execute(
        select(
            Certification.id,
            Certification.name,
            Certification.total_questions,
            func.count(distinct(SessionAnswer.question_id)).label("answered"),
            func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
        )
        .select_from(Certification)
        .outerjoin(Question, Question.certification_id == Certification.id)
        .outerjoin(SessionAnswer, SessionAnswer.question_id == Question.id)
        .group_by(Certification.id, Certification.name, Certification.total_questions)
    )
    
    performances = []
    for row in result:
        answered = row.answered or 0
        correct = row.correct or 0
        accuracy = (correct / answered * 100) if answered > 0 else 0
        
        performances.append(CertificationPerformance(
            certification_id=row.id,
            certification_name=row.name,
            total_questions=row.total_questions,
            answered=answered,
            correct=correct,
            accuracy=round(accuracy, 1)
        ))
    
    return performances


async def calculate_exam_readiness(
    db: AsyncSession,
    certification_id: uuid.UUID
) -> Dict[str, Any]:
    """Calculate exam readiness score based on topic coverage and preparation."""
    cert = await db.get(Certification, certification_id)
    if not cert:
        return {"readiness_score": 0}
    
    # Get all topics with their stats
    topics_result = await db.execute(
        select(
            Question.topic,
            func.count(Question.id).label("total_questions")
        )
        .where(Question.certification_id == certification_id)
        .group_by(Question.topic)
    )
    
    topics_data = []
    total_topics = 0
    topics_covered = 0
    topics_mastered = 0  # accuracy >= 70%
    total_topic_accuracy = 0
    
    for row in topics_result:
        total_topics += 1
        topic_name = row.topic if row.topic else "Uncategorized"
        total_in_topic = row.total_questions
        
        # Get stats for this topic
        if row.topic is not None:
            stats_result = await db.execute(
                select(
                    func.count(distinct(SessionAnswer.question_id)).label("answered"),
                    func.count(SessionAnswer.id).label("attempts"),
                    func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
                )
                .select_from(SessionAnswer)
                .join(Question, SessionAnswer.question_id == Question.id)
                .where(
                    and_(
                        Question.certification_id == certification_id,
                        Question.topic == row.topic,
                        SessionAnswer.is_correct.isnot(None)
                    )
                )
            )
        else:
            stats_result = await db.execute(
                select(
                    func.count(distinct(SessionAnswer.question_id)).label("answered"),
                    func.count(SessionAnswer.id).label("attempts"),
                    func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
                )
                .select_from(SessionAnswer)
                .join(Question, SessionAnswer.question_id == Question.id)
                .where(
                    and_(
                        Question.certification_id == certification_id,
                        Question.topic.is_(None),
                        SessionAnswer.is_correct.isnot(None)
                    )
                )
            )
        
        stats_row = stats_result.one()
        answered = stats_row.answered or 0
        attempts = stats_row.attempts or 0
        correct = stats_row.correct or 0
        
        # Calculate topic coverage and accuracy
        topic_coverage = (answered / total_in_topic * 100) if total_in_topic > 0 else 0
        topic_accuracy = (correct / attempts * 100) if attempts > 0 else 0
        
        # Track topic stats
        if answered > 0:
            topics_covered += 1
            total_topic_accuracy += topic_accuracy
            if topic_accuracy >= 70:
                topics_mastered += 1
        
        topics_data.append({
            "topic": topic_name,
            "total": total_in_topic,
            "answered": answered,
            "coverage": round(topic_coverage, 1),
            "accuracy": round(topic_accuracy, 1) if attempts > 0 else None,
            "mastered": topic_accuracy >= 70 if attempts > 0 else False
        })
    
    # Calculate component scores
    # 1. Topic Coverage Score (how many topics have been studied)
    topic_coverage_score = (topics_covered / total_topics * 100) if total_topics > 0 else 0
    
    # 2. Topic Mastery Score (how many topics have accuracy >= 70%)
    topic_mastery_score = (topics_mastered / total_topics * 100) if total_topics > 0 else 0
    
    # 3. Average Topic Accuracy
    avg_topic_accuracy = (total_topic_accuracy / topics_covered) if topics_covered > 0 else 0
    
    # 4. Question Coverage (% of unique questions answered)
    coverage_result = await db.execute(
        select(func.count(distinct(SessionAnswer.question_id)))
        .select_from(SessionAnswer)
        .join(Question, SessionAnswer.question_id == Question.id)
        .where(Question.certification_id == certification_id)
    )
    questions_answered = coverage_result.scalar() or 0
    question_coverage_score = (questions_answered / cert.total_questions * 100) if cert.total_questions > 0 else 0
    
    # Component weights
    topic_coverage_weight = 0.25   # Have you studied all topics?
    topic_mastery_weight = 0.30    # How many topics are you good at?
    accuracy_weight = 0.30         # Overall accuracy across topics
    question_coverage_weight = 0.15  # How many questions have you seen?
    
    # Calculate final readiness score
    readiness_score = (
        topic_coverage_score * topic_coverage_weight +
        topic_mastery_score * topic_mastery_weight +
        avg_topic_accuracy * accuracy_weight +
        question_coverage_score * question_coverage_weight
    )
    
    # Sort topics by priority (not mastered first, then by accuracy)
    topics_data.sort(key=lambda x: (x["mastered"], x["accuracy"] or 0))
    
    # Generate recommendation
    uncovered_topics = [t for t in topics_data if t["answered"] == 0]
    weak_topics = [t for t in topics_data if t["accuracy"] is not None and t["accuracy"] < 70]
    
    if readiness_score >= 80:
        recommendation = "Excellent preparation! You're ready for the exam."
    elif readiness_score >= 60:
        if len(uncovered_topics) > 0:
            recommendation = f"Good progress! Study these topics: {', '.join([t['topic'] for t in uncovered_topics[:3]])}"
        elif len(weak_topics) > 0:
            recommendation = f"Good progress! Improve on: {', '.join([t['topic'] for t in weak_topics[:3]])}"
        else:
            recommendation = "Good progress! Keep practicing to solidify your knowledge."
    elif readiness_score >= 40:
        if len(uncovered_topics) > 0:
            recommendation = f"Cover all topics first. Missing: {', '.join([t['topic'] for t in uncovered_topics[:3]])}"
        else:
            recommendation = "Keep studying. Focus on topics with lower accuracy."
    else:
        recommendation = f"More study needed. Start with the {total_topics} topics systematically."
    
    return {
        "certification_id": certification_id,
        "certification_name": cert.name,
        "readiness_score": round(readiness_score, 1),
        "components": {
            "topic_coverage": round(topic_coverage_score, 1),
            "topic_mastery": round(topic_mastery_score, 1),
            "accuracy": round(avg_topic_accuracy, 1),
            "question_coverage": round(question_coverage_score, 1)
        },
        "topic_stats": {
            "total": total_topics,
            "covered": topics_covered,
            "mastered": topics_mastered
        },
        "topics": topics_data[:10],  # Top 10 topics to focus on
        "recommendation": recommendation
    }


async def get_recent_activity(
    db: AsyncSession,
    limit: int = 10
) -> List[RecentActivityItem]:
    """Get recent activity timeline."""
    activities = []
    
    # Get recent completed sessions
    sessions_result = await db.execute(
        select(QuizSession, Certification.name)
        .join(Certification, QuizSession.certification_id == Certification.id)
        .where(QuizSession.status == "completed")
        .order_by(QuizSession.completed_at.desc())
        .limit(limit)
    )
    
    for session, cert_name in sessions_result:
        accuracy = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
        
        activities.append(RecentActivityItem(
            type="quiz_completed",
            title=f"Completed {session.total_questions} questions",
            description=f"{cert_name} - {round(accuracy)}% accuracy",
            timestamp=session.completed_at or session.started_at,
            data={
                "session_id": str(session.id),
                "correct": session.correct_answers,
                "total": session.total_questions
            }
        ))
    
    # Get recent certifications added
    certs_result = await db.execute(
        select(Certification)
        .where(Certification.processing_status == "completed")
        .order_by(Certification.created_at.desc())
        .limit(5)
    )
    
    for cert in certs_result.scalars():
        activities.append(RecentActivityItem(
            type="certification_added",
            title=f"Added {cert.name}",
            description=f"{cert.total_questions} questions",
            timestamp=cert.created_at,
            data={"certification_id": str(cert.id)}
        ))
    
    # Sort all activities by timestamp
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    
    return activities[:limit]


async def refresh_analytics(
    db: AsyncSession,
    certification_id: Optional[uuid.UUID] = None
):
    """Refresh analytics cache after session completion."""
    # For now, analytics are calculated on-demand
    # This function can be expanded to pre-calculate and cache metrics
    pass
