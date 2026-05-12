import tempfile
import traceback
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.config import settings

from app.pipeline.stage0_forensics import detect_pdf_type
from app.pipeline.stage1_extract import extract_text
from app.pipeline.stage1b_checkboxes import extract_checkboxes
from app.pipeline.stage2_classify import classify_document, DocumentType
from app.pipeline.stage3_zones import split_zones
from app.pipeline.stage4a_structured import extract_structured
from app.pipeline.stage4b_labs import extract_labs
from app.pipeline.stage4c_checkboxgroups import map_checkboxes
from app.pipeline.stage4d_appointment import extract_appointment
from app.pipeline.stage4e_epicriza import extract_epicriza
from app.pipeline.stage4f_medications import extract_medications
from app.pipeline.stage4g_oncology import extract_oncology
from app.pipeline.stage5_merge import merge_and_validate
from app.pipeline.stage6_fhir import build_fhir_resources
from app.pipeline.stage7_bundle import assemble_bundle
from app.pipeline.stage8_anonymize import anonymize_record
from app.pipeline.stage9_upload import upload_to_fhir
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger()

async def process_pdf_pipeline(file: UploadFile) -> tuple:
    """
    Executes the extraction pipeline up to the merge_and_validate stage.
    Returns (MergedRecord, DocumentType)
    """
    # Create temporary file to store the uploaded PDF
    logger.info(f"Received file upload: {file.filename}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
        
    try:
        # Stage 0
        logger.debug(f"Stage 0: Analyzing forensics for {tmp_path}")
        forensics = detect_pdf_type(tmp_path)
        logger.debug(f"Forensics: scanned={forensics.is_scanned}, acroform={forensics.has_acroform_widgets}")
        
        # Stage 1 & 1b
        logger.debug("Stage 1: Extracting text")
        text = extract_text(tmp_path, forensics)
        logger.debug("Stage 1b: Extracting checkboxes")
        raw_checkboxes = extract_checkboxes(tmp_path, text, forensics)
        
        # Stage 2
        logger.debug("Stage 2: Classifying document")
        doc_type = classify_document(text)
        logger.info(f"Classified document as: {doc_type.value}")
        
        # Stage 3
        logger.debug("Stage 3: Splitting zones")
        zones = split_zones(text, doc_type)
        
        # Stage 4a
        logger.debug("Stage 4a: Extracting structured data")
        structured = extract_structured(zones, doc_type)
        
        # Stage 4b
        logger.debug("Stage 4b: Extracting labs")
        labs = extract_labs(zones.get("Investigatii efectuate", ""))
        
        # Stage 4c
        logger.debug("Stage 4c: Mapping checkboxes")
        admin_checkboxes = map_checkboxes(raw_checkboxes)
        
        # Stage 4d
        logger.debug("Stage 4d: Extracting appointments")
        appointment = extract_appointment(zones.get("APPOINTMENT_BLOCK", ""))
        
        # Stage 4e
        logger.debug("Stage 4e: Querying LLM for Epicriza")
        epicriza = await extract_epicriza(zones.get("Epicriza", ""), doc_type)
        
        # Stage 4f
        logger.debug("Stage 4f: Extracting medications")
        medications = extract_medications(zones.get("Tratament", ""))
        
        # Stage 4g
        logger.debug("Stage 4g: Extracting oncology fields")
        oncology = extract_oncology(zones, epicriza)
        
        # Stage 5
        logger.debug("Stage 5: Merging and validating record")
        merged_record = merge_and_validate(
            doc_type=doc_type,
            structured=structured,
            labs=labs,
            checkboxes=admin_checkboxes,
            appointment=appointment,
            epicriza=epicriza,
            medications=medications,
            oncology=oncology
        )
        
        logger.info(f"Pipeline processing complete. Confidence: {merged_record.overall_confidence:.2f}")
        return merged_record, doc_type
        
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
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
    if not file.filename.endswith(".pdf"):
        logger.warning(f"Invalid file upload attempted: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    merged_record, doc_type = await process_pdf_pipeline(file)
    
    # Stage 6
    logger.debug("Stage 6: Building FHIR resources")
    fhir_resources = build_fhir_resources(merged_record)
    
    # Stage 7
    logger.debug("Stage 7: Assembling FHIR Bundle")
    medic_name = merged_record.structured.medic
    bundle = assemble_bundle(fhir_resources, doc_type, medic_name)
    
    # Stage 9 (Upload in background)
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
    if not file.filename.endswith(".pdf"):
        logger.warning(f"Invalid file upload attempted: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    merged_record, doc_type = await process_pdf_pipeline(file)
    
    # Stage 8: Anonymize
    logger.info("Stage 8: Anonymizing record for Pillar 2 compliance")
    anonymized_record = anonymize_record(merged_record)
    
    # Stage 6
    logger.debug("Stage 6: Building FHIR resources")
    fhir_resources = build_fhir_resources(anonymized_record)
    
    # Stage 7
    logger.debug("Stage 7: Assembling FHIR Bundle")
    medic_name = anonymized_record.structured.medic
    bundle = assemble_bundle(fhir_resources, doc_type, medic_name)
    
    # Stage 9 (Upload in background)
    logger.info(f"Scheduling background upload of anonymized bundle to FHIR server: {settings.hapi_fhir_base_url}")
    background_tasks.add_task(upload_to_fhir, bundle, settings.hapi_fhir_base_url)
    
    return bundle.model_dump(by_alias=True)
