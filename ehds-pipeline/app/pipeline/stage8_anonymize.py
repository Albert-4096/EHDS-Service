import hashlib
import random
import re
from copy import deepcopy
from datetime import timedelta, datetime
from app.models.internal import MergedRecord, DiagnosticEntry
from app.terminology.mappings import is_rare_diagnosis, generalize_snomed, CIM10_TO_SNOMED
from app.utils.time_shifter import TimeShifter

REGEX_PHONE = re.compile(r"(\+40|0)?(7\d{8}|2\d{8}|3\d{8})\b")
REGEX_CNP_TEXT = re.compile(r"\b\d{13}\b")
REGEX_NAME_PREFIX = re.compile(r"(Nume|Prenume|Pacient)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.IGNORECASE)
REGEX_ADDRESS = re.compile(r"(Strada|Str\.|Bd\.|Bulevardul|Aleea)[:\s]+[A-Za-z0-9\s\.-]+", re.IGNORECASE)

def _scrub_text(text: str | None) -> str | None:
    if not text:
        return text
    t = REGEX_PHONE.sub("[REDACTED PHONE]", text)
    t = REGEX_CNP_TEXT.sub("[REDACTED CNP]", t)
    t = REGEX_NAME_PREFIX.sub(r"\1: [REDACTED NAME]", t)
    t = REGEX_ADDRESS.sub(r"\1 [REDACTED ADDRESS]", t)
    return t

def _hash_cnp(cnp: str | None) -> str | None:
    if not cnp:
        return None
    # Use SHA-256 for consistent, anonymous hashing
    return hashlib.sha256(cnp.encode('utf-8')).hexdigest()

def _shift_datetime(dt: datetime | None, offset_days: int) -> datetime | None:
    if not dt:
        return None
    return dt + timedelta(days=offset_days)

def anonymize_record(record: MergedRecord) -> MergedRecord:
    """
    EHDS Pillar 2 Compliance: Takes a merged Pydantic record and scrubs it.
    Replaces names with [REDACTED], hashes the CNP, and shifts dates by a deterministic random offset.
    Returns a deeply copied, anonymized new record.
    """
    anon = deepcopy(record)
    
    # 1. Hash the CNP to generate a consistent but anonymous patient ID
    if anon.structured.cnp:
        seed_str = anon.structured.cnp
        anon.structured.cnp = _hash_cnp(anon.structured.cnp)
    else:
        seed_str = anon.structured.nr_focg or "unknown"
        
    shifter = TimeShifter(seed_str)

    # 2. Shift dates
    if anon.structured.dob_from_cnp:
        anon.structured.dob_from_cnp = anon.structured.dob_from_cnp + timedelta(days=shifter.offset_days)
    
    anon.structured.data_internarii = shifter.shift_datetime(anon.structured.data_internarii)
    anon.structured.data_externarii = shifter.shift_datetime(anon.structured.data_externarii)
    
    if anon.appointment and anon.appointment.datetime_parsed:
        anon.appointment.datetime_parsed = shifter.shift_datetime(anon.appointment.datetime_parsed)
        anon.appointment.datetime_raw = "[REDACTED DATE]"
        
    if anon.epicriza:
        # Shift imaging dates
        for img in anon.epicriza.imaging_results:
            if img.date:
                img.date = shifter.shift_datetime(img.date)
                
    # 3. Replace Names and identifiers with [REDACTED]
    anon.structured.medic = "[REDACTED]"
    
    # If there's any raw headers that could contain names, scrub them
    if anon.epicriza:
        anon.epicriza.antecedente_heredocolaterale = _scrub_text(anon.epicriza.antecedente_heredocolaterale)
        anon.epicriza.current_treatment_narrative = _scrub_text(anon.epicriza.current_treatment_narrative)
        anon.epicriza.motive_internare = [_scrub_text(m) for m in anon.epicriza.motive_internare if m]
        anon.epicriza.antecedente_personale = [_scrub_text(a) for a in anon.epicriza.antecedente_personale if a]
            
    # Scrub specific explicit fields
    if anon.structured.contract_number:
        anon.structured.contract_number = "[REDACTED]"
        
    # We could do more advanced NLP-based NER scrubbing here for names in the text,
    # but based on the prompt, explicit structured names and IDs are the primary target.
    
    # 4. K-Anon Generalization
    def _generalize_diagnosis(diag: DiagnosticEntry) -> DiagnosticEntry:
        if diag.cod_cim10 and is_rare_diagnosis(diag.cod_cim10):
            snomed_info = CIM10_TO_SNOMED.get(diag.cod_cim10)
            if snomed_info:
                generalized = generalize_snomed(snomed_info["code"])
                if generalized:
                    return DiagnosticEntry(
                        denumire=f"[GENERALIZED] {generalized['display']}",
                        cod_cim10=None # We generalized it, remove the specific CIM-10
                    )
            return DiagnosticEntry(denumire="[REDACTED RARE DIAGNOSIS]", cod_cim10=None)
        return diag

    if anon.structured.diagnostic_principal:
        anon.structured.diagnostic_principal = _generalize_diagnosis(anon.structured.diagnostic_principal)
    
    anon.structured.diagnostice_secundare = [
        _generalize_diagnosis(d) for d in anon.structured.diagnostice_secundare
    ]
    
    return anon
