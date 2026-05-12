import httpx
from fhir.resources.bundle import Bundle

async def upload_to_fhir(bundle: Bundle, base_url: str) -> dict:
    """
    Uploads a FHIR Bundle to a FHIR server (e.g., HAPI FHIR).
    Sends an HTTP POST to the base URL as this is a transaction/batch bundle.
    """
    
    headers = {
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json"
    }
    
    # Dump model to JSON string, by_alias is needed for FHIR fields like class_fhir -> class
    payload = bundle.model_dump_json(by_alias=True)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            base_url,
            content=payload,
            headers=headers,
            timeout=30.0 # Bundles can take a bit to process
        )
        
        response.raise_for_status()
        
        # Return parsed JSON response from HAPI FHIR
        return response.json()
