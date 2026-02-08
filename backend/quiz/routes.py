"""
API routes for quiz feature.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.dependencies import get_db
from quiz.schemas import (
    SessionCreate, SessionResponse, AnswerSubmit, AnswerResponse,
    SessionResultsResponse, SuggestionsResponse, BookmarkCreate,
    BookmarkResponse, QuestionWithAnswerResponse, TopicsResponse, TopicInfo
)
from quiz.services import (
    create_session, get_session, get_session_questions,
    submit_answer, complete_session, get_suggestions,
    add_bookmark, remove_bookmark, list_bookmarks, get_topics_for_certification
)


router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def start_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Start a new quiz session."""
    try:
        session = await create_session(
            db=db,
            certification_id=data.certification_id,
            session_type=data.session_type,
            question_count=data.question_count or 20,
            questions_per_topic=data.questions_per_topic
        )
        return SessionResponse.model_validate(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/topics", response_model=TopicsResponse)
async def get_topics(
    certification_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get available topics for a certification with question counts."""
    topics = await get_topics_for_certification(db, certification_id)
    total = sum(t.question_count for t in topics)
    return TopicsResponse(topics=topics, total_questions=total)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get quiz session details."""
    session = await get_session(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/questions", response_model=List[QuestionWithAnswerResponse])
async def get_questions_for_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all questions for a session with answer status."""
    session = await get_session(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    questions = await get_session_questions(db, session)
    
    # Build answer lookup
    answers_lookup = {
        str(a.question_id): a for a in session.answers
    }
    
    return [
        QuestionWithAnswerResponse(
            id=q.id,
            question_number=q.question_number,
            question_text=q.question_text,
            options=q.options if isinstance(q.options, list) else list(q.options),
            correct_answer=q.correct_answer,
            explanation=q.explanation,
            has_images=q.has_images,
            images=[
                {
                    "id": str(img.id),
                    "image_path": img.image_path,
                    "image_order": img.image_order,
                    "position_in_pdf": img.position_in_pdf,
                    "width": img.width,
                    "height": img.height
                }
                for img in q.images
            ],
            is_bookmarked=q.bookmark is not None,
            user_answer=answers_lookup.get(str(q.id), {}).user_answer if str(q.id) in answers_lookup else None,
            is_answered=str(q.id) in answers_lookup
        )
        for q in questions
    ]


@router.post("/sessions/{session_id}/answers", response_model=AnswerResponse)
async def submit_session_answer(
    session_id: uuid.UUID,
    data: AnswerSubmit,
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer for a question in a session."""
    session = await get_session(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="Session is not active")
    
    try:
        answer = await submit_answer(
            db=db,
            session=session,
            question_id=data.question_id,
            user_answer=data.user_answer,
            time_spent_seconds=data.time_spent_seconds
        )
        
        # Get question for response
        question = await db.get(
            __import__("shared.models", fromlist=["Question"]).Question,
            data.question_id
        )
        
        return AnswerResponse(
            question_id=answer.question_id,
            user_answer=answer.user_answer,
            is_correct=answer.is_correct,
            correct_answer=question.correct_answer if question else "",
            explanation=question.explanation if question else ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/complete", response_model=SessionResultsResponse)
async def complete_quiz_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Complete a quiz session and get results."""
    session = await get_session(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status == "completed":
        # Already completed, just return results
        pass
    else:
        session = await complete_session(db, session)
    
    incorrect = session.total_questions - session.correct_answers
    accuracy = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
    
    return SessionResultsResponse(
        session_id=session.id,
        total_questions=session.total_questions,
        correct_answers=session.correct_answers,
        incorrect_answers=incorrect,
        accuracy=round(accuracy, 1)
    )


@router.get("/sessions/{session_id}/results", response_model=SessionResultsResponse)
async def get_session_results(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get results for a completed session."""
    session = await get_session(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    incorrect = session.total_questions - session.correct_answers
    accuracy = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
    
    return SessionResultsResponse(
        session_id=session.id,
        total_questions=session.total_questions,
        correct_answers=session.correct_answers,
        incorrect_answers=incorrect,
        accuracy=round(accuracy, 1)
    )


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_quiz_suggestions(
    certification_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get smart study suggestions for a certification."""
    suggestions = await get_suggestions(db, certification_id)
    
    return SuggestionsResponse(
        certification_id=certification_id,
        suggestions=suggestions
    )


# Bookmark endpoints
@router.get("/bookmarks", response_model=List[BookmarkResponse])
async def list_all_bookmarks(
    certification_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all bookmarked questions."""
    bookmarks = await list_bookmarks(db, certification_id)
    
    return [
        BookmarkResponse(
            id=b.id,
            question_id=b.question_id,
            bookmarked_at=b.bookmarked_at,
            notes=b.notes,
            question_text=b.question.question_text[:100] + "..." if b.question else None,
            certification_name=b.question.certification.name if b.question and b.question.certification else None
        )
        for b in bookmarks
    ]


@router.post("/bookmarks", response_model=BookmarkResponse)
async def create_bookmark(
    data: BookmarkCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a bookmark for a question."""
    try:
        bookmark = await add_bookmark(
            db=db,
            question_id=data.question_id,
            notes=data.notes
        )
        return BookmarkResponse(
            id=bookmark.id,
            question_id=bookmark.question_id,
            bookmarked_at=bookmark.bookmarked_at,
            notes=bookmark.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/bookmarks/{question_id}")
async def delete_bookmark(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove a bookmark for a question."""
    removed = await remove_bookmark(db, question_id)
    
    if not removed:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {"message": "Bookmark removed successfully"}
