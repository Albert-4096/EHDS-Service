import pdfplumber
import fitz  # PyMuPDF
from pathlib import Path
from app.models.internal import PDFForensics

def detect_pdf_type(pdf_path: Path) -> PDFForensics:
    """
    Analyzes a PDF file to determine if it is scanned, how many pages it has,
    if it contains AcroForm widgets, and its estimated text density.
    """
    total_characters = 0
    page_count = 0
    
    # 1. Use pdfplumber to check text density and page count
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                total_characters += len(text)
                
    estimated_text_density = total_characters / page_count if page_count > 0 else 0.0
    is_scanned = estimated_text_density < 100
    
    # 2. Use pymupdf to check for AcroForm widgets
    has_acroform_widgets = False
    with fitz.open(pdf_path) as doc:
        for page in doc:
            if page.widgets():
                # We found at least one widget, but let's check if there are actual checkbox widgets
                # to be safe, although the prompt just says "widget count > 0"
                has_acroform_widgets = True
                break

    return PDFForensics(
        is_scanned=is_scanned,
        page_count=page_count,
        has_acroform_widgets=has_acroform_widgets,
        estimated_text_density=estimated_text_density
    )
