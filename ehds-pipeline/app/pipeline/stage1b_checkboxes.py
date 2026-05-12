import re
import fitz
from pathlib import Path
from app.models.internal import PDFForensics, CheckboxGroup, CheckboxOption

class CheckboxExtractionWarning(Warning):
    pass

class CheckboxStateWarning(Warning):
    pass

CHECKBOX_CHARS = {
    '☒': True, '☑': True, '✓': True, '✗': False,
    '☐': False, '□': False, '○': False, '●': True
}

def extract_checkboxes(pdf_path: Path, text: str, forensics: PDFForensics) -> list[CheckboxGroup]:
    groups = []
    
    # Determine extraction method
    unicode_count = text.count('☒') + text.count('☐')
    ascii_count = text.count('[X]') + text.count('[ ]')

    method = "unknown"
    if forensics.has_acroform_widgets:
        method = "acroform"
    elif unicode_count >= 2:
        method = "unicode"
    elif ascii_count >= 2:
        method = "ocr_ascii"
    else:
        # Check if we at least have the "Calea de transmitere" which doesn't use standard checkboxes
        # We will handle it separately below, but if nothing is found, warn.
        import warnings
        warnings.warn("No checkboxes detected.", CheckboxExtractionWarning)

    if method == "acroform":
        groups = _extract_acroform(pdf_path)
    elif method == "unicode":
        groups = _extract_unicode(text)
    elif method == "ocr_ascii":
        # Replace ascii with unicode and run unicode extraction
        replaced_text = text.replace("[X]", "☒").replace("[ ]", "☐")
        groups = _extract_unicode(replaced_text)
        for g in groups:
            g.extraction_method = "ocr_ascii"

    # Step 3 - Calea de transmitere
    calea_group = _extract_calea_de_transmitere(text)
    if calea_group:
        groups.append(calea_group)

    # Step 4 - Validate
    import warnings
    for group in groups:
        checked_count = sum(1 for opt in group.options if opt.checked)
        if checked_count == 0:
            warnings.warn(f"No checked option in group {group.header}", CheckboxStateWarning)
        elif checked_count > 1:
            warnings.warn(f"Multiple checked in group {group.header}", CheckboxStateWarning)

    return groups

def _extract_acroform(pdf_path: Path) -> list[CheckboxGroup]:
    # Placeholder for AcroForm extraction logic as requested.
    # The prompt described widget matching by Y coordinates.
    # We group by field_name prefix.
    groups_dict = {}
    
    with fitz.open(pdf_path) as doc:
        for page in doc:
            page_text = page.get_text("dict")
            for widget in page.widgets():
                if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    # Match nearest text using rect.y1 + 20pt
                    label = widget.field_name # Fallback
                    # Very simple grouping by prefix (assuming dot notation or similar)
                    prefix = widget.field_name.split('.')[0] if '.' in widget.field_name else "Unknown Group"
                    checked = widget.field_value in ["Yes", "On", "1", "True"]
                    
                    if prefix not in groups_dict:
                        groups_dict[prefix] = []
                    groups_dict[prefix].append(CheckboxOption(label=label, checked=checked, raw_marker="[AcroForm]"))
                    
    groups = []
    for header, options in groups_dict.items():
        groups.append(CheckboxGroup(header=header, options=options, extraction_method="acroform"))
        
    return groups

def _extract_unicode(text: str) -> list[CheckboxGroup]:
    groups = []
    current_header = "Unknown"
    current_options = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        found_char = None
        for char in CHECKBOX_CHARS:
            if char in line:
                found_char = char
                break

        if found_char:
            checked = CHECKBOX_CHARS[found_char]
            # Strip char and leading prefixes
            # E.g., "- ☒ da, revine" -> "da, revine"
            label = line.replace(found_char, "", 1).strip()
            label = re.sub(r"^[-\•]\s*", "", label).strip()
            
            current_options.append(CheckboxOption(label=label, checked=checked, raw_marker=found_char))
        elif line.endswith(":"):
            if current_options:
                groups.append(CheckboxGroup(header=current_header, options=current_options, extraction_method="unicode"))
                current_options = []
            # Normalize header
            current_header = re.sub(r"^[-\•]\s*", "", line).strip().rstrip(":")

    if current_options:
        groups.append(CheckboxGroup(header=current_header, options=current_options, extraction_method="unicode"))

    return groups

def _extract_calea_de_transmitere(text: str) -> CheckboxGroup | None:
    # Regex: r"^X\s*-\s*(.+)$" on each line in the calea zone
    # We'll just scan the text for a block that looks like Calea de transmitere
    
    calea_options = []
    in_calea_zone = False
    
    for line in text.splitlines():
        line = line.strip()
        if "Calea de transmitere" in line:
            in_calea_zone = True
            continue
            
        if in_calea_zone:
            match_x = re.match(r"^X\s*-\s*(.+)$", line)
            match_dash = re.match(r"^-\s*(.+)$", line)
            
            if match_x:
                calea_options.append(CheckboxOption(label=match_x.group(1).strip(), checked=True, raw_marker="X"))
            elif match_dash:
                calea_options.append(CheckboxOption(label=match_dash.group(1).strip(), checked=False, raw_marker="-"))
            elif not line:
                pass
            else:
                # Exited zone
                if calea_options:
                    break

    if calea_options:
        return CheckboxGroup(header="Calea de transmitere", options=calea_options, extraction_method="text_marker")
        
    return None
