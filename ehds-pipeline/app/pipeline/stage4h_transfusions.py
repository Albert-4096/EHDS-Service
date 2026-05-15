import re
from app.models.internal import TransfusionRecord
from app.pipeline.stage2_classify import DocumentType
from app.utils.date_parser import parse_romanian_date, DateParseError

HEADER_PATTERN = re.compile(
    r"Grupa\s+sang[eé]\s*\|\s*RH\s*\|\s*Tip\s*\|\s*Nr\s+pungii\s*\|\s*Data",
    re.IGNORECASE,
)
ROW_PATTERN = re.compile(
    r"^([ABO]{1,2}|AB)\s*\|\s*"
    r"(pozitiv|negativ|\+|-)\s*\|\s*"
    r"([^|]+)\s*\|\s*"
    r"([^|]+)\s*\|\s*"
    r"(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{4})\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def extract_transfusions(header_zone_text: str, doc_type: DocumentType) -> list[TransfusionRecord]:
    """
    HP-14: Parse blood transfusion table from DOC_BIS header zone.
    Empty table -> [].
    """
    if doc_type != DocumentType.OUTPATIENT_MEDICAL_LETTER:
        return []

    if not header_zone_text or not HEADER_PATTERN.search(header_zone_text):
        return []

    records: list[TransfusionRecord] = []
    for match in ROW_PATTERN.finditer(header_zone_text):
        blood_group, rh, product_type, bag_number, date_str = match.groups()
        parsed_date = None
        try:
            parsed_date = parse_romanian_date(date_str.strip())
        except DateParseError:
            pass

        records.append(
            TransfusionRecord(
                blood_group=blood_group.strip(),
                rh=rh.strip(),
                product_type=product_type.strip(),
                bag_number=bag_number.strip(),
                date=parsed_date,
            )
        )

    return records
