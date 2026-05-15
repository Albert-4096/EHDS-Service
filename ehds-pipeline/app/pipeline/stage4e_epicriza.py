from pydantic import BaseModel, Field
from typing import Optional, List, Dict

from app.models.internal import EpicrizaExtracted, ImagingResult, ProcedureEntry, DeviceEntry
from app.pipeline.stage2_classify import DocumentType
from app.services.llm_client import llm_client, LLMParseError
from app.utils.text_clean import strip_page_artifacts
from app.utils.date_parser import parse_romanian_date, DateParseError

# CONTEXT.md §9 — schema aligned with specification


class CurrentVisitSchema(BaseModel):
    motive_internare: List[str] = Field(default_factory=list)
    examen_obiectiv: Dict[str, Optional[str]] = Field(default_factory=dict)
    clinical_status: Optional[str] = None
    administered_in_hospital: List[str] = Field(default_factory=list)
    treatment_narrative: Optional[str] = None


class HistoryTimelineEvent(BaseModel):
    date: Optional[str] = None
    event_type: str
    description: str


class HistoryProcedureSchema(BaseModel):
    date: Optional[str] = None
    performed_age: Optional[str] = None
    description: str
    anatomical_site: Optional[str] = None
    implants_inserted: List[str] = Field(default_factory=list)
    implants_removed: List[str] = Field(default_factory=list)


class ImagingResultSchema(BaseModel):
    modality: str
    date: Optional[str] = None
    institution: Optional[str] = None
    conclusion: str
    is_current_visit: bool = False


class HistorySchema(BaseModel):
    antecedente_heredocolaterale: Optional[str] = None
    antecedente_personale_patologice: List[str] = Field(default_factory=list)
    history_timeline: List[HistoryTimelineEvent] = Field(default_factory=list)
    procedures: List[HistoryProcedureSchema] = Field(default_factory=list)
    imaging_results: List[ImagingResultSchema] = Field(default_factory=list)


class TNMSchema(BaseModel):
    t_category: Optional[str] = None
    n_category: Optional[str] = None
    n_detail: Optional[str] = None
    m_category: Optional[str] = None
    stage_group: Optional[str] = None
    modifiers: List[str] = Field(default_factory=list)


class OncologySchema(BaseModel):
    ecog_score: Optional[int] = None
    response_status: Optional[str] = None
    tnm: Optional[TNMSchema] = None
    molecular_markers: Dict[str, str] = Field(default_factory=dict)


class EpicrizaLLMResponse(BaseModel):
    current_visit: CurrentVisitSchema
    history: HistorySchema
    oncology: OncologySchema


SYSTEM_PROMPT = """You are a medical data extraction engine for an EHDS-compliant FHIR pipeline.
You receive the Epicriza section of a Romanian clinical document. The document
may span multiple years of patient history.

CRITICAL RULES:
1. Return ONLY valid JSON. No markdown. No explanation. No preamble.
2. If a value is absent from the text, return null. NEVER infer or fabricate.
3. Separate CURRENT VISIT data from HISTORICAL data:
   - "current_visit": data about THIS specific admission/session only.
     Signaled by: "Actual, se prezinta...", "Se administreaza...",
     "In prezent...", or the most recent dated event.
   - "history_timeline": all prior events mentioned in the narrative.
4. Preserve original Romanian text for all string fields. Do not translate.
5. For imaging results: extract each separately with its date.
6. For surgical/procedural events: extract each as a procedure entry with
   date (YYYY-MM-DD or null), description, anatomical_site, implants array.
7. For relative temporal expressions ("la varsta de 3 saptamani", "dupa 12 ani"):
   return date as null and populate performed_age with the relative expression.
   NEVER infer an absolute date you cannot calculate from the text.
8. ECOG/IP/PS performance status -> oncology.ecog_score as integer.
"""


def _parse_optional_date(raw: str | None):
    if not raw:
        return None
    try:
        return parse_romanian_date(raw)
    except DateParseError:
        return None


async def extract_epicriza(epicriza_text: str, doc_type: DocumentType) -> EpicrizaExtracted:
    """Extracts structured data from the Epicriza narrative using the LLM client."""
    if not epicriza_text.strip():
        return EpicrizaExtracted()

    cleaned_text = strip_page_artifacts(epicriza_text)

    response: EpicrizaLLMResponse = await llm_client.extract_structured_data(
        text=cleaned_text,
        schema=EpicrizaLLMResponse,
        system_prompt=SYSTEM_PROMPT,
    )

    imaging_results_mapped = []
    for img in response.history.imaging_results:
        imaging_results_mapped.append(
            ImagingResult(
                modality=img.modality,
                date=_parse_optional_date(img.date),
                institution=img.institution,
                conclusion=img.conclusion,
                is_current_visit=img.is_current_visit,
            )
        )

    history_timeline_mapped = [
        {
            "date": event.date,
            "event_type": event.event_type,
            "description": event.description,
        }
        for event in response.history.history_timeline
    ]

    historical_procedures = []
    for proc in response.history.procedures:
        historical_procedures.append(
            ProcedureEntry(
                name=proc.description,
                date=_parse_optional_date(proc.date),
                performed_age=proc.performed_age,
                body_site=proc.anatomical_site,
                implants_inserted=proc.implants_inserted,
                implants_removed=proc.implants_removed,
            )
        )

    implants_mapped = []
    for proc in response.history.procedures:
        for imp_name in proc.implants_inserted:
            implants_mapped.append(
                DeviceEntry(name=imp_name, body_site=proc.anatomical_site)
            )

    return EpicrizaExtracted(
        motive_internare=response.current_visit.motive_internare,
        examen_obiectiv=response.current_visit.examen_obiectiv,
        current_labs_in_narrative=[],
        current_treatment_narrative=response.current_visit.treatment_narrative,
        clinical_status=response.current_visit.clinical_status,
        antecedente_heredocolaterale=response.history.antecedente_heredocolaterale,
        antecedente_personale=response.history.antecedente_personale_patologice,
        history_timeline=history_timeline_mapped,
        imaging_results=imaging_results_mapped,
        administered_in_hospital=response.current_visit.administered_in_hospital,
        procedures=[],
        historical_procedures=historical_procedures,
        implants=implants_mapped,
        adverse_events=[],
        oncology_raw=response.oncology.model_dump() if response.oncology else {},
    )
