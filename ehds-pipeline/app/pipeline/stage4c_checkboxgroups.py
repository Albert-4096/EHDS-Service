import re
from app.models.internal import CheckboxGroup, AdminCheckboxes

def map_checkboxes(groups: list[CheckboxGroup]) -> AdminCheckboxes:
    """
    Semantically maps extracted raw CheckboxGroups to structured fields.
    HP-01 logic.
    """
    
    # Defaults
    result = AdminCheckboxes(raw_groups=groups)
    
    for group in groups:
        header_lower = group.header.lower()
        
        # Find the checked option
        checked_opt = None
        for opt in group.options:
            if opt.checked:
                checked_opt = opt
                break
                
        if not checked_opt:
            continue
            
        label = checked_opt.label
        label_lower = label.lower()
        
        # 1. Indicatie de revenire pentru internare
        if "indicatie de revenire" in header_lower or "revenire pentru internare" in header_lower:
            if label_lower.startswith("da") or "revine pentru internare" in label_lower:
                result.readmission_required = True
                match = re.search(r"(\d+)\s*s[aă]pt[aă]m[aâ]ni", label_lower)
                if match:
                    result.readmission_timeframe_weeks = int(match.group(1))
            else:
                result.readmission_required = False
                
        # 2. Prescriptie medicala
        elif "prescriptie medicala" in header_lower and "dispozitive" not in header_lower:
            if label_lower.startswith("s-a eliberat"):
                result.prescription_issued = True
                match = re.search(r"seria\s+si\s+numarul\s*[:\s]*(.+?)$", label_lower)
                if match:
                    result.prescription_serial = match.group(1).rstrip(")")
            elif label_lower.startswith("nu s-a eliberat"):
                result.prescription_issued = False
                
        # 3. Concediu medical
        elif "concediu medical" in header_lower:
            if label_lower.startswith("s-a eliberat"):
                result.sick_leave_issued = True
                match = re.search(r"seria\s+si\s+numarul\s*[:\s]*(.+?)$", label_lower)
                if match:
                    result.sick_leave_serial = match.group(1).rstrip(")")
            elif label_lower.startswith("nu s-a eliberat"):
                result.sick_leave_issued = False
                
        # 4. Recomandare ingrijiri / paliative
        elif "ingrijiri medicale la domiciliu" in header_lower or "paliative" in header_lower:
            if label_lower.startswith("s-a eliberat"):
                result.home_care_referral_issued = True
            elif label_lower.startswith("nu s-a eliberat"):
                result.home_care_referral_issued = False
                
        # 5. Prescriptie dispozitive
        elif "dispozitive medicale" in header_lower:
            if label_lower.startswith("s-a eliberat"):
                result.medical_device_prescription_issued = True
            elif label_lower.startswith("nu s-a eliberat"):
                result.medical_device_prescription_issued = False
                
        # 6. Calea de transmitere
        elif "calea de transmitere" in header_lower:
            if "prin asigurat" in label_lower:
                result.document_transmission = "prin asigurat"
            elif "prin posta" in label_lower:
                result.document_transmission = "prin posta"

    return result
