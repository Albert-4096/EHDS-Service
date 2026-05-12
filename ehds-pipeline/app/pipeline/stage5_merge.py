from datetime import date
from app.models.internal import (
    DocumentType, StructuredFields, LabResults, AdminCheckboxes,
    AppointmentBlock, EpicrizaExtracted, MedicationEntry, OncologyFields,
    TransfusionRecord, MergedRecord
)
from app.utils.logger import get_logger

logger = get_logger()

def merge_and_validate(
    doc_type: DocumentType,
    structured: StructuredFields,
    labs: LabResults | None = None,
    checkboxes: AdminCheckboxes | None = None,
    appointment: AppointmentBlock | None = None,
    epicriza: EpicrizaExtracted | None = None,
    medications: list[MedicationEntry] | None = None,
    oncology: OncologyFields | None = None,
    transfusions: list[TransfusionRecord] | None = None
) -> MergedRecord:
    
    all_warnings = structured.parsing_warnings.copy()
    
    # HP-13: Validation Gate - Age vs CNP DOB
    if structured.dob_from_cnp and structured.varsta is not None:
        if structured.data_internarii:
            document_year = structured.data_internarii.year
        else:
            document_year = date.today().year
            
        calculated_age = document_year - structured.dob_from_cnp.year
        if abs(calculated_age - structured.varsta) > 1:
            warn_msg = f"Age discrepancy detected: CNP implies age {calculated_age}, but text states {structured.varsta}."
            logger.warning(warn_msg)
            all_warnings.append(warn_msg)
            
    # HP-12: Cross-validation
    if doc_type == DocumentType.DOC_BIS and structured.data_externarii is None:
        if appointment and appointment.datetime_parsed:
            from datetime import timedelta
            structured.data_externarii = appointment.datetime_parsed - timedelta(days=1)
            logger.info("Data externarii inferred from appointment date (-1 day).")
            all_warnings.append("Data externarii inferred from appointment date (-1 day).")
            
    # Compute overall confidence
    # structured (50%), epicriza (30%, 1.0 if successfully parsed), labs (20%)
    c_struct = structured.confidence_score
    c_epicriza = 1.0 if epicriza and epicriza.motive_internare else 0.0 # basic check for successful parse
    c_labs = 1.0 if labs and (labs.cbc or labs.biochemistry or labs.other) else 0.0
    
    overall_confidence = (c_struct * 0.5) + (c_epicriza * 0.3) + (c_labs * 0.2)
    
    return MergedRecord(
        doc_type=doc_type.value,
        structured=structured,
        labs=labs,
        checkboxes=checkboxes,
        appointment=appointment,
        epicriza=epicriza,
        medications=medications or [],
        oncology=oncology,
        transfusions=transfusions or [],
        overall_confidence=overall_confidence,
        all_warnings=all_warnings
    )
