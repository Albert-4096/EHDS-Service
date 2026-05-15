## SECTION 1 — Pipeline Architecture: How It Actually Works

The data flow from `POST /extract/primary` (or `/secondary`) in `app/api/v1/routes.py` to the FHIR server operates as follows:

- **Input**: A file (`UploadFile`) which is saved to a temporary location.
- **Stage 0 (`detect_file_type`)**: Receives the file path. Detects if it's scanned (density heuristic) and if it has AcroForm widgets. Outputs `DocumentForensics`.
- **Stage 1 (`extract_text`)**: Receives the file path and forensics. Uses `pdfplumber`, `pytesseract`, or `docx` to extract raw text, applying basic cleaning (page joining, header stripping). Outputs a `str`.
- **Stage 1B (`extract_checkboxes`)**: Receives the raw text and forensics. Extracts raw checkbox markers. Outputs `list[CheckboxGroup]`. **Note: This occurs *before* classification, violating the pipeline architecture.**
- **Stage 2 (`classify_document`)**: Receives the raw text. Classifies the document based on the first 30 lines. Outputs a `DocumentType` enum. 
- **Stage 3 (`split_zones`)**: Receives text and doc type. Uses regex anchors to slice text into sections. Outputs `dict[str, str]` (zone name to text).
- **Stage 4A–4G (Parallel/Sequential Extraction)**:
  - **4A**: Receives zones. Extracts demographics via regex heuristics. Outputs `StructuredFields`.
  - **4B**: Receives "Investigatii efectuate" zone. Extracts lab panels. Outputs `LabResults`.
  - **4C**: Receives Stage 1B's raw checkboxes. Semantically maps them to `AdminCheckboxes`.
  - **4D**: Receives "APPOINTMENT_BLOCK" zone. Extracts appointment times. Outputs `AppointmentBlock`.
  - **4E**: Receives "Epicriza" zone. Sends it to an LLM for structured extraction. Outputs `EpicrizaExtracted`.
  - **4F**: Receives "Tratament" zone. Uses regex heuristics to extract drug names and doses. Outputs `list[MedicationEntry]`.
  - **4G**: Receives all zones and Stage 4E's output. Extracts TNM, ECOG, cycle tracking. Outputs `OncologyFields`.
- **Stage 5 (`merge_and_validate`)**: Receives outputs from all Stage 4s. Validates age vs CNP, computes a confidence score, but does *not* enforce blocking errors. Outputs `MergedRecord`.
- **Stage 6 (`build_fhir_resources`)**: Receives `MergedRecord`. Maps fields to a flat list of `fhir.resources` models. Outputs `list[DomainResource]`.
- **Stage 7 (`assemble_bundle`)**: Receives the list of resources, doc type, and file hash. Wraps them in a `Bundle` with a `Composition` at Entry 0, and natively calls `stage9_provenance.py` to build the `Provenance` resource. Outputs a FHIR `Bundle`.
- **Stage 8 (`anonymize_record`)**: (Only on `/extract/secondary`). Receives `MergedRecord` and applies PII scrubbing, time-shifting, and K-Anonymity generalization. Outputs a scrubbed `MergedRecord`.
- **Stage 9 (`upload_to_fhir`)**: Receives the FHIR `Bundle` and base URL. Deconstructs the Bundle into individual `PUT` requests based on a hardcoded dependency priority list. Runs asynchronously in the background.

**Linear Chain**:
`[Stage 0] → [Stage 1] → [Stage 1B] → [Stage 2] → [Stage 3] → [Stages 4A-4G] → [Stage 5] → [Stage 8 (Optional)] → [Stage 6] → [Stage 7 (Includes Stage 9 Provenance)] → [Stage 9 Upload]`

**Wiring/Call Chain Gaps**:
- Stage 1B (`stage1b_checkboxes.py`) is explicitly executed before Stage 2 classification (`app/api/v1/routes.py:58`), which violates the architecture rules.
- The outputs of Stage 4D (`AppointmentBlock`) and parts of Stage 4E (e.g., `imaging_results`, `history_timeline`) are completely ignored in Stage 6 (`stage6_fhir.py`), effectively blackholing the data before it reaches FHIR.

---

## SECTION 2 — Hard Problems: Implementation Status

| HP | Name | Status | Evidence |
|----|------|--------|----------|
| HP-01 | Checkbox State Extraction | ⚠️ Partial | `app/pipeline/stage1b_checkboxes.py:64` |
| HP-02 | Multi-Column Demographics Table | ❌ Missing | `app/pipeline/stage4a_structured.py:29` |
| HP-03 | Superscript Loss in Lab Values | ✅ Implemented | `app/pipeline/stage4b_labs.py:26` |
| HP-04 | Asterisk-Flagged Lab Values | ⚠️ Partial | `app/pipeline/stage6_fhir.py:186` |
| HP-05 | Lab Panel Boundary Detection | ⚠️ Partial | `app/pipeline/stage4b_labs.py:146` |
| HP-06 | Date Format Heterogeneity | ⚠️ Partial | `app/utils/date_parser.py:35` |
| HP-07 | Multi-Page Epicriza | ⚠️ Partial | `app/utils/text_clean.py:16` |
| HP-08 | Dual Identifier on Same Line | ⚠️ Partial | `app/pipeline/stage6_fhir.py:93` |
| HP-09 | Appointment Block Extraction | ⚠️ Partial | `app/pipeline/stage6_fhir.py` |
| HP-10 | Oncology-Specific Fields | ⚠️ Partial | `app/pipeline/stage6_fhir.py:228` |
| HP-11 | TNM Staging Notation Parsing | ⚠️ Partial | `app/pipeline/stage6_fhir.py:230` |
| HP-12 | Longitudinal History in Epicriza | ⚠️ Partial | `app/pipeline/stage6_fhir.py:124` |
| HP-13 | Blank/Redacted Mandatory Fields | ⚠️ Partial | `app/pipeline/stage5_merge.py:26` |
| HP-14 | Blood Transfusion Table | ❌ Missing | No implementation in pipeline |
| HP-15 | Document-Type-Specific LOINC Code | ✅ Implemented | `app/pipeline/stage7_bundle.py:39` |
| HP-16 | Romanian Decimal Comma | ✅ Implemented | `app/utils/numeric.py:7` |
| HP-17 | Same-Day Encounter | ❌ Missing | `app/pipeline/stage6_fhir.py:95` |
| HP-18 | Imaging Result Extraction | ⚠️ Partial | `app/pipeline/stage6_fhir.py` |

**Gap Explanations**:
- **HP-01**: `_extract_acroform` is explicitly mocked with a `[AcroForm]` placeholder and no real widget state reading.
- **HP-02**: Entirely missing. Uses naive regexes on concatenated header text instead of bounding-box/tabular layout analysis.
- **HP-04**: Asterisks are detected, but the `Observation.interpretation = "A"` is never applied during FHIR generation in `stage6_fhir.py`.
- **HP-05**: Does not handle hormone sections as a distinct boundary, lumping remaining data into biochem/other.
- **HP-06**: Fails to implement all 7 formats (only supports 4 specific regexes).
- **HP-07**: `strip_repeated_headers` uses exact literal replacement instead of handling page artifacts like "2 / 3".
- **HP-08**: Contract and FO numbers are extracted in Stage 4A, but `stage6_fhir.py` completely ignores them when building the `Encounter`.
- **HP-09**: Extraction works, but `Appointment` and `CarePlan` resources are completely omitted from `stage6_fhir.py`.
- **HP-10/HP-11**: Ciclul, Acronim, ECOG, and individual T/N/M markers are extracted in Stage 4G, but ignored in Stage 6 (which only outputs the overall stage group).
- **HP-12**: Current/Historical split is prompted, but `stage6_fhir.py` throws all extracted conditions into the same active `Condition` pool and discards the `history_timeline`.
- **HP-13**: Missing fields do not raise `CoreSetError` blockades, and missing Medic does not result in a properly shaped `DataAbsentReason` Practitioner.
- **HP-14**: No file exists to handle the "Grupa sange | RH..." table extraction.
- **HP-17**: `Encounter.class` is hardcoded to `IMP` vs `AMB` based purely on `doc_type`, blatantly ignoring the <24h duration calculation logic.
- **HP-18**: Imaging results are parsed by Claude but entirely ignored in `stage6_fhir.py` (no `DiagnosticReport` created).

---

## SECTION 3 — Absolute Rules: Compliance Check

- **R1 (No Hallucination)**: **Violated.** `app/pipeline/stage4e_epicriza.py:57`. The prompt does not match CONTEXT.md verbatim, and the Pydantic JSON schema has been significantly modified (e.g., adding `implants` and `adverse_events` to the root `CurrentVisitSchema` instead of inside `procedures` as `implants_inserted`/`removed`).
- **R2 (CodeableConcept Integrity)**: **Violated.** `app/pipeline/stage6_fhir.py:278`. `p.bodySite = [CodeableConcept(text=proc.body_site)]` uses raw strings without SNOMED CT codings.
- **R3 (Temporal Precision)**: **Violated.** `app/utils/date_parser.py:35`. While `Europe/Bucharest` is applied, the parser lacks the 7 date formats required by HP-06.
- **R4 (UUID per Resource)**: **Upheld.** `app/pipeline/stage6_fhir.py:25`.
- **R5 (No Custom Extensions)**: **Upheld.** Only standard HL7 extensions are visible.
- **R6 (CIM-10 Dual Coding)**: **Upheld.** `app/pipeline/stage6_fhir.py:133` adds both SNOMED and ICD-10 codings to `Condition`.
- **R7 (Core Set Gate)**: **Violated.** `app/pipeline/stage5_merge.py:26`. `CoreSetError` is never raised for missing Patient, missing admission dates, or missing narratives. It merely logs warnings and calculates a confidence score.
- **R8 (Document Classification First)**: **Violated.** `app/api/v1/routes.py:58`. `extract_checkboxes` is explicitly called *before* `classify_document`.
- **R9 (Never Hardcode Clinical Values)**: **Violated.** `app/terminology/mappings.py:23`. `RARE_DIAGNOSES` hardcodes a static mock list of clinical codes to generalize.

---

## SECTION 4 — FHIR Resource Coverage

### 4A — Core Set (blocking if absent):
| Resource | Builder function exists? | Actually populated? | Gaps |
|----------|--------------------------|---------------------|------|
| Composition | Yes | Yes | `Composition.section.text

[ignoring loop detection]

## SECTION 1 — Pipeline Architecture: How It Actually Works

The data flow from `POST /extract/primary` (or `/secondary`) in `app/api/v1/routes.py` to the FHIR server operates as follows:

- **Input**: A file (`UploadFile`) is saved to a temporary location.
- **Stage 0 (`detect_file_type`)**: Receives the file path. Detects if it's scanned (density heuristic) and if it has AcroForm widgets. Outputs `DocumentForensics`.
- **Stage 1 (`extract_text`)**: Receives the file path and forensics. Uses `pdfplumber`, `pytesseract`, or `docx` to extract raw text, applying basic cleaning (page joining, header stripping). Outputs a `str`.
- **Stage 1B (`extract_checkboxes`)**: Receives the raw text and forensics. Extracts raw checkbox markers. Outputs `list[CheckboxGroup]`. **CRITICAL GAP: This occurs *before* classification (`stage2_classify.py`), explicitly violating Rule R8.**
- **Stage 2 (`classify_document`)**: Receives the raw text. Classifies the document based on the first 30 lines. Outputs a `DocumentType` enum. 
- **Stage 3 (`split_zones`)**: Receives text and doc type. Uses regex anchors to slice text into sections. Outputs `dict[str, str]` (zone name to text).
- **Stage 4A–4G (Parallel/Sequential Extraction)**:
  - **4A**: Receives zones. Extracts demographics via regex heuristics. Outputs `StructuredFields`.
  - **4B**: Receives "Investigatii efectuate" zone. Extracts lab panels. Outputs `LabResults`.
  - **4C**: Receives Stage 1B's raw checkboxes. Semantically maps them to `AdminCheckboxes`.
  - **4D**: Receives "APPOINTMENT_BLOCK" zone. Extracts appointment times. Outputs `AppointmentBlock`.
  - **4E**: Receives "Epicriza" zone. Sends it to an LLM for structured extraction. Outputs `EpicrizaExtracted`.
  - **4F**: Receives "Tratament" zone. Uses regex heuristics to extract drug names and doses. Outputs `list[MedicationEntry]`.
  - **4G**: Receives all zones and Stage 4E's output. Extracts TNM, ECOG, cycle tracking. Outputs `OncologyFields`.
- **Stage 5 (`merge_and_validate`)**: Receives outputs from all Stage 4s. Validates age vs CNP, computes a confidence score, but does *not* enforce blocking errors. Outputs `MergedRecord`.
- **Stage 8 (`anonymize_record`)**: (Only on `/extract/secondary`). Receives `MergedRecord` and applies PII scrubbing, time-shifting, and K-Anonymity generalization. Outputs a scrubbed `MergedRecord`.
- **Stage 6 (`build_fhir_resources`)**: Receives `MergedRecord`. Maps fields to a flat list of `fhir.resources` models. Outputs `list[DomainResource]`.
- **Stage 7 (`assemble_bundle`)**: Receives the list of resources, doc type, and file hash. Wraps them in a `Bundle` with a `Composition` at Entry 0, and natively calls `stage9_provenance.py` to build the `Provenance` resource. Outputs a FHIR `Bundle`.
- **Stage 9 (`upload_to_fhir`)**: Receives the FHIR `Bundle` and base URL. Deconstructs the Bundle into individual `PUT` requests based on a hardcoded priority list. Runs asynchronously.

**Wiring/Call Chain Gaps**:
- `Stage 1B` is wired incorrectly before `Stage 2`, violating the architecture.
- Outputs from `Stage 4D` (`AppointmentBlock`) and `Stage 4E` (`imaging_results`, `history_timeline`) are completely ignored by `Stage 6`, meaning they never make it into the FHIR output.

---

## SECTION 2 — Hard Problems: Implementation Status

| HP | Name | Status | Evidence |
|----|------|--------|----------|
| HP-01 | Checkbox State Extraction | ⚠️ Partial | `app/pipeline/stage1b_checkboxes.py:64` |
| HP-02 | Multi-Column Demographics Table | ❌ Missing | `app/pipeline/stage4a_structured.py:29` |
| HP-03 | Superscript Loss in Lab Values | ✅ Implemented | `app/pipeline/stage4b_labs.py:26` |
| HP-04 | Asterisk-Flagged Lab Values | ⚠️ Partial | `app/pipeline/stage6_fhir.py:186` |
| HP-05 | Lab Panel Boundary Detection | ⚠️ Partial | `app/pipeline/stage4b_labs.py:146` |
| HP-06 | Date Format Heterogeneity | ⚠️ Partial | `app/utils/date_parser.py:35` |
| HP-07 | Multi-Page Epicriza | ⚠️ Partial | `app/utils/text_clean.py:16` |
| HP-08 | Dual Identifier on Same Line | ⚠️ Partial | `app/pipeline/stage6_fhir.py:93` |
| HP-09 | Appointment Block Extraction | ⚠️ Partial | `app/pipeline/stage6_fhir.py` |
| HP-10 | Oncology-Specific Fields | ⚠️ Partial | `app/pipeline/stage6_fhir.py:228` |
| HP-11 | TNM Staging Notation Parsing | ⚠️ Partial | `app/pipeline/stage6_fhir.py:230` |
| HP-12 | Longitudinal History in Epicriza | ⚠️ Partial | `app/pipeline/stage6_fhir.py:124` |
| HP-13 | Blank/Redacted Mandatory Fields | ⚠️ Partial | `app/pipeline/stage5_merge.py:26` |
| HP-14 | Blood Transfusion Table | ❌ Missing | No implementation in codebase |
| HP-15 | Document-Type-Specific LOINC Code | ✅ Implemented | `app/pipeline/stage7_bundle.py:39` |
| HP-16 | Romanian Decimal Comma | ✅ Implemented | `app/utils/numeric.py:7` |
| HP-17 | Same-Day Encounter | ❌ Missing | `app/pipeline/stage6_fhir.py:95` |
| HP-18 | Imaging Result Extraction | ⚠️ Partial | `app/pipeline/stage6_fhir.py` |

**Gap Explanations**:
- **HP-01**: `_extract_acroform` is an explicitly mocked placeholder returning `[AcroForm]`.
- **HP-02**: Completely missing. It uses concatenated regex matching across all header strings instead of layout analysis or table extraction.
- **HP-04**: Asterisks are detected, but `Observation.interpretation = "A"` is completely missing in `stage6_fhir.py`.
- **HP-05**: Fails to separate the `hormones` sub-panel, placing everything else into `biochemistry` or `other`.
- **HP-06**: Fails to implement all 7 formats. It lacks support for formats without times if they don't exactly match the 4 regexes provided.
- **HP-07**: Uses literal exact match string replacement (`strip_repeated_headers`) which breaks on page numbers ("2 / 3"). Does not strip page break artifacts *inside* the Epicriza before LLM submission.
- **HP-08**: Contract and FO numbers are extracted in Stage 4A, but `stage6_fhir.py` ignores them and only builds an Identifier for the CNP.
- **HP-09**: Appointment is extracted successfully but the resulting `CarePlan` and `Appointment` resources are not built in `stage6_fhir.py`.
- **HP-10/11**: Staging data is extracted, but only the overall Stage Group is mapped in `stage6_fhir.py`. Individual T, N, and M components are ignored.
- **HP-12**: The LLM extracts the `history_timeline`, but `stage6_fhir.py` discards it entirely and does not create historical `Condition` or `Procedure` resources.
- **HP-13**: Does not raise `CoreSetError` for missing mandatory fields; it only appends to `parsing_warnings`.
- **HP-14**: The table extraction for blood transfusions does not exist anywhere.
- **HP-17**: `Encounter.class` is hardcoded to `IMP` for DOC_HDR, entirely ignoring the <24hr duration calculation logic required for `AMB`.
- **HP-18**: Imaging is parsed by the LLM, but `stage6_fhir.py` does not output any `DiagnosticReport` resources.

---

## SECTION 3 — Absolute Rules: Compliance Check

- **R1 (No Hallucination)**: **Violated.** `app/pipeline/stage4e_epicriza.py:57`. The system prompt and JSON schema do not match `CONTEXT.md`. The schema diverges heavily (adds `implants`, `adverse_events` at the root, missing `performed_age`).
- **R2 (CodeableConcept Integrity)**: **Violated.** `app/pipeline/stage6_fhir.py:278`. `p.bodySite = [CodeableConcept(text=proc.body_site)]` assigns a raw string without a proper code system.
- **R3 (Temporal Precision)**: **Violated.** `app/utils/date_parser.py`. Fails to support all 7 Romanian date formats.
- **R4 (UUID per Resource)**: **Upheld.** `app/pipeline/stage6_fhir.py:25`.
- **R5 (No Custom Extensions)**: **Upheld.** 
- **R6 (CIM-10 Dual Coding)**: **Upheld.** `app/pipeline/stage6_fhir.py:133`. SNOMED and ICD-10 are combined in the same CodeableConcept.
- **R7 (Core Set Gate)**: **Violated.** `app/pipeline/stage5_merge.py:26`. Missing blocking fields do not raise `CoreSetError` and do not stop pipeline execution.
- **R8 (Document Classification First)**: **Violated.** `app/api/v1/routes.py:58`. `extract_checkboxes` happens prior to classification.
- **R9 (Never Hardcode Clinical Values)**: **Violated.** `app/terminology/mappings.py:23`. Contains a hardcoded mock list of "rare diagnoses" (`RARE_DIAGNOSES = {"Q87.4", "7488008"}`).

---

## SECTION 4 — FHIR Resource Coverage

### 4A — Core Set (blocking if absent):
| Resource | Builder function exists? | Actually populated? | Gaps |
|----------|--------------------------|---------------------|------|
| Composition | Yes | Yes | `Composition.section.text` is missing entirely (a mandatory narrative block). |
| Patient | Yes | Yes | Missing `DataAbsentReason` extension if name is missing. |
| Practitioner | No | No | Completely omitted from `stage6_fhir.py`. |
| PractitionerRole | No | No | Completely omitted from `stage6_fhir.py`. |
| Encounter | Yes | Yes | Missing `class` calculation based on stay duration. |
| Condition | Yes | Yes | Historical diagnoses and `history_timeline` are ignored. |

### 4B — Extended + Previously-Omitted Mandatory Resources:
| Resource | Required by | Builder exists? | Populated? | Gaps |
|----------|-------------|-----------------|------------|------|
| Procedure | CONTEXT.md §3 | Yes | Yes | Historical procedures from `history_timeline` are ignored. |
| Device | CONTEXT.md §3 | Yes | Yes | SNOMED CT coding missing. |
| DeviceUseStatement | CONTEXT.md §3 | Yes | Yes | SNOMED CT coding missing. |
| AdverseEvent | CONTEXT.md §3 | Yes | Yes | Causal reference to Medication/Procedure/Device is missing. |
| Provenance | CONTEXT.md §3 | Yes | Yes | `Composition.attester` is not populated. |
| MedicationRequest | CONTEXT.md §3 | No | No | Code uses `MedicationStatement` instead of `MedicationRequest`. |
| Observation (labs) | LOINC | Yes | Yes | Missing interpretations for unflagged/flagged. |
| Observation (vitals) | LOINC | No | No | Missing entirely. |
| Observation (ECOG, TNM) | LOINC | Yes | Partial | Maps Stage Group, ignores individual T, N, M components. |
| DiagnosticReport | HP-18 | No | No | Extracted by LLM but dropped. |
| CarePlan | HP-09 | No | No | Extracted by regex but dropped. |
| Appointment | HP-09 | No | No | Extracted by regex but dropped. |
| AllergyIntolerance | CONTEXT.md | No | No | Handled as text in `StructuredFields` but dropped in FHIR builder. |

---

## SECTION 5 — Terminology Bindings: Coverage and Accuracy

### 5A — loinc_map.py
- **Missing**: MCV (787-2), MCH (785-6), MCHC (786-4), PLT (777-3), Neutrofile% (770-8), Limfocite% (736-9), MPV (32623-1). Cancer response (88040-1).
- **Present**: WBC, RBC, HGB, HCT, RDW-CV, Bilirubina, Calciu, Creatinina, FA, Glicemie, K, Na, TGO, TGP, TSH, FT4, Cortizol, DHEA-S, ECOG.

### 5B — atc_lookup.py
- **Missing**: Fraxiparine (B01AB05), Fosamax (M05BA04).
- **Present**: Nivolumab, Ipilimumab, IFN alfa, Aspirina, Atorvastatin, Bisoprolol, Metformin, Furosemid, Omeprazol, Levotiroxina, Enoxaparin, Heparina, Clopidogrel.

### 5C — cim10_to_snomed.py
- **Missing**: The file `app/terminology/cim10_to_snomed.py` DOES NOT EXIST. The code uses a mocked dictionary in `app/terminology/mappings.py`.
- **Accuracy**: It only maps 4 codes (I21.4, C34.9, E11.9, Q87.4) instead of the required 50. It does not return `DataAbsentCoding` on failure.

### 5D — oncology_terms.py
- **Present**: Contains the regimen acronym dictionary, response status mapping, and TNM prefix meanings as specified.

### 5E — UCUM Unit Normalization
- **Violated**: `app/pipeline/stage4b_labs.py:10` uses `× 10^9/L` instead of properly mapping superscript `109/L`. The prompt requires fixing the superscript, but the current `UCUM_MAPPING` does not normalize to standard UCUM string formats properly for previously dropped superscripts without `x 10^`.

---

## SECTION 6 — Mock Data and Stubs: Complete Inventory

| File | Line(s) | Type | Description | What must replace it |
|------|---------|------|-------------|----------------------|
| `app/api/v1/routes.py` | 170 | Mock Logic | Checks if CNP ends with "0000" for Opt-Out. | Real database lookup for patient consent. |
| `app/pipeline/stage1b_checkboxes.py` | 64 | Stub | `_extract_acroform` returns mocked `[AcroForm]` markers instead of actual PDF coordinate logic. | PyMuPDF real widget value extraction. |
| `app/terminology/mappings.py` | 4-21 | Hardcoded return | `CIM10_TO_SNOMED` has only 4 mock values. | A full 50+ item dictionary or database mapping. |
| `app/terminology/mappings.py` | 24 | Hardcoded return | `RARE_DIAGNOSES` is a mock array. | Real dynamic k-anonymity checks. |
| `app/pipeline/stage4g_oncology.py` | 86 | Hardcoded return | `molecular_markers["BRAF"] = "V600E"` is mocked as a generic assumption. | Real extraction from the narrative. |

---

## SECTION 7 — Internal Data Models: Conformance

- `ProcedureEntry` (`app/models/internal.py:106`): Exists, but is missing `implants_inserted` and `implants_removed` (they are instead modelled as a separate `implants` list of `DeviceEntry`). Missing `performed_age`.
- `LabValue`: `flagged` and `unit_ucum` are present.
- `OncologyFields`: `tnm` is correctly typed as `TNMStaging | None`.
- `AdminCheckboxes`: The distinction between `None` and `False` is supported via `Optional[bool]`.
- **Violations**: The `EpicrizaExtracted` model schema severely diverges from Section 8 requirements, placing `procedures`, `implants`, and `adverse_events` at the root and altering the historical schema. 

---

## SECTION 8 — Stage 4E Deep Dive: Claude API Extraction

1. **Prompt conformance**: **Violated.** `stage4e_epicriza.py:57`. The system prompt is heavily truncated and lacks exact required phrasings.
2. **Schema conformance**: **Violated.** `CurrentVisitSchema` adds `implants` and `adverse_events` as flat arrays. `HistorySchema` drops the `procedures` entirely.
3. **Model and token budget**: **Violated.** The code delegates to `llm_client.extract_structured_data` without specifying `claude-sonnet-4-20250514` or `max_tokens=3000`.
4. **HP-07 pre-processing**: **Violated.** Repeated headers are stripped in Stage 1, but page break artifacts inside the Epicriza are not handled before the LLM call.
5. **HP-12 separation**: The prompt instructs separation, but the Pydantic schema structure drops historical procedures.
6. **Error handling**: Emits a `RuntimeWarning` and returns an empty `EpicrizaExtracted`, which partially satisfies the safety requirement but fails to propagate `LLMParseError` appropriately.
7. **Complex medication routing**: **Violated.** `stage4f_medications.py:5` relies entirely on basic regexes and string splits. It does not detect complex conditional/cyclical regimens or route them to the LLM.

---

## SECTION 9 — Security and Pillar 2: Gap Analysis

1. **SMART on FHIR (Pillar 1)**: **CRITICAL GAP.** Missing entirely from `main.py` and `routes.py`. There is no OAuth 2.0 Authorization Code Grant, no PKCE, and no `fhirUser` claim validation.
2. **Opt-Out mechanism**: **CRITICAL GAP.** The opt-out check (`routes.py:170`) is a hardcoded mock checking if the CNP ends in "0000".
3. **Pillar 2 de-identification**: **HIGH GAP.** `stage8_anonymize.py` implements basic name redaction, CNP hashing, and time-shifting, but it completely lacks the K-Anonymity enforcement layer (suppression based on combinations). Generalization is hardcoded to a mock dictionary.
4. **Provenance**: **HIGH GAP.** `stage9_provenance.py` creates a Provenance resource with SHA-256 and model version, but it fails to extract and populate `Composition.attester` with signatory data.

---

## SECTION 10 — Critical Gap Summary and Priority Remediation Plan

1. **CRITICAL** — `Composition.section.text` narrative block is missing from `stage7_bundle.py`. (Rule R2, §3). Fix: Map the concatenated raw text into the Composition's narrative element.
2. **CRITICAL** — SMART on FHIR OAuth 2.0 validation is entirely absent. (Section 12). Fix: Implement an authentication middleware verifying JWKS and enforcing `patient/*.read` scopes.
3. **CRITICAL** — Stage 1B Checkboxes run before Stage 2 Classification. (Rule R8). Fix: Move `extract_checkboxes` below `classify_document` in `routes.py`.
4. **HIGH** — Core Set Validation gate does not raise `CoreSetError`. (Rule R7). Fix: Modify `stage5_merge.py` to raise an Exception and halt processing instead of logging warnings.
5. **HIGH** — `app/terminology/cim10_to_snomed.py` does not exist; mappings are mocked. (§4). Fix: Create the file with minimum 50 correct SNOMED CT mappings.
6. **HIGH** — The Claude System Prompt and Pydantic Schema in `stage4e_epicriza.py` do not match the exact specification. (Rule R1, §9). Fix: Replace the string and models verbatim with the exact schemas provided.
7. **HIGH** — Historical events (`history_timeline`, historical procedures) are dropped from FHIR assembly. (HP-12). Fix: Update `stage6_fhir.py` to iterate over historical arrays and generate past-dated `Condition` and `Procedure` resources.
8. **MEDIUM** — `Encounter.class` duration calculation logic (<24h vs >=24h) is absent. (HP-17). Fix: Implement `timedelta` logic in `stage6_fhir.py`.
9. **MEDIUM** — `AdverseEvent` causal linkages are missing. (§3). Fix: Link the AdverseEvent to the suspected Medication/Procedure in `stage6_fhir.py`.
