"""
Pydantic schemas for quiz feature.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Schema for creating a quiz session."""
    certification_id: UUID
    session_type: str = Field(..., pattern="^(weak_areas|continue|review|random|full|stratified)$")
    question_count: Optional[int] = 20
    questions_per_topic: Optional[int] = None  # For stratified mode


class TopicInfo(BaseModel):
    """Schema for topic information."""
    topic: str
    question_count: int
    accuracy: Optional[float] = None


class TopicsResponse(BaseModel):
    """Schema for topics list response."""
    topics: List[TopicInfo]
    total_questions: int


class SessionResponse(BaseModel):
    """Schema for quiz session response."""
    id: UUID
    certification_id: UUID
    session_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_questions: int
    correct_answers: int
    status: str
    current_question_index: int
    
    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    """Schema for submitting an answer."""
    question_id: UUID
    user_answer: str
    time_spent_seconds: Optional[int] = None


class AnswerResponse(BaseModel):
    """Schema for answer response."""
    question_id: UUID
    user_answer: str
    is_correct: bool
    correct_answer: str
    explanation: str


class SessionResultsResponse(BaseModel):
    """Schema for completed session results."""
    session_id: UUID
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    accuracy: float
    time_spent: Optional[int] = None


class QuizSuggestion(BaseModel):
    """Schema for quiz suggestion."""
    type: str
    title: str
    description: str
    question_count: int
    data: Optional[Dict[str, Any]] = None


class SuggestionsResponse(BaseModel):
    """Schema for suggestions response."""
    certification_id: UUID
    suggestions: List[QuizSuggestion]


class BookmarkCreate(BaseModel):
    """Schema for creating a bookmark."""
    question_id: UUID
    notes: Optional[str] = None


class BookmarkResponse(BaseModel):
    """Schema for bookmark response."""
    id: UUID
    question_id: UUID
    bookmarked_at: datetime
    notes: Optional[str] = None
    question_text: Optional[str] = None
    certification_name: Optional[str] = None
    last_answer_correct: Optional[bool] = None
    
    class Config:
        from_attributes = True


class QuestionWithAnswerResponse(BaseModel):
    """Schema for question with user's answer."""
    id: UUID
    question_number: int
    question_text: str
    options: List[str]
    correct_answer: str
    explanation: str
    has_images: bool
    images: List[Dict[str, Any]] = []
    is_bookmarked: bool = False
    user_answer: Optional[str] = None
    is_answered: bool = False
    
    class Config:
        from_attributes = True
