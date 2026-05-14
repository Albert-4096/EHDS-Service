import re
from typing import Tuple, Dict
from app.models.internal import LabResults, LabValue
from app.utils.numeric import normalise_romanian_decimal
from app.terminology.loinc_map import lab_to_loinc

REGEX_SUPERSCRIPT = re.compile(r"(\d+\.?\d*)\s*(?:[x×X])?\s*(10)(\d{1,2})/([Ll])")

UCUM_MAPPING = {
    "× 10^9/L": "10*9/L",
    "× 10^12/L": "10*12/L",
    "g/dL": "g/dL",
    "fL": "fL",
    "pg": "pg",
    "%": "%",
    "mmol/L": "mmol/L",
    "mg/dL": "mg/dL",
    "U/L": "U/L",
    "UI/l": "U/L",
    "mUI/L": "m[IU]/L",
    "ng/dl": "ng/dL",
    "ug/dl": "ug/dL",
    "mmol": "mmol"
}

def _repair_superscripts(text: str) -> str:
    """HP-03: Repairs scientific notation superscripts lost during PDF extraction."""
    return REGEX_SUPERSCRIPT.sub(r"\1 × 10^\3/\4", text)

def _map_ucum(unit_raw: str) -> str | None:
    """Maps extracted raw unit to UCUM notation."""
    if not unit_raw:
        return None
    unit_clean = unit_raw.strip()
    # Case insensitive lookup for some units, exact for others
    # Best effort mapping based on prompt requirements
    for k, v in UCUM_MAPPING.items():
        if k.lower() == unit_clean.lower():
            return v
    return unit_clean # fallback to raw if unknown, but usually we map exactly

def _parse_lab_entry(entry: str) -> Tuple[str, LabValue] | None:
    """
    Parses a single lab entry string like:
    "*(RDW-CV) Coef de variatie al indicelui...=12.7 %"
    "WBC) Leucocite=5.79 × 10^9/L"
    "Bilirubina totala=0.626 mg/dL"
    """
    entry = entry.strip()
    if not entry:
        return None
        
    # Flags
    flagged = False
    if entry.startswith("*"):
        flagged = True
        entry = entry[1:].strip()
        
    # Detect abbreviation in parentheses
    abbrev = None
    if entry.startswith("("):
        closing_idx = entry.find(")")
        if closing_idx != -1:
            abbrev = entry[1:closing_idx].strip()
            entry = entry[closing_idx+1:].strip()
    else:
        # HP-05 specifies some keys have brackets without opening paren: "WBC) Leucocite"
        closing_idx = entry.find(")")
        eq_idx = entry.find("=")
        # if closing paren is before equals sign
        if closing_idx != -1 and (eq_idx == -1 or closing_idx < eq_idx):
            abbrev = entry[:closing_idx].strip()
            entry = entry[closing_idx+1:].strip()

    # Split key and value
    if "=" not in entry:
        return None
        
    name_part, value_part = entry.split("=", 1)
    test_name = name_part.strip()
    value_part = value_part.strip()
    
    # Extract value and unit
    # Values might contain spaces, but generally it's numeric then unit
    # e.g., "5.79 × 10^9/L" or "56.7 %"
    # We split by first space after digits/commas
    # Wait, the value could be a number with comma decimal: "0,46 ng/dl"
    # We can match the numeric part and the rest as unit
    match = re.match(r"^([\d\.,]+)\s*(.*)$", value_part)
    if not match:
        # Unable to parse purely numeric, maybe textual value?
        return test_name, LabValue(
            test_name=test_name,
            test_abbreviation=abbrev,
            value_raw=value_part,
            value_numeric=None,
            unit_raw=None,
            unit_ucum=None,
            flagged=flagged,
            loinc_code=lab_to_loinc(test_name, abbrev)
        )
        
    value_raw = match.group(1).strip()
    unit_raw = match.group(2).strip() if match.group(2) else None
    
    # HP-16: Decimal comma normalization
    value_normalized = normalise_romanian_decimal(value_raw)
    try:
        value_numeric = float(value_normalized)
    except ValueError:
        value_numeric = None
        
    unit_ucum = _map_ucum(unit_raw)
    
    loinc_code = lab_to_loinc(test_name, abbrev)
    
    # For HP-04, we prefer abbrev if it's there for the key, else test_name
    key_name = abbrev if abbrev else test_name
    
    return key_name, LabValue(
        test_name=test_name,
        test_abbreviation=abbrev,
        value_raw=value_raw,
        value_numeric=value_numeric,
        unit_raw=unit_raw,
        unit_ucum=unit_ucum,
        flagged=flagged,
        loinc_code=loinc_code
    )

def extract_labs(lab_zone_text: str) -> LabResults:
    """
    Extracts laboratory panels from the lab zone text.
    Handles hemoleucograma and biochemistry distinct patterns.
    """
    cbc = {}
    biochem = {}
    other = {}
    
    if not lab_zone_text:
        return LabResults(cbc=cbc, biochemistry=biochem, hormones={}, other=other)
        
    # HP-03: Superscript repair BEFORE any parsing
    text = _repair_superscripts(lab_zone_text)
    
    # Identify Hemoleucograma completa
    cbc_start = text.find("Hemoleucograma completa:")
    if cbc_start != -1:
        bracket_start = text.find("[", cbc_start)
        if bracket_start != -1:
            bracket_end = text.find("]", bracket_start)
            if bracket_end != -1:
                cbc_text = text[bracket_start+1:bracket_end]
                # Split by comma
                # Note: Some test names might have commas? Generally lab names here don't.
                entries = [e.strip() for e in cbc_text.replace("\n", " ").split(",")]
                for entry in entries:
                    parsed = _parse_lab_entry(entry)
                    if parsed:
                        cbc[parsed[0]] = parsed[1]
                
                # After the closing "]", extract comma-separated pairs as biochemistry panel
                after_cbc = text[bracket_end+1:].strip()
                biochem_entries = [e.strip() for e in after_cbc.replace("\n", " ").split(",")]
                for entry in biochem_entries:
                    parsed = _parse_lab_entry(entry)
                    if parsed:
                        biochem[parsed[0]] = parsed[1]
    else:
        # If no Hemoleucograma marker, parse everything as other or biochem
        # We can just attempt comma separated
        entries = [e.strip() for e in text.replace("\n", " ").split(",")]
        for entry in entries:
            parsed = _parse_lab_entry(entry)
            if parsed:
                other[parsed[0]] = parsed[1]
                
    return LabResults(
        bulletin_date=None, # HP-06 format F says lab results have dates, but extraction strategy for bulletin date wasn't explicit. Leaving None.
        cbc=cbc,
        biochemistry=biochem,
        hormones={},
        other=other
    )
