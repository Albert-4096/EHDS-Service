import re
import math
from pathlib import Path

from app.models.internal import StructuredFields, DiagnosticEntry
from app.pipeline.stage2_classify import DocumentType
from app.utils.cnp_parser import parse_cnp, CNPParseError
from app.utils.date_parser import parse_romanian_datetime, DateParseError

# Pre-compiled regex patterns (case-insensitive, tolerant of spaces)
REGEX_CNP = re.compile(r"C\.?N\.?P\.?:?\s*(\d{13})", re.IGNORECASE)
REGEX_FO = re.compile(r"\bFO:\s*(\d+)", re.IGNORECASE)
REGEX_CONTRACT = re.compile(r"Nr\.\s*contract/conventie:\s*([A-Z0-9/]+)", re.IGNORECASE)
REGEX_VARSTA = re.compile(r"Varst[aă]:\s*(\d+)", re.IGNORECASE)
REGEX_SEX = re.compile(r"\|\s*Sex:\s*([MF])", re.IGNORECASE)
REGEX_GRUP_SANGVIN = re.compile(r"Grup\s+sangvin:\s*([ABO]{1,2}|AB)", re.IGNORECASE)
REGEX_RH = re.compile(r"\|\s*RH:\s*(pozitiv|negativ|\+|-)", re.IGNORECASE)
REGEX_ALERGII = re.compile(r"Alergii:\s*(.+?)(?:\n|$)", re.IGNORECASE)
REGEX_DATA_INTERNARE = re.compile(r"Data\s+intern[aă]re:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})", re.IGNORECASE)
REGEX_DATA_EXTERNARE = re.compile(r"Data\s+extern[aă]re:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})", re.IGNORECASE)
REGEX_SECTIA = re.compile(r"Sec[tț]ia:[^\S\n]*([^|\n]+?)[^\S\n]*(?:\||\n|$)", re.IGNORECASE)
REGEX_MEDIC = re.compile(r"Medic:[^\S\n]*([^|\n]+?)[^\S\n]*(?:\||\n|$)", re.IGNORECASE)
REGEX_CIM10 = re.compile(r"\b([A-Z]\d{2}(?:\.\d{1,2})?)\b")
REGEX_STARE = re.compile(r"STARE\s+LA\s+EXTERNARE[:\s]*(vindecat|ameliorat|sta[tț]ionar|agravat|decedat)", re.IGNORECASE)

def extract_structured(zones: dict[str, str], doc_type: DocumentType) -> StructuredFields:
    warnings = []
    
    # Combine text from typical header zones for basic demographic/admin searches
    header_text = ""
    if doc_type == DocumentType.DOC_HDR:
        header_text = zones.get("DATE PACIENT", "") + "\n" + zones.get("DATE INTERNARE", "") + "\n" + zones.get("MEDIC CURANT", "")
    elif doc_type == DocumentType.DOC_BIS:
        header_text = zones.get("DATE PACIENT / HEADER", "")
        
    def extract_field(regex, text):
        match = regex.search(text)
        return match.group(1).strip() if match else None

    cnp = extract_field(REGEX_CNP, header_text)
    fo_number = extract_field(REGEX_FO, header_text)
    contract_number = extract_field(REGEX_CONTRACT, header_text)
    varsta_str = extract_field(REGEX_VARSTA, header_text)
    sex_explicit = extract_field(REGEX_SEX, header_text)
    grup_sangvin = extract_field(REGEX_GRUP_SANGVIN, header_text)
    rh = extract_field(REGEX_RH, header_text)
    alergii = extract_field(REGEX_ALERGII, header_text)
    
    data_internarii_str = extract_field(REGEX_DATA_INTERNARE, header_text)
    data_externarii_str = extract_field(REGEX_DATA_EXTERNARE, header_text)
    
    sectia = extract_field(REGEX_SECTIA, header_text)
    medic = extract_field(REGEX_MEDIC, header_text)
    
    # STARE LA EXTERNARE
    stare_externare = extract_field(REGEX_STARE, zones.get("STARE LA EXTERNARE", ""))
    
    # Process CNP
    dob_from_cnp = None
    sex_from_cnp = None
    if cnp:
        try:
            cnp_data = parse_cnp(cnp)
            dob_from_cnp = cnp_data.date_of_birth
            sex_from_cnp = cnp_data.sex
        except CNPParseError as e:
            warnings.append(str(e))
            
    # Process Dates
    data_internarii = None
    if data_internarii_str:
        try:
            data_internarii = parse_romanian_datetime(data_internarii_str)
        except DateParseError as e:
            warnings.append(str(e))

    data_externarii = None
    if data_externarii_str:
        try:
            data_externarii = parse_romanian_datetime(data_externarii_str)
        except DateParseError as e:
            warnings.append(str(e))

    # Process Diagnoses
    diag_zone = zones.get("DIAGNOSTIC PRINCIPAL LA EXTERNARE", "")
    if doc_type == DocumentType.DOC_BIS:
        diag_zone = zones.get("Diagnostic", "")
        
    diagnostic_principal = None
    diagnostice_secundare = []
    
    if diag_zone:
        cim_match = REGEX_CIM10.search(diag_zone)
        cod_cim10 = cim_match.group(1) if cim_match else None
        
        diagnostic_principal = DiagnosticEntry(
            denumire=diag_zone.strip().split('\n')[0][:100],  # Rough heuristic
            cod_cim10=cod_cim10
        )
        
        # Secondaries would typically be parsed from "DIAGNOSTICE SECUNDARE" zone
        sec_zone = zones.get("DIAGNOSTICE SECUNDARE", "")
        if sec_zone:
            for line in sec_zone.splitlines():
                line = line.strip()
                if line:
                    c_match = REGEX_CIM10.search(line)
                    diagnostice_secundare.append(DiagnosticEntry(
                        denumire=line[:100],
                        cod_cim10=c_match.group(1) if c_match else None
                    ))

    # Calculate confidence score
    expected_fields = 9 # Core subset
    filled_fields = sum(1 for x in [
        cnp, fo_number, data_internarii, data_externarii, medic, diagnostic_principal
    ] if x is not None)
    
    confidence_score = min(1.0, filled_fields / 6)

    return StructuredFields(
        doc_type=doc_type.value,
        nr_focg=fo_number,
        contract_number=contract_number,
        cnp=cnp,
        dob_from_cnp=dob_from_cnp,
        sex_from_cnp=sex_from_cnp,
        varsta=int(varsta_str) if varsta_str and varsta_str.isdigit() else None,
        sex_explicit=sex_explicit,
        grup_sangvin=grup_sangvin,
        rh=rh,
        alergii=alergii,
        data_internarii=data_internarii,
        data_externarii=data_externarii,
        sectia=sectia,
        medic=medic,
        stare_externare=stare_externare,
        diagnostic_principal=diagnostic_principal,
        diagnostice_secundare=diagnostice_secundare,
        confidence_score=confidence_score,
        parsing_warnings=warnings
    )
