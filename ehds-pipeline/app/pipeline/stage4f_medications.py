import re
from app.models.internal import MedicationEntry
from app.terminology.atc_lookup import drug_to_atc

def extract_medications(tratament_zone: str) -> list[MedicationEntry]:
    """
    Extracts discharge medications from the treatment zone.
    Parses numbered or bulleted lines. Detects "DT" suffix for total dose.
    Looks up ATC code.
    """
    medications = []
    
    if not tratament_zone:
        return medications
        
    for line in tratament_zone.splitlines():
        line = line.strip()
        if not line:
            continue
            
        # Ignore non-medication lines like "Ciclul: 38..."
        if line.lower().startswith("ciclul:") or line.lower().startswith("acronim:"):
            continue
            
        # Attempt to match bullet or number
        # e.g., "1. Nivolumab 480 mg DT", "- Aspirina 100 mg", "Bisoprolol 5mg - 1/zi"
        line_clean = re.sub(r"^(\d+\.|-|•)\s*", "", line).strip()
        
        if not line_clean:
            continue
            
        # Basic heuristic parsing
        # We can split by dashes or commas for parts, or just use regex
        # A common pattern: Drug Dose [DT] [- freq] [- duration]
        # For a robust implementation, since medical text varies, we extract the first few words as drug
        # and look for mg, g, ml, etc. as dose.
        
        dose_is_total = " DT" in line_clean
        
        # Simple extraction: let's try to isolate the dose
        dose_match = re.search(r"(\d+(?:[\.,]\d+)?\s*(?:mg|g|mcg|ml|UI|U|L))", line_clean, re.IGNORECASE)
        doza = dose_match.group(1) if dose_match else None
        
        drug_name = line_clean
        if doza:
            drug_name = line_clean[:line_clean.find(doza)].strip()
            
        # Fallback if no dose found, just use the first word or two as drug name
        if not doza:
            parts = line_clean.split()
            if parts:
                drug_name = parts[0]
                
        # Frequency and duration heuristic
        frecventa = None
        durata = None
        
        if "-" in line_clean:
            parts = [p.strip() for p in line_clean.split("-")]
            if len(parts) > 1:
                # the last or second to last part could be frequency
                for p in parts[1:]:
                    if "zi" in p.lower() or "ora" in p.lower() or "luni" in p.lower() or "sapt" in p.lower():
                        if "luni" in p.lower() or "sapt" in p.lower() or "zile" in p.lower():
                            durata = p
                        else:
                            frecventa = p
                            
        atc_code = drug_to_atc(drug_name)
        
        medications.append(MedicationEntry(
            medicament=drug_name,
            doza=doza,
            frecventa=frecventa,
            durata=durata,
            atc_code=atc_code,
            dose_is_total=dose_is_total,
            raw=line
        ))
        
    return medications
