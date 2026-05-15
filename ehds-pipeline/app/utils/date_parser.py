import re
import warnings
from datetime import date, datetime
from zoneinfo import ZoneInfo

class DateParseError(Exception):
    """Exception raised when a date string cannot be parsed."""
    pass

ROMANIAN_MONTHS = {
    "ianuarie": 1,
    "februarie": 2,
    "martie": 3,
    "aprilie": 4,
    "mai": 5,
    "iunie": 6,
    "iulie": 7,
    "august": 8,
    "septembrie": 9,
    "octombrie": 10,
    "noiembrie": 11,
    "decembrie": 12,
}

# Format A/B: DD/MM/YYYY HH:MM
REGEX_SLASH_DATETIME = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{2}):(\d{2})$")
# Format A/B date-only: DD/MM/YYYY
REGEX_SLASH_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
# Format C/D/F/G: DD.MM.YYYY
REGEX_DOT_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
# Format with time: DD.MM.YYYY HH:MM
REGEX_DOT_DATETIME = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{2}):(\d{2})$")
# Dash separator: DD-MM-YYYY
REGEX_DASH_DATE = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")
REGEX_DASH_DATETIME = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{2}):(\d{2})$")
# ISO: YYYY-MM-DD
REGEX_ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
# Format E: DD MonthName YYYY (diacritic-tolerant)
REGEX_ROMANIAN_MONTH_DATE = re.compile(
    r"^(\d{1,2})\s+([a-zA-ZăâîșțĂÂÎȘȚ]+)\s+(\d{4})$"
)
# Optional 2-digit year: DD/MM/YY
REGEX_SLASH_DATE_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")


def _build_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, day, month)


def _expand_century(year_2digit: int) -> int:
    return 2000 + year_2digit if year_2digit < 70 else 1900 + year_2digit


def _normalize_month_name(name: str) -> str | None:
    lower = name.lower()
    # Strip diacritics for lookup
    replacements = {"ă": "a", "â": "a", "î": "i", "ș": "s", "ț": "t"}
    normalized = lower
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    if normalized in ROMANIAN_MONTHS:
        return normalized
    if lower in ROMANIAN_MONTHS:
        return lower
    return None


def parse_romanian_date(raw: str) -> date:
    """
    Parses a Romanian date string into a datetime.date object.
    Supports all 7 format families (A–G) per HP-06.
    """
    raw_stripped = raw.strip()

    match = REGEX_SLASH_DATETIME.match(raw_stripped)
    if match:
        day, month, year, _, _ = match.groups()
        return _build_date(int(year), int(month), int(day))

    match = REGEX_DOT_DATETIME.match(raw_stripped)
    if match:
        day, month, year, _, _ = match.groups()
        return _build_date(int(year), int(month), int(day))

    match = REGEX_DASH_DATETIME.match(raw_stripped)
    if match:
        day, month, year, _, _ = match.groups()
        return _build_date(int(year), int(month), int(day))

    match = REGEX_SLASH_DATE.match(raw_stripped)
    if match:
        day, month, year = match.groups()
        return _build_date(int(year), int(month), int(day))

    match = REGEX_DOT_DATE.match(raw_stripped)
    if match:
        day, month, year = match.groups()
        return _build_date(int(year), int(month), int(day))

    match = REGEX_DASH_DATE.match(raw_stripped)
    if match:
        day, month, year = match.groups()
        return _build_date(int(year), int(month), int(day))

    match = REGEX_ISO_DATE.match(raw_stripped)
    if match:
        year, month, day = match.groups()
        return _build_date(int(year), int(month), int(day))

    match = REGEX_SLASH_DATE_SHORT.match(raw_stripped)
    if match:
        day, month, year_2 = match.groups()
        year = _expand_century(int(year_2))
        return _build_date(year, int(month), int(day))

    match = REGEX_ROMANIAN_MONTH_DATE.match(raw_stripped)
    if match:
        day, month_name, year = match.groups()
        month_key = _normalize_month_name(month_name)
        if month_key:
            return date(int(year), ROMANIAN_MONTHS[month_key], int(day))

    raise DateParseError(f"Could not parse date: '{raw}'")


def parse_romanian_datetime(raw: str) -> datetime:
    """
    Parses a Romanian datetime string into a timezone-aware datetime (Europe/Bucharest).
    """
    raw_stripped = raw.strip()
    dt = None

    match = REGEX_SLASH_DATETIME.match(raw_stripped)
    if match:
        day, month, year, hour, minute = match.groups()
        dt = datetime(int(year), int(month), int(day), int(hour), int(minute))

    if dt is None:
        match = REGEX_DOT_DATETIME.match(raw_stripped)
        if match:
            day, month, year, hour, minute = match.groups()
            dt = datetime(int(year), int(month), int(day), int(hour), int(minute))

    if dt is None:
        match = REGEX_DASH_DATETIME.match(raw_stripped)
        if match:
            day, month, year, hour, minute = match.groups()
            dt = datetime(int(year), int(month), int(day), int(hour), int(minute))

    if dt is None:
        try:
            d = parse_romanian_date(raw)
            dt = datetime(d.year, d.month, d.day, 0, 0)
        except DateParseError:
            pass

    if dt is None:
        raise DateParseError(f"Could not parse datetime: '{raw}'")

    tz = ZoneInfo("Europe/Bucharest")
    localized_dt = dt.replace(tzinfo=tz)
    return localized_dt
