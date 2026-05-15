import re
import fitz
from pathlib import Path
from app.models.internal import DocumentForensics, CheckboxGroup, CheckboxOption

class CheckboxExtractionWarning(Warning):
    pass

class CheckboxStateWarning(Warning):
    pass

CHECKBOX_CHARS = {
    '☒': True, '☑': True, '✓': True, '✗': False,
    '☐': False, '□': False, '○': False, '●': True
}

def extract_checkboxes(file_path: Path, text: str, forensics: DocumentForensics) -> list[CheckboxGroup]:
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
        groups = _extract_acroform(file_path)
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

def _nearest_label(page_dict: dict, widget_rect, y_tolerance: float = 20.0) -> str:
    """HP-01: Match checkbox widget to nearest text span by Y proximity."""
    wx0, wy0, wx1, wy1 = widget_rect
    widget_mid_y = (wy0 + wy1) / 2
    best_label = ""
    best_dist = float("inf")

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text or len(text) > 120:
                    continue
                sx0, sy0, sx1, sy1 = span["bbox"]
                if sx0 > wx1 + 5:
                    continue
                span_mid_y = (sy0 + sy1) / 2
                dist = abs(span_mid_y - widget_mid_y)
                if dist <= y_tolerance and dist < best_dist:
                    best_dist = dist
                    best_label = text

    return best_label


def _extract_acroform(pdf_path: Path) -> list[CheckboxGroup]:
    groups_dict: dict[str, list] = {}

    with fitz.open(pdf_path) as doc:
        for page in doc:
            page_dict = page.get_text("dict")
            for widget in page.widgets():
                if widget.field_type != fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    continue
                field_name = widget.field_name or "Unknown"
                label = _nearest_label(page_dict, widget.rect) or field_name
                prefix = field_name.split(".")[0] if "." in field_name else "Unknown Group"
                checked = widget.field_value in ["Yes", "On", "1", "True", True]

                if prefix not in groups_dict:
                    groups_dict[prefix] = []
                groups_dict[prefix].append(
                    CheckboxOption(label=label, checked=bool(checked), raw_marker="[AcroForm]")
                )

    return [
        CheckboxGroup(header=header, options=options, extraction_method="acroform")
        for header, options in groups_dict.items()
    ]

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
