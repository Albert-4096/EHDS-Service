# Oncology Terminology Mappings

# Regimen acronyms -> Description / ATC mapping
ONCOLOGY_REGIMENS = {
    "Nivo q4w": "Nivolumab administrat la 4 saptamani",
    "Ipi+Nivo": "Ipilimumab + Nivolumab",
    "FOLFOX": "Folinic acid, Fluorouracil, Oxaliplatin",
    "FOLFIRI": "Folinic acid, Fluorouracil, Irinotecan",
    "AC-T": "Doxorubicin, Cyclophosphamide, followed by Paclitaxel",
    "BEP": "Bleomycin, Etoposide, Cisplatin",
    "CHOP": "Cyclophosphamide, Doxorubicin, Vincristine, Prednisone",
    "R-CHOP": "Rituximab + CHOP"
}

# Response status mapping
RESPONSE_STATUS = {
    "RC": "CR",
    "Remisiune completa": "CR",
    "RP": "PR",
    "Remisiune partiala": "PR",
    "BS": "SD",
    "Boala stationara": "SD",
    "SD": "SD",
    "PD": "PD",
    "Progresie": "PD"
}

# TNM Prefix meanings
TNM_PREFIXES = {
    "p": "pathological",
    "c": "clinical",
    "y": "post-treatment",
    "r": "recurrence"
}
