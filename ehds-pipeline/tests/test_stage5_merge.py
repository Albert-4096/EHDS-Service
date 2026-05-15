import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.errors import CoreSetError
from app.models.internal import StructuredFields, EpicrizaExtracted
from app.pipeline.stage2_classify import DocumentType
from app.pipeline.stage5_merge import merge_and_validate


def _structured(**kwargs) -> StructuredFields:
    defaults = dict(
        doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER.value,
        cnp="1234567890123",
        data_internarii=datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Europe/Bucharest")),
    )
    defaults.update(kwargs)
    return StructuredFields(**defaults)


def test_core_set_error_missing_patient():
    with pytest.raises(CoreSetError, match="CNP or Nume"):
        merge_and_validate(
            doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER,
            structured=_structured(cnp=None, nume=None),
            epicriza_zone_text="Epicriza text",
        )


def test_core_set_error_missing_admission_date():
    with pytest.raises(CoreSetError, match="admission date"):
        merge_and_validate(
            doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER,
            structured=_structured(data_internarii=None),
            epicriza_zone_text="Epicriza text",
        )


def test_core_set_error_missing_epicriza():
    with pytest.raises(CoreSetError, match="Epicriza"):
        merge_and_validate(
            doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER,
            structured=_structured(),
            epicriza_zone_text="",
            epicriza=EpicrizaExtracted(),
        )


def test_merge_succeeds_with_warnings_for_missing_medic():
    record = merge_and_validate(
        doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER,
        structured=_structured(medic=None),
        epicriza_zone_text="Pacient internat pentru tratament.",
    )
    assert any("Medic absent" in w for w in record.all_warnings)
