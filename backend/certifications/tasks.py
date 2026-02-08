"""
Background tasks for PDF processing.
"""
import os
import re
import json
import hashlib
import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

import pdfplumber
from pdf2image import convert_from_path
from PIL import Image

from shared.config import settings
from shared.cache import get_cached, set_cached, get_cache_key
from shared.database import async_session
from shared.models import Certification, Question, QuestionImage
from sqlalchemy import select

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from PDF using pdfplumber."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
            if text:
                full_text += text + "\n"
    return full_text.strip()


def extract_images_from_pdf(pdf_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """Extract images from PDF using pdf2image."""
    os.makedirs(output_dir, exist_ok=True)
    
    images_info = []
    try:
        # Convert PDF pages to images
        pages = convert_from_path(pdf_path, dpi=150)
        
        for i, page in enumerate(pages):
            image_filename = f"page_{i + 1}.png"
            image_path = os.path.join(output_dir, image_filename)
            page.save(image_path, "PNG")
            
            images_info.append({
                "page": i + 1,
                "filename": image_filename,
                "path": image_path,
                "width": page.width,
                "height": page.height
            })
    except Exception as e:
        logger.error(f"Error extracting images: {e}")
    
    return images_info


def split_into_question_blocks(text: str) -> List[str]:
    """Split text into question blocks using regex patterns."""
    # Pattern to match question headers (Question 1, Q1, 1., Question #1, etc.)
    # Patterns are tried in order of specificity (most specific first)
    patterns = [
        # "Question #1" or "Question # 1" - with optional Topic info after
        r"(Question\s*#\s*\d+)",
        # "Question 1" or "Question  23"
        r"(Question\s+\d+)",
        # "Q1.", "Q 5:", "Q12)"
        r"(Q\s*\d+[\.\):])",
        # "QUESTION 1" or "QUESTION: 1" (uppercase with optional colon)
        r"(QUESTION\s*:?\s*\d+)",
        # "1." or "42. " at start of line
        r"(?:^|\n)(\d+\.\s+)",
        # "1)" or "42)" - numbered with parenthesis
        r"(?:^|\n)(\d+\)\s+)",
    ]
    
    blocks = []
    
    for pattern in patterns:
        raw_blocks = re.split(pattern, text, flags=re.IGNORECASE)
        if len(raw_blocks) > 1:
            for i in range(1, len(raw_blocks), 2):
                block = raw_blocks[i]
                if i + 1 < len(raw_blocks):
                    block += "\n" + raw_blocks[i + 1]
                block = block.strip()
                if len(block) > 50:  # Minimum meaningful block length
                    blocks.append(block)
            if len(blocks) >= 2:  # Found at least 2 questions with this pattern
                break
    
    if not blocks:
        # Fallback: split by double newlines
        blocks = [b.strip() for b in text.split("\n\n") if len(b.strip()) > 100]
    
    return blocks


async def parse_question_with_llm(block: str) -> Optional[Dict[str, Any]]:
    """Parse a question block using LLM with caching."""
    # Skip cache for now to avoid Redis event loop issues
    
    # Parse with LLM
    try:
        from langchain_openai import ChatOpenAI
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        # Select LLM provider
        if settings.google_api_key and settings.llm_provider == "gemini":
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0,
                google_api_key=settings.google_api_key
            )
        elif settings.openai_api_key:
            llm = ChatOpenAI(
                temperature=0,
                model_name="gpt-4o-mini",
                openai_api_key=settings.openai_api_key
            )
        else:
            print("[TASK ERROR] No LLM API key configured", flush=True)
            return None
        
        prompt_template = PromptTemplate(
            input_variables=["input_text"],
            template="""
You are an expert teacher. Given a multiple-choice question with its options, respond in JSON format as follows:

"question": the question text 
"options": a list of options as strings, each starting with a letter label (A., B., C., ...) — if the input options do not have letters, add them in this format 
"correct_answer": the letter and text of the correct option (e.g. "B. Example answer") 
"explanation": a detailed explanation of why the answer is correct
"topic": a short topic/category for this question (e.g., "Delta Lake", "Spark SQL", "Data Pipelines", "Security", etc.) - choose a concise, relevant topic based on the question content

Question text + options: 
{input_text}

Respond only with valid JSON:
"""
        )
        
        chain = prompt_template | llm | StrOutputParser()
        
        # Use synchronous invoke directly (LangChain handles this)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(chain.invoke, {"input_text": block.strip()})
            raw_response = future.result(timeout=60)
        
        # Clean and parse JSON
        raw_response = raw_response.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw_response)
        
        # Validate required fields
        if all(k in result for k in ["question", "options", "correct_answer", "explanation"]):
            return result
        else:
            print(f"[TASK WARN] Missing required fields in LLM response", flush=True)
            return None
            
    except json.JSONDecodeError as e:
        print(f"[TASK ERROR] JSON parsing error: {e}", flush=True)
        return None
    except Exception as e:
        print(f"[TASK ERROR] LLM parsing error: {e}", flush=True)
        return None


async def process_pdf_background(certification_id: UUID, pdf_path: str):
    """Background task to process a PDF and extract questions."""
    import sys
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    
    print(f"[TASK] Starting PDF processing for {certification_id}", flush=True)
    sys.stdout.flush()
    
    # Create a new engine and session for this event loop
    DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    task_engine = create_async_engine(DATABASE_URL, echo=False)
    task_session_factory = async_sessionmaker(task_engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with task_session_factory() as db:
            try:
                # Update status to processing
                cert = await db.get(Certification, certification_id)
                if not cert:
                    print(f"[TASK ERROR] Certification {certification_id} not found", flush=True)
                    return
                
                cert.processing_status = "processing"
                cert.processing_progress = 0
                await db.commit()
                print(f"[TASK] Status updated to processing", flush=True)
            
                # Extract text
                print(f"[TASK] Extracting text from {pdf_path}", flush=True)
                text = extract_text_from_pdf(pdf_path)
                print(f"[TASK] Extracted {len(text)} characters of text", flush=True)
                cert.processing_progress = 10
                await db.commit()
                
                # Extract images
                print("[TASK] Extracting images from PDF", flush=True)
                images_dir = os.path.join(
                    settings.data_path, "images", str(certification_id)
                )
                images_info = extract_images_from_pdf(pdf_path, images_dir)
                print(f"[TASK] Extracted {len(images_info)} images", flush=True)
                cert.processing_progress = 20
                await db.commit()
                
                # Split into question blocks
                print("[TASK] Splitting text into question blocks", flush=True)
                blocks = split_into_question_blocks(text)
                total_blocks = len(blocks)
                print(f"[TASK] Found {total_blocks} question blocks", flush=True)
                
                if total_blocks == 0:
                    cert.processing_status = "failed"
                    cert.processing_progress = 100
                    await db.commit()
                    print("[TASK ERROR] No question blocks found in PDF", flush=True)
                    return
                
                # Process each block
                questions_created = 0
                cert.processing_total_blocks = total_blocks
                cert.processing_current_block = 0
                await db.commit()
                
                for i, block in enumerate(blocks):
                    print(f"[TASK] Processing block {i+1}/{total_blocks}...", flush=True)
                    cert.processing_current_block = i + 1
                    
                    try:
                        question_data = await parse_question_with_llm(block)
                    except Exception as llm_err:
                        print(f"[TASK ERROR] LLM failed for block {i+1}: {llm_err}", flush=True)
                        question_data = None
                    
                    if question_data:
                        # Create question
                        question = Question(
                            certification_id=certification_id,
                            question_number=i + 1,
                            question_text=question_data["question"],
                            options=question_data["options"],
                            correct_answer=question_data["correct_answer"],
                            explanation=question_data["explanation"],
                            topic=question_data.get("topic"),
                            has_images=False
                        )
                        db.add(question)
                        await db.flush()
                        questions_created += 1
                        cert.total_questions = questions_created
                        print(f"[TASK] Question {i+1} created (topic: {question_data.get('topic', 'N/A')})", flush=True)
                    else:
                        print(f"[TASK WARN] Block {i+1} skipped (no valid question)", flush=True)
                    
                    # Update progress
                    progress = 20 + int((i + 1) / total_blocks * 70)
                    cert.processing_progress = progress
                    await db.commit()
                
                # Update certification with final count
                cert.total_questions = questions_created
                cert.processing_status = "completed"
                cert.processing_progress = 100
                await db.commit()
                
                print(f"[TASK] Processing complete: {questions_created} questions created", flush=True)
                
            except Exception as e:
                print(f"[TASK ERROR] Error processing PDF: {e}", flush=True)
                import traceback
                traceback.print_exc()
                async with task_session_factory() as error_db:
                    cert = await error_db.get(Certification, certification_id)
                    if cert:
                        cert.processing_status = "failed"
                        cert.processing_progress = 100
                        await error_db.commit()
        
        # Dispose engine when done
        await task_engine.dispose()
        
    except Exception as outer_e:
        print(f"[TASK OUTER ERROR] {outer_e}", flush=True)
        import traceback
        traceback.print_exc()
