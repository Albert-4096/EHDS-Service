import re
from app.models.internal import OncologyFields, EpicrizaExtracted, TNMStaging
from app.terminology.oncology_terms import RESPONSE_STATUS

REGEX_CICLUL = re.compile(r"Ciclul:\s*(\d+)\s+Acronim:\s*(.+?)$", re.IGNORECASE | re.MULTILINE)
REGEX_ECOG = re.compile(r"(?:IP|ECOG|PS)\s*[=:]\s*(\d)\s*(?:ECOG)?", re.IGNORECASE)
REGEX_TNM = re.compile(r"([pcyr]?T[0-4X][a-z]?)\s*([Nn][0-3X])(?:\(([^)]+)\))?\s*([Mm][01X])", re.IGNORECASE)
REGEX_STADIUM = re.compile(r"st(?:d|adiu)?\.\s*([IVX]+\s*[ABCabc]?)", re.IGNORECASE)
REGEX_BRAF = re.compile(r"BRAF\s+V600E|BRAF\s+mutant", re.IGNORECASE)

def extract_oncology(zones: dict[str, str], epicriza_data: EpicrizaExtracted | None) -> OncologyFields | None:
    tratament_zone = zones.get("Tratament", "")
    epicriza_zone = zones.get("Epicriza", "")
    diag_zone = zones.get("Diagnostic", "") or zones.get("DIAGNOSTIC PRINCIPAL LA EXTERNARE", "")
    
    # Check if this is an oncology document
    ciclul_match = REGEX_CICLUL.search(tratament_zone)
    if not ciclul_match and "oncologie" not in zones.get("DATE PACIENT / HEADER", "").lower():
        # Heuristic: if no Ciclul and no "oncologie" in header, we might still have oncology data,
        # but the prompt specifically says: "Return None if doc_type is not an oncology document (no 'Ciclul' field)."
        # So we will strictly follow:
        if not ciclul_match:
            return None
            
    cycle_number = int(ciclul_match.group(1)) if ciclul_match else None
    regimen_acronym = ciclul_match.group(2).strip() if ciclul_match else None
    
    oncology_raw = epicriza_data.oncology_raw if epicriza_data and epicriza_data.oncology_raw else {}
    
    # ECOG
    ecog_score = oncology_raw.get("ecog_score")
    if ecog_score is None:
        ecog_match = REGEX_ECOG.search(epicriza_zone)
        if ecog_match:
            ecog_score = int(ecog_match.group(1))
            
    # TNM
    tnm = None
    llm_tnm = oncology_raw.get("tnm")
    if llm_tnm and isinstance(llm_tnm, dict):
        tnm = TNMStaging(**llm_tnm)
    else:
        # Fallback to regex on Diagnostic zone
        tnm_match = REGEX_TNM.search(diag_zone)
        if tnm_match:
            t_cat = tnm_match.group(1)
            n_cat = tnm_match.group(2)
            n_det = tnm_match.group(3)
            m_cat = tnm_match.group(4)
            
            stage_match = REGEX_STADIUM.search(diag_zone)
            stage_group = stage_match.group(1).strip() if stage_match else None
            
            prefix = t_cat[0] if t_cat and t_cat[0].lower() in "pcyr" else None
            
            # Look for modifiers
            modifiers = []
            if "op." in diag_zone.lower():
                modifiers.append("op.")
            if REGEX_BRAF.search(diag_zone):
                modifiers.append("braf mutant")
                
            tnm = TNMStaging(
                t_category=t_cat,
                n_category=n_cat,
                n_detail=n_det,
                m_category=m_cat,
                stage_group=stage_group,
                prefix=prefix,
                modifiers=modifiers
            )

    # Response Status
    response_status = oncology_raw.get("response_status")
    if not response_status:
        # Search in epicriza_zone
        for key, val in RESPONSE_STATUS.items():
            if re.search(r"\b" + re.escape(key) + r"\b", epicriza_zone, re.IGNORECASE):
                response_status = val
                break
                
    # Molecular Markers
    molecular_markers = dict(oncology_raw.get("molecular_markers", {}) or {})
    if not molecular_markers.get("BRAF"):
        if REGEX_BRAF.search(diag_zone) or REGEX_BRAF.search(epicriza_zone):
            molecular_markers["BRAF"] = "mutant"

    return OncologyFields(
        cycle_number=cycle_number,
        regimen_acronym=regimen_acronym,
        ecog_score=ecog_score,
        response_status=response_status,
        tnm=tnm,
        molecular_markers=molecular_markers
    )
