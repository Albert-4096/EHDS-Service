import re
from app.models.internal import AppointmentBlock
from app.utils.date_parser import parse_romanian_date, DateParseError, ZoneInfo
from datetime import datetime

REGEX_APPOINTMENT = re.compile(r"Sunteti programat in data:\s+(.+?)\s+ora:\s+(\d{2}:\d{2})", re.IGNORECASE)

def extract_appointment(text: str) -> AppointmentBlock | None:
    """
    Extracts the appointment block from the document text.
    Expected format: "Sunteti programat in data: 21 Mai 2026 ora: 09:10"
    """
    if not text:
        return None
        
    match = REGEX_APPOINTMENT.search(text)
    if not match:
        return None
        
    date_str = match.group(1).strip()
    time_str = match.group(2).strip()
    
    datetime_raw = f"{date_str} {time_str}"
    datetime_parsed = None
    
    try:
        # First parse the date
        d = parse_romanian_date(date_str)
        # Combine with time
        hour, minute = map(int, time_str.split(':'))
        dt = datetime(d.year, d.month, d.day, hour, minute)
        # Apply timezone (Europe/Bucharest)
        tz = ZoneInfo("Europe/Bucharest")
        datetime_parsed = dt.replace(tzinfo=tz)
    except DateParseError:
        pass
        
    return AppointmentBlock(
        datetime_raw=datetime_raw,
        datetime_parsed=datetime_parsed,
        location=None
    )
