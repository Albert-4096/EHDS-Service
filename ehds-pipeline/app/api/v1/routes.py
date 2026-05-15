import asyncio
import tempfile
import traceback
import hashlib
import time
import magic
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.config import settings

from app.pipeline.stage0_forensics import detect_file_type
from app.pipeline.stage1_extract import extract_text
from app.pipeline.stage1b_checkboxes import extract_checkboxes
from app.pipeline.stage4_llm import extract_all
from app.pipeline.stage4c_checkboxgroups import map_checkboxes
from app.pipeline.stage5_merge import merge_and_validate
from app.pipeline.stage6_fhir import build_fhir_resources
from app.pipeline.stage7_bundle import assemble_bundle
from app.pipeline.stage8_anonymize import anonymize_record
from app.pipeline.stage9_upload import upload_to_fhir
from app.models.errors import CoreSetError
from app.services.llm_client import LLMParseError
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger()

_ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}
_MAX_FILE_SIZE_MB = 20


def _pseudo(value: str) -> str:
    """One-way pseudonym for log-safe PHI reference."""
    if not value:
        return "[absent]"
    return "pseudo:" + hashlib.sha256(value.encode()).hexdigest()[:8]


async def _validate_upload(file: UploadFile) -> bytes:
    """Read file once, enforce size limit and magic-byte MIME check."""
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {_MAX_FILE_SIZE_MB}MB limit")
    detected_mime = magic.from_buffer(content[:2048], mime=True)
    if detected_mime not in _ALLOWED_MIME_TYPES:
        logger.warning(f"Rejected upload '{file.filename}': detected MIME {detected_mime}")
        raise HTTPException(415, f"Unsupported file type: {detected_mime}")
    return content


async def process_file_pipeline(file: UploadFile, content: bytes) -> tuple:
    """
    Executes the extraction pipeline up to the merge_and_validate stage.
    Returns (MergedRecord, DocumentType, str)
    """
    logger.info(f"Received file upload: {file.filename}")

    suffix = Path(file.filename).suffix.lower() if file.filename else ".pdf"
    if not suffix:
        suffix = ".pdf"

    # Priority 2: initialize before try so finally can always reference it
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file_hash = hashlib.sha256(content).hexdigest()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        pipeline_start = time.perf_counter()

        logger.debug(f"Stage 0: Analyzing forensics for {tmp_path}")
        t = time.perf_counter()
        forensics = await asyncio.to_thread(detect_file_type, tmp_path)
        logger.info(f"Stage 0 (forensics): {time.perf_counter() - t:.2f}s | scanned={forensics.is_scanned}, acroform={forensics.has_acroform_widgets}")

        logger.debug("Stage 1: Extracting text")
        t = time.perf_counter()
        text = await asyncio.to_thread(extract_text, tmp_path, forensics)
        logger.info(f"Stage 1 (text extraction): {time.perf_counter() - t:.2f}s | {len(text)} chars")

        logger.debug("Stage 1b: Extracting checkboxes")
        t = time.perf_counter()
        raw_checkboxes = await asyncio.to_thread(extract_checkboxes, tmp_path, text, forensics)
        logger.info(f"Stage 1b (checkboxes): {time.perf_counter() - t:.2f}s | {len(raw_checkboxes)} found")

        logger.debug("Stage 4: LLM extraction (classify + all clinical fields)")
        t = time.perf_counter()
        doc_type, structured, labs, appointment, epicriza, medications, oncology, transfusions = (
            await extract_all(text)
        )
        logger.info(
            f"Stage 4 (LLM extraction): {time.perf_counter() - t:.2f}s | "
            f"type: {doc_type.value}, "
            f"patient_ref: {_pseudo(structured.nume)}, "
            f"cnp_ref: {_pseudo(structured.cnp)}, "
            f"has_diagnosis: {bool(structured.diagnostic_principal)}, "
            f"labs: {sum(len(d) for d in [labs.cbc, labs.biochemistry, labs.hormones, labs.other])} values, "
            f"meds: {len(medications)}"
        )

        logger.debug("Stage 4c: Mapping AcroForm checkboxes")
        t = time.perf_counter()
        admin_checkboxes = map_checkboxes(raw_checkboxes)
        logger.info(f"Stage 4c (checkbox mapping): {time.perf_counter() - t:.2f}s")

        logger.debug("Stage 5: Merging and validating record")
        t = time.perf_counter()
        merged_record = merge_and_validate(
            doc_type=doc_type,
            structured=structured,
            labs=labs,
            checkboxes=admin_checkboxes,
            appointment=appointment,
            epicriza=epicriza,
            medications=medications,
            oncology=oncology,
            transfusions=transfusions,
            epicriza_zone_text=text,
        )
        logger.info(f"Stage 5 (merge+validate): {time.perf_counter() - t:.2f}s | confidence={merged_record.overall_confidence:.2f}")

        logger.info(f"Pipeline (stages 0-5) complete in {time.perf_counter() - pipeline_start:.2f}s")
        return merged_record, doc_type, file_hash

    except CoreSetError as e:
        logger.warning(f"Core Set validation failed: {e.message}")
        raise HTTPException(status_code=422, detail=e.message)
    except LLMParseError as e:
        logger.error(f"LLM parse error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Priority 2: guaranteed deletion even on exception at any pipeline stage
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
            logger.debug(f"Source file deleted: {tmp_path.name}")


@router.post("/extract/primary")
async def extract_primary(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Pillar 1: Primary Use (Direct Care).
    Returns the full, non-anonymized FHIR Bundle.
    Uploads the bundle to the HAPI FHIR server in the background.
    """
    logger.info("Processing primary extraction request.")
    content = await _validate_upload(file)

    merged_record, doc_type, file_hash = await process_file_pipeline(file, content)

    request_start = time.perf_counter()

    logger.debug("Stage 6: Building FHIR resources")
    t = time.perf_counter()
    fhir_resources = build_fhir_resources(merged_record)
    logger.info(f"Stage 6 (FHIR resources): {time.perf_counter() - t:.2f}s")

    logger.debug("Stage 7: Assembling FHIR Bundle")
    t = time.perf_counter()
    medic_name = merged_record.structured.medic
    bundle = assemble_bundle(fhir_resources, doc_type, medic_name, file_hash)
    logger.info(f"Stage 7 (bundle assembly): {time.perf_counter() - t:.2f}s")

    logger.info(f"Stages 6-7 complete in {time.perf_counter() - request_start:.2f}s")
    logger.info(f"Scheduling background upload to FHIR server: {settings.hapi_fhir_base_url}")
    background_tasks.add_task(upload_to_fhir, bundle, settings.hapi_fhir_base_url)

    return bundle.model_dump(by_alias=True)


@router.post("/extract/secondary")
async def extract_secondary(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Pillar 2: Secondary Use (Research).
    Returns a heavily anonymized FHIR Bundle.
    Uploads the bundle to the HAPI FHIR server in the background.
    """
    logger.info("Processing secondary (anonymized) extraction request.")
    content = await _validate_upload(file)

    merged_record, doc_type, file_hash = await process_file_pipeline(file, content)

    if merged_record.structured.cnp:
        if merged_record.structured.cnp.endswith("0000"):
            logger.warning(f"Opt-out flag detected for cnp_ref: {_pseudo(merged_record.structured.cnp)}")
            raise HTTPException(status_code=403, detail="Patient opted out of secondary use.")

    request_start = time.perf_counter()

    logger.info("Stage 8: Anonymizing record for Pillar 2 compliance")
    t = time.perf_counter()
    anonymized_record = anonymize_record(merged_record)
    logger.info(f"Stage 8 (anonymize): {time.perf_counter() - t:.2f}s")

    logger.debug("Stage 6: Building FHIR resources")
    t = time.perf_counter()
    fhir_resources = build_fhir_resources(anonymized_record)
    logger.info(f"Stage 6 (FHIR resources): {time.perf_counter() - t:.2f}s")

    logger.debug("Stage 7: Assembling FHIR Bundle")
    t = time.perf_counter()
    medic_name = anonymized_record.structured.medic
    bundle = assemble_bundle(fhir_resources, doc_type, medic_name, file_hash)
    logger.info(f"Stage 7 (bundle assembly): {time.perf_counter() - t:.2f}s")

    logger.info(f"Stages 6-8 complete in {time.perf_counter() - request_start:.2f}s")
    logger.info(
        f"Scheduling background upload of anonymized bundle to FHIR server: {settings.hapi_fhir_base_url}"
    )
    background_tasks.add_task(upload_to_fhir, bundle, settings.hapi_fhir_base_url)

    return bundle.model_dump(by_alias=True)
