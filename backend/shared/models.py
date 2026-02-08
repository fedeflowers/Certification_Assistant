"""
SQLAlchemy models for the Certification Assistant database.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class Certification(Base):
    """Represents an uploaded certification exam."""
    __tablename__ = "certifications"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    processing_progress: Mapped[int] = mapped_column(Integer, default=0)
    processing_total_blocks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_current_block: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="certification", cascade="all, delete-orphan"
    )
    quiz_sessions: Mapped[List["QuizSession"]] = relationship(
        "QuizSession", back_populates="certification", cascade="all, delete-orphan"
    )
    analytics_cache: Mapped[List["AnalyticsCache"]] = relationship(
        "AnalyticsCache", back_populates="certification", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_certifications_slug", "slug"),
        Index("idx_certifications_status", "processing_status"),
    )


class Question(Base):
    """Individual exam question with metadata."""
    __tablename__ = "questions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    certification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    has_images: Mapped[bool] = mapped_column(Boolean, default=False)
    topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    certification: Mapped["Certification"] = relationship(
        "Certification", back_populates="questions"
    )
    images: Mapped[List["QuestionImage"]] = relationship(
        "QuestionImage", back_populates="question", cascade="all, delete-orphan"
    )
    session_answers: Mapped[List["SessionAnswer"]] = relationship(
        "SessionAnswer", back_populates="question", cascade="all, delete-orphan"
    )
    bookmark: Mapped[Optional["BookmarkedQuestion"]] = relationship(
        "BookmarkedQuestion", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_questions_cert", "certification_id"),
        Index("idx_questions_topic", "topic"),
        Index("idx_questions_number", "certification_id", "question_number"),
    )


class QuestionImage(Base):
    """Images associated with questions."""
    __tablename__ = "question_images"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    image_order: Mapped[int] = mapped_column(Integer, default=1)
    position_in_pdf: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="images")
    
    __table_args__ = (
        Index("idx_images_question", "question_id"),
    )


class QuizSession(Base):
    """Tracks individual study sessions."""
    __tablename__ = "quiz_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    certification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False
    )
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="in_progress")
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    question_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    
    # Relationships
    certification: Mapped["Certification"] = relationship(
        "Certification", back_populates="quiz_sessions"
    )
    answers: Mapped[List["SessionAnswer"]] = relationship(
        "SessionAnswer", back_populates="session", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_sessions_cert", "certification_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_started", "started_at"),
    )


class SessionAnswer(Base):
    """Individual answers within a quiz session."""
    __tablename__ = "session_answers"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    session: Mapped["QuizSession"] = relationship("QuizSession", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="session_answers")
    
    __table_args__ = (
        Index("idx_answers_session", "session_id"),
        Index("idx_answers_question", "question_id"),
        Index("idx_answers_correct", "is_correct"),
    )


class BookmarkedQuestion(Base):
    """Questions marked for review."""
    __tablename__ = "bookmarked_questions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    bookmarked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="bookmark")
    
    __table_args__ = (
        Index("idx_bookmarks_question", "question_id"),
    )


class AnalyticsCache(Base):
    """Pre-calculated analytics metrics."""
    __tablename__ = "analytics_cache"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    certification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certifications.id", ondelete="CASCADE"), nullable=True
    )
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    certification: Mapped[Optional["Certification"]] = relationship(
        "Certification", back_populates="analytics_cache"
    )
    
    __table_args__ = (
        Index("idx_analytics_cert", "certification_id"),
        Index("idx_analytics_type", "metric_type"),
        Index("idx_analytics_unique", "certification_id", "metric_type", unique=True),
    )
