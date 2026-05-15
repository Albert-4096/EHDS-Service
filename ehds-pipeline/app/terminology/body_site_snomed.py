"""SNOMED CT mappings for common anatomical sites (R2 CodeableConcept integrity)."""

BODY_SITE_SNOMED: dict[str, dict[str, str]] = {
    "pulmon": {"code": "39607008", "display": "Lung structure"},
    "pulmonar": {"code": "39607008", "display": "Lung structure"},
    "ficat": {"code": "10200004", "display": "Liver structure"},
    "hepatic": {"code": "10200004", "display": "Liver structure"},
    "rinichi": {"code": "64033007", "display": "Kidney structure"},
    "renal": {"code": "64033007", "display": "Kidney structure"},
    "creier": {"code": "12738006", "display": "Brain structure"},
    "cerebral": {"code": "12738006", "display": "Brain structure"},
    "san": {"code": "76752008", "display": "Breast structure"},
    "mamar": {"code": "76752008", "display": "Breast structure"},
    "colon": {"code": "71854001", "display": "Colon structure"},
    "stomac": {"code": "69695003", "display": "Stomach structure"},
    "gastric": {"code": "69695003", "display": "Stomach structure"},
    "pancreas": {"code": "15719003", "display": "Pancreatic structure"},
    "ovarian": {"code": "15497006", "display": "Ovarian structure"},
    "uter": {"code": "35039007", "display": "Uterine structure"},
    "prostata": {"code": "41216001", "display": "Prostatic structure"},
    "tiroida": {"code": "69748006", "display": "Thyroid structure"},
    "os": {"code": "272673000", "display": "Bone structure"},
    "femur": {"code": "71341001", "display": "Bone structure of femur"},
    "umeral": {"code": "40983000", "display": "Bone structure of humerus"},
}


def lookup_body_site(text: str | None) -> dict[str, str] | None:
    if not text:
        return None
    lower = text.lower()
    for key, mapping in BODY_SITE_SNOMED.items():
        if key in lower:
            return mapping
    return None
