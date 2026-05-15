from datetime import date, timedelta
from app.pipeline.stage2_classify import DocumentType
from app.models.errors import CoreSetError
from app.models.internal import (
    StructuredFields, LabResults, AdminCheckboxes,
    AppointmentBlock, EpicrizaExtracted, MedicationEntry, OncologyFields,
    TransfusionRecord, MergedRecord
)
from app.utils.logger import get_logger

logger = get_logger()


def _has_patient_identity(structured: StructuredFields) -> bool:
    cnp = (structured.cnp or "").strip()
    nume = (structured.nume or "").strip()
    return bool(cnp) or bool(nume)


def _epicriza_required(doc_type: DocumentType) -> bool:
    return doc_type in (
        DocumentType.HOSPITAL_DISCHARGE_REPORT,
        DocumentType.OUTPATIENT_MEDICAL_LETTER,
    )


def _epicriza_present(epicriza: EpicrizaExtracted | None, epicriza_zone_text: str) -> bool:
    if epicriza_zone_text.strip():
        return True
    if not epicriza:
        return False
    return bool(
        epicriza.motive_internare
        or epicriza.clinical_status
        or epicriza.current_treatment_narrative
        or epicriza.procedures
        or epicriza.history_timeline
        or epicriza.imaging_results
    )


def merge_and_validate(
    doc_type: DocumentType,
    structured: StructuredFields,
    labs: LabResults | None = None,
    checkboxes: AdminCheckboxes | None = None,
    appointment: AppointmentBlock | None = None,
    epicriza: EpicrizaExtracted | None = None,
    medications: list[MedicationEntry] | None = None,
    oncology: OncologyFields | None = None,
    transfusions: list[TransfusionRecord] | None = None,
    epicriza_zone_text: str = "",
) -> MergedRecord:
    all_warnings = structured.parsing_warnings.copy()

    # R7 / HP-13: Core Set validation gate
    if not _has_patient_identity(structured):
        raise CoreSetError("Core Set violation: Patient requires CNP or Nume.")

    if not structured.data_internarii:
        raise CoreSetError("Core Set violation: missing admission date (data_internarii).")

    if _epicriza_required(doc_type) and not _epicriza_present(epicriza, epicriza_zone_text):
        raise CoreSetError("Core Set violation: missing Epicriza narrative.")

    cnp_blank = not (structured.cnp or "").strip()
    nume_present = bool((structured.nume or "").strip())
    if cnp_blank and nume_present:
        all_warnings.append(
            "CNP absent but Nume present: Patient.identifier will use DataAbsentReason."
        )

    if not (structured.medic or "").strip():
        all_warnings.append(
            "Medic absent: Practitioner will be created with DataAbsentReason (non-blocking)."
        )

    # HP-13: Age vs CNP DOB
    if structured.dob_from_cnp and structured.varsta is not None:
        if structured.data_internarii:
            document_year = structured.data_internarii.year
        else:
            document_year = date.today().year

        calculated_age = document_year - structured.dob_from_cnp.year
        if abs(calculated_age - structured.varsta) > 1:
            warn_msg = (
                f"Age discrepancy detected: CNP implies age {calculated_age}, "
                f"but text states {structured.varsta}."
            )
            logger.warning(warn_msg)
            all_warnings.append(warn_msg)

    # HP-12: Cross-validation
    if doc_type == DocumentType.HOSPITAL_DISCHARGE_REPORT and structured.data_externarii is None:
        if appointment and appointment.datetime_parsed:
            structured.data_externarii = appointment.datetime_parsed - timedelta(days=1)
            logger.info("Data externarii inferred from appointment date (-1 day).")
            all_warnings.append("Data externarii inferred from appointment date (-1 day).")

    c_struct = structured.confidence_score
    c_epicriza = 1.0 if epicriza and epicriza.motive_internare else 0.0
    c_labs = 1.0 if labs and (labs.cbc or labs.biochemistry or labs.other or labs.hormones) else 0.0

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
        all_warnings=all_warnings,
    )
