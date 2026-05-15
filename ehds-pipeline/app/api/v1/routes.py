import tempfile
import traceback
import hashlib
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


async def process_file_pipeline(file: UploadFile) -> tuple:
    """
    Executes the extraction pipeline up to the merge_and_validate stage.
    Returns (MergedRecord, DocumentType, str)
    """
    logger.info(f"Received file upload: {file.filename}")

    suffix = Path(file.filename).suffix.lower() if file.filename else ".pdf"
    if not suffix:
        suffix = ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        logger.debug(f"Stage 0: Analyzing forensics for {tmp_path}")
        forensics = detect_file_type(tmp_path)
        logger.debug(
            f"Forensics: scanned={forensics.is_scanned}, acroform={forensics.has_acroform_widgets}"
        )

        logger.debug("Stage 1: Extracting text")
        text = extract_text(tmp_path, forensics)

        logger.debug("Stage 1b: Extracting checkboxes")
        raw_checkboxes = extract_checkboxes(tmp_path, text, forensics)

        logger.debug("Stage 4: LLM extraction (classify + all clinical fields)")
        doc_type, structured, labs, appointment, epicriza, medications, oncology, transfusions = (
            await extract_all(text)
        )

        logger.info(
            f"Stage 4 extracted — type: {doc_type.value}, patient: '{structured.nume}', "
            f"cnp: '{structured.cnp}', diagnosis: '{structured.diagnostic_principal}', "
            f"labs: {sum(len(d) for d in [labs.cbc, labs.biochemistry, labs.hormones, labs.other])} values, "
            f"meds: {len(medications)}, "
            f"epicriza_fields: motive={bool(epicriza.motive_internare)}, "
            f"narrative={bool(epicriza.current_treatment_narrative)}, "
            f"history={bool(epicriza.antecedente_personale)}"
        )
        logger.debug("Stage 4c: Mapping AcroForm checkboxes")
        admin_checkboxes = map_checkboxes(raw_checkboxes)

        logger.debug("Stage 5: Merging and validating record")
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

        logger.info(f"Pipeline processing complete. Confidence: {merged_record.overall_confidence:.2f}")
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
        if tmp_path.exists():
            logger.debug(f"Cleaning up temporary file {tmp_path}")
            tmp_path.unlink()


@router.post("/extract/primary")
async def extract_primary(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Pillar 1: Primary Use (Direct Care).
    Returns the full, non-anonymized FHIR Bundle.
    Uploads the bundle to the HAPI FHIR server in the background.
    """
    logger.info("Processing primary extraction request.")
    supported_exts = (".pdf", ".jpg", ".jpeg", ".png", ".docx")
    if not file.filename.lower().endswith(supported_exts):
        logger.warning(f"Invalid file upload attempted: {file.filename}")
        raise HTTPException(status_code=400, detail="Unsupported file format")

    merged_record, doc_type, file_hash = await process_file_pipeline(file)

    logger.debug("Stage 6: Building FHIR resources")
    fhir_resources = build_fhir_resources(merged_record)

    logger.debug("Stage 7: Assembling FHIR Bundle")
    medic_name = merged_record.structured.medic
    bundle = assemble_bundle(fhir_resources, doc_type, medic_name, file_hash)

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
    supported_exts = (".pdf", ".jpg", ".jpeg", ".png", ".docx")
    if not file.filename.lower().endswith(supported_exts):
        logger.warning(f"Invalid file upload attempted: {file.filename}")
        raise HTTPException(status_code=400, detail="Unsupported file format")

    merged_record, doc_type, file_hash = await process_file_pipeline(file)

    if merged_record.structured.cnp:
        if merged_record.structured.cnp.endswith("0000"):
            logger.warning(f"Patient {merged_record.structured.cnp} has opted out of secondary use.")
            raise HTTPException(status_code=403, detail="Patient opted out of secondary use.")

    logger.info("Stage 8: Anonymizing record for Pillar 2 compliance")
    anonymized_record = anonymize_record(merged_record)

    logger.debug("Stage 6: Building FHIR resources")
    fhir_resources = build_fhir_resources(anonymized_record)

    logger.debug("Stage 7: Assembling FHIR Bundle")
    medic_name = anonymized_record.structured.medic
    bundle = assemble_bundle(fhir_resources, doc_type, medic_name, file_hash)

    logger.info(
        f"Scheduling background upload of anonymized bundle to FHIR server: {settings.hapi_fhir_base_url}"
    )
    background_tasks.add_task(upload_to_fhir, bundle, settings.hapi_fhir_base_url)

    return bundle.model_dump(by_alias=True)
