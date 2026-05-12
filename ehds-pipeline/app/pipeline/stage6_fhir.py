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
from datetime import datetime, timezone

from app.models.internal import MergedRecord, LabValue

def generate_uuid() -> str:
    return str(uuid.uuid4())

def build_fhir_resources(record: MergedRecord) -> List[DomainResource]:
    resources = []
    
    # 1. Patient
    patient = Patient(id=generate_uuid())
    if record.structured.cnp:
        patient.identifier = [
            Identifier(
                system="urn:oid:2.16.428.1.100.1.1.1",
                value=record.structured.cnp
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
    
    # 2. Encounter
    encounter = Encounter(id=generate_uuid(), status="finished", class_fhir={"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "inpatient encounter"})
    encounter.subject = patient_ref
    
    # Encounter Period
    if record.structured.data_internarii or record.structured.data_externarii:
        period = Period()
        if record.structured.data_internarii:
            # FHIR requires timezone-aware datetime for Period
            dt_in = record.structured.data_internarii
            period.start = dt_in
        if record.structured.data_externarii:
            dt_out = record.structured.data_externarii
            period.end = dt_out
        encounter.period = period
        
    resources.append(encounter)
    encounter_ref = Reference(reference=f"Encounter/{encounter.id}")
    
    # 3. Conditions
    def create_condition(diag, rank=1):
        cond = Condition(id=generate_uuid(), subject=patient_ref, encounter=encounter_ref)
        cond.clinicalStatus = CodeableConcept(coding=[Coding(system="http://terminology.hl7.org/CodeSystem/condition-clinical", code="active")])
        code_concept = CodeableConcept(text=diag.denumire)
        if diag.cod_cim10:
            code_concept.coding = [Coding(system="http://hl7.org/fhir/sid/icd-10", code=diag.cod_cim10)]
        cond.code = code_concept
        return cond

    if record.structured.diagnostic_principal:
        cond_primary = create_condition(record.structured.diagnostic_principal)
        cond_primary.category = [CodeableConcept(coding=[Coding(system="http://terminology.hl7.org/CodeSystem/condition-category", code="encounter-diagnosis")])]
        resources.append(cond_primary)
        
    for diag in record.structured.diagnostice_secundare:
        cond_sec = create_condition(diag)
        resources.append(cond_sec)
        
    # 4. Observation (Labs)
    if record.labs:
        def create_lab_obs(lab: LabValue, category_code: str):
            obs = Observation(id=generate_uuid(), status="final", subject=patient_ref, encounter=encounter_ref)
            obs.category = [CodeableConcept(coding=[Coding(system="http://terminology.hl7.org/CodeSystem/observation-category", code=category_code)])]
            
            code_concept = CodeableConcept(text=lab.test_name)
            if lab.loinc_code:
                code_concept.coding = [Coding(system="http://loinc.org", code=lab.loinc_code)]
            obs.code = code_concept
            
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

        # Iterate all panels
        for _, lab in record.labs.cbc.items():
            resources.append(create_lab_obs(lab, "laboratory"))
        for _, lab in record.labs.biochemistry.items():
            resources.append(create_lab_obs(lab, "laboratory"))
        for _, lab in record.labs.hormones.items():
            resources.append(create_lab_obs(lab, "laboratory"))
        for _, lab in record.labs.other.items():
            resources.append(create_lab_obs(lab, "laboratory"))
            
    # 5. Observation (TNM)
    if record.oncology and record.oncology.tnm:
        tnm = record.oncology.tnm
        obs = Observation(id=generate_uuid(), status="final", subject=patient_ref, encounter=encounter_ref)
        # Stage group LOINC is 21908-9
        obs.code = CodeableConcept(coding=[Coding(system="http://loinc.org", code="21908-9", display="Stage group.clinical Cancer")])
        if tnm.stage_group:
            obs.valueString = tnm.stage_group
        resources.append(obs)
        
    # 6. MedicationStatement
    for med in record.medications:
        mstmt = MedicationStatement(id=generate_uuid(), status="active", subject=patient_ref, context=encounter_ref)
        
        code_concept = CodeableConcept(text=med.medicament)
        if med.atc_code:
            code_concept.coding = [Coding(system="http://www.whocc.no/atc", code=med.atc_code)]
        mstmt.medicationCodeableConcept = code_concept
        
        # We can add dosage information as text for simplicity
        dosage_text = f"{med.doza or ''} {med.frecventa or ''} {med.durata or ''}".strip()
        if dosage_text:
            from fhir.resources.dosage import Dosage
            mstmt.dosage = [Dosage(text=dosage_text)]
            
        resources.append(mstmt)

    return resources
