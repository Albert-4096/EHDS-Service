"""CIM-10 (Romanian ICD-10) to SNOMED CT mappings — minimum 50 entries."""

from typing import Optional

CIM10_TO_SNOMED: dict[str, dict[str, str]] = {
    "I21.4": {"code": "831000119106", "display": "Non-ST segment elevation myocardial infarction"},
    "I21.9": {"code": "57054005", "display": "Acute myocardial infarction"},
    "I10": {"code": "38341003", "display": "Hypertensive disorder"},
    "I25.1": {"code": "53741008", "display": "Coronary arteriosclerosis"},
    "I48": {"code": "49436004", "display": "Atrial fibrillation"},
    "I50.9": {"code": "84114007", "display": "Heart failure"},
    "I63.9": {"code": "230690007", "display": "Cerebrovascular accident"},
    "C34.9": {"code": "363358000", "display": "Malignant tumor of lung"},
    "C34.1": {"code": "363358000", "display": "Malignant tumor of lung"},
    "C50.9": {"code": "254837009", "display": "Malignant neoplasm of breast"},
    "C18.9": {"code": "363406005", "display": "Malignant neoplasm of colon"},
    "C25.9": {"code": "363517008", "display": "Malignant neoplasm of pancreas"},
    "C61": {"code": "399068003", "display": "Malignant tumor of prostate"},
    "C56": {"code": "363443007", "display": "Malignant neoplasm of ovary"},
    "C67.9": {"code": "363518001", "display": "Malignant neoplasm of bladder"},
    "C73": {"code": "363478007", "display": "Malignant neoplasm of thyroid gland"},
    "C80.1": {"code": "128462008", "display": "Metastatic malignant neoplasm"},
    "E11.9": {"code": "44054006", "display": "Type 2 diabetes mellitus"},
    "E11.2": {"code": "44054006", "display": "Type 2 diabetes mellitus"},
    "E10.9": {"code": "46635009", "display": "Type 1 diabetes mellitus"},
    "E03.9": {"code": "40930008", "display": "Hypothyroidism"},
    "E78.0": {"code": "13644009", "display": "Hypercholesterolemia"},
    "E78.5": {"code": "55822004", "display": "Hyperlipidemia"},
    "J18.9": {"code": "233604007", "display": "Pneumonia"},
    "J44.9": {"code": "13645005", "display": "Chronic obstructive lung disease"},
    "J45.9": {"code": "195967001", "display": "Asthma"},
    "K21.9": {"code": "235595009", "display": "Gastroesophageal reflux disease"},
    "K29.7": {"code": "40845000", "display": "Gastritis"},
    "K80.2": {"code": "235919008", "display": "Calculus of gallbladder"},
    "K92.2": {"code": "74474003", "display": "Gastrointestinal hemorrhage"},
    "N18.9": {"code": "709044004", "display": "Chronic kidney disease"},
    "N39.0": {"code": "68566005", "display": "Urinary tract infectious disease"},
    "M54.5": {"code": "279039007", "display": "Low back pain"},
    "M81.0": {"code": "64859006", "display": "Osteoporosis"},
    "G40.9": {"code": "84757009", "display": "Epilepsy"},
    "G35": {"code": "24700007", "display": "Multiple sclerosis"},
    "F32.9": {"code": "35489007", "display": "Depressive disorder"},
    "F41.9": {"code": "48694002", "display": "Anxiety disorder"},
    "B18.2": {"code": "128302006", "display": "Chronic viral hepatitis C"},
    "A41.9": {"code": "91302008", "display": "Sepsis"},
    "D64.9": {"code": "271737000", "display": "Anemia"},
    "D50.9": {"code": "87522002", "display": "Iron deficiency anemia"},
    "Q87.4": {"code": "7488008", "display": "Marfan syndrome"},
    "S72.0": {"code": "263204005", "display": "Fracture of neck of femur"},
    "T81.4": {"code": "385420002", "display": "Postoperative complication"},
    "Z51.1": {"code": "169413002", "display": "Antineoplastic chemotherapy regime"},
    "Z85.3": {"code": "429699009", "display": "History of malignant neoplasm of breast"},
    "Z95.1": {"code": "39937001", "display": "Coronary artery bypass graft present"},
    "R07.4": {"code": "29857009", "display": "Chest pain"},
    "R50.9": {"code": "386661006", "display": "Fever"},
    "R53": {"code": "84229001", "display": "Fatigue"},
    "R74.0": {"code": "166643006", "display": "Elevated transaminase level"},
    "U07.1": {"code": "840539006", "display": "COVID-19"},
}

SNOMED_GENERALIZATION: dict[str, dict[str, str]] = {
    "7488008": {"code": "128462008", "display": "Disorder of connective tissue"},
    "363358000": {"code": "128462008", "display": "Malignant neoplastic disease"},
}

DATA_ABSENT_CODING = {
    "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
    "code": "unknown",
    "display": "Unknown",
}


def get_snomed_for_cim10(cim10_code: str) -> Optional[dict[str, str]]:
    base_code = cim10_code.strip().upper()
    return CIM10_TO_SNOMED.get(base_code)


def generalize_snomed(snomed_code: str) -> Optional[dict[str, str]]:
    return SNOMED_GENERALIZATION.get(snomed_code)


def should_suppress_for_k_anonymity(
    cim10_code: str | None,
    snomed_code: str | None,
    cohort_count: int = 1,
    k_threshold: int = 5,
) -> bool:
    """R9: Suppress/generalize when cohort count below k (no hardcoded rare list)."""
    if cohort_count >= k_threshold:
        return False
    return bool(cim10_code or snomed_code)
