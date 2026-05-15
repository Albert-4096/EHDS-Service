import uuid
from datetime import datetime, timezone
from fhir.resources.provenance import Provenance, ProvenanceAgent, ProvenanceEntity
from fhir.resources.reference import Reference
from fhir.resources.coding import Coding
from fhir.resources.codeableconcept import CodeableConcept

def generate_uuid() -> str:
    return str(uuid.uuid4())

def build_provenance(composition_ref: str, file_hash: str, ai_model_version: str = "Gemini-3.1-Pro") -> Provenance:
    """
    EEHRxF Provenance Requirement:
    Every Bundle MUST have a 'Provenance' resource with a SHA-256 hash of the source PDF
    and the AI model version used, linked to the Composition.
    """
    # Identify the AI Model
    agent = ProvenanceAgent(
        type=CodeableConcept(
            coding=[Coding(system="http://terminology.hl7.org/CodeSystem/provenance-participant-type", code="assembler")]
        ),
        who=Reference(display=f"EHDS Pipeline AI: {ai_model_version}")
    )
    
    # Store the file hash
    entity = ProvenanceEntity(
        role="source",
        what=Reference(display=f"Source Document SHA-256: {file_hash}")
    )

    prov = Provenance(
        id=generate_uuid(),
        target=[Reference(reference=composition_ref)],
        recorded=datetime.now(timezone.utc),
        agent=[agent],
        entity=[entity]
    )
    
    return prov
