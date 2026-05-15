import re
from pathlib import Path
from typing import Optional

import pdfplumber

from app.config import settings
from app.models.internal import StructuredFields, DiagnosticEntry
from app.pipeline.stage2_classify import DocumentType
from app.utils.cnp_parser import parse_cnp, CNPParseError
from app.utils.date_parser import parse_romanian_datetime, DateParseError

REGEX_CNP = re.compile(r"C\.?N\.?P\.?:?\s*(\d{13})", re.IGNORECASE)
REGEX_NUME = re.compile(
    r"Nume(?:\s+si\s+Prenume)?[:\s]+([A-ZĂÂÎȘȚ][A-Za-zĂÂÎȘȚăâîșț\-\s]+?)(?:\n|\||$)",
    re.IGNORECASE,
)
REGEX_DOMICILIU = re.compile(r"Domiciliu[:\s]+(.+?)(?:\n|Alergii|$)", re.IGNORECASE | re.DOTALL)
REGEX_FO = re.compile(r"\bFO:\s*(\d+)", re.IGNORECASE)
REGEX_CONTRACT = re.compile(r"Nr\.\s*contract/conventie:\s*([A-Z0-9/]+)", re.IGNORECASE)
REGEX_VARSTA = re.compile(r"Varst[aă]:\s*(\d+)", re.IGNORECASE)
REGEX_SEX = re.compile(r"Varsta:\s*\d+\s*\|\s*Sex:\s*([MF])", re.IGNORECASE)
REGEX_GRUP_SANGVIN = re.compile(r"Grup\s+sangvin:\s*([ABO]{1,2}|AB)", re.IGNORECASE)
REGEX_RH = re.compile(r"\|\s*RH:\s*(pozitiv|negativ|\+|-)", re.IGNORECASE)
REGEX_ALERGII = re.compile(r"Alergii:\s*(.+?)(?:\n|$)", re.IGNORECASE)
REGEX_DATA_INTERNARE = re.compile(
    r"Data\s+intern[aă]r(?:e|ii)[:\s]*(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4}(?:\s+\d{2}:\d{2})?)",
    re.IGNORECASE,
)
REGEX_DATA_EXTERNARE = re.compile(
    r"Data\s+extern[aă]r(?:e|ii)[:\s]*(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4}(?:\s+\d{2}:\d{2})?)",
    re.IGNORECASE,
)
REGEX_SECTIA = re.compile(r"Sec[tț]ia:[^\S\n]*([^|\n]+?)[^\S\n]*(?:\||\n|$)", re.IGNORECASE)
REGEX_MEDIC = re.compile(r"Medic:[^\S\n]*([^|\n]+?)[^\S\n]*(?:\||\n|$)", re.IGNORECASE)
REGEX_CIM10 = re.compile(r"\b([A-Z]\d{2}(?:\.\d{1,2})?)\b")
REGEX_STARE = re.compile(
    r"STARE\s+LA\s+EXTERNARE[:\s]*(vindecat|ameliorat|sta[tț]ionar|agravat|decedat)",
    re.IGNORECASE,
)


def _extract_from_tables(pdf_path: Path) -> dict[str, str]:
    """HP-02 phased: pdfplumber table extraction on page 1."""
    result: dict[str, str] = {}
    if pdf_path.suffix.lower() != ".pdf":
        return result

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return result
            page = pdf.pages[0]
            tables = page.extract_tables() or []
            flat_cells: list[str] = []
            for table in tables:
                for row in table:
                    if row:
                        flat_cells.extend(str(c).strip() for c in row if c)

            joined = " ".join(flat_cells)
            if not joined:
                return result

            for pattern, key in (
                (REGEX_CNP, "cnp"),
                (REGEX_NUME, "nume"),
                (REGEX_DOMICILIU, "domiciliu"),
                (REGEX_DATA_INTERNARE, "data_internarii"),
                (REGEX_DATA_EXTERNARE, "data_externarii"),
                (REGEX_MEDIC, "medic"),
                (REGEX_VARSTA, "varsta"),
                (REGEX_GRUP_SANGVIN, "grup_sangvin"),
                (REGEX_RH, "rh"),
                (REGEX_ALERGII, "alergii"),
            ):
                m = pattern.search(joined)
                if m:
                    result[key] = m.group(1).strip()
    except Exception:
        pass

    return result


def extract_structured(
    zones: dict[str, str],
    doc_type: DocumentType,
    pdf_path: Optional[Path] = None,
) -> StructuredFields:
    warnings: list[str] = []

    header_text = zones.get("DATE PACIENT / HEADER", "")
    if doc_type == DocumentType.HOSPITAL_DISCHARGE_REPORT:
        header_text += "\n" + zones.get("DATE PACIENT", "")
        header_text += "\n" + zones.get("DATE INTERNARE", "")
        header_text += "\n" + zones.get("MEDIC CURANT", "")
    elif doc_type == DocumentType.OUTPATIENT_MEDICAL_LETTER:
        header_text += "\n" + zones.get("Medic", "")

    table_fields = _extract_from_tables(pdf_path) if pdf_path else {}

    def extract_field(regex, text):
        match = regex.search(text)
        return match.group(1).strip() if match else None

    cnp = table_fields.get("cnp") or extract_field(REGEX_CNP, header_text)
    nume = table_fields.get("nume") or extract_field(REGEX_NUME, header_text)
    domiciliu = table_fields.get("domiciliu") or extract_field(REGEX_DOMICILIU, header_text)
    fo_number = extract_field(REGEX_FO, header_text)
    contract_number = extract_field(REGEX_CONTRACT, header_text)
    varsta_str = table_fields.get("varsta") or extract_field(REGEX_VARSTA, header_text)
    sex_explicit = extract_field(REGEX_SEX, header_text)
    grup_sangvin = table_fields.get("grup_sangvin") or extract_field(REGEX_GRUP_SANGVIN, header_text)
    rh = table_fields.get("rh") or extract_field(REGEX_RH, header_text)
    alergii = table_fields.get("alergii") or extract_field(REGEX_ALERGII, header_text)

    data_internarii_str = table_fields.get("data_internarii") or extract_field(
        REGEX_DATA_INTERNARE, header_text
    )
    data_externarii_str = table_fields.get("data_externarii") or extract_field(
        REGEX_DATA_EXTERNARE, header_text
    )

    if not data_internarii_str and not data_externarii_str:
        generic_date_match = re.search(
            r"(?:^|\s)DATA[:\s]*(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{4})",
            header_text,
            re.IGNORECASE,
        )
        if generic_date_match:
            data_internarii_str = generic_date_match.group(1)
            data_externarii_str = generic_date_match.group(1)

    sectia = extract_field(REGEX_SECTIA, header_text)
    medic = table_fields.get("medic") or extract_field(REGEX_MEDIC, header_text)
    stare_externare = extract_field(REGEX_STARE, zones.get("STARE LA EXTERNARE", ""))

    dob_from_cnp = None
    sex_from_cnp = None
    if cnp:
        try:
            cnp_data = parse_cnp(cnp)
            dob_from_cnp = cnp_data.date_of_birth
            sex_from_cnp = cnp_data.sex
        except CNPParseError as e:
            warnings.append(str(e))

    data_internarii = None
    if data_internarii_str:
        try:
            data_internarii = parse_romanian_datetime(data_internarii_str)
        except DateParseError as e:
            warnings.append(str(e))

    data_externarii = None
    if data_externarii_str:
        try:
            data_externarii = parse_romanian_datetime(data_externarii_str)
        except DateParseError as e:
            warnings.append(str(e))

    diag_zone = zones.get("Diagnostic", "")
    if doc_type == DocumentType.HOSPITAL_DISCHARGE_REPORT:
        diag_zone += "\n" + zones.get("DIAGNOSTIC PRINCIPAL LA EXTERNARE", "")

    diagnostic_principal = None
    diagnostice_secundare = []

    if diag_zone.strip():
        cim_match = REGEX_CIM10.search(diag_zone)
        cod_cim10 = cim_match.group(1) if cim_match else None

        diagnostic_principal = DiagnosticEntry(
            denumire=diag_zone.strip().split("\n")[0][:100],
            cod_cim10=cod_cim10,
        )

        sec_zone = zones.get("DIAGNOSTICE SECUNDARE", "")
        if sec_zone:
            for line in sec_zone.splitlines():
                line = line.strip()
                if line:
                    c_match = REGEX_CIM10.search(line)
                    diagnostice_secundare.append(
                        DiagnosticEntry(
                            denumire=line[:100],
                            cod_cim10=c_match.group(1) if c_match else None,
                        )
                    )

    filled_fields = sum(
        1
        for x in [cnp, nume, fo_number, data_internarii, data_externarii, medic, diagnostic_principal]
        if x is not None
    )
    confidence_score = min(1.0, filled_fields / 6)

    return StructuredFields(
        doc_type=doc_type.value,
        nume=nume,
        domiciliu=domiciliu,
        nr_focg=fo_number,
        contract_number=contract_number,
        cnp=cnp,
        dob_from_cnp=dob_from_cnp,
        sex_from_cnp=sex_from_cnp,
        varsta=int(varsta_str) if varsta_str and varsta_str.isdigit() else None,
        sex_explicit=sex_explicit,
        grup_sangvin=grup_sangvin,
        rh=rh,
        alergii=alergii,
        data_internarii=data_internarii,
        data_externarii=data_externarii,
        sectia=sectia,
        medic=medic,
        stare_externare=stare_externare,
        diagnostic_principal=diagnostic_principal,
        diagnostice_secundare=diagnostice_secundare,
        confidence_score=confidence_score,
        parsing_warnings=warnings,
    )
