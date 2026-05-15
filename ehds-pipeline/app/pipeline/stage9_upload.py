import httpx
from fhir.resources.bundle import Bundle
from app.utils.logger import get_logger

logger = get_logger()


async def upload_to_fhir(bundle: Bundle, base_url: str) -> dict:
    """
    Uploads all resources from a FHIR document Bundle to a FHIR server
    by PUTting each resource individually to its typed endpoint.

    HAPI FHIR (R4 mode) rejects Bundle.type=document via the transaction
    endpoint (HAPI-0527). Instead, we extract each entry and PUT it directly
    at  PUT /fhir/{ResourceType}/{id}  which is always supported.
    """
    headers = {
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    results = []
    errors = []

    # Resource upload priority to resolve dependencies (e.g., Patient before Composition)
    PRIORITY = {
        "Patient": 0,
        "Practitioner": 1,
        "Organization": 1,
        "Location": 1,
        "Encounter": 2,
        "Condition": 3,
        "Procedure": 3,
        "MedicationRequest": 3,
        "Medication": 3,
        "Observation": 3,
        "DiagnosticReport": 3,
        "Composition": 10,
        "Provenance": 20,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        if not bundle.entry:
            logger.warning("Bundle has no entries – nothing to upload.")
            return {"uploaded": 0, "errors": []}

        # Sort entries by priority (default 5 for unknown types)
        sorted_entries = sorted(
            bundle.entry,
            key=lambda e: PRIORITY.get(e.resource.get_resource_type(), 5) if e.resource else 99
        )

        for entry in sorted_entries:
            resource = entry.resource
            if resource is None:
                continue

            resource_type = resource.get_resource_type()
            resource_id = resource.id

            if not resource_id:
                logger.warning(f"Skipping {resource_type} with no id.")
                continue

            url = f"{base_url.rstrip('/')}/{resource_type}/{resource_id}"
            payload = resource.model_dump_json(by_alias=True)

            try:
                response = await client.put(url, content=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Uploaded {resource_type}/{resource_id} → {response.status_code}")
                results.append({"resource": f"{resource_type}/{resource_id}", "status": response.status_code})
            except httpx.HTTPStatusError as exc:
                msg = f"Failed to upload {resource_type}/{resource_id}: {exc.response.status_code} {exc.response.text[:200]}"
                logger.error(msg)
                errors.append(msg)
            except httpx.RequestError as exc:
                msg = f"Network error uploading {resource_type}/{resource_id}: {exc}"
                logger.error(msg)
                errors.append(msg)

    logger.info(f"FHIR upload complete: {len(results)} succeeded, {len(errors)} failed.")
    return {"uploaded": len(results), "errors": errors}
