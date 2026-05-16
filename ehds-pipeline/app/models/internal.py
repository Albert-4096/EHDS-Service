from datetime import date as DateType, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class CheckboxOption(BaseModel):
    label: str
    checked: bool
    raw_marker: str            # the exact character/text detected ("☒", "X", "[X]")

class CheckboxGroup(BaseModel):
    header: str
    options: list[CheckboxOption]
    extraction_method: str     # "unicode" | "acroform" | "ocr_ascii" | "unknown"

class DiagnosticEntry(BaseModel):
    denumire: str
    cod_cim10: Optional[str] = None      # e.g. "I21.4"

class LabValue(BaseModel):
    test_name: str             # e.g. "Leucocite"
    test_abbreviation: Optional[str] = None  # e.g. "WBC"
    value_raw: str             # raw string before normalisation
    value_numeric: Optional[float] = None
    unit_raw: Optional[str] = None       # as extracted
    unit_ucum: Optional[str] = None      # normalised UCUM unit
    flagged: bool = False      # HP-04: asterisk prefix
    loinc_code: Optional[str] = None     # from loinc_map lookup

class LabResults(BaseModel):
    bulletin_date: Optional[DateType] = None
    cbc: dict[str, LabValue]           # hemoleucograma
    biochemistry: dict[str, LabValue]  # biochimie
    hormones: dict[str, LabValue]      # TSH, FT4, cortizol etc.
    other: dict[str, LabValue]

class ImagingResult(BaseModel):
    modality: str              # "PET CT", "CT TAP", "RMN cerebral"
    date: Optional[DateType] = None
    institution: Optional[str] = None
    conclusion: Optional[str] = None
    is_current_visit: bool     # HP-12: True only if from this admission

class TNMStaging(BaseModel):
    t_category: Optional[str] = None     # "pT2", "T3a", etc.
    n_category: Optional[str] = None
    n_detail: Optional[str] = None       # sentinel node info
    m_category: Optional[str] = None
    stage_group: Optional[str] = None    # "I B", "IV", etc.
    prefix: Optional[str] = None         # "p", "c", "y", "r"
    modifiers: list[str] = Field(default_factory=list)       # ["braf mutant", "op."]

class OncologyFields(BaseModel):
    cycle_number: Optional[int] = None
    regimen_acronym: Optional[str] = None    # "Nivo q4w"
    ecog_score: Optional[int] = None
    response_status: Optional[str] = None    # "RC", "RP", "BS", "PD"
    tnm: Optional[TNMStaging] = None
    molecular_markers: dict[str, str] = Field(default_factory=dict)  # {"BRAF": "V600E", "KRAS": "wild-type"}

class TransfusionRecord(BaseModel):
    blood_group: str
    rh: str
    product_type: str
    bag_number: str
    date: Optional[DateType] = None

class AdminCheckboxes(BaseModel):
    readmission_required: Optional[bool] = None
    readmission_timeframe_weeks: Optional[int] = None
    prescription_issued: Optional[bool] = None
    prescription_serial: Optional[str] = None
    sick_leave_issued: Optional[bool] = None
    sick_leave_serial: Optional[str] = None
    home_care_referral_issued: Optional[bool] = None
    medical_device_prescription_issued: Optional[bool] = None
    document_transmission: Optional[str] = None  # "prin asigurat" | "prin posta"
    raw_groups: list[CheckboxGroup] = Field(default_factory=list)

class AppointmentBlock(BaseModel):
    datetime_raw: str
    datetime_parsed: Optional[datetime] = None
    location: Optional[str] = None

class StructuredFields(BaseModel):
    doc_type: str                   # "DOC_HDR" | "DOC_BIS"
    nume: Optional[str] = None                # HP-13 patient name
    domiciliu: Optional[str] = None           # HP-02 address column
    nr_focg: Optional[str] = None
    contract_number: Optional[str] = None     # HP-08
    cnp: Optional[str] = None
    dob_from_cnp: Optional[DateType] = None       # HP-13: derived from CNP
    dob_explicit: Optional[DateType] = None        # HP-13: from "Data nastere" text
    sex_from_cnp: Optional[str] = None
    varsta: Optional[int] = None
    sex_explicit: Optional[str] = None
    grup_sangvin: Optional[str] = None
    rh: Optional[str] = None
    alergii: Optional[str] = None
    data_internarii: Optional[datetime] = None   # includes time + tz
    data_externarii: Optional[datetime] = None
    sectia: Optional[str] = None
    medic: Optional[str] = None
    stare_externare: Optional[str] = None
    diagnostic_principal: Optional[DiagnosticEntry] = None
    diagnostice_secundare: list[DiagnosticEntry] = Field(default_factory=list)
    confidence_score: float = 0.0
    parsing_warnings: list[str] = Field(default_factory=list)

class ProcedureEntry(BaseModel):
    name: str
    date: Optional[DateType] = None
    performed_age: Optional[str] = None
    body_site: Optional[str] = None
    implants_inserted: list[str] = Field(default_factory=list)
    implants_removed: list[str] = Field(default_factory=list)
    
class DeviceEntry(BaseModel):
    name: str
    body_site: Optional[str] = None

class EpicrizaExtracted(BaseModel):
    # current visit only (HP-12)
    motive_internare: list[str] = Field(default_factory=list)
    examen_obiectiv: dict[str, Optional[str]] = Field(default_factory=dict)
    current_labs_in_narrative: list[str] = Field(default_factory=list)  # anything not in formal lab section
    current_treatment_narrative: Optional[str] = None
    clinical_status: Optional[str] = None    # "ameliorat", "stabil", etc.
    # historical (HP-12)
    antecedente_heredocolaterale: Optional[str] = None
    antecedente_personale: list[str] = Field(default_factory=list)
    history_timeline: list[dict] = Field(default_factory=list)   # [{date, event_type, description}]
    imaging_results: list[ImagingResult] = Field(default_factory=list)  # HP-18
    administered_in_hospital: list[str] = Field(default_factory=list)
    procedures: list[ProcedureEntry] = Field(default_factory=list)
    historical_procedures: list[ProcedureEntry] = Field(default_factory=list)
    implants: list[DeviceEntry] = Field(default_factory=list)
    adverse_events: list[str] = Field(default_factory=list)
    oncology_raw: Optional[dict] = Field(default_factory=dict)  # From LLM extraction


class MedicationEntry(BaseModel):
    medicament: str
    doza: Optional[str] = None
    frecventa: Optional[str] = None
    durata: Optional[str] = None
    atc_code: Optional[str] = None
    dose_is_total: bool = False    # HP-10: "DT" suffix
    raw: str

class MergedRecord(BaseModel):
    doc_type: str
    structured: StructuredFields
    labs: Optional[LabResults] = None
    checkboxes: Optional[AdminCheckboxes] = None
    appointment: Optional[AppointmentBlock] = None
    epicriza: Optional[EpicrizaExtracted] = None
    medications: list[MedicationEntry] = Field(default_factory=list)
    oncology: Optional[OncologyFields] = None
    transfusions: list[TransfusionRecord] = Field(default_factory=list)
    overall_confidence: float = 0.0
    all_warnings: list[str] = Field(default_factory=list)

# Additional model for stage0 forensics
class DocumentForensics(BaseModel):
    is_scanned: bool
    page_count: int
    has_acroform_widgets: bool
    estimated_text_density: float
    file_type: str = "pdf"  # To track the detected file type
    cached_pages_text: list[str] = Field(default_factory=list)
