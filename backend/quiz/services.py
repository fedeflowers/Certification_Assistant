"""
Business logic for quiz feature.
"""
import uuid
import random
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import re

from shared.models import (
    Certification, Question, QuizSession, SessionAnswer,
    BookmarkedQuestion
)
from quiz.schemas import QuizSuggestion


def _extract_answer_letters(answer: str) -> set[str]:
    """Extract answer letters from an answer string.
    Handles formats like 'B', 'A,C', 'A, C', 'A. Foo, C. Bar', 'AC',
    'A. Foo\\nC. Bar', 'A. Foo and C. Bar'."""
    # Split by comma, newline, or ' and '
    parts = re.split(r'[,\n]| and ', answer)
    letters = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^([A-Za-z])(?:\.|\b)', part)
        if m:
            letters.add(m.group(1).upper())
    if letters:
        return letters
    # Fallback: consecutive uppercase letters (e.g. "AC")
    stripped = answer.strip().upper()
    if stripped.isalpha() and len(stripped) <= 6:
        return set(stripped)
    # Last resort: first character
    if stripped:
        return {stripped[0]}
    return set()


def check_answer_correct(user_answer: str, correct_answer: str) -> bool:
    """Check if user answer matches correct answer, supporting multi-select."""
    user_letters = _extract_answer_letters(user_answer)
    correct_letters = _extract_answer_letters(correct_answer)
    return user_letters == correct_letters


async def get_weak_topics(
    db: AsyncSession,
    certification_id: uuid.UUID,
    threshold: float = 60.0
) -> List[str]:
    """Get topics with accuracy below threshold."""
    # Get all answered questions with their topics
    result = await db.execute(
        select(
            Question.topic,
            func.count(SessionAnswer.id).label("total"),
            func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
        )
        .join(SessionAnswer, SessionAnswer.question_id == Question.id)
        .where(
            and_(
                Question.certification_id == certification_id,
                Question.topic.isnot(None),
                SessionAnswer.is_correct.isnot(None)
            )
        )
        .group_by(Question.topic)
    )
    
    weak_topics = []
    for row in result:
        if row.total > 0:
            accuracy = (row.correct / row.total) * 100
            if accuracy < threshold:
                weak_topics.append(row.topic)
    
    return weak_topics


async def get_topics_for_certification(
    db: AsyncSession,
    certification_id: uuid.UUID
) -> List[Dict[str, Any]]:
    """Get all topics for a certification with question counts and accuracy."""
    from quiz.schemas import TopicInfo
    
    # Get topics with counts and accuracy
    result = await db.execute(
        select(
            Question.topic,
            func.count(Question.id).label("question_count")
        )
        .where(Question.certification_id == certification_id)
        .group_by(Question.topic)
        .order_by(func.count(Question.id).desc())
    )
    
    topics = []
    for row in result:
        topic_name = row.topic if row.topic else "Uncategorized"
        
        # Get accuracy for this topic
        accuracy_result = await db.execute(
            select(
                func.count(SessionAnswer.id).label("total"),
                func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
            )
            .select_from(SessionAnswer)
            .join(Question, SessionAnswer.question_id == Question.id)
            .where(
                and_(
                    Question.certification_id == certification_id,
                    Question.topic == row.topic if row.topic else Question.topic.is_(None),
                    SessionAnswer.is_correct.isnot(None)
                )
            )
        )
        acc_row = accuracy_result.one()
        accuracy = None
        if acc_row.total and acc_row.total > 0:
            accuracy = round((acc_row.correct / acc_row.total) * 100, 1)
        
        topics.append(TopicInfo(
            topic=topic_name,
            question_count=row.question_count,
            accuracy=accuracy
        ))
    
    return topics


async def get_questions_for_session(
    db: AsyncSession,
    certification_id: uuid.UUID,
    session_type: str,
    question_count: int = 20,
    questions_per_topic: int = None
) -> List[uuid.UUID]:
    """Get question IDs for a session based on type."""
    
    if session_type == "weak_areas":
        # Get questions from weak topics
        weak_topics = await get_weak_topics(db, certification_id)
        
        if weak_topics:
            result = await db.execute(
                select(Question.id)
                .where(
                    and_(
                        Question.certification_id == certification_id,
                        Question.topic.in_(weak_topics)
                    )
                )
                .order_by(func.random())
                .limit(question_count)
            )
        else:
            # No weak topics identified, use random
            result = await db.execute(
                select(Question.id)
                .where(Question.certification_id == certification_id)
                .order_by(func.random())
                .limit(question_count)
            )
        
    elif session_type == "review":
        # Get bookmarked questions
        result = await db.execute(
            select(Question.id)
            .join(BookmarkedQuestion, BookmarkedQuestion.question_id == Question.id)
            .where(Question.certification_id == certification_id)
            .order_by(BookmarkedQuestion.bookmarked_at.desc())
            .limit(question_count)
        )
        
    elif session_type == "random":
        # Random questions
        result = await db.execute(
            select(Question.id)
            .where(Question.certification_id == certification_id)
            .order_by(func.random())
            .limit(question_count)
        )
        
    elif session_type == "stratified":
        # Stratified by topic - distribute question_count across topics
        # prioritizing topics with lower accuracy or not yet answered
        question_ids = []
        
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
        
        for row in topics_result:
            topic_name = row.topic
            total_in_topic = row.total_questions
            
            # Get accuracy for this topic (lower accuracy = higher priority)
            if topic_name is not None:
                acc_result = await db.execute(
                    select(
                        func.count(SessionAnswer.id).label("answered"),
                        func.sum(case((SessionAnswer.is_correct == True, 1), else_=0)).label("correct")
                    )
                    .select_from(SessionAnswer)
                    .join(Question, SessionAnswer.question_id == Question.id)
                    .where(
                        and_(
                            Question.certification_id == certification_id,
                            Question.topic == topic_name,
                            SessionAnswer.is_correct.isnot(None)
                        )
                    )
                )
            else:
                acc_result = await db.execute(
                    select(
                        func.count(SessionAnswer.id).label("answered"),
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
            
            acc_row = acc_result.one()
            answered = acc_row.answered or 0
            correct = acc_row.correct or 0
            
            # Calculate priority score (lower accuracy = higher priority, never answered = highest)
            if answered == 0:
                priority = 1000  # Highest priority for unanswered topics
            else:
                accuracy = (correct / answered) * 100
                priority = 100 - accuracy  # Lower accuracy = higher priority
            
            topics_data.append({
                "topic": topic_name,
                "total": total_in_topic,
                "answered": answered,
                "priority": priority
            })
        
        # Sort by priority (highest first = topics that need more work)
        topics_data.sort(key=lambda x: x["priority"], reverse=True)
        
        # Distribute questions proportionally across topics
        num_topics = len(topics_data)
        if num_topics == 0:
            return []
        
        # Calculate how many questions per topic (at least 1 per topic if possible)
        base_per_topic = max(1, question_count // num_topics)
        remaining = question_count - (base_per_topic * num_topics)
        
        # Collect questions from each topic
        for i, topic_info in enumerate(topics_data):
            # Give extra questions to higher priority topics
            extra = 1 if i < remaining else 0
            count_for_topic = min(base_per_topic + extra, topic_info["total"])
            
            topic_name = topic_info["topic"]
            if topic_name is not None:
                topic_result = await db.execute(
                    select(Question.id)
                    .where(
                        and_(
                            Question.certification_id == certification_id,
                            Question.topic == topic_name
                        )
                    )
                    .order_by(func.random())
                    .limit(count_for_topic)
                )
            else:
                topic_result = await db.execute(
                    select(Question.id)
                    .where(
                        and_(
                            Question.certification_id == certification_id,
                            Question.topic.is_(None)
                        )
                    )
                    .order_by(func.random())
                    .limit(count_for_topic)
                )
            question_ids.extend([row[0] for row in topic_result.all()])
        
        # Shuffle the final list
        random.shuffle(question_ids)
        
        # Ensure we don't exceed the requested count
        if len(question_ids) > question_count:
            question_ids = question_ids[:question_count]
        
        return question_ids
        
    elif session_type == "full":
        # All questions in order
        result = await db.execute(
            select(Question.id)
            .where(Question.certification_id == certification_id)
            .order_by(Question.question_number)
        )
        
    else:  # continue - handled separately
        result = await db.execute(
            select(Question.id)
            .where(Question.certification_id == certification_id)
            .order_by(Question.question_number)
        )
    
    return [row[0] for row in result.all()]


async def create_session(
    db: AsyncSession,
    certification_id: uuid.UUID,
    session_type: str,
    question_count: int = 20,
    questions_per_topic: int = None
) -> QuizSession:
    """Create a new quiz session."""
    
    # For "continue" type, find existing incomplete session
    if session_type == "continue":
        existing = await db.execute(
            select(QuizSession)
            .where(
                and_(
                    QuizSession.certification_id == certification_id,
                    QuizSession.status == "in_progress"
                )
            )
            .order_by(QuizSession.started_at.desc())
            .limit(1)
        )
        existing_session = existing.scalar_one_or_none()
        if existing_session:
            return existing_session
    
    # Get questions for session
    question_ids = await get_questions_for_session(
        db, certification_id, session_type, question_count, questions_per_topic
    )
    
    if not question_ids:
        raise ValueError("No questions available for this session type")
    
    # Create session
    session = QuizSession(
        certification_id=certification_id,
        session_type=session_type,
        total_questions=len(question_ids),
        question_ids=[str(qid) for qid in question_ids],
        status="in_progress"
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Optional[QuizSession]:
    """Get quiz session by ID."""
    result = await db.execute(
        select(QuizSession)
        .options(selectinload(QuizSession.answers))
        .where(QuizSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_session_questions(
    db: AsyncSession,
    session: QuizSession
) -> List[Question]:
    """Get questions for a session with answer status."""
    question_ids = [uuid.UUID(qid) for qid in session.question_ids]
    
    result = await db.execute(
        select(Question)
        .options(
            selectinload(Question.images),
            selectinload(Question.bookmark)
        )
        .where(Question.id.in_(question_ids))
    )
    
    questions = {q.id: q for q in result.scalars().all()}
    
    # Return in session order
    return [questions[qid] for qid in question_ids if qid in questions]


async def submit_answer(
    db: AsyncSession,
    session: QuizSession,
    question_id: uuid.UUID,
    user_answer: str,
    time_spent_seconds: Optional[int] = None
) -> SessionAnswer:
    """Submit an answer for a question in a session."""
    
    # Get the question to validate answer
    question = await db.get(Question, question_id)
    if not question:
        raise ValueError("Question not found")
    
    # Check if already answered
    existing = await db.execute(
        select(SessionAnswer)
        .where(
            and_(
                SessionAnswer.session_id == session.id,
                SessionAnswer.question_id == question_id
            )
        )
    )
    existing_answer = existing.scalar_one_or_none()
    
    if existing_answer:
        # Update existing answer
        existing_answer.user_answer = user_answer
        existing_answer.is_correct = check_answer_correct(user_answer, question.correct_answer)
        existing_answer.answered_at = datetime.utcnow()
        existing_answer.time_spent_seconds = time_spent_seconds
        answer = existing_answer
    else:
        # Create new answer
        is_correct = check_answer_correct(user_answer, question.correct_answer)
        
        answer = SessionAnswer(
            session_id=session.id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
            time_spent_seconds=time_spent_seconds
        )
        db.add(answer)
        
        # Update session stats
        if is_correct:
            session.correct_answers += 1
    
    # Update current question index
    question_ids = [uuid.UUID(qid) for qid in session.question_ids]
    try:
        current_idx = question_ids.index(question_id)
        session.current_question_index = current_idx + 1
    except ValueError:
        pass
    
    await db.commit()
    await db.refresh(answer)
    
    return answer


async def complete_session(db: AsyncSession, session: QuizSession) -> QuizSession:
    """Complete a quiz session and calculate final stats."""
    session.status = "completed"
    session.completed_at = datetime.utcnow()
    
    # Recalculate correct answers
    result = await db.execute(
        select(func.count())
        .select_from(SessionAnswer)
        .where(
            and_(
                SessionAnswer.session_id == session.id,
                SessionAnswer.is_correct == True
            )
        )
    )
    session.correct_answers = result.scalar() or 0
    
    await db.commit()
    await db.refresh(session)
    
    # Trigger analytics recalculation
    from analytics.services import refresh_analytics
    await refresh_analytics(db, session.certification_id)
    
    return session


async def build_session_results(db: AsyncSession, session: QuizSession):
    """Build full session results with per-topic stats."""
    from quiz.schemas import SessionResultsResponse, TopicStat
    
    incorrect = session.total_questions - session.correct_answers
    accuracy = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
    
    # Calculate duration
    duration = None
    if session.started_at and session.completed_at:
        duration = int((session.completed_at - session.started_at).total_seconds())
    
    # Per-topic breakdown
    topic_rows = await db.execute(
        select(
            Question.topic,
            func.count().label("total"),
            func.count(case((SessionAnswer.is_correct == True, 1))).label("correct"),
        )
        .join(SessionAnswer, SessionAnswer.question_id == Question.id)
        .where(SessionAnswer.session_id == session.id)
        .group_by(Question.topic)
        .order_by(func.count().desc())
    )
    
    topic_stats = []
    for row in topic_rows:
        t_total = row.total
        t_correct = row.correct
        t_acc = (t_correct / t_total * 100) if t_total > 0 else 0
        topic_stats.append(TopicStat(
            topic=row.topic or "Uncategorized",
            total=t_total,
            correct=t_correct,
            accuracy=round(t_acc, 1),
        ))
    
    return SessionResultsResponse(
        session_id=session.id,
        total_questions=session.total_questions,
        correct_answers=session.correct_answers,
        incorrect_answers=incorrect,
        accuracy=round(accuracy, 1),
        duration_seconds=duration,
        session_type=session.session_type,
        topic_stats=topic_stats,
    )


async def get_suggestions(
    db: AsyncSession,
    certification_id: uuid.UUID
) -> List[QuizSuggestion]:
    """Get smart study suggestions for a certification."""
    suggestions = []
    
    # Check for weak areas
    weak_topics = await get_weak_topics(db, certification_id)
    if weak_topics:
        # Count questions in weak topics
        result = await db.execute(
            select(func.count())
            .select_from(Question)
            .where(
                and_(
                    Question.certification_id == certification_id,
                    Question.topic.in_(weak_topics)
                )
            )
        )
        weak_count = result.scalar() or 0
        
        suggestions.append(QuizSuggestion(
            type="weak_areas",
            title="🎯 Focus on Weak Areas",
            description=f"Practice questions from topics where you scored below 60%",
            question_count=min(weak_count, 25),
            data={"topics": weak_topics}
        ))
    
    # Check for incomplete session
    result = await db.execute(
        select(QuizSession)
        .where(
            and_(
                QuizSession.certification_id == certification_id,
                QuizSession.status == "in_progress"
            )
        )
        .order_by(QuizSession.started_at.desc())
        .limit(1)
    )
    incomplete_session = result.scalar_one_or_none()
    
    if incomplete_session:
        remaining = incomplete_session.total_questions - incomplete_session.current_question_index
        suggestions.append(QuizSuggestion(
            type="continue",
            title="▶️ Continue Where You Left Off",
            description=f"Resume from question {incomplete_session.current_question_index + 1}",
            question_count=remaining,
            data={"session_id": str(incomplete_session.id)}
        ))
    
    # Check for bookmarked questions
    result = await db.execute(
        select(func.count())
        .select_from(BookmarkedQuestion)
        .join(Question, BookmarkedQuestion.question_id == Question.id)
        .where(Question.certification_id == certification_id)
    )
    bookmark_count = result.scalar() or 0
    
    if bookmark_count > 0:
        suggestions.append(QuizSuggestion(
            type="review",
            title="🔖 Review Marked Questions",
            description=f"Study the {bookmark_count} questions you marked for review",
            question_count=bookmark_count,
            data=None
        ))
    
    # Always add random option
    result = await db.execute(
        select(func.count())
        .select_from(Question)
        .where(Question.certification_id == certification_id)
    )
    total_count = result.scalar() or 0
    
    suggestions.append(QuizSuggestion(
        type="random",
        title="🎲 Random Practice",
        description="Practice 20 random questions from all topics",
        question_count=min(total_count, 20),
        data=None
    ))
    
    return suggestions


# Bookmark functions
async def add_bookmark(
    db: AsyncSession,
    question_id: uuid.UUID,
    notes: Optional[str] = None
) -> BookmarkedQuestion:
    """Add a bookmark for a question."""
    # Check if already bookmarked
    existing = await db.execute(
        select(BookmarkedQuestion)
        .where(BookmarkedQuestion.question_id == question_id)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Question already bookmarked")
    
    bookmark = BookmarkedQuestion(
        question_id=question_id,
        notes=notes
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    
    return bookmark


async def remove_bookmark(db: AsyncSession, question_id: uuid.UUID) -> bool:
    """Remove a bookmark for a question."""
    result = await db.execute(
        select(BookmarkedQuestion)
        .where(BookmarkedQuestion.question_id == question_id)
    )
    bookmark = result.scalar_one_or_none()
    
    if not bookmark:
        return False
    
    await db.delete(bookmark)
    await db.commit()
    
    return True


async def list_bookmarks(
    db: AsyncSession,
    certification_id: Optional[uuid.UUID] = None
) -> List[BookmarkedQuestion]:
    """List all bookmarked questions."""
    query = (
        select(BookmarkedQuestion)
        .join(Question, BookmarkedQuestion.question_id == Question.id)
        .options(selectinload(BookmarkedQuestion.question))
    )
    
    if certification_id:
        query = query.where(Question.certification_id == certification_id)
    
    query = query.order_by(BookmarkedQuestion.bookmarked_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()
