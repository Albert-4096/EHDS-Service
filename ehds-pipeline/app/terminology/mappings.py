from typing import Dict, Optional

# Mock mapping from CIM-10 (Romanian ICD-10) to SNOMED CT
CIM10_TO_SNOMED: Dict[str, Dict[str, str]] = {
    "I21.4": {
        "code": "831000119106",
        "display": "Non-ST segment elevation myocardial infarction"
    },
    "C34.9": {
        "code": "363358000",
        "display": "Malignant tumor of lung"
    },
    "E11.9": {
        "code": "44054006",
        "display": "Type 2 diabetes mellitus"
    },
    "Q87.4": { # Example rare diagnosis
        "code": "7488008",
        "display": "Marfan syndrome"
    }
}

# List of rare diagnoses that trigger K-Anon generalization
RARE_DIAGNOSES = {
    "Q87.4", # Marfan syndrome (CIM-10)
    "7488008" # Marfan syndrome (SNOMED)
}

# Generalization hierarchy (Specific Concept -> General Concept)
SNOMED_GENERALIZATION: Dict[str, Dict[str, str]] = {
    "7488008": { # Marfan
        "code": "128462008",
        "display": "Disorder of connective tissue"
    }
}

def get_snomed_for_cim10(cim10_code: str) -> Optional[Dict[str, str]]:
    """Returns the primary SNOMED CT mapping for a given CIM-10 code."""
    # Strip any potential extra spaces
    base_code = cim10_code.strip()
    return CIM10_TO_SNOMED.get(base_code)

def is_rare_diagnosis(code: str) -> bool:
    """Checks if a given CIM-10 or SNOMED code is considered a rare diagnosis."""
    return code in RARE_DIAGNOSES

def generalize_snomed(snomed_code: str) -> Optional[Dict[str, str]]:
    """Returns the generalized parent SNOMED CT concept for a rare diagnosis."""
    return SNOMED_GENERALIZATION.get(snomed_code)
