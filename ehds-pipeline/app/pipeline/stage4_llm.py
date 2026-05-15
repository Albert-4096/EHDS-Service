"""Stage 4: Unified LLM extraction — replaces stages 4a, 4b, 4d, 4e, 4f, 4g, 4h."""

import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.models.internal import (
    AppointmentBlock,
    DeviceEntry,
    DiagnosticEntry,
    EpicrizaExtracted,
    ImagingResult,
    LabResults,
    LabValue,
    MedicationEntry,
    MergedRecord,
    OncologyFields,
    ProcedureEntry,
    StructuredFields,
    TNMStaging,
    TransfusionRecord,
)
from app.pipeline.stage2_classify import DocumentType
from app.services.llm_client import llm_client
from app.terminology.atc_lookup import drug_to_atc
from app.terminology.loinc_map import lab_to_loinc
from app.utils.cnp_parser import CNPParseError, parse_cnp
from app.utils.date_parser import DateParseError, parse_romanian_date, parse_romanian_datetime
from app.utils.numeric import normalise_romanian_decimal

_BUCHAREST = ZoneInfo("Europe/Bucharest")

# ──────────────────────────────────────────────────────────
# Extraction schema — LLM populates text only, never codes
# ──────────────────────────────────────────────────────────


class LabEntryLLM(BaseModel):
    test_name: str
    test_abbreviation: Optional[str] = None
    value_raw: str
    unit_raw: Optional[str] = None
    flagged: bool = False
    panel: str = "other"  # "cbc" | "biochemistry" | "hormones" | "other"


class MedicationLLM(BaseModel):
    medicament: str
    doza: Optional[str] = None
    frecventa: Optional[str] = None
    durata: Optional[str] = None
    dose_is_total: bool = False
    raw: str = ""


class HistoryEventLLM(BaseModel):
    date: Optional[str] = None
    event_type: str
    description: str


class ProcedureLLM(BaseModel):
    description: str
    date: Optional[str] = None
    performed_age: Optional[str] = None
    anatomical_site: Optional[str] = None
    implants_inserted: list[str] = Field(default_factory=list)
    implants_removed: list[str] = Field(default_factory=list)


class ImagingLLM(BaseModel):
    modality: str
    date: Optional[str] = None
    institution: Optional[str] = None
    conclusion: str
    is_current_visit: bool = False


class TransfusionLLM(BaseModel):
    blood_group: str
    rh: str
    product_type: str
    bag_number: str
    date: Optional[str] = None


class ClinicalDocumentExtraction(BaseModel):
    # Document type — derived from document content, not a separate classifier
    # "DOC_HDR" = Bilet de Externare (Hospital Discharge Report)
    # "DOC_BIS" = Bilet de Iesire / Scrisoare Medicala (Outpatient Letter)
    document_type: str = "DOC_HDR"

    # Patient demographics
    patient_name: Optional[str] = None
    cnp: Optional[str] = None
    age: Optional[int] = None
    blood_group: Optional[str] = None
    rh_factor: Optional[str] = None
    address: Optional[str] = None
    allergies: Optional[str] = None
    fo_number: Optional[str] = None
    contract_number: Optional[str] = None

    # Encounter
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    department: Optional[str] = None
    attending_physician: Optional[str] = None
    # Exact Romanian term: vindecat | ameliorat | staționar | agravat | decedat
    discharge_status: Optional[str] = None

    # Diagnoses — exact document text, NO codes
    primary_diagnosis_text: Optional[str] = None
    secondary_diagnoses_texts: list[str] = Field(default_factory=list)

    # Laboratory results — numeric values with units, NO LOINC codes
    lab_date: Optional[str] = None
    lab_results: list[LabEntryLLM] = Field(default_factory=list)

    # Discharge medications — drug names with dosing, NO ATC codes
    medications: list[MedicationLLM] = Field(default_factory=list)

    # Follow-up appointment
    next_appointment_datetime: Optional[str] = None
    next_appointment_location: Optional[str] = None

    # Oncology fields
    ecog_score: Optional[int] = None
    tnm_staging: Optional[str] = None  # raw string, e.g. "pT2N1M0 st. IIIB"
    oncology_cycle: Optional[int] = None
    oncology_regimen: Optional[str] = None
    molecular_markers: dict[str, str] = Field(default_factory=dict)
    response_status: Optional[str] = None

    # Current-visit epicriza narrative
    chief_complaint: list[str] = Field(default_factory=list)
    physical_exam: dict[str, Optional[str]] = Field(default_factory=dict)
    clinical_status: Optional[str] = None
    treatment_narrative: Optional[str] = None
    administered_in_hospital: list[str] = Field(default_factory=list)

    # Medical history
    family_history: Optional[str] = None
    personal_medical_history: list[str] = Field(default_factory=list)
    history_timeline: list[HistoryEventLLM] = Field(default_factory=list)
    past_procedures: list[ProcedureLLM] = Field(default_factory=list)
    imaging_results: list[ImagingLLM] = Field(default_factory=list)

    # Transfusions (primarily DOC_BIS)
    transfusions: list[TransfusionLLM] = Field(default_factory=list)

    # Administrative (text-based checkbox mentions)
    readmission_required: Optional[bool] = None
    prescription_issued: Optional[bool] = None
    sick_leave_issued: Optional[bool] = None


SYSTEM_PROMPT = """You are a medical data extraction engine for an EHDS-compliant FHIR pipeline.
You receive the full text of a Romanian hospital discharge report (Bilet de Externare)
or outpatient medical letter (Bilet de Ieșire / Scrisoare Medicală).

CRITICAL RULES:
1. Return ONLY valid JSON matching the schema. No markdown, no explanation, no preamble.
2. Return null for any field absent from the document. NEVER fabricate or infer values.
3. Preserve EXACT Romanian text for all string fields. Do not translate.
4. Set document_type: "DOC_HDR" for Bilet de Externare (hospital discharge), "DOC_BIS" for
   Bilet de Ieșire or Scrisoare Medicală (outpatient letter). Default to "DOC_HDR" if unclear.
5. NEVER generate medical codes (SNOMED CT, ICD-10/CIM-10, LOINC, ATC, UCUM). TEXT ONLY.
6. Dates: extract exactly as written ("15.03.2023", "15 martie 2023", "2023-03-15").
7. CNP: exactly 13 digits. Return null if not found or if the string is not 13 digits.
8. Lab results: extract ALL individual test name/value/unit triplets from any lab section.
   Panel classification:
   - "cbc": hemoleucograma (WBC/Leucocite, RBC/Hematii, HGB/Hemoglobina, HCT, PLT, MCV, MCH, MCHC, neutrofile, limfocite, monocite, eozinofile, RDW, MPV...)
   - "hormones": TSH, FT4, cortizol, DHEA, FSH, LH, prolactina, estradiol, testosteron, progesteron
   - "biochemistry": all other quantitative lab values (creatinina, glicemie, bilirubina, transaminaze, sodiu, potasiu, calciu, fosfataza, etc.)
   - "other": anything unclear
   Set flagged=true if the value has an asterisk prefix or is explicitly marked outside reference range.
9. Medications: one entry per drug from the discharge medication list or treatment section.
   raw = full original text line. dose_is_total=true if line contains " DT" after the dose.
10. Separate CURRENT VISIT from HISTORY:
    - chief_complaint, treatment_narrative, administered_in_hospital: THIS admission only.
    - past_procedures, history_timeline, personal_medical_history: all prior events.
11. Oncology: ECOG/IP/PS → ecog_score (integer 0–4). TNM → exact raw string ("pT2N1M0").
    "Ciclul: N" → oncology_cycle (integer).
11. Blood group: "A", "B", "AB", or "O" only. Rh factor: "pozitiv" | "negativ" | "+" | "-".
12. discharge_status: exact Romanian term (vindecat / ameliorat / staționar / agravat / decedat).
13. physical_exam: keys are organ/system names, values are the finding text.
"""

# ──────────────────────────────────────────────────────────
# UCUM unit normalisation (text → canonical notation)
# ──────────────────────────────────────────────────────────

_UCUM: dict[str, str] = {
    "× 10^9/l": "10*9/L",
    "x 10^9/l": "10*9/L",
    "10^9/l": "10*9/L",
    "× 10^12/l": "10*12/L",
    "10^12/l": "10*12/L",
    "g/dl": "g/dL",
    "g/l": "g/L",
    "fl": "fL",
    "pg": "pg",
    "%": "%",
    "mmol/l": "mmol/L",
    "mg/dl": "mg/dL",
    "mg/l": "mg/L",
    "u/l": "U/L",
    "ui/l": "U/L",
    "iu/l": "U/L",
    "mui/l": "m[IU]/L",
    "ng/dl": "ng/dL",
    "ng/ml": "ng/mL",
    "ug/dl": "ug/dL",
    "ug/ml": "ug/mL",
    "mmol": "mmol",
    "meq/l": "meq/L",
    "mosm/kg": "mosm/kg",
    "sec": "s",
    "min": "min",
}


def _ucum(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return _UCUM.get(raw.strip().lower(), raw.strip())


# ──────────────────────────────────────────────────────────
# Date parsing helpers
# ──────────────────────────────────────────────────────────

def _parse_dt(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return parse_romanian_datetime(raw)
    except DateParseError:
        pass
    try:
        d = parse_romanian_date(raw)
        return datetime(d.year, d.month, d.day, tzinfo=_BUCHAREST)
    except DateParseError:
        return None


# ──────────────────────────────────────────────────────────
# Post-processing: LLM response → internal Pydantic models
# ──────────────────────────────────────────────────────────

_CIM10_RE = re.compile(r"\b([A-Z]\d{2}(?:\.\d{1,2})?)\b")


def _build_structured(ex: ClinicalDocumentExtraction, doc_type: DocumentType) -> StructuredFields:
    warnings: list[str] = []
    dob_from_cnp = None
    sex_from_cnp = None

    if ex.cnp:
        try:
            cnp_data = parse_cnp(ex.cnp)
            dob_from_cnp = cnp_data.date_of_birth
            sex_from_cnp = cnp_data.sex
        except CNPParseError as e:
            warnings.append(str(e))

    admission_dt = _parse_dt(ex.admission_date)
    discharge_dt = _parse_dt(ex.discharge_date)

    primary_diag = None
    if ex.primary_diagnosis_text:
        m = _CIM10_RE.search(ex.primary_diagnosis_text)
        primary_diag = DiagnosticEntry(
            denumire=ex.primary_diagnosis_text[:200],
            cod_cim10=m.group(1) if m else None,
        )

    sec_diags = []
    for text in ex.secondary_diagnoses_texts:
        m = _CIM10_RE.search(text)
        sec_diags.append(DiagnosticEntry(denumire=text[:200], cod_cim10=m.group(1) if m else None))

    filled = sum(
        1
        for x in [
            ex.cnp, ex.patient_name, ex.fo_number,
            admission_dt, discharge_dt, ex.attending_physician, primary_diag,
        ]
        if x is not None
    )
    confidence = min(1.0, filled / 6)

    return StructuredFields(
        doc_type=doc_type.value,
        nume=ex.patient_name,
        domiciliu=ex.address,
        nr_focg=ex.fo_number,
        contract_number=ex.contract_number,
        cnp=ex.cnp,
        dob_from_cnp=dob_from_cnp,
        sex_from_cnp=sex_from_cnp,
        varsta=ex.age,
        grup_sangvin=ex.blood_group,
        rh=ex.rh_factor,
        alergii=ex.allergies,
        data_internarii=admission_dt,
        data_externarii=discharge_dt,
        sectia=ex.department,
        medic=ex.attending_physician,
        stare_externare=ex.discharge_status,
        diagnostic_principal=primary_diag,
        diagnostice_secundare=sec_diags,
        confidence_score=confidence,
        parsing_warnings=warnings,
    )


def _build_labs(ex: ClinicalDocumentExtraction) -> LabResults:
    cbc: dict[str, LabValue] = {}
    biochem: dict[str, LabValue] = {}
    hormones: dict[str, LabValue] = {}
    other: dict[str, LabValue] = {}

    lab_date_parsed = None
    if ex.lab_date:
        try:
            lab_date_parsed = parse_romanian_date(ex.lab_date)
        except DateParseError:
            pass

    for entry in ex.lab_results:
        normalized = normalise_romanian_decimal(entry.value_raw) if entry.value_raw else ""
        try:
            val_numeric = float(normalized)
        except ValueError:
            val_numeric = None

        lab_val = LabValue(
            test_name=entry.test_name,
            test_abbreviation=entry.test_abbreviation,
            value_raw=entry.value_raw,
            value_numeric=val_numeric,
            unit_raw=entry.unit_raw,
            unit_ucum=_ucum(entry.unit_raw),
            flagged=entry.flagged,
            loinc_code=lab_to_loinc(entry.test_name, entry.test_abbreviation),
        )
        key = entry.test_abbreviation or entry.test_name
        panel = entry.panel.lower()
        if panel == "cbc":
            cbc[key] = lab_val
        elif panel == "hormones":
            hormones[key] = lab_val
        elif panel == "biochemistry":
            biochem[key] = lab_val
        else:
            other[key] = lab_val

    return LabResults(
        bulletin_date=lab_date_parsed,
        cbc=cbc,
        biochemistry=biochem,
        hormones=hormones,
        other=other,
    )


def _build_medications(ex: ClinicalDocumentExtraction) -> list[MedicationEntry]:
    return [
        MedicationEntry(
            medicament=m.medicament,
            doza=m.doza,
            frecventa=m.frecventa,
            durata=m.durata,
            atc_code=drug_to_atc(m.medicament),
            dose_is_total=m.dose_is_total,
            raw=m.raw or m.medicament,
        )
        for m in ex.medications
    ]


def _build_appointment(ex: ClinicalDocumentExtraction) -> Optional[AppointmentBlock]:
    if not ex.next_appointment_datetime:
        return None
    return AppointmentBlock(
        datetime_raw=ex.next_appointment_datetime,
        datetime_parsed=_parse_dt(ex.next_appointment_datetime),
        location=ex.next_appointment_location,
    )


def _build_epicriza(ex: ClinicalDocumentExtraction) -> EpicrizaExtracted:
    imaging = []
    for img in ex.imaging_results:
        try:
            d = parse_romanian_date(img.date) if img.date else None
        except DateParseError:
            d = None
        imaging.append(
            ImagingResult(
                modality=img.modality,
                date=d,
                institution=img.institution,
                conclusion=img.conclusion,
                is_current_visit=img.is_current_visit,
            )
        )

    timeline = [
        {"date": e.date, "event_type": e.event_type, "description": e.description}
        for e in ex.history_timeline
    ]

    historical_procs: list[ProcedureEntry] = []
    implants: list[DeviceEntry] = []
    for proc in ex.past_procedures:
        try:
            d = parse_romanian_date(proc.date) if proc.date else None
        except DateParseError:
            d = None
        historical_procs.append(
            ProcedureEntry(
                name=proc.description,
                date=d,
                performed_age=proc.performed_age,
                body_site=proc.anatomical_site,
                implants_inserted=proc.implants_inserted,
                implants_removed=proc.implants_removed,
            )
        )
        for imp_name in proc.implants_inserted:
            implants.append(DeviceEntry(name=imp_name, body_site=proc.anatomical_site))

    oncology_raw: dict = {}
    for key, val in [
        ("ecog_score", ex.ecog_score),
        ("tnm_staging", ex.tnm_staging),
        ("molecular_markers", ex.molecular_markers or {}),
        ("response_status", ex.response_status),
        ("cycle", ex.oncology_cycle),
        ("regimen", ex.oncology_regimen),
    ]:
        if val is not None and val != {}:
            oncology_raw[key] = val

    return EpicrizaExtracted(
        motive_internare=ex.chief_complaint,
        examen_obiectiv=ex.physical_exam,
        current_labs_in_narrative=[],
        current_treatment_narrative=ex.treatment_narrative,
        clinical_status=ex.clinical_status,
        antecedente_heredocolaterale=ex.family_history,
        antecedente_personale=ex.personal_medical_history,
        history_timeline=timeline,
        imaging_results=imaging,
        administered_in_hospital=ex.administered_in_hospital,
        procedures=[],
        historical_procedures=historical_procs,
        implants=implants,
        adverse_events=[],
        oncology_raw=oncology_raw,
    )


_TNM_RE = re.compile(
    r"(?P<prefix>[pcyr])?T(?P<t>[0-4][a-z]?)(?:N(?P<n>[0-3x][a-z]?))?(?:M(?P<m>[01][a-z]?))?",
    re.IGNORECASE,
)
_STAGE_RE = re.compile(r"\bst(?:adiu[lm]?)?\s*\.?\s*([IVX]+[A-D]?)\b", re.IGNORECASE)


def _build_oncology(ex: ClinicalDocumentExtraction) -> Optional[OncologyFields]:
    has_data = any([
        ex.ecog_score is not None,
        ex.tnm_staging,
        ex.oncology_cycle is not None,
        ex.oncology_regimen,
        ex.molecular_markers,
        ex.response_status,
    ])
    if not has_data:
        return None

    tnm = None
    if ex.tnm_staging:
        m = _TNM_RE.search(ex.tnm_staging)
        if m:
            sm = _STAGE_RE.search(ex.tnm_staging)
            tnm = TNMStaging(
                prefix=m.group("prefix"),
                t_category=f"T{m.group('t')}" if m.group("t") else None,
                n_category=f"N{m.group('n')}" if m.group("n") else None,
                m_category=f"M{m.group('m')}" if m.group("m") else None,
                stage_group=sm.group(1) if sm else None,
            )

    return OncologyFields(
        cycle_number=ex.oncology_cycle,
        regimen_acronym=ex.oncology_regimen,
        ecog_score=ex.ecog_score,
        response_status=ex.response_status,
        tnm=tnm,
        molecular_markers=ex.molecular_markers,
    )


def _build_transfusions(ex: ClinicalDocumentExtraction) -> list[TransfusionRecord]:
    result = []
    for t in ex.transfusions:
        try:
            d = parse_romanian_date(t.date) if t.date else None
        except DateParseError:
            d = None
        result.append(TransfusionRecord(
            blood_group=t.blood_group,
            rh=t.rh,
            product_type=t.product_type,
            bag_number=t.bag_number,
            date=d,
        ))
    return result


# ──────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────

async def extract_all(
    full_text: str,
) -> tuple[
    DocumentType,
    StructuredFields,
    LabResults,
    Optional[AppointmentBlock],
    EpicrizaExtracted,
    list[MedicationEntry],
    Optional[OncologyFields],
    list[TransfusionRecord],
]:
    """
    Single LLM pass over the full document text.
    Classifies the document type AND extracts all clinical fields in one call,
    replacing stages 2, 4a, 4b, 4d, 4e, 4f, 4g, and 4h.
    The LLM extracts clinical TEXT only; terminology codes are resolved deterministically
    from local maps (LOINC, ATC) and any CIM-10 codes embedded in the source text.
    """
    extraction: ClinicalDocumentExtraction = await llm_client.extract_structured_data(
        text=full_text,
        schema=ClinicalDocumentExtraction,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=8192,
    )

    doc_type = (
        DocumentType.OUTPATIENT_MEDICAL_LETTER
        if extraction.document_type == "DOC_BIS"
        else DocumentType.HOSPITAL_DISCHARGE_REPORT
    )

    return (
        doc_type,
        _build_structured(extraction, doc_type),
        _build_labs(extraction),
        _build_appointment(extraction),
        _build_epicriza(extraction),
        _build_medications(extraction),
        _build_oncology(extraction),
        _build_transfusions(extraction),
    )
