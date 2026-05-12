# Romanian trade name to ATC code mappings

ATC_MAPPING = {
    "Nivolumab": "L01FF02",
    "Ipilimumab": "L01FX04",
    "IFN alfa": "L03AB",
    "Interferon alfa": "L03AB",
    "Aspenter": "B01AC06",
    "Aspirina": "B01AC06",
    "Atoris": "C10AA05",
    "Atorvastatin": "C10AA05",
    "Concor": "C07AB07",
    "Bisoprolol": "C07AB07",
    "Metformin": "A10BA02",
    "Prestarium": "C09AA04",
    "Furosemid": "C03CA01",
    "Omeprazol": "A02BC01",
    "Euthyrox": "H03AA01",
    "Levotiroxina": "H03AA01",
    "Clexane": "B01AB05",
    "Enoxaparin": "B01AB05",
    "Heparina nefraction": "B01AB01",
    "Isosorbid mononitrat": "C01DA14",
    "Trombex": "B01AC04",
    "Clopidogrel": "B01AC04"
}

def drug_to_atc(drug_name: str) -> str | None:
    """
    Returns the ATC code for a given drug name, if mapped.
    """
    if not drug_name:
        return None
        
    drug_lower = drug_name.lower().strip()
    
    for k, v in ATC_MAPPING.items():
        if k.lower() in drug_lower:
            return v
            
    return None
