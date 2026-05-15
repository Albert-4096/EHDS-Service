from app.pipeline.stage4h_transfusions import extract_transfusions
from app.pipeline.stage2_classify import DocumentType


def test_empty_transfusion_table():
    text = "Grupa sange | RH | Tip | Nr pungii | Data\n"
    assert extract_transfusions(text, DocumentType.OUTPATIENT_MEDICAL_LETTER) == []


def test_transfusion_row_parsed():
    text = """
Grupa sange | RH | Tip | Nr pungii | Data
A | pozitiv | MER | 12345 | 23/04/2026
"""
    records = extract_transfusions(text, DocumentType.OUTPATIENT_MEDICAL_LETTER)
    assert len(records) == 1
    assert records[0].blood_group == "A"
    assert records[0].bag_number == "12345"
