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

def generate_uuid() -> str:
    return str(uuid.uuid4())

def assemble_bundle(resources: List[DomainResource], doc_type: DocumentType, medic_name: str | None = None) -> Bundle:
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
            
    # Create Composition
    composition = Composition(
        id=generate_uuid(),
        status="final",
        type=CodeableConcept(
            coding=[Coding(system="http://loinc.org", code="18842-5", display="Discharge Summary")]
        ),
        date=datetime.now(timezone.utc),
        title=f"Romanian Hospital Discharge Report - {doc_type.value}"
    )
    
    if patient_ref:
        composition.subject = patient_ref
    if encounter_ref:
        composition.encounter = encounter_ref
        
    # Author
    if medic_name:
        composition.author = [Reference(display=medic_name)]
    else:
        composition.author = [Reference(display="Unknown Physician")]
        
    # Build Bundle Entries
    entries = []
    
    # Composition must be first
    comp_entry = BundleEntry()
    comp_entry.fullUrl = f"urn:uuid:{composition.id}"
    comp_entry.resource = composition
    entries.append(comp_entry)
    
    for res in resources:
        entry = BundleEntry()
        entry.fullUrl = f"urn:uuid:{res.id}"
        entry.resource = res
        entries.append(entry)
        
    bundle.entry = entries
    
    return bundle
