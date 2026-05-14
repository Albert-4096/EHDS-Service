import re
from app.pipeline.stage2_classify import DocumentType

HOSPITAL_DISCHARGE_REPORT_ANCHORS = [
    "DATE PACIENT",
    "DATE PACIENT / HEADER",   # virtual
    "DATE INTERNARE",
    "DIAGNOSTIC DE TRIMITERE",
    "DIAGNOSTIC LA INTERNARE",
    "DIAGNOSTIC PRINCIPAL LA EXTERNARE",
    "DIAGNOSTICE SECUNDARE",
    "Diagnostic",
    "Investigatii efectuate",
    "STARE LA EXTERNARE",
    "TRATAMENT LA EXTERNARE",
    "Tratament",
    "EPICRIZĂ",
    "Epicriza",
    "RECOMANDĂRI",
    "Recomandari",
    "MEDIC CURANT",
    "APPOINTMENT_BLOCK",       # virtual
    "CHECKBOX_BLOCKS",         # virtual
    "Calea de transmitere"
]

OUTPATIENT_MEDICAL_LETTER_ANCHORS = [
    "DATE PACIENT / HEADER",
    "Diagnostic",
    "Recomandari",
    "Tratament",
    "Medic"
]

def _build_diacritic_core(anchor: str) -> str:
    """
    Builds the core (inner) diacritic-tolerant pattern for an anchor string.
    Does NOT include start/end anchors — those are added at usage sites.
    """
    mapping = {
        'ă': '[ăa]', 'a': '[aăâ]', 'â': '[âa]',
        'î': '[îi]', 'i': '[iî]',
        'ș': '[șs]', 's': '[sș]',
        'ț': '[țt]', 't': '[tț]'
    }

    pattern = ""
    for char in anchor:
        c_lower = char.lower()
        if c_lower in mapping:
            pattern += mapping[c_lower]
        else:
            pattern += re.escape(char)
    return pattern


def _build_diacritic_regex(anchor: str) -> str:
    """
    Builds a full line-matching regex for an anchor (start/end anchors included).
    """
    return r"^\s*" + _build_diacritic_core(anchor) + r"[:\s]*$"

def split_zones(text: str, doc_type: DocumentType) -> dict[str, str]:
    """
    Splits document text into logical zones based on type-specific anchor sets.
    Returns a dictionary mapping anchor names to their extracted text content.
    If an anchor is not found, its key maps to "".
    """
    if doc_type == DocumentType.HOSPITAL_DISCHARGE_REPORT:
        anchors = HOSPITAL_DISCHARGE_REPORT_ANCHORS
    elif doc_type == DocumentType.OUTPATIENT_MEDICAL_LETTER:
        anchors = OUTPATIENT_MEDICAL_LETTER_ANCHORS
    else:
        return {}

    zones = {a: "" for a in anchors}
    lines = text.splitlines()

    # Pre-compile regexes for non-virtual anchors
    anchor_regexes = {}
    for a in anchors:
        if a not in ["DATE PACIENT / HEADER", "APPOINTMENT_BLOCK", "CHECKBOX_BLOCKS"]:
            anchor_regexes[a] = re.compile(_build_diacritic_regex(a), re.IGNORECASE)

    # Start assuming we are in the header
    current_zone = "DATE PACIENT / HEADER"

    for i, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            if current_zone:
                zones[current_zone] += "\n"
            continue
            
        matched_anchor = None
        
        # Check virtual anchors for HOSPITAL_DISCHARGE_REPORT
        if doc_type == DocumentType.HOSPITAL_DISCHARGE_REPORT:
            if re.search(r"Sunteti programat in data", line_clean, re.IGNORECASE):
                matched_anchor = "APPOINTMENT_BLOCK"
            elif re.search(r"Indicatie de revenire", line_clean, re.IGNORECASE):
                matched_anchor = "CHECKBOX_BLOCKS"
                
        # Check explicit anchors
        if not matched_anchor:
            for a, regex in anchor_regexes.items():
                if regex.match(line_clean) or regex.search(line_clean) and line_clean.startswith(a[:3]):
                    prefix_regex = re.compile(r"^\s*" + _build_diacritic_core(a) + r"[:\s]*(.*)$", re.IGNORECASE)
                    m = prefix_regex.match(line_clean)
                    if m:
                        matched_anchor = a
                        # The rest of the line belongs to the new zone
                        line_clean = m.group(1).strip()
                        break

        if matched_anchor:
            current_zone = matched_anchor
            if line_clean:
                zones[current_zone] += line_clean + "\n"
        elif current_zone:
            zones[current_zone] += line_clean + "\n"
            
    # Clean up trailing newlines
    for k in zones:
        zones[k] = zones[k].strip()

    return zones
