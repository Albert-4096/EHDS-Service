from enum import Enum

class DocumentType(str, Enum):
    HOSPITAL_DISCHARGE_REPORT = "Hospital_Discharge_Report"
    OUTPATIENT_MEDICAL_LETTER = "Outpatient_Medical_Letter"
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

    # Rule 1: "bilet de iesire", "bilet de externare", or "fo:" -> HOSPITAL_DISCHARGE_REPORT
    if "bilet de iesire" in header_text or "bilet de externare" in header_text or "fo:" in header_text:
        return DocumentType.HOSPITAL_DISCHARGE_REPORT
        
    # Rule 2: "scrisoare medicala" -> OUTPATIENT_MEDICAL_LETTER
    if "scrisoare medicala" in header_text:
        return DocumentType.OUTPATIENT_MEDICAL_LETTER
        
    # Rule 3: Else -> UNKNOWN -> raise DocumentTypeError
    raise DocumentTypeError(f"Unknown document type. Header text was:\n{header_text}")
