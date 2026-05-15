"""
Async FHIR terminology validation via public servers.

Strategy:
  1. Primary: local maps (cim10_to_snomed, loinc_map, atc_lookup) — fast, deterministic.
  2. Fallback: Snowstorm public SNOMED CT server (snowstorm.snomedtools.org, no auth).
     Used only when a code is NOT in the local map.
  3. All network calls are best-effort with a short timeout; failures are logged and
     the pipeline continues with DATA_ABSENT_CODING rather than hard-failing.

The LLM NEVER generates codes. This module validates codes extracted from source text
or resolves free-text clinical labels to SNOMED CT concepts.
"""

from typing import Optional

import httpx

from app.config import settings
from app.terminology.cim10_to_snomed import DATA_ABSENT_CODING, get_snomed_for_cim10
from app.utils.logger import get_logger

logger = get_logger()

_TIMEOUT = 5.0  # seconds — short so an unavailable server never blocks the pipeline


def _snowstorm() -> str:
    """Returns the configured Snowstorm FHIR base URL (no trailing slash)."""
    return settings.snowstorm_url.rstrip("/")


async def validate_snomed_code(code: str) -> bool:
    """Returns True if *code* is a valid active SNOMED CT concept per Snowstorm."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_snowstorm()}/CodeSystem/$validate-code",
                params={"system": "http://snomed.info/sct", "code": code},
            )
            if resp.status_code == 200:
                for param in resp.json().get("parameter", []):
                    if param.get("name") == "result":
                        return bool(param.get("valueBoolean", False))
    except Exception as exc:
        logger.warning(f"Snowstorm validate_snomed_code({code}) unavailable: {exc}")
    return False


async def search_snomed_concept(clinical_text: str) -> Optional[dict[str, str]]:
    """
    Search Snowstorm for the best SNOMED CT concept matching a clinical text description.
    Returns {"code": "...", "display": "..."} or None if not found / server unavailable.

    Call this only for diagnosis texts that have no local CIM-10 mapping.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_snowstorm()}/ValueSet/$expand",
                params={
                    "url": "http://snomed.info/sct?fhir_vs",
                    "filter": clinical_text,
                    "count": 1,
                },
            )
            if resp.status_code == 200:
                contains = resp.json().get("expansion", {}).get("contains", [])
                if contains:
                    best = contains[0]
                    return {"code": best.get("code"), "display": best.get("display")}
    except Exception as exc:
        logger.warning(f"Snowstorm search_snomed_concept('{clinical_text}') unavailable: {exc}")
    return None


async def resolve_diagnosis_to_snomed(
    diagnosis_text: str,
    cim10_code: Optional[str] = None,
) -> dict[str, str]:
    """
    Resolve a diagnosis to a SNOMED CT coding dict:
      {"system": "http://snomed.info/sct", "code": "...", "display": "..."}

    Resolution order:
      1. If cim10_code is given, look it up in the local CIM-10→SNOMED map.
      2. If not found locally, query Snowstorm with the diagnosis text.
      3. If Snowstorm is unavailable or returns nothing, return DATA_ABSENT_CODING.
    """
    # Step 1 — local map (fast, offline-capable)
    if cim10_code:
        local = get_snomed_for_cim10(cim10_code)
        if local:
            return {
                "system": "http://snomed.info/sct",
                "code": local["code"],
                "display": local["display"],
            }

    # Step 2 — Snowstorm fuzzy search on the clinical text label
    if diagnosis_text:
        remote = await search_snomed_concept(diagnosis_text)
        if remote and remote.get("code"):
            return {
                "system": "http://snomed.info/sct",
                "code": remote["code"],
                "display": remote["display"],
            }

    # Step 3 — graceful fallback
    return DATA_ABSENT_CODING
