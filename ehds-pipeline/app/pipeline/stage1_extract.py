import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path

from app.pipeline.stage0_forensics import PDFForensics
from app.utils.text_clean import join_pages, get_header_fingerprint, strip_repeated_headers, normalise_whitespace
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger()

def extract_text(pdf_path: Path, forensics: PDFForensics) -> str:
    """
    Extracts text from a PDF, handling both digital and scanned documents.
    Applies text cleaning pipeline to join pages and strip repeated headers.
    """
    pages_text = []

    if not forensics.is_scanned:
        # Digital PDF extraction
        logger.debug(f"Extracting text directly from digital PDF: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
    else:
        # Scanned PDF extraction (OCR)
        logger.info(f"PDF is scanned. Running OCR with lang={settings.pdf_ocr_lang} on {pdf_path}")
        images = convert_from_path(pdf_path, dpi=300)
        for i, img in enumerate(images):
            logger.debug(f"Running OCR on page {i+1}/{len(images)}")
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
