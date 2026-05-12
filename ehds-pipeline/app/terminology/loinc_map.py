# LOINC Code mappings for common Romanian lab tests

LAB_TO_LOINC = {
    # CBC
    "WBC": "6690-2",
    "Leucocite": "6690-2",
    "RBC": "789-8",
    "Hematii": "789-8",
    "HGB": "718-7",
    "Hemoglobina": "718-7",
    "HCT": "4544-3",
    "Hematocrit": "4544-3",
    "MCV": "787-2",
    "Volum mediu eritrocitar": "787-2",
    "MCH": "785-6",
    "Hemoglobina eritrocitara medie": "785-6",
    "MCHC": "786-4",
    "Concentr. medie de hemoglob. eritrocitara": "786-4",
    "PLT": "777-3",
    "Trombocite": "777-3",
    "Neutrofile %": "770-8",
    "Limfocite %": "736-9",
    "Monocite %": "5905-5",
    "Eosinofile %": "713-8",
    "Eozinofile %": "713-8",
    "RDW-CV": "21000-5",
    "Coef de variatie al indicelui de ditributie al eritrocitelor": "21000-5",
    "MPV": "32623-1",
    "Volum mediu trombocitar": "32623-1",
    
    # Biochemistry
    "Bilirubina totala": "1975-2",
    "Calciu seric total": "17861-6",
    "Calciu seric": "17861-6",
    "Creatinina serica": "2160-0",
    "Creatinina": "2160-0",
    "Fosfataza alcalina": "6768-6",
    "Glicemie": "2339-0",
    "Potasiu seric": "2823-3",
    "Potasiu": "2823-3",
    "Sodiu seric": "2951-2",
    "Sodiu": "2951-2",
    "TGO/AST": "1920-8",
    "TGP/ALT": "1742-6",

    # Hormones
    "TSH": "3016-3",
    "FT4": "3024-7",
    "Cortizol": "2143-6",
    "cortizol seric": "2143-6",
    "DHEA-S": "2191-5",
    
    # Oncology
    "Troponin I": "10839-9",
    "ECOG": "89247-1",
    "Cancer response": "88040-1",
}

def lab_to_loinc(test_name: str, abbrev: str = None) -> str | None:
    """
    Returns the LOINC code for a given test name or abbreviation, if mapped.
    """
    if abbrev and abbrev in LAB_TO_LOINC:
        return LAB_TO_LOINC[abbrev]
    
    # Try exact match
    if test_name in LAB_TO_LOINC:
        return LAB_TO_LOINC[test_name]
        
    # Try case-insensitive match
    test_name_lower = test_name.lower()
    for k, v in LAB_TO_LOINC.items():
        if k.lower() == test_name_lower:
            return v
            
    return None
