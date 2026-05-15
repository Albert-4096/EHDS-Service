import pytest
from datetime import date, datetime
from app.utils.date_parser import parse_romanian_date, parse_romanian_datetime, DateParseError
from zoneinfo import ZoneInfo


def test_parse_romanian_date_formats():
    assert parse_romanian_date("23/04/2026 10:06") == date(2026, 4, 23)
    assert parse_romanian_date("23/04/2026 14:21") == date(2026, 4, 23)
    assert parse_romanian_date("26.05.2023") == date(2023, 5, 26)
    assert parse_romanian_date("01.09.2023") == date(2023, 9, 1)
    assert parse_romanian_date("21 Mai 2026") == date(2026, 5, 21)
    assert parse_romanian_date("19.04.2024") == date(2024, 4, 19)


def test_parse_romanian_date_extended_formats():
    assert parse_romanian_date("23-04-2026") == date(2026, 4, 23)
    assert parse_romanian_date("23.04.2026 10:06") == date(2026, 4, 23)
    assert parse_romanian_date("2026-04-23") == date(2026, 4, 23)
    assert parse_romanian_date("23/04/26") == date(2026, 4, 23)


def test_parse_romanian_datetime():
    tz = ZoneInfo("Europe/Bucharest")

    dt1 = parse_romanian_datetime("23/04/2026 10:06")
    assert dt1.year == 2026
    assert dt1.month == 4
    assert dt1.day == 23
    assert dt1.hour == 10
    assert dt1.minute == 6
    assert dt1.tzinfo == tz

    dt2 = parse_romanian_datetime("21 Mai 2026")
    assert dt2.year == 2026
    assert dt2.hour == 0
    assert dt2.minute == 0
    assert dt2.tzinfo == tz

    dt3 = parse_romanian_datetime("23.04.2026 14:21")
    assert dt3.hour == 14
    assert dt3.minute == 21


def test_parse_romanian_date_errors():
    with pytest.raises(DateParseError):
        parse_romanian_date("invalid date string")
