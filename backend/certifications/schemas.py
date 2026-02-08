"""
Pydantic schemas for certifications feature.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class CertificationBase(BaseModel):
    """Base certification schema."""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None


class CertificationCreate(CertificationBase):
    """Schema for creating certification."""
    pass


class CertificationResponse(CertificationBase):
    """Schema for certification response."""
    id: UUID
    slug: str
    pdf_path: str
    total_questions: int
    created_at: datetime
    updated_at: datetime
    processing_status: str
    processing_progress: int
    
    class Config:
        from_attributes = True


class CertificationListResponse(BaseModel):
    """Schema for listing certifications."""
    id: UUID
    name: str
    slug: str
    total_questions: int
    processing_status: str
    created_at: datetime
    last_studied: Optional[datetime] = None
    accuracy: Optional[float] = None
    
    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Schema for upload response."""
    job_id: UUID
    certification_id: UUID
    message: str


class ProcessingStatusResponse(BaseModel):
    """Schema for processing status response."""
    certification_id: UUID
    status: str
    progress: int
    message: str
    total_questions: Optional[int] = None
    questions_extracted: Optional[int] = None
    total_blocks: Optional[int] = None
    current_block: Optional[int] = None
    error: Optional[str] = None


class QuestionImageResponse(BaseModel):
    """Schema for question image."""
    id: UUID
    image_path: str
    image_order: int
    position_in_pdf: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    
    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    """Schema for question response."""
    id: UUID
    question_number: int
    question_text: str
    options: List[str]
    correct_answer: str
    explanation: str
    has_images: bool
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    images: List[QuestionImageResponse] = []
    is_bookmarked: bool = False
    
    class Config:
        from_attributes = True
