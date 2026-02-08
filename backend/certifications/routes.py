"""
API routes for certifications feature.
"""
import os
import uuid
import asyncio
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from shared.dependencies import get_db
from shared.config import settings
from certifications.schemas import (
    CertificationResponse, CertificationListResponse,
    UploadResponse, ProcessingStatusResponse, QuestionResponse
)
from certifications.services import (
    create_certification, get_certification, list_certifications,
    delete_certification, get_questions_for_certification
)
from certifications.tasks import process_pdf_background


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_certification(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a PDF and start processing."""
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate file size (max 50MB)
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Generate certification name from filename
    name = os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ")
    
    # Create certification record
    certification = await create_certification(
        db=db,
        name=name,
        pdf_path=""  # Will be updated after saving
    )
    
    # Save PDF to filesystem
    pdf_dir = os.path.join(settings.data_path, "pdfs", str(certification.id))
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, "original.pdf")
    
    with open(pdf_path, "wb") as f:
        f.write(contents)
    
    # Update certification with PDF path
    certification.pdf_path = pdf_path
    await db.commit()
    
    # Start background processing - use sync wrapper for async function
    import asyncio
    import sys
    
    def run_processing():
        print(f"[ROUTE] run_processing called for {certification.id}", flush=True)
        sys.stdout.flush()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print(f"[ROUTE] Starting event loop for {certification.id}", flush=True)
            loop.run_until_complete(process_pdf_background(certification.id, pdf_path))
            print(f"[ROUTE] Event loop completed for {certification.id}", flush=True)
        except Exception as e:
            print(f"[ROUTE ERROR] Exception in run_processing: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            loop.close()
    
    print(f"[ROUTE] Adding background task for {certification.id}", flush=True)
    background_tasks.add_task(run_processing)
    
    return UploadResponse(
        job_id=certification.id,
        certification_id=certification.id,
        message="Upload successful. Processing started."
    )


@router.get("/{certification_id}/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    certification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get processing status for a certification."""
    certification = await get_certification(db, certification_id)
    
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")
    
    # Build detailed message
    if certification.processing_status == "processing":
        if certification.processing_current_block and certification.processing_total_blocks:
            message = f"Processing question {certification.processing_current_block} of {certification.processing_total_blocks}..."
        else:
            message = f"Processing... {certification.processing_progress}%"
    elif certification.processing_status == "completed":
        message = f"Processing complete! {certification.total_questions} questions extracted."
    elif certification.processing_status == "failed":
        message = "Processing failed."
    else:
        message = "Waiting to start processing..."
    
    return ProcessingStatusResponse(
        certification_id=certification.id,
        status=certification.processing_status,
        progress=certification.processing_progress,
        message=message,
        total_questions=certification.total_questions,
        questions_extracted=certification.total_questions if certification.processing_status != "pending" else 0,
        total_blocks=certification.processing_total_blocks,
        current_block=certification.processing_current_block
    )


@router.get("", response_model=List[CertificationListResponse])
async def list_all_certifications(db: AsyncSession = Depends(get_db)):
    """List all certifications with stats."""
    return await list_certifications(db)


@router.get("/{certification_id}", response_model=CertificationResponse)
async def get_certification_details(
    certification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get certification details by ID."""
    certification = await get_certification(db, certification_id)
    
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")
    
    return CertificationResponse.model_validate(certification)


@router.get("/{certification_id}/questions", response_model=List[QuestionResponse])
async def get_certification_questions(
    certification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all questions for a certification."""
    certification = await get_certification(db, certification_id)
    
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")
    
    questions = await get_questions_for_certification(db, certification_id)
    
    return [
        QuestionResponse(
            id=q.id,
            question_number=q.question_number,
            question_text=q.question_text,
            options=q.options if isinstance(q.options, list) else list(q.options),
            correct_answer=q.correct_answer,
            explanation=q.explanation,
            has_images=q.has_images,
            topic=q.topic,
            difficulty=q.difficulty,
            images=[
                {
                    "id": img.id,
                    "image_path": img.image_path,
                    "image_order": img.image_order,
                    "position_in_pdf": img.position_in_pdf,
                    "width": img.width,
                    "height": img.height
                }
                for img in q.images
            ],
            is_bookmarked=q.bookmark is not None
        )
        for q in questions
    ]


@router.delete("/{certification_id}")
async def remove_certification(
    certification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a certification and all related data."""
    deleted = await delete_certification(db, certification_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Certification not found")
    
    return {"message": "Certification deleted successfully"}
