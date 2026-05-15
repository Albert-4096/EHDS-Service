import uuid
from typing import List
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.identifier import Identifier
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.period import Period
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from fhir.resources.domainresource import DomainResource
from fhir.resources.extension import Extension
from fhir.resources.procedure import Procedure
from fhir.resources.device import Device, DeviceName
from fhir.resources.deviceusage import DeviceUsage
from fhir.resources.adverseevent import AdverseEvent
from datetime import datetime, timezone

from app.models.internal import MergedRecord, LabValue
from app.terminology.mappings import CIM10_TO_SNOMED

def generate_uuid() -> str:
    return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coding(system: str, code: str, display: str | None = None) -> Coding:
    """Build a Coding object, optionally with display."""
    kwargs = {"system": system, "code": code}
    if display:
        kwargs["display"] = display
    return Coding(**kwargs)

def _codeable_concept(system: str, code: str, text: str | None = None, display: str | None = None) -> CodeableConcept:
    """Build a CodeableConcept with one coding entry."""
    kwargs: dict = {"coding": [_coding(system, code, display)]}
    if text:
        kwargs["text"] = text
    return CodeableConcept(**kwargs)

def _data_absent_reason() -> Extension:
    return Extension(
        url="http://hl7.org/fhir/StructureDefinition/data-absent-reason",
        valueCode="unknown"
    )

# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_fhir_resources(record: MergedRecord) -> List[DomainResource]:
    resources = []

    # ------------------------------------------------------------------
    # 1. Patient
    # ------------------------------------------------------------------
    patient = Patient(id=generate_uuid())
    if record.structured.cnp:
        patient.identifier = [
            Identifier(
                system="urn:oid:2.16.428.1.100.1.1.1",
                value=record.structured.cnp,
            )
        ]

    if record.structured.dob_from_cnp:
        patient.birthDate = record.structured.dob_from_cnp
    else:
        patient.extension = [_data_absent_reason()] # R-NULL compliance

    sex = record.structured.sex_from_cnp or record.structured.sex_explicit
    if sex:
        sex_map = {"M": "male", "F": "female"}
        patient.gender = sex_map.get(sex.upper(), "unknown")
    else:
        # Pydantic validation for fhir.resources might not allow extension on gender directly without _gender, 
        # so we set it to 'unknown' which is standard in FHIR.
        patient.gender = "unknown"

    resources.append(patient)
    patient_ref = Reference(reference=f"Patient/{patient.id}")

    # ------------------------------------------------------------------
    # 2. Encounter  (FHIR R4)
    # ------------------------------------------------------------------
    from app.pipeline.stage2_classify import DocumentType

    encounter_class_code = "IMP"
    encounter_class_display = "inpatient encounter"
    if record.doc_type == DocumentType.OUTPATIENT_MEDICAL_LETTER.value:
        encounter_class_code = "AMB"
        encounter_class_display = "ambulatory"

    encounter = Encounter(
        id=generate_uuid(),
        status="finished",
        class_fhir=[
            _codeable_concept(
                "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                encounter_class_code,
                display=encounter_class_display,
            )
        ]
    )
    encounter.subject = patient_ref

    if record.structured.data_internarii or record.structured.data_externarii:
        period = Period()
        if record.structured.data_internarii:
            period.start = record.structured.data_internarii
        if record.structured.data_externarii:
            period.end = record.structured.data_externarii
        encounter.actualPeriod = period  # R5 uses actualPeriod

    resources.append(encounter)
    encounter_ref = Reference(reference=f"Encounter/{encounter.id}")

    # ------------------------------------------------------------------
    # 3. Conditions
    # ------------------------------------------------------------------
    def create_condition(diag, rank: int = 1) -> Condition:
        code_concept = CodeableConcept(text=diag.denumire)
        codings = []
        
        if diag.cod_cim10:
            # R-DUAL compliance: CIM-10 + SNOMED CT
            snomed_mapping = CIM10_TO_SNOMED.get(diag.cod_cim10)
            if snomed_mapping:
                codings.append(_coding("http://snomed.info/sct", snomed_mapping["code"], snomed_mapping["display"]))
            # Add CIM-10
            codings.append(_coding("http://hl7.org/fhir/sid/icd-10", diag.cod_cim10))
            
        if codings:
            code_concept.coding = codings
            
        cond = Condition(
            id=generate_uuid(),
            subject=patient_ref,
            clinicalStatus=_codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-clinical", "active"
            )
        )
        cond.code = code_concept
        cond.encounter = encounter_ref
        return cond

    if record.structured.diagnostic_principal:
        cond_primary = create_condition(record.structured.diagnostic_principal)
        cond_primary.category = [
            _codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-category",
                "encounter-diagnosis",
            )
        ]
        resources.append(cond_primary)

    adverse_keywords = ["toxicitate", "degradare", "hipofizita autoimuna"]
    
    def is_adverse_event(diag_name: str) -> bool:
        lower_name = diag_name.lower()
        return any(kw in lower_name for kw in adverse_keywords)

    for diag in record.structured.diagnostice_secundare:
        if is_adverse_event(diag.denumire):
            ae = AdverseEvent(
                id=generate_uuid(),
                status="completed", # R5 status
                actuality="actual",
                subject=patient_ref,
                encounter=encounter_ref,
                code=CodeableConcept(text=diag.denumire)
            )
            resources.append(ae)
        else:
            resources.append(create_condition(diag))

    # ------------------------------------------------------------------
    # 4. Observations (Labs)
    # ------------------------------------------------------------------
    if record.labs:
        def create_lab_obs(lab: LabValue, category_code: str) -> Observation:
            code_concept = CodeableConcept(text=lab.test_name)
            if lab.loinc_code:
                code_concept.coding = [_coding("http://loinc.org", lab.loinc_code)]
            obs = Observation(
                id=generate_uuid(),
                status="final",
                subject=patient_ref,
                code=code_concept,
                category=[
                    _codeable_concept(
                        "http://terminology.hl7.org/CodeSystem/observation-category",
                        category_code,
                    )
                ],
            )
            obs.encounter = encounter_ref

            if lab.value_numeric is not None:
                quantity = Quantity(value=lab.value_numeric)
                if lab.unit_ucum:
                    quantity.unit = lab.unit_ucum
                    quantity.system = "http://unitsofmeasure.org"
                    quantity.code = lab.unit_ucum
                elif lab.unit_raw:
                    quantity.unit = lab.unit_raw
                obs.valueQuantity = quantity
            elif lab.value_raw:
                obs.valueString = lab.value_raw

            return obs

        for _, lab in record.labs.cbc.items():
            resources.append(create_lab_obs(lab, "laboratory"))
        for _, lab in record.labs.biochemistry.items():
            resources.append(create_lab_obs(lab, "laboratory"))
        for _, lab in record.labs.hormones.items():
            resources.append(create_lab_obs(lab, "laboratory"))
        for _, lab in record.labs.other.items():
            resources.append(create_lab_obs(lab, "laboratory"))

    # ------------------------------------------------------------------
    # 5. Observation (TNM / Oncology staging)
    # ------------------------------------------------------------------
    if record.oncology and record.oncology.tnm:
        tnm = record.oncology.tnm
        obs = Observation(
            id=generate_uuid(),
            status="final",
            subject=patient_ref,
            code=_codeable_concept("http://loinc.org", "21908-9", display="Stage group.clinical Cancer"),
            encounter=encounter_ref
        )
        if tnm.stage_group:
            obs.valueString = tnm.stage_group
        resources.append(obs)

    # ------------------------------------------------------------------
    # 6. MedicationStatement (FHIR R4)
    # ------------------------------------------------------------------
    for med in record.medications:
        concept = CodeableConcept(text=med.medicament)
        if med.atc_code:
            concept.coding = [
                _coding("http://www.whocc.no/atc", med.atc_code)
            ]

        mstmt = MedicationStatement(
            id=generate_uuid(),
            status="recorded",
            subject=patient_ref,
            medication=concept,
        )
        mstmt.encounter = encounter_ref

        dosage_text = f"{med.doza or ''} {med.frecventa or ''} {med.durata or ''}".strip()
        if dosage_text:
            from fhir.resources.dosage import Dosage
            mstmt.dosage = [Dosage(text=dosage_text)]

        resources.append(mstmt)

    # ------------------------------------------------------------------
    # 7. Procedures, Devices, and extra Adverse Events
    # ------------------------------------------------------------------
    if record.epicriza:
        for proc in record.epicriza.procedures:
            p = Procedure(
                id=generate_uuid(),
                status="completed",
                subject=patient_ref,
                encounter=encounter_ref,
                code=CodeableConcept(text=proc.name)
            )
            if proc.date:
                p.performedDateTime = proc.date
            if proc.body_site:
                p.bodySite = [CodeableConcept(text=proc.body_site)]
            resources.append(p)

        for imp in record.epicriza.implants:
            dev = Device(id=generate_uuid())
            dev.deviceName = [DeviceName(value=imp.name, type="user-friendly-name")]
            resources.append(dev)

            dus = DeviceUsage(
                id=generate_uuid(),
                status="active",
                patient=patient_ref,
                device=Reference(reference=f"Device/{dev.id}")
            )
            if imp.body_site:
                dus.bodySite = CodeableConcept(text=imp.body_site)
            resources.append(dus)

        for ae_text in record.epicriza.adverse_events:
            ae = AdverseEvent(
                id=generate_uuid(),
                status="completed",
                actuality="actual",
                subject=patient_ref,
                encounter=encounter_ref,
                code=CodeableConcept(text=ae_text)
            )
            resources.append(ae)

    return resources
