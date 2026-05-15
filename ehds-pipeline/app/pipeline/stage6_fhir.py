import uuid
from datetime import datetime
from typing import List

from fhir.resources.adverseevent import AdverseEvent
from fhir.resources.appointment import Appointment
from fhir.resources.careplan import CarePlan, CarePlanActivity
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.condition import Condition
from fhir.resources.device import Device, DeviceName
from fhir.resources.deviceusage import DeviceUsage
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.domainresource import DomainResource
from fhir.resources.encounter import Encounter
from fhir.resources.extension import Extension
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.practitioner import Practitioner
from fhir.resources.practitionerrole import PractitionerRole
from fhir.resources.procedure import Procedure
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from fhir.resources.narrative import Narrative

from app.models.internal import LabValue, MergedRecord, ProcedureEntry
from app.terminology.body_site_snomed import lookup_body_site
from app.terminology.cim10_to_snomed import get_snomed_for_cim10, DATA_ABSENT_CODING
from app.utils.date_parser import parse_romanian_date, DateParseError


def generate_uuid() -> str:
    return str(uuid.uuid4())


def _coding(system: str, code: str, display: str | None = None) -> Coding:
    kwargs = {"system": system, "code": code}
    if display:
        kwargs["display"] = display
    return Coding(**kwargs)


def _codeable_concept(
    system: str,
    code: str,
    text: str | None = None,
    display: str | None = None,
) -> CodeableConcept:
    kwargs: dict = {"coding": [_coding(system, code, display)]}
    if text:
        kwargs["text"] = text
    return CodeableConcept(**kwargs)


def _body_site_concept(site_text: str | None) -> CodeableConcept | None:
    if not site_text:
        return None
    mapping = lookup_body_site(site_text)
    if mapping:
        return CodeableConcept(
            coding=[_coding("http://snomed.info/sct", mapping["code"], mapping["display"])],
            text=site_text,
        )
    return CodeableConcept(text=site_text)


def _data_absent_reason() -> Extension:
    return Extension(
        url="http://hl7.org/fhir/StructureDefinition/data-absent-reason",
        valueCode="unknown",
    )


def _encounter_class(record: MergedRecord) -> tuple[str, str]:
    """HP-17: duration-based AMB vs IMP."""
    start = record.structured.data_internarii
    end = record.structured.data_externarii
    if start and end:
        duration_hours = (end - start).total_seconds() / 3600
        if duration_hours < 24:
            return "AMB", "ambulatory"
    from app.pipeline.stage2_classify import DocumentType

    if record.doc_type == DocumentType.OUTPATIENT_MEDICAL_LETTER.value:
        return "AMB", "ambulatory"
    return "IMP", "inpatient encounter"


def _parse_timeline_date(raw: str | None):
    if not raw:
        return None
    try:
        return parse_romanian_date(raw)
    except DateParseError:
        return None


def build_fhir_resources(record: MergedRecord) -> List[DomainResource]:
    resources: List[DomainResource] = []

    # --- Patient ---
    patient = Patient(id=generate_uuid())
    cnp_present = bool((record.structured.cnp or "").strip())
    nume_present = bool((record.structured.nume or "").strip())

    if cnp_present:
        patient.identifier = [
            Identifier(
                system="urn:oid:2.16.428.1.100.1.1.1",
                value=record.structured.cnp,
            )
        ]
    elif nume_present:
        patient.identifier = [
            Identifier(
                system="urn:oid:2.16.428.1.100.1.1.1",
                extension=[_data_absent_reason()],
            )
        ]
        if record.structured.nume:
            patient.name = [HumanName(text=record.structured.nume)]

    if record.structured.dob_from_cnp:
        patient.birthDate = record.structured.dob_from_cnp
    elif not cnp_present and not nume_present:
        patient.extension = [_data_absent_reason()]

    sex = record.structured.sex_from_cnp or record.structured.sex_explicit
    if sex:
        sex_map = {"M": "male", "F": "female"}
        patient.gender = sex_map.get(sex.upper(), "unknown")
    else:
        patient.gender = "unknown"

    alergii = (record.structured.alergii or "").strip()
    if not alergii or alergii.upper() in ("NU CUNOASTE", "NU ȘTIU", "NECUNOSCUT"):
        narrative = "Alergii: necunoscute sau necompletate in documentul sursa."
    elif alergii:
        narrative = f"Alergii: {alergii}"
    else:
        narrative = None
    if narrative:
        patient.text = Narrative(
            status="generated",
            div=f"<div xmlns='http://www.w3.org/1999/xhtml'><p>{narrative}</p></div>",
        )

    resources.append(patient)
    patient_ref = Reference(reference=f"Patient/{patient.id}")

    # --- Practitioner ---
    practitioner = Practitioner(id=generate_uuid())
    if record.structured.medic and record.structured.medic.strip():
        practitioner.name = [HumanName(text=record.structured.medic.strip())]
    else:
        practitioner.extension = [_data_absent_reason()]

    resources.append(practitioner)
    practitioner_ref = Reference(reference=f"Practitioner/{practitioner.id}")

    # --- Encounter ---
    enc_code, enc_display = _encounter_class(record)
    encounter = Encounter(
        id=generate_uuid(),
        status="finished",
        class_fhir=[
            _codeable_concept(
                "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                enc_code,
                display=enc_display,
            )
        ],
    )
    encounter.subject = patient_ref

    encounter_ids = []
    if record.structured.contract_number:
        encounter_ids.append(
            Identifier(
                system="urn:ro:cnas:contract",
                value=record.structured.contract_number,
            )
        )
    fo = record.structured.nr_focg
    if fo:
        encounter_ids.append(
            Identifier(
                system="urn:oid:2.16.840.1.113883.2.24.1.3",
                value=fo,
            )
        )
    if encounter_ids:
        encounter.identifier = encounter_ids

    if record.structured.data_internarii or record.structured.data_externarii:
        period = Period()
        if record.structured.data_internarii:
            period.start = record.structured.data_internarii
        if record.structured.data_externarii:
            period.end = record.structured.data_externarii
        encounter.actualPeriod = period

    resources.append(encounter)
    encounter_ref = Reference(reference=f"Encounter/{encounter.id}")

    role = PractitionerRole(
        id=generate_uuid(),
        practitioner=practitioner_ref,
        organization=Reference(display=record.structured.sectia or "Unknown organization"),
    )
    resources.append(role)

    # --- Conditions ---
    def create_condition(diag, clinical_code: str = "active", onset=None) -> Condition:
        code_concept = CodeableConcept(text=diag.denumire)
        codings = []
        if diag.cod_cim10:
            snomed_mapping = get_snomed_for_cim10(diag.cod_cim10)
            if snomed_mapping:
                codings.append(
                    _coding("http://snomed.info/sct", snomed_mapping["code"], snomed_mapping["display"])
                )
            else:
                codings.append(
                    _coding(
                        DATA_ABSENT_CODING["system"],
                        DATA_ABSENT_CODING["code"],
                        DATA_ABSENT_CODING["display"],
                    )
                )
            codings.append(_coding("http://hl7.org/fhir/sid/icd-10", diag.cod_cim10))
        if codings:
            code_concept.coding = codings

        cond = Condition(
            id=generate_uuid(),
            subject=patient_ref,
            clinicalStatus=_codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-clinical",
                clinical_code,
            ),
        )
        cond.code = code_concept
        cond.encounter = encounter_ref
        if onset:
            cond.onsetDateTime = onset
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

    # --- Labs ---
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
            if lab.flagged:
                obs.interpretation = [
                    _codeable_concept(
                        "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "A",
                        "Abnormal",
                    )
                ]
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

        for panel in (
            record.labs.cbc,
            record.labs.biochemistry,
            record.labs.hormones,
            record.labs.other,
        ):
            for _, lab in panel.items():
                resources.append(create_lab_obs(lab, "laboratory"))

    # --- Oncology observations ---
    if record.oncology:
        if record.oncology.ecog_score is not None:
            ecog_obs = Observation(
                id=generate_uuid(),
                status="final",
                subject=patient_ref,
                code=_codeable_concept("http://loinc.org", "89247-1", display="ECOG performance status"),
                encounter=encounter_ref,
                valueInteger=record.oncology.ecog_score,
            )
            resources.append(ecog_obs)

        if record.oncology.cycle_number is not None:
            cycle_obs = Observation(
                id=generate_uuid(),
                status="final",
                subject=patient_ref,
                code=CodeableConcept(text="Chemotherapy cycle number"),
                encounter=encounter_ref,
                valueInteger=record.oncology.cycle_number,
            )
            resources.append(cycle_obs)

        if record.oncology.regimen_acronym:
            regimen_obs = Observation(
                id=generate_uuid(),
                status="final",
                subject=patient_ref,
                code=CodeableConcept(text="Chemotherapy regimen acronym"),
                encounter=encounter_ref,
                valueString=record.oncology.regimen_acronym,
            )
            resources.append(regimen_obs)

        if record.oncology.response_status:
            resp_obs = Observation(
                id=generate_uuid(),
                status="final",
                subject=patient_ref,
                code=_codeable_concept("http://loinc.org", "88040-1", display="Cancer response"),
                encounter=encounter_ref,
                valueString=record.oncology.response_status,
            )
            resources.append(resp_obs)

        if record.oncology.tnm:
            tnm = record.oncology.tnm
            tnm_components = [
                (tnm.t_category, "3853356007", "T category"),
                (tnm.n_category, "385382003", "N category"),
                (tnm.m_category, "385380006", "M category"),
            ]
            for value, snomed_code, label in tnm_components:
                if value:
                    comp_obs = Observation(
                        id=generate_uuid(),
                        status="final",
                        subject=patient_ref,
                        code=_codeable_concept("http://snomed.info/sct", snomed_code, display=label),
                        encounter=encounter_ref,
                        valueString=value,
                    )
                    resources.append(comp_obs)
            if tnm.stage_group:
                stage_obs = Observation(
                    id=generate_uuid(),
                    status="final",
                    subject=patient_ref,
                    code=_codeable_concept(
                        "http://loinc.org", "21908-9", display="Stage group.clinical Cancer"
                    ),
                    encounter=encounter_ref,
                    valueString=tnm.stage_group,
                )
                resources.append(stage_obs)

        for marker, value in record.oncology.molecular_markers.items():
            if marker.upper() == "BRAF":
                braf_obs = Observation(
                    id=generate_uuid(),
                    status="final",
                    subject=patient_ref,
                    code=_codeable_concept("http://loinc.org", "51971-4", display="BRAF gene mutation"),
                    encounter=encounter_ref,
                    valueString=value,
                )
                resources.append(braf_obs)

    # --- Medications ---
    for med in record.medications:
        concept = CodeableConcept(text=med.medicament)
        if med.atc_code:
            concept.coding = [_coding("http://www.whocc.no/atc", med.atc_code)]
        mstmt = MedicationStatement(
            id=generate_uuid(),
            status="unknown",
            subject=patient_ref,
            medication=CodeableReference(concept=concept),
        )
        mstmt.encounter = encounter_ref
        dosage_text = f"{med.doza or ''} {med.frecventa or ''} {med.durata or ''}".strip()
        if dosage_text:
            from fhir.resources.dosage import Dosage

            mstmt.dosage = [Dosage(text=dosage_text)]
        resources.append(mstmt)

    def add_procedure(proc: ProcedureEntry, historical: bool = False) -> Procedure:
        p = Procedure(
            id=generate_uuid(),
            status="completed",
            subject=patient_ref,
            encounter=encounter_ref if not historical else None,
            code=CodeableConcept(text=proc.name),
        )
        if proc.date:
            p.performedDateTime = proc.date
        if proc.body_site:
            site = _body_site_concept(proc.body_site)
            if site:
                p.bodySite = [site]
        if proc.performed_age:
            from fhir.resources.age import Age

            p.performedAge = Age(value=proc.performed_age)
        return p

    if record.epicriza:
        for proc in record.epicriza.procedures:
            resources.append(add_procedure(proc))

        for proc in record.epicriza.historical_procedures:
            resources.append(add_procedure(proc, historical=True))

        for imp in record.epicriza.implants:
            dev = Device(id=generate_uuid())
            dev.deviceName = [DeviceName(value=imp.name, type="user-friendly-name")]
            resources.append(dev)
            dus = DeviceUsage(
                id=generate_uuid(),
                status="active",
                patient=patient_ref,
                device=Reference(reference=f"Device/{dev.id}"),
            )
            if imp.body_site:
                site = _body_site_concept(imp.body_site)
                if site:
                    dus.bodySite = site
            resources.append(dus)

        for ae_text in record.epicriza.adverse_events:
            ae = AdverseEvent(
                id=generate_uuid(),
                status="completed",
                actuality="actual",
                subject=patient_ref,
                encounter=encounter_ref,
                code=CodeableConcept(text=ae_text),
            )
            resources.append(ae)

        for img in record.epicriza.imaging_results:
            dr = DiagnosticReport(
                id=generate_uuid(),
                status="final" if not img.is_current_visit else "preliminary",
                subject=patient_ref,
                code=CodeableConcept(text=img.modality),
                conclusion=img.conclusion,
            )
            if img.date:
                dr.effectiveDateTime = img.date
            if not img.is_current_visit:
                dr.encounter = None
            else:
                dr.encounter = encounter_ref
            resources.append(dr)

        for event in record.epicriza.history_timeline:
            event_type = (event.get("event_type") or "").lower()
            description = event.get("description") or ""
            onset = _parse_timeline_date(event.get("date"))
            if event_type == "diagnosis" and description:
                from app.models.internal import DiagnosticEntry

                cond = create_condition(
                    DiagnosticEntry(denumire=description),
                    clinical_code="inactive",
                    onset=onset,
                )
                resources.append(cond)
            elif event_type in ("surgery", "treatment", "procedure") and description:
                proc_entry = ProcedureEntry(name=description, date=onset)
                resources.append(add_procedure(proc_entry, historical=True))
            elif event_type == "imaging" and description:
                dr = DiagnosticReport(
                    id=generate_uuid(),
                    status="final",
                    subject=patient_ref,
                    code=CodeableConcept(text="Imaging"),
                    conclusion=description,
                )
                if onset:
                    dr.effectiveDateTime = onset
                resources.append(dr)

    # --- Transfusions (HP-14) ---
    for tx in record.transfusions:
        tx_proc = Procedure(
            id=generate_uuid(),
            status="completed",
            subject=patient_ref,
            encounter=encounter_ref,
            code=_codeable_concept(
                "http://snomed.info/sct",
                "116877001",
                display="Administration of blood product",
            ),
        )
        if tx.date:
            tx_proc.performedDateTime = tx.date
        resources.append(tx_proc)

    # --- Appointment + CarePlan (HP-09) ---
    if record.appointment and record.appointment.datetime_parsed:
        appt = Appointment(
            id=generate_uuid(),
            status="booked",
            start=record.appointment.datetime_parsed,
            participant=[
                {
                    "actor": patient_ref,
                    "status": "accepted",
                }
            ],
        )
        resources.append(appt)
        appt_ref = Reference(reference=f"Appointment/{appt.id}")

        care_plan = CarePlan(
            id=generate_uuid(),
            status="active",
            intent="plan",
            subject=patient_ref,
            encounter=encounter_ref,
            activity=[
                CarePlanActivity(
                    plannedActivityReference=appt_ref,
                )
            ],
        )
        resources.append(care_plan)

    return resources
