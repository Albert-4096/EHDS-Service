import pytest
from datetime import date, datetime
from app.utils.date_parser import parse_romanian_date, parse_romanian_datetime, DateParseError
from zoneinfo import ZoneInfo

def test_parse_romanian_date_formats():
    # FORMAT A
    assert parse_romanian_date("23/04/2026 10:06") == date(2026, 4, 23)
    # FORMAT B
    assert parse_romanian_date("23/04/2026 14:21") == date(2026, 4, 23)
    # FORMAT C & D
    assert parse_romanian_date("26.05.2023") == date(2023, 5, 26)
    assert parse_romanian_date("01.09.2023") == date(2023, 9, 1)
    # FORMAT E
    assert parse_romanian_date("21 Mai 2026") == date(2026, 5, 21)
    # FORMAT F & G
    assert parse_romanian_date("19.04.2024") == date(2024, 4, 19)

def test_parse_romanian_datetime():
    tz = ZoneInfo("Europe/Bucharest")
    
    # With time
    dt1 = parse_romanian_datetime("23/04/2026 10:06")
    assert dt1.year == 2026
    assert dt1.month == 4
    assert dt1.day == 23
    assert dt1.hour == 10
    assert dt1.minute == 6
    assert dt1.tzinfo == tz
    
    # Without time (defaults to 00:00)
    dt2 = parse_romanian_datetime("21 Mai 2026")
    assert dt2.year == 2026
    assert dt2.hour == 0
    assert dt2.minute == 0
    assert dt2.tzinfo == tz

def test_parse_romanian_date_errors():
    with pytest.raises(DateParseError):
        parse_romanian_date("invalid date string")
