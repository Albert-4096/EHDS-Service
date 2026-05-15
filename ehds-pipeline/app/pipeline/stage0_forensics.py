import pdfplumber
import fitz  # PyMuPDF
from pathlib import Path
from app.models.internal import DocumentForensics

def detect_file_type(file_path: Path) -> DocumentForensics:
    """
    Analyzes a file to determine if it is scanned, how many pages it has,
    if it contains AcroForm widgets, and its estimated text density.
    Supports PDF, DOCX, and images (JPG, PNG).
    """
    ext = file_path.suffix.lower()
    total_characters = 0
    page_count = 0
    is_scanned = False
    has_acroform_widgets = False
    estimated_text_density = 0.0
    file_type = "pdf"
    
    if ext == ".pdf":
        file_type = "pdf"
        pages_text_cache = []
        # 1. Use pdfplumber to check text density and page count
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    total_characters += len(text)
                    pages_text_cache.append(text)

        estimated_text_density = total_characters / page_count if page_count > 0 else 0.0
        is_scanned = estimated_text_density < 100

        # 2. Use pymupdf to check for AcroForm widgets
        with fitz.open(file_path) as doc:
            for page in doc:
                if page.widgets():
                    has_acroform_widgets = True
                    break
    elif ext in (".jpg", ".jpeg", ".png"):
        file_type = "image"
        page_count = 1
        is_scanned = True  # Images are essentially scanned
        has_acroform_widgets = False
        estimated_text_density = 0.0
    elif ext == ".docx":
        file_type = "docx"
        page_count = 1  # For docx we might not easily know page count without layout
        is_scanned = False
        has_acroform_widgets = False
        # Density doesn't strictly matter for docx, but we'll set it high to show not scanned
        estimated_text_density = 1000.0
        
    forensics = DocumentForensics(
        is_scanned=is_scanned,
        page_count=page_count,
        has_acroform_widgets=has_acroform_widgets,
        estimated_text_density=estimated_text_density,
        file_type=file_type,
    )
    # Cache extracted page texts for digital PDFs so stage1 can skip a re-read.
    # Scanned PDFs have no usable pdfplumber text, so the cache stays empty.
    if file_type == "pdf" and not is_scanned:
        forensics.cached_pages_text = pages_text_cache
    return forensics
