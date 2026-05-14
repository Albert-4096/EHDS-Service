import json
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from app.models.internal import EpicrizaExtracted, ImagingResult
from app.pipeline.stage2_classify import DocumentType
from app.services.llm_client import llm_client, LLMParseError
import warnings

# Define the exact nested schema from Example E4
class CurrentVisitSchema(BaseModel):
    motive_internare: List[str] = Field(default_factory=list)
    examen_obiectiv: Dict[str, Optional[str]] = Field(default_factory=dict)
    clinical_status: Optional[str] = None
    administered_in_hospital: List[str] = Field(default_factory=list)
    procedures: List[Dict[str, Optional[str]]] = Field(default_factory=list) # name, date, body_site
    implants: List[Dict[str, Optional[str]]] = Field(default_factory=list) # name, body_site
    adverse_events: List[str] = Field(default_factory=list)
    treatment_narrative: Optional[str] = None

class HistoryTimelineEvent(BaseModel):
    date: Optional[str] = None
    event_type: str
    description: str

class ImagingResultSchema(BaseModel):
    modality: str
    date: Optional[str] = None
    institution: Optional[str] = None
    conclusion: str
    is_current_visit: bool

class HistorySchema(BaseModel):
    antecedente_heredocolaterale: Optional[str] = None
    antecedente_personale_patologice: List[str] = Field(default_factory=list)
    history_timeline: List[HistoryTimelineEvent] = Field(default_factory=list)
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
You receive the Epicriza section of a Romanian clinical document and extract
structured data. The document may span multiple years of patient history.

CRITICAL RULES:
1. Return ONLY valid JSON. No markdown. No explanation.
2. If a value is absent from the text, return null. NEVER infer or fabricate.
3. Separate CURRENT VISIT data from HISTORICAL data.
   - "current_visit": data about THIS specific admission/session only.
     The current visit is signaled by phrases like "Actual, se prezinta...",
     "Se administreaza...", "In prezent...", or the most recent dated event.
   - "history_timeline": all prior events mentioned in the narrative.
4. Preserve original Romanian text for all string fields. Do not translate.
5. For imaging results, extract each as a separate entry with its date.
6. ECOG/IP/PS performance status goes into oncology.ecog_score as an integer.
7. Explicitly extract orthopedic/pediatric procedures (e.g., surgeries, Ender nails, osteosinteza) into `procedures`.
8. Explicitly extract implantable hardware (K-wires, tije, placi, suruburi) into `implants`.
9. Extract any treatment-induced adverse events (e.g., toxicitate, degradare montaj, hipofizita autoimuna) into `adverse_events`.
"""

from app.utils.date_parser import parse_romanian_date, DateParseError

async def extract_epicriza(epicriza_text: str, doc_type: DocumentType) -> EpicrizaExtracted:
    """
    Extracts structured data from the Epicriza narrative using the LLM client.
    """
    if not epicriza_text.strip():
        return EpicrizaExtracted()
        
    try:
        response: EpicrizaLLMResponse = await llm_client.extract_structured_data(
            text=epicriza_text,
            schema=EpicrizaLLMResponse,
            system_prompt=SYSTEM_PROMPT
        )
        
        # Map response to EpicrizaExtracted
        imaging_results_mapped = []
        for img in response.history.imaging_results:
            img_date = None
            if img.date:
                try:
                    img_date = parse_romanian_date(img.date)
                except DateParseError:
                    pass
            imaging_results_mapped.append(ImagingResult(
                modality=img.modality,
                date=img_date,
                institution=img.institution,
                conclusion=img.conclusion,
                is_current_visit=img.is_current_visit
            ))
            
        history_timeline_mapped = []
        for event in response.history.history_timeline:
            history_timeline_mapped.append({
                "date": event.date,
                "event_type": event.event_type,
                "description": event.description
            })
            
        from app.models.internal import ProcedureEntry, DeviceEntry
        
        procedures_mapped = []
        for proc in response.current_visit.procedures:
            proc_date = None
            if proc.get("date"):
                try:
                    proc_date = parse_romanian_date(proc.get("date"))
                except DateParseError:
                    pass
            procedures_mapped.append(ProcedureEntry(
                name=proc.get("name", "Unknown Procedure"),
                date=proc_date,
                body_site=proc.get("body_site")
            ))
            
        implants_mapped = [
            DeviceEntry(name=imp.get("name", "Unknown Device"), body_site=imp.get("body_site"))
            for imp in response.current_visit.implants
        ]
            
        return EpicrizaExtracted(
            motive_internare=response.current_visit.motive_internare,
            examen_obiectiv=response.current_visit.examen_obiectiv,
            current_labs_in_narrative=[], # Not part of this specific LLM schema, can be derived or added if needed
            current_treatment_narrative=response.current_visit.treatment_narrative,
            clinical_status=response.current_visit.clinical_status,
            antecedente_heredocolaterale=response.history.antecedente_heredocolaterale,
            antecedente_personale=response.history.antecedente_personale_patologice,
            history_timeline=history_timeline_mapped,
            imaging_results=imaging_results_mapped,
            administered_in_hospital=response.current_visit.administered_in_hospital,
            procedures=procedures_mapped,
            implants=implants_mapped,
            adverse_events=response.current_visit.adverse_events,
            oncology_raw=response.oncology.model_dump() if response.oncology else {}
        )
        
    except LLMParseError as e:
        warnings.warn(f"LLM Parse Error: {str(e)}", RuntimeWarning)
        # On failure, return empty, emit warning
        return EpicrizaExtracted()
