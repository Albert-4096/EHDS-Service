import uuid
from typing import List
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.composition import Composition
from fhir.resources.domainresource import DomainResource
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter
from fhir.resources.reference import Reference
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from datetime import datetime, timezone
from app.pipeline.stage2_classify import DocumentType
from app.pipeline.stage9_provenance import build_provenance

def generate_uuid() -> str:
    return str(uuid.uuid4())

def assemble_bundle(resources: List[DomainResource], doc_type: DocumentType, medic_name: str | None = None, file_hash: str | None = None) -> Bundle:
    """
    Assembles a FHIR Bundle of type 'document' (EEHRxF compliant).
    The first resource must be a Composition.
    """
    bundle = Bundle(type="document")
    
    # Extract key references
    patient_ref = None
    encounter_ref = None
    
    for res in resources:
        if isinstance(res, Patient):
            patient_ref = Reference(reference=f"Patient/{res.id}")
        elif isinstance(res, Encounter):
            encounter_ref = Reference(reference=f"Encounter/{res.id}")
            
    # Author (required in R5 – must be in constructor)
    author_ref = [Reference(display=medic_name)] if medic_name else [Reference(display="Unknown Physician")]

    # Create Composition
    loinc_code = "34105-7"
    loinc_display = "Hospital discharge summary"
    title_prefix = "Romanian Hospital Discharge Report"
    
    if doc_type == DocumentType.OUTPATIENT_MEDICAL_LETTER:
        loinc_code = "34133-9"
        loinc_display = "Summary of episode note"
        title_prefix = "Romanian Outpatient Medical Letter"

    composition = Composition(
        id=generate_uuid(),
        status="final",
        type=CodeableConcept(
            coding=[Coding(system="http://loinc.org", code=loinc_code, display=loinc_display)]
        ),
        date=datetime.now(timezone.utc),
        title=f"{title_prefix} - {doc_type.value}",
        author=author_ref,  # required in R5 constructor
    )

    if patient_ref:
        composition.subject = [patient_ref]  # R5: subject is now List[Reference]
    if encounter_ref:
        composition.encounter = encounter_ref

    # Build Bundle Entries
    entries = []
    
    # Composition must be first
    comp_entry = BundleEntry()
    comp_entry.fullUrl = f"urn:uuid:{composition.id}"
    comp_entry.resource = composition
    entries.append(comp_entry)
    
    # Append Provenance if file hash is provided
    if file_hash:
        prov = build_provenance(f"urn:uuid:{composition.id}", file_hash)
        prov_entry = BundleEntry()
        prov_entry.fullUrl = f"urn:uuid:{prov.id}"
        prov_entry.resource = prov
        entries.append(prov_entry)
        
    for res in resources:
        entry = BundleEntry()
        entry.fullUrl = f"urn:uuid:{res.id}"
        entry.resource = res
        entries.append(entry)
        
    bundle.entry = entries
    
    return bundle
