from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.internal import (
    MergedRecord,
    StructuredFields,
    LabResults,
    LabValue,
    OncologyFields,
    TNMStaging,
)
from app.pipeline.stage2_classify import DocumentType
from app.pipeline.stage6_fhir import build_fhir_resources
from fhir.resources.observation import Observation
from fhir.resources.appointment import Appointment
from fhir.resources.diagnosticreport import DiagnosticReport


def test_build_fhir_resources_core():
    tz = ZoneInfo("Europe/Bucharest")
    structured = StructuredFields(
        doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER.value,
        cnp="1234567890123",
        data_internarii=datetime(2026, 4, 23, 10, 0, tzinfo=tz),
        data_externarii=datetime(2026, 4, 23, 14, 0, tzinfo=tz),
        medic="Dr. Test",
    )
    labs = LabResults(
        cbc={},
        biochemistry={
            "RDW": LabValue(
                test_name="RDW",
                value_raw="12.7",
                value_numeric=12.7,
                flagged=True,
                loinc_code="21000-5",
            )
        },
        hormones={},
        other={},
    )
    record = MergedRecord(
        doc_type=DocumentType.OUTPATIENT_MEDICAL_LETTER.value,
        structured=structured,
        labs=labs,
        oncology=OncologyFields(
            ecog_score=1,
            tnm=TNMStaging(t_category="pT2", n_category="n0", m_category="m0", stage_group="I"),
        ),
    )
    resources = build_fhir_resources(record)
    types = {type(r).__name__ for r in resources}
    assert "Patient" in types
    assert "Encounter" in types
    assert "Practitioner" in types

    flagged_obs = [
        r
        for r in resources
        if isinstance(r, Observation) and r.interpretation
    ]
    assert len(flagged_obs) >= 1


def test_encounter_class_ambulatory_same_day():
    tz = ZoneInfo("Europe/Bucharest")
    structured = StructuredFields(
        doc_type=DocumentType.HOSPITAL_DISCHARGE_REPORT.value,
        cnp="1234567890123",
        data_internarii=datetime(2026, 4, 23, 10, 0, tzinfo=tz),
        data_externarii=datetime(2026, 4, 23, 14, 0, tzinfo=tz),
    )
    record = MergedRecord(
        doc_type=DocumentType.HOSPITAL_DISCHARGE_REPORT.value,
        structured=structured,
    )
    from fhir.resources.encounter import Encounter

    resources = build_fhir_resources(record)
    enc = next(r for r in resources if isinstance(r, Encounter))
    assert enc.class_fhir[0].coding[0].code == "AMB"
