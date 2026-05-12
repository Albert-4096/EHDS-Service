from enum import Enum

class DocumentType(str, Enum):
    DOC_HDR = "DOC_HDR"
    DOC_BIS = "DOC_BIS"
    DOC_SM = "DOC_SM"
    UNKNOWN = "UNKNOWN"

class DocumentTypeError(Exception):
    """Raised when the document type cannot be identified."""
    pass

def classify_document(text: str) -> DocumentType:
    """
    Classifies a medical document based on its first 30 lines.
    Raises DocumentTypeError if the document type is unknown.
    """
    lines = text.splitlines()
    header_text = "\n".join(lines[:30]).lower()

    # Rule 1: If text contains "BILET DE IESIRE" or "FO:" near the header -> DOC_BIS
    if "bilet de iesire" in header_text or "fo:" in header_text:
        return DocumentType.DOC_BIS
        
    # Rule 2: Else if text contains "BILET DE EXTERNARE" -> DOC_HDR
    if "bilet de externare" in header_text:
        return DocumentType.DOC_HDR
        
    # Rule 3: Else if text contains "SCRISOARE MEDICALA" without "BILET DE IESIRE" -> DOC_SM
    if "scrisoare medicala" in header_text:
        return DocumentType.DOC_SM
        
    # Rule 4: Else -> UNKNOWN -> raise DocumentTypeError
    raise DocumentTypeError(f"Unknown document type. Header text was:\n{header_text}")
