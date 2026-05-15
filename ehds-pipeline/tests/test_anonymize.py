import pytest
from datetime import date
from app.pipeline.stage8_anonymize import anonymize_record, _hash_cnp
from app.models.internal import MergedRecord, StructuredFields, EpicrizaExtracted
from app.pipeline.stage2_classify import DocumentType

def test_anonymize_record():
    original_cnp = "1800101123456"
    
    structured = StructuredFields(
        doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER.value,
        cnp=original_cnp,
        dob_from_cnp=date(1980, 1, 1),
        data_internarii=None,
        medic="Dr. Popescu Ion"
    )
    
    epicriza = EpicrizaExtracted(
        antecedente_heredocolaterale="Nume pacient: Ion",
        administered_in_hospital=[]
    )
    
    record = MergedRecord(
        doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER.value,
        structured=structured,
        epicriza=epicriza,
        medications=[],
        transfusions=[]
    )
    
    anon = anonymize_record(record)
    
    # Assert CNP is hashed
    assert anon.structured.cnp != original_cnp
    assert anon.structured.cnp == _hash_cnp(original_cnp)
    
    # Assert Medic name is redacted
    assert anon.structured.medic == "[REDACTED]"
    
    # Assert DOB is shifted but not exactly the same
    assert anon.structured.dob_from_cnp != date(1980, 1, 1)
    
    # Assert PII in narrative is scrubbed
    assert "Ion" not in (anon.epicriza.antecedente_heredocolaterale or "")
    assert "[REDACTED" in (anon.epicriza.antecedente_heredocolaterale or "")
