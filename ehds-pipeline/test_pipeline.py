import asyncio
import os
from pathlib import Path
from app.pipeline.stage0_forensics import detect_file_type
from app.pipeline.stage1_extract import extract_text
from app.pipeline.stage1b_checkboxes import extract_checkboxes
from app.pipeline.stage2_classify import classify_document
from app.pipeline.stage3_zones import split_zones
from app.pipeline.stage4a_structured import extract_structured
from app.pipeline.stage5_merge import merge_and_validate
from app.pipeline.stage6_fhir import build_fhir_resources
from app.pipeline.stage7_bundle import assemble_bundle
import warnings
warnings.filterwarnings("ignore")

async def test_pipeline():
    input_dir = Path("/home/user/Projects/EHDS-Service/input_data")
    for file_path in input_dir.iterdir():
        if not file_path.is_file():
            continue
        print(f"\n--- Testing {file_path.name} ---")
        try:
            forensics = detect_file_type(file_path)
            print(f"Forensics: type={forensics.file_type}, scanned={forensics.is_scanned}")
            
            text = extract_text(file_path, forensics)
            print(f"Extracted {len(text)} characters of text.")
            
            doc_type = classify_document(text)
            print(f"Classified as: {doc_type.value}")
            
            zones = split_zones(text, doc_type)
            print(f"Split into {len(zones)} zones.")
            
            structured = extract_structured(zones, doc_type)
            print(f"Structured extraction done. Confidence: {structured.confidence_score}")
            
            # Create dummy record for fhir build testing
            merged_record = merge_and_validate(doc_type=doc_type, structured=structured)
            
            resources = build_fhir_resources(merged_record)
            print(f"Built {len(resources)} FHIR resources.")
            
            bundle = assemble_bundle(resources, doc_type, structured.medic)
            print(f"Successfully assembled FHIR Bundle with id {bundle.id}")
            
        except Exception as e:
            print(f"ERROR processing {file_path.name}: {e}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
