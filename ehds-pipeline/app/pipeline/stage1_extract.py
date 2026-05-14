import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path
from PIL import Image
import docx

from app.pipeline.stage0_forensics import DocumentForensics
from app.utils.text_clean import join_pages, get_header_fingerprint, strip_repeated_headers, normalise_whitespace
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger()

def extract_text(file_path: Path, forensics: DocumentForensics) -> str:
    """
    Extracts text from a file, handling PDF, docx, and images.
    Applies text cleaning pipeline to join pages and strip repeated headers.
    """
    pages_text = []

    if forensics.file_type == "pdf":
        if not forensics.is_scanned:
            # Digital PDF extraction
            logger.debug(f"Extracting text directly from digital PDF: {file_path}")
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
        else:
            # Scanned PDF extraction (OCR)
            logger.info(f"PDF is scanned. Running OCR with lang={settings.pdf_ocr_lang} on {file_path}")
            images = convert_from_path(file_path, dpi=300)
            for i, img in enumerate(images):
                logger.debug(f"Running OCR on page {i+1}/{len(images)}")
                text = pytesseract.image_to_string(img, lang=settings.pdf_ocr_lang)
                if text:
                    pages_text.append(text)
                    
    elif forensics.file_type == "docx":
        logger.debug(f"Extracting text from DOCX: {file_path}")
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        if text:
            pages_text.append(text)
            
    elif forensics.file_type == "image":
        logger.info(f"File is an image. Running OCR with lang={settings.pdf_ocr_lang} on {file_path}")
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang=settings.pdf_ocr_lang)
        if text:
            pages_text.append(text)

    if not pages_text:
        return ""

    # Text cleaning pipeline
    # 1. Join pages with a single newline
    joined_text = join_pages(pages_text)
    
    # 2. Extract header fingerprint from the first page
    header_fingerprint = get_header_fingerprint(pages_text[0])
    
    # 3. Strip repeated headers
    text_without_headers = strip_repeated_headers(joined_text, header_fingerprint)
    
    # 4. Normalise whitespace
    final_text = normalise_whitespace(text_without_headers)

    return final_text
