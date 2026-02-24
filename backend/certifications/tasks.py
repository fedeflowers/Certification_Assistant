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
import fitz  # PyMuPDF

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


def extract_text_with_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract text from PDF page by page, returning page number and text."""
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
            if text:
                pages_data.append({
                    "page": i + 1,
                    "text": text
                })
    return pages_data


def extract_images_from_pdf(pdf_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """Extract full-page renders from PDF using pdf2image (fallback)."""
    os.makedirs(output_dir, exist_ok=True)
    
    images_info = []
    try:
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
        logger.error(f"Error extracting page images: {e}")
    
    return images_info


# Minimum dimensions (px) to keep an image — filters out icons, dots, bullets
MIN_IMAGE_WIDTH = 80
MIN_IMAGE_HEIGHT = 80
MIN_IMAGE_AREA = 10000  # at least ~100x100


def extract_embedded_images(pdf_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """Extract actual embedded images from PDF using PyMuPDF.
    
    Returns a list of dicts with: page, filename, path, width, height, y_position.
    Filters out tiny images (icons, bullets, decorations).
    """
    os.makedirs(output_dir, exist_ok=True)
    images_info = []
    
    try:
        doc = fitz.open(pdf_path)
        img_counter = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img_ref in enumerate(image_list):
                xref = img_ref[0]
                
                try:
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue
                    
                    img_bytes = base_image["image"]
                    img_ext = base_image.get("ext", "png")
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    
                    # Filter out small images (icons, bullets, decorative elements)
                    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                        continue
                    if width * height < MIN_IMAGE_AREA:
                        continue
                    
                    # Get image position on page for association with questions
                    y_position = 0.0
                    for img_rect in page.get_image_rects(xref):
                        y_position = img_rect.y0 / page.rect.height  # normalized 0..1
                        break
                    
                    img_counter += 1
                    image_filename = f"img_p{page_num + 1}_{img_counter}.{img_ext}"
                    image_path = os.path.join(output_dir, image_filename)
                    
                    with open(image_path, "wb") as f:
                        f.write(img_bytes)
                    
                    images_info.append({
                        "page": page_num + 1,
                        "filename": image_filename,
                        "path": image_path,
                        "width": width,
                        "height": height,
                        "y_position": y_position,  # vertical position on page (0=top, 1=bottom)
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to extract image {xref} from page {page_num + 1}: {e}")
                    continue
        
        doc.close()
        print(f"[TASK] Extracted {len(images_info)} embedded images (filtered from {img_counter + (img_counter == 0)} candidates)", flush=True)
        
    except Exception as e:
        logger.error(f"Error extracting embedded images: {e}")
        print(f"[TASK ERROR] PyMuPDF image extraction failed: {e}", flush=True)
    
    return images_info


def split_into_question_blocks(text: str) -> List[str]:
    """Split text into question blocks using regex patterns."""
    patterns = [
        r"(Question\s*#\s*\d+)",
        r"(Question\s+\d+)",
        r"(Q\s*\d+[\.\):])",
        r"(QUESTION\s*:?\s*\d+)",
        r"(?:^|\n)(\d+\.\s+)",
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
                if len(block) > 50:
                    blocks.append(block)
            if len(blocks) >= 2:
                break
    
    if not blocks:
        blocks = [b.strip() for b in text.split("\n\n") if len(b.strip()) > 100]
    
    return blocks


def split_into_question_blocks_with_pages(
    pages_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Split text into question blocks while tracking which pages each block spans.
    
    Returns a list of dicts with 'text' and 'pages' (set of page numbers).
    """
    # Build full text with page markers
    PAGE_MARKER = "\x00PAGE_{page}\x00"
    full_text = ""
    for pd in pages_data:
        marker = PAGE_MARKER.replace("{page}", str(pd["page"]))
        full_text += marker + pd["text"] + "\n"
    
    # Split into blocks using existing logic
    patterns = [
        r"(Question\s*#\s*\d+)",
        r"(Question\s+\d+)",
        r"(Q\s*\d+[\.\):])",
        r"(QUESTION\s*:?\s*\d+)",
        r"(?:^|\n)(\d+\.\s+)",
        r"(?:^|\n)(\d+\)\s+)",
    ]
    
    raw_blocks_with_markers: List[str] = []
    
    for pattern in patterns:
        raw_blocks = re.split(pattern, full_text, flags=re.IGNORECASE)
        if len(raw_blocks) > 1:
            for i in range(1, len(raw_blocks), 2):
                block = raw_blocks[i]
                if i + 1 < len(raw_blocks):
                    block += "\n" + raw_blocks[i + 1]
                block = block.strip()
                # Check length without markers
                clean = re.sub(r"\x00PAGE_\d+\x00", "", block)
                if len(clean.strip()) > 50:
                    raw_blocks_with_markers.append(block)
            if len(raw_blocks_with_markers) >= 2:
                break
    
    if not raw_blocks_with_markers:
        for chunk in full_text.split("\n\n"):
            clean = re.sub(r"\x00PAGE_\d+\x00", "", chunk)
            if len(clean.strip()) > 100:
                raw_blocks_with_markers.append(chunk.strip())
    
    # Extract page numbers from markers and clean text
    result = []
    for block in raw_blocks_with_markers:
        page_numbers = sorted(set(int(m) for m in re.findall(r"\x00PAGE_(\d+)\x00", block)))
        clean_text = re.sub(r"\x00PAGE_\d+\x00", "", block).strip()
        if clean_text:
            result.append({
                "text": clean_text,
                "pages": page_numbers if page_numbers else []
            })
    
    return result


async def parse_question_with_llm(block: str, existing_topics: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
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
                model_name="gpt-4.1-mini",
                openai_api_key=settings.openai_api_key
            )
        else:
            print("[TASK ERROR] No LLM API key configured", flush=True)
            return None
        
        # Build topic instruction based on existing topics
        if existing_topics:
            topics_list = ", ".join(f'"{t}"' for t in existing_topics)
            topic_instruction = (
                f'"topic": first, determine the main subject of this question based on its content. '
                f'Then check if it matches one of these existing topics: [{topics_list}]. '
                f'Use an existing topic ONLY if the question is specifically and directly about that subject. '
                f'If the question covers a different subject, create a new concise topic name. '
                f'Do NOT force-fit a question into an existing topic — accuracy matters more than reuse.'
            )
        else:
            topic_instruction = (
                '"topic": a short topic/category for this question (e.g., "Delta Lake", "Spark SQL", '
                '"Data Pipelines", "Security", etc.) - choose a concise, relevant topic based on the question content'
            )
        
        prompt_template = PromptTemplate(
            input_variables=["input_text", "topic_instruction"],
            template="""
You are an expert teacher. Given a multiple-choice question with its options, respond in JSON format as follows:

"question": the question text 
"options": a list of options as strings, each starting with a letter label (A., B., C., ...) — if the input options do not have letters, add them in this format 
"correct_answer": the letter and text of the correct option (e.g. "B. Example answer") 
"explanation": a detailed explanation of why the answer is correct
{topic_instruction}

Question text + options: 
{input_text}

Respond only with valid JSON:
"""
        )
        
        chain = prompt_template | llm | StrOutputParser()
        
        # Use synchronous invoke directly (LangChain handles this)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(chain.invoke, {
                "input_text": block.strip(),
                "topic_instruction": topic_instruction,
            })
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
            
                # Extract text with page tracking
                print(f"[TASK] Extracting text from {pdf_path}", flush=True)
                pages_data = extract_text_with_pages(pdf_path)
                total_chars = sum(len(pd["text"]) for pd in pages_data)
                print(f"[TASK] Extracted {total_chars} characters from {len(pages_data)} pages", flush=True)
                cert.processing_progress = 10
                await db.commit()
                
                # Extract embedded images (actual images, not full pages)
                print("[TASK] Extracting embedded images from PDF", flush=True)
                images_dir = os.path.join(
                    settings.data_path, "images", str(certification_id)
                )
                embedded_images = extract_embedded_images(pdf_path, images_dir)
                # Group images by page for easy lookup
                images_by_page: Dict[int, List[Dict[str, Any]]] = {}
                for img in embedded_images:
                    images_by_page.setdefault(img["page"], []).append(img)
                print(f"[TASK] Found {len(embedded_images)} embedded images across {len(images_by_page)} pages", flush=True)
                cert.processing_progress = 20
                await db.commit()
                
                # Split into question blocks with page tracking
                print("[TASK] Splitting text into question blocks", flush=True)
                blocks_with_pages = split_into_question_blocks_with_pages(pages_data)
                total_blocks = len(blocks_with_pages)
                print(f"[TASK] Found {total_blocks} question blocks", flush=True)
                
                if total_blocks == 0:
                    cert.processing_status = "failed"
                    cert.processing_progress = 100
                    await db.commit()
                    print("[TASK ERROR] No question blocks found in PDF", flush=True)
                    return
                
                # Process each block
                questions_created = 0
                extracted_topics: List[str] = []  # Track topics for consistency
                cert.processing_total_blocks = total_blocks
                cert.processing_current_block = 0
                await db.commit()
                
                for i, block_info in enumerate(blocks_with_pages):
                    block = block_info["text"]
                    block_pages = block_info["pages"]
                    print(f"[TASK] Processing block {i+1}/{total_blocks} (pages: {block_pages})...", flush=True)
                    cert.processing_current_block = i + 1
                    
                    try:
                        question_data = await parse_question_with_llm(block, existing_topics=extracted_topics or None)
                    except Exception as llm_err:
                        print(f"[TASK ERROR] LLM failed for block {i+1}: {llm_err}", flush=True)
                        question_data = None
                    
                    if question_data:
                        # Find embedded images on the pages this question spans
                        question_images: List[Dict[str, Any]] = []
                        for page_num in block_pages:
                            if page_num in images_by_page:
                                question_images.extend(images_by_page[page_num])
                        
                        has_imgs = len(question_images) > 0
                        
                        # Create question
                        question = Question(
                            certification_id=certification_id,
                            question_number=i + 1,
                            question_text=question_data["question"],
                            options=question_data["options"],
                            correct_answer=question_data["correct_answer"],
                            explanation=question_data["explanation"],
                            topic=question_data.get("topic"),
                            has_images=has_imgs
                        )
                        db.add(question)
                        await db.flush()
                        
                        # Create QuestionImage records for each embedded image
                        if has_imgs:
                            for img_order, img in enumerate(question_images, 1):
                                relative_path = f"{certification_id}/{img['filename']}"
                                qi = QuestionImage(
                                    question_id=question.id,
                                    image_path=relative_path,
                                    image_order=img_order,
                                    position_in_pdf=f"page_{img['page']}",
                                    width=img["width"],
                                    height=img["height"]
                                )
                                db.add(qi)
                            await db.flush()
                            print(f"[TASK]   -> {len(question_images)} image(s) linked", flush=True)
                        
                        questions_created += 1
                        cert.total_questions = questions_created
                        # Track extracted topic for future questions
                        topic = question_data.get("topic")
                        if topic and topic not in extracted_topics:
                            extracted_topics.append(topic)
                        print(f"[TASK] Question {i+1} created (topic: {topic or 'N/A'}, known topics: {len(extracted_topics)})", flush=True)
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
