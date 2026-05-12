import hashlib
import random
from copy import deepcopy
from datetime import timedelta, datetime
from app.models.internal import MergedRecord

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
        # We use a hash of the CNP to seed the random offset so the same patient gets the same shift
        # which preserves longitudinal timelines if multiple documents exist.
        seed_str = anon.structured.cnp
        hashed_id = _hash_cnp(anon.structured.cnp)
        anon.structured.cnp = hashed_id
    else:
        seed_str = anon.structured.nr_focg or "unknown"
        
    # Generate deterministic random offset between -30 and +30 days
    rng = random.Random(seed_str)
    offset_days = rng.randint(-30, 30)

    # 2. Shift dates
    if anon.structured.dob_from_cnp:
        anon.structured.dob_from_cnp = anon.structured.dob_from_cnp + timedelta(days=offset_days)
    
    anon.structured.data_internarii = _shift_datetime(anon.structured.data_internarii, offset_days)
    anon.structured.data_externarii = _shift_datetime(anon.structured.data_externarii, offset_days)
    
    if anon.appointment and anon.appointment.datetime_parsed:
        anon.appointment.datetime_parsed = _shift_datetime(anon.appointment.datetime_parsed, offset_days)
        anon.appointment.datetime_raw = "[REDACTED DATE]"
        
    if anon.epicriza:
        # Shift imaging dates
        for img in anon.epicriza.imaging_results:
            if img.date:
                img.date = img.date + timedelta(days=offset_days)
                
    # 3. Replace Names and identifiers with [REDACTED]
    anon.structured.medic = "[REDACTED]"
    
    # If there's any raw headers that could contain names, scrub them
    if anon.epicriza:
        if anon.epicriza.antecedente_heredocolaterale:
            anon.epicriza.antecedente_heredocolaterale = anon.epicriza.antecedente_heredocolaterale.replace(
                "Nume", "[REDACTED]"
            ) # Very basic PII scrubbing in narrative
            
    # Scrub specific explicit fields
    if anon.structured.contract_number:
        anon.structured.contract_number = "[REDACTED]"
        
    # We could do more advanced NLP-based NER scrubbing here for names in the text,
    # but based on the prompt, explicit structured names and IDs are the primary target.
    
    return anon
