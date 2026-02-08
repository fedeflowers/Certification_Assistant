"""
Business logic for certifications feature.
"""
import os
import re
import uuid
import asyncio
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models import Certification, Question, QuestionImage, QuizSession
from shared.config import settings
from certifications.schemas import CertificationListResponse


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from certification name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


async def create_certification(
    db: AsyncSession,
    name: str,
    pdf_path: str,
    description: Optional[str] = None
) -> Certification:
    """Create a new certification record."""
    slug = generate_slug(name)
    
    # Check if slug exists and make it unique
    base_slug = slug
    counter = 1
    while True:
        existing = await db.execute(
            select(Certification).where(Certification.slug == slug)
        )
        if not existing.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    certification = Certification(
        name=name,
        slug=slug,
        description=description,
        pdf_path=pdf_path,
        processing_status="pending",
        processing_progress=0
    )
    
    db.add(certification)
    await db.commit()
    await db.refresh(certification)
    
    return certification


async def get_certification(db: AsyncSession, certification_id: uuid.UUID) -> Optional[Certification]:
    """Get certification by ID."""
    result = await db.execute(
        select(Certification).where(Certification.id == certification_id)
    )
    return result.scalar_one_or_none()


async def get_certification_by_slug(db: AsyncSession, slug: str) -> Optional[Certification]:
    """Get certification by slug."""
    result = await db.execute(
        select(Certification).where(Certification.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_certifications(db: AsyncSession) -> List[CertificationListResponse]:
    """List all certifications with stats."""
    # Get all certifications
    result = await db.execute(
        select(Certification).order_by(Certification.created_at.desc())
    )
    certifications = result.scalars().all()
    
    responses = []
    for cert in certifications:
        # Get last studied date
        last_session_result = await db.execute(
            select(QuizSession.started_at)
            .where(QuizSession.certification_id == cert.id)
            .order_by(QuizSession.started_at.desc())
            .limit(1)
        )
        last_studied = last_session_result.scalar_one_or_none()
        
        # Calculate accuracy
        from analytics.services import calculate_certification_accuracy
        accuracy = await calculate_certification_accuracy(db, cert.id)
        
        responses.append(CertificationListResponse(
            id=cert.id,
            name=cert.name,
            slug=cert.slug,
            total_questions=cert.total_questions,
            processing_status=cert.processing_status,
            created_at=cert.created_at,
            last_studied=last_studied,
            accuracy=accuracy
        ))
    
    return responses


async def update_processing_status(
    db: AsyncSession,
    certification_id: uuid.UUID,
    status: str,
    progress: int,
    total_questions: Optional[int] = None
):
    """Update certification processing status."""
    certification = await get_certification(db, certification_id)
    if certification:
        certification.processing_status = status
        certification.processing_progress = progress
        if total_questions is not None:
            certification.total_questions = total_questions
        certification.updated_at = datetime.utcnow()
        await db.commit()


async def delete_certification(db: AsyncSession, certification_id: uuid.UUID) -> bool:
    """Delete a certification and all related data."""
    certification = await get_certification(db, certification_id)
    if not certification:
        return False
    
    # Delete associated files
    pdf_dir = os.path.join(settings.data_path, "pdfs", str(certification_id))
    images_dir = os.path.join(settings.data_path, "images", str(certification_id))
    
    import shutil
    if os.path.exists(pdf_dir):
        shutil.rmtree(pdf_dir)
    if os.path.exists(images_dir):
        shutil.rmtree(images_dir)
    
    # Delete from database (cascades to related tables)
    await db.delete(certification)
    await db.commit()
    
    return True


async def get_questions_for_certification(
    db: AsyncSession,
    certification_id: uuid.UUID,
    include_bookmarks: bool = True
) -> List[Question]:
    """Get all questions for a certification."""
    query = (
        select(Question)
        .where(Question.certification_id == certification_id)
        .options(selectinload(Question.images))
        .order_by(Question.question_number)
    )
    
    if include_bookmarks:
        query = query.options(selectinload(Question.bookmark))
    
    result = await db.execute(query)
    return result.scalars().all()
