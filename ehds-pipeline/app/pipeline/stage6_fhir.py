import uuid
from typing import List
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.identifier import Identifier
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.period import Period
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from fhir.resources.domainresource import DomainResource
from datetime import datetime, timezone

from app.models.internal import MergedRecord, LabValue

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

    sex = record.structured.sex_from_cnp or record.structured.sex_explicit
    if sex:
        sex_map = {"M": "male", "F": "female"}
        patient.gender = sex_map.get(sex.upper(), "unknown")

    resources.append(patient)
    patient_ref = Reference(reference=f"Patient/{patient.id}")

    # ------------------------------------------------------------------
    # 2. Encounter  (fhir.resources v8 = FHIR R5)
    #    R5: Encounter.class  is list[Coding]  (was class_fhir: Coding in R4)
    # ------------------------------------------------------------------
    encounter = Encounter(
        id=generate_uuid(),
        status="finished",
        **{
            "class": [
                _codeable_concept(
                    "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "IMP",
                    display="inpatient encounter",
                )
            ]
        },
    )
    encounter.subject = patient_ref

    if record.structured.data_internarii or record.structured.data_externarii:
        period = Period()
        if record.structured.data_internarii:
            period.start = record.structured.data_internarii
        if record.structured.data_externarii:
            period.end = record.structured.data_externarii
        encounter.actualPeriod = period  # R5: was 'period' in R4

    resources.append(encounter)
    encounter_ref = Reference(reference=f"Encounter/{encounter.id}")

    # ------------------------------------------------------------------
    # 3. Conditions
    # ------------------------------------------------------------------
    def create_condition(diag, rank: int = 1) -> Condition:
        code_concept = CodeableConcept(text=diag.denumire)
        if diag.cod_cim10:
            code_concept.coding = [
                _coding("http://hl7.org/fhir/sid/icd-10", diag.cod_cim10)
            ]
        cond = Condition(
            id=generate_uuid(),
            subject=patient_ref,
            clinicalStatus=_codeable_concept(   # required in R5 constructor
                "http://terminology.hl7.org/CodeSystem/condition-clinical", "active"
            ),
            code=code_concept,
        )
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

    for diag in record.structured.diagnostice_secundare:
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
                code=code_concept,  # required in R5 constructor
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
            code=_codeable_concept(   # required in R5 constructor
                "http://loinc.org", "21908-9", display="Stage group.clinical Cancer"
            ),
        )
        obs.encounter = encounter_ref
        if tnm.stage_group:
            obs.valueString = tnm.stage_group
        resources.append(obs)

    # ------------------------------------------------------------------
    # 6. MedicationStatement  (fhir.resources v8 = FHIR R5)
    #    R5: medication is CodeableReference  (was medicationCodeableConcept in R4)
    #        context -> encounter
    #        status "active" -> "recorded"
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
            medication=CodeableReference(concept=concept),
        )
        mstmt.encounter = encounter_ref

        dosage_text = f"{med.doza or ''} {med.frecventa or ''} {med.durata or ''}".strip()
        if dosage_text:
            from fhir.resources.dosage import Dosage
            mstmt.dosage = [Dosage(text=dosage_text)]

        resources.append(mstmt)

    return resources
