import re
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

# Pre-compile regex patterns for performance
# Formats: DD/MM/YYYY HH:MM or DD/MM/YYYY
REGEX_SLASH_DATETIME = re.compile(r"^(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})$")
REGEX_SLASH_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

# Formats: DD.MM.YYYY
REGEX_DOT_DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")

# Format: DD MonthName YYYY
REGEX_ROMANIAN_MONTH_DATE = re.compile(r"^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})$")

def parse_romanian_date(raw: str) -> date:
    """
    Parses a Romanian date string into a datetime.date object.
    Supported formats:
    - DD/MM/YYYY
    - DD/MM/YYYY HH:MM (time is ignored)
    - DD.MM.YYYY
    - DD MonthName YYYY (e.g., 21 Mai 2026)
    """
    raw_stripped = raw.strip()

    # Try DD/MM/YYYY HH:MM
    match = REGEX_SLASH_DATETIME.match(raw_stripped)
    if match:
        day, month, year, _, _ = match.groups()
        return date(int(year), int(month), int(day))

    # Try DD/MM/YYYY
    match = REGEX_SLASH_DATE.match(raw_stripped)
    if match:
        day, month, year = match.groups()
        return date(int(year), int(month), int(day))

    # Try DD.MM.YYYY
    match = REGEX_DOT_DATE.match(raw_stripped)
    if match:
        day, month, year = match.groups()
        return date(int(year), int(month), int(day))

    # Try DD MonthName YYYY
    match = REGEX_ROMANIAN_MONTH_DATE.match(raw_stripped)
    if match:
        day, month_name, year = match.groups()
        month_lower = month_name.lower()
        if month_lower in ROMANIAN_MONTHS:
            return date(int(year), ROMANIAN_MONTHS[month_lower], int(day))

    raise DateParseError(f"Could not parse date: '{raw}'")

def parse_romanian_datetime(raw: str) -> datetime:
    """
    Parses a Romanian datetime string into an aware datetime.datetime object.
    Includes Romania's UTC offset automatically (Europe/Bucharest).
    If no time is provided, defaults to 00:00.
    """
    raw_stripped = raw.strip()
    dt = None

    # Try DD/MM/YYYY HH:MM
    match = REGEX_SLASH_DATETIME.match(raw_stripped)
    if match:
        day, month, year, hour, minute = match.groups()
        dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
    
    # Try other formats without time
    if dt is None:
        try:
            d = parse_romanian_date(raw)
            dt = datetime(d.year, d.month, d.day, 0, 0)
        except DateParseError:
            pass

    if dt is None:
        raise DateParseError(f"Could not parse datetime: '{raw}'")

    # Localize using Europe/Bucharest to automatically handle DST rules.
    # The prompt mentions defaulting to +02:00 in ambiguity. fold=0 does this natively in zoneinfo (first occurrence).
    tz = ZoneInfo("Europe/Bucharest")
    localized_dt = dt.replace(tzinfo=tz)
    return localized_dt
