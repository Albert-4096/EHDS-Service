# Technical Blueprint and Source of Truth: EHDS-Compliant Medical Document Pipeline

---

## 1. Regulatory Guardrails: EHDS & EEHRxF Framework

System architecture MUST align with the European Health Data Space (EHDS) regulatory timeline. The EHDS Regulation (EU) 2025/327 was adopted February 11, 2025, published March 5, 2025, and entered into force on **March 26, 2025**. The MyHealth@EU infrastructure demands immediate architectural readiness for the European Electronic Health Record Exchange Format (EEHRxF), built on HL7 FHIR R4. The eHealth Network (eHN) Guidelines on Hospital Discharge Report (Release 1.1, November 2024) provide the normative data structure under Cross-Border Directive 2011/24/EU and are the primary semantic reference for HDR content.

### Pillar 1 (Primary Use) vs. Pillar 2 (Secondary Use)

**Pillar 1** governs data exchange for healthcare delivery — sharing Patient Summaries and ePrescriptions across EU borders for authorized health professionals in direct patient care. **Pillar 2** governs data reuse for research and policy-making, strictly gated by a "data permit" from a Health Data Access Body (HDAB) and processed within a Secure Processing Environment (SPE). Using data for insurance premium hikes or predatory marketing is strictly prohibited. The platform MUST implement a robust Opt-Out mechanism; a patient\'s Opt-Out choice dynamically filters record availability in the ingestion and egress pipelines.

There is a direct mathematical tension between Pillar 1 (highly granular, precisely dated FHIR data) and Pillar 2 (k-anonymity requirements). A patient with a rare diagnosis like Osteogenesis Imperfecta and exact surgery dates at a specific hospital will have k=1, making them instantly identifiable even after name/CNP removal. Achieving k-anonymity requires: (a) **Temporal Shifting (\\u0394t):** all dates for a given patient shifted by a consistent random integer of days, preserving longitudinal sequence while obfuscating absolute dates; (b) **Categorical Generalization:** rare genomic markers or congenital diseases generalized to higher-level SNOMED CT parent concepts (e.g., "Osteogenesis Imperfecta" \\u2192 "Congenital Bone Disorder"). The current pipeline design only addresses Pillar 1. A dedicated post-FHIR-assembly de-identification layer applying both techniques must be added before secondary-use output.

### Implementation Timeline

| Milestone Date | Requirement |
|---|---|
| March 26, 2025 | EHDS Regulation enters into force |
| March 2027 | Commission adopts implementing acts and EEHRxF technical specifications |
| **March 2029** | Patient Summaries & ePrescriptions/eDispensations mandatory in all EU member states |
| **March 2031** | Hospital Discharge Reports, medical images, lab results mandatory for primary use |
| March 2034 | Third countries may apply to join HealthData@EU for secondary use |

---

## 2. Document Taxonomy & Classification

Classification MUST happen at Stage 2, before any zone detection or field extraction begins. Using the wrong anchor set for the wrong document type produces silently corrupt output (Rule R8).

### Document Types

**DOC_HDR — Bilet de Externare (Hospital Discharge Report):** Standard multi-day inpatient stay. Issued by public hospitals. Key anchors: `BILET DE EXTERNARE`, `DIAGNOSTIC PRINCIPAL LA EXTERNARE`, `EPICRI\\u0162\\u0102`, `TRATAMENT LA EXTERNARE`, `RECOMAND\\u0102RI`. Mandatory fields: CNP, FOCG number, admission date, discharge date, primary diagnosis with CIM-10, discharge status. Maps to LOINC `34105-7` (Hospital Discharge summary). `Encounter.class = IMP` (Inpatient). Legally governed by Ministry of Health Order 1782/2006 (and revisions, e.g., 1503/2013) and the Romanian DRG system (RO DRG v.1, derived from ICD-10-AM). The underlying medical record is the Foaie de Observatie Clinica Generala (FOCG).

**DOC_BIS — Bilet de Iesire / Scrisoare Medicala (Day-Hospital / Ambulatory Visit):** Single-day treatment session (e.g., chemotherapy cycle, dialysis). Issued by private clinics and day-hospital units. Key anchors: `BILET DE IESIRE`, `SCRISOARE MEDICALA`, `FO:`, `Epicriza:`, `Investigatii efectuate:`, `Tratament:`, `Recomandari:`. Critical differences from DOC_HDR: contains checkbox administrative blocks at document end (prescriptie, concediu, recomandare, dispozitive); contains `Ciclul:` and `Acronim:` fields for oncology; may contain a blood transfusion table; contains an appointment scheduling block. Maps to LOINC `34133-9` (Summarization of episode note). When admission and discharge timestamps share the same date, `Encounter.class = AMB` (Ambulatory). Duration < 24 hours \\u2192 AMB; \\u2265 24 hours \\u2192 IMP.

**DOC_SM — Scrisoare Medicala (referral only):** Referral or consultation letter between physicians. Key anchor: `SCRISOARE MEDICALA` without `BILET DE IESIRE`. **Out of scope for this pipeline.** Classify and reject gracefully with `DocumentTypeError`.

### Classification Rules (case-insensitive, applied to first 30 lines)

1. Text contains `BILET DE IESIRE` or `FO:` near header \\u2192 `DOC_BIS`
2. Else if text contains `BILET DE EXTERNARE` \\u2192 `DOC_HDR`
3. Else if text contains `SCRISOARE MEDICALA` without `BILET DE IESIRE` \\u2192 `DOC_SM` \\u2192 raise `DocumentTypeError`
4. Else \\u2192 `UNKNOWN` \\u2192 raise `DocumentTypeError` with first 30 lines in message

---

## 3. The Interoperability Schema: FHIR Data Modeling

### Six EEHRxF Priority Data Categories

| EHDS Priority Category | HL7 FHIR IG | Rollout |
|---|---|---|
| Patient Summaries | HL7 IPS v2.0 | 2029 |
| Electronic Prescriptions | HL7 Europe Medication Prescription & Dispense | 2029 |
| Electronic Dispensations | HL7 Europe Medication Prescription & Dispense | 2029 |
| Medical Imaging Studies & Reports | HL7 Europe Imaging Report | 2031 |
| Lab Results / Diagnostic Reports | HL7 Europe Laboratory Report (v0.1.1) | 2031 |
| **Hospital Discharge Reports** | **HL7 Europe HDR (v0.1.0-ballot)** | **2031** |

This pipeline targets **Patient Summary** and **Hospital Discharge Report** as primary scope.

### FHIR Document Structure

A FHIR Document is a `Bundle` resource with `type: document`. Entry 0 MUST be the `Composition` resource — the document\'s table of contents, spine, and legal authentication. All subsequent entries are referenced FHIR resources. The `Composition` SHALL include `status: "final"` and a LOINC document type code (DOC_HDR \\u2192 `34105-7`, DOC_BIS \\u2192 `34133-9`).

### EEHRxF Mandatory Core Set

| Field ID | Element | FHIR Resource | Notes |
|---|---|---|---|
| A.1.1 | Patient Identification | `Patient` | Blocks pipeline if both CNP and Nume are absent |
| A.1.4 | Health Professional | `Practitioner`, `PractitionerRole` | Non-blocking if absent — DataAbsentReason |
| A.2.1 | Admission & Discharge Info | `Encounter` | Mandatory dates and reason; blocks if absent |
| A.2.0 | Narrative Report | `Composition.section.text` | Full free-text clinical summary; blocks if absent |

### Complete FHIR Resource Map

**Core Set (transmission-blocking if absent):** `Composition`, `Patient`, `Practitioner`, `PractitionerRole`, `Encounter`, `Condition`

**Extended Set (non-blocking warnings if absent):** `MedicationRequest`, `Observation` (labs, vitals, ECOG), `CarePlan` (follow-up), `Appointment` (next visit), `AllergyIntolerance`, `DiagnosticReport` (imaging)

**Previously omitted — required for full EEHRxF compliance:**

`Procedure` is MANDATORY for surgical history (Composition section LOINC 47519-4). All orthopedic, oncological, and cardiothoracic surgical events must be extracted and mapped. Omitting historical surgical interventions is a critical clinical data loss affecting future surgical decisions and therapeutic dosing.

`Device` + `DeviceUseStatement` are MANDATORY for implantable hardware tracking (Ender nails, K-wires, centromedullary nails, Maquet plates, cardiac devices). EHDS regulations explicitly mandate this for post-market surveillance and device safety recalls.

`AdverseEvent` is required for treatment-induced adverse events with causal linkage. Events like "Hipofizita autoimuna G1" (immunotherapy toxicity), hardware failure ("degradare montaj"), post-operative anemia, and "intrerupt datorita toxicitatii" must be mapped here with an explicit causal reference to the specific `Medication`, `Procedure`, or `Device` — not simply as generic `Condition` entries.

`Provenance` is required for legal authentication under EEHRxF. Every Bundle must record: extraction timestamp, AI model version, SHA-256 hash of source PDF, and signatory data from "Medic curant" / "Medic Sef de Sectie" signature fields \\u2192 `Composition.attester`.

### IPS Required Sections & FHIR Resources

| IPS Section | FHIR Resource(s) | Terminology Binding |
|---|---|---|
| Patient demographics | `Patient` | Mandatory |
| Current problems / diagnoses | `Condition` | SNOMED CT (GPS) |
| Allergies & intolerances | `AllergyIntolerance` | SNOMED CT |
| Current medications | `MedicationStatement` / `MedicationRequest` | ATC / RxNorm |
| History of procedures | `Procedure` | SNOMED CT |
| Immunizations | `Immunization` | SNOMED CT |
| Lab results | `Observation`, `DiagnosticReport` | LOINC |
| Medical devices | `DeviceUseStatement` | SNOMED CT |
| Vital signs | `Observation` | LOINC |

### HDR Additional Sections & FHIR Resources

| HDR Section | FHIR Resource(s) | Notes |
|---|---|---|
| Patient identification | `Patient` | EEHRxF A.1.1 |
| Responsible clinician | `Practitioner`, `PractitionerRole` | EEHRxF A.1.4 |
| Admission & discharge info | `Encounter` | EEHRxF A.2.1 |
| Narrative clinical summary | `Composition.section.text` | EEHRxF A.2.0 |
| Admission diagnosis | `Condition` (encounter-diagnosis) | SNOMED CT |
| Discharge diagnosis | `Condition` | SNOMED CT, dual-coded with ICD-10 |
| Procedures | `Procedure` | SNOMED CT — current AND historical |
| Discharge medications | `MedicationRequest` | ATC / SNOMED CT |
| Lab results during admission | `Observation`, `DiagnosticReport` | LOINC |
| Follow-up instructions | `CarePlan`, `ServiceRequest` | — |
| Referrals | `ServiceRequest` | — |
| Medical devices / implants | `Device`, `DeviceUseStatement` | SNOMED CT |
| Adverse events / toxicities | `AdverseEvent` | SNOMED CT (causal link required) |
| Document provenance | `Provenance` | SHA-256 of source PDF |

### Core FHIR R4 Resource Constraints

`Patient.birthTime` SHALL be precise to the Year (CONF: 1198-5299) and SHOULD be precise to the Day (CONF: 1198-5300). `Composition` SHALL include `status: "final"`. `Condition` SHALL include `clinicalStatus` and `verificationStatus`. `MedicationStatement` SHALL express intent and timing; if missing, return `NullFlavor`. All `Observation` resources for flagged lab values SHALL include `interpretation = "A"` (Abnormal).

### Composition Section LOINC Codes by Document Type

**DOC_HDR sections:** History of Present Illness (11329-0 or 34117-2), Investigations (30954-2), Discharge Diagnosis (11535-2), Discharge Medications (10183-2), Procedures (47519-4), Follow-up Plan (18776-5).

**DOC_BIS sections:** Narrative (11329-0), Active Problems (11450-4), Treatment (18776-5), Lab Results (30954-2), Follow-up Plan (18776-5), Imaging (18748-4) when present.

Romanian clinical headers must be mapped to LOINC section codes: "Istoricul Bolii" and "Epicriza" \\u2192 LOINC 11329-0; "Investigatii efectuate" \\u2192 LOINC 30954-2.

### Document Architecture: Narrative vs. Entry

The Narrative block (`Composition.section.text`) is the authenticated content the clinician signs — the legal clinical record. The Entry blocks (FHIR resources) provide machine-readable discrete data for automated safety checks. Both SHALL always be present; coded data without a human-readable narrative is non-compliant.

---

## 4. Terminology Bindings & Code Systems

**SNOMED CT** (`http://snomed.info/sct`): Mandatory for clinical findings, disorders, and procedures. Prioritize the Global Patient Set (GPS) and CORE Problem List Subset. Used for all diagnoses, procedures, medical devices, allergies, and functional status.

**LOINC** (`http://loinc.org`): Mandatory for document types, laboratory observations, ECOG status (89247-1), cancer response (88040-1), and imaging modalities.

**ATC** (`http://www.whocc.no/atc`): Mandatory for medication coding. Mapping from Romanian commercial brand names to ATC is a mandatory EEHRxF requirement for cross-border ePrescription continuity.

**ICD-10 / CIM-10 (secondary only):** Romanian hospitals use the RO DRG v.1 system (ICD-10-AM). Administrative codes must be dual-coded per Rule R6: SNOMED CT as primary + ICD-10 as secondary in the same `CodeableConcept`. A 1:1 deterministic mapping from DRG codes to SNOMED CT is a semantic fallacy — DRG codes are optimized for financial reimbursement grouping and lack granular clinical specificity. The pipeline MUST use the actual narrative text as the primary source for SNOMED CT NLP extraction. ICD-10 codes populate `Condition.extension` or `Condition.category` for billing reference only.

**UCUM** (`http://unitsofmeasure.org`): Mandatory for all physical quantities in `Observation.valueQuantity.unit`.

### Key Oncology Terminology

TNM staging components map to individual SNOMED CT observable entities: T \\u2192 385356007, N \\u2192 385382003, M \\u2192 385380006, Overall Stage \\u2192 385361009. BRAF V600E \\u2192 LOINC 51971-4. ECOG score \\u2192 LOINC 89247-1. Cancer response status: RC \\u2192 CR (SNOMED 550001003 Complete remission), RP \\u2192 PR, BS/SD \\u2192 Stable Disease, PD \\u2192 Progressive Disease. Cancer response LOINC: 88040-1.

### UCUM Unit Normalization Map

| Raw (from PDF) | UCUM |
|---|---|
| `109/L` (after superscript repair) | `10*9/L` |
| `1012/L` (after superscript repair) | `10*12/L` |
| `g/dL`, `fL`, `pg`, `%`, `mmol/L`, `mg/dL` | unchanged |
| `U/L`, `UI/l` | `U/L` |
| `mUI/L` | `m[IU]/L` |
| `ng/dl` | `ng/dL` |
| `ug/dl` | `ug/dL` |

### Terminology Module Requirements

`loinc_map.py` must cover — CBC: WBC/Leucocite (6690-2), RBC/Hematii (789-8), HGB/Hemoglobina (718-7), HCT/Hematocrit (4544-3), MCV (787-2), MCH (785-6), MCHC (786-4), PLT/Trombocite (777-3), Neutrofile% (770-8), Limfocite% (736-9), RDW-CV (21000-5), MPV (32623-1). Biochemistry: Bilirubina totala (1975-2), Calciu (17861-6), Creatinina (2160-0), FA (6768-6), Glicemie (2339-0), K (2823-3), Na (2951-2), TGO/AST (1920-8), TGP/ALT (1742-6). Hormones: TSH (3016-3), FT4 (3024-7), Cortizol (2143-6), DHEA-S (2191-5). Oncology: ECOG (89247-1), cancer response (88040-1).

`atc_lookup.py` must cover (Romanian trade name \\u2192 ATC): Nivolumab (L01FF02), Ipilimumab (L01FX04), IFN alfa (L03AB), Aspirina/Aspenter (B01AC06), Atorvastatin (C10AA05), Bisoprolol (C07AB07), Metformin (A10BA02), Furosemid (C03CA01), Omeprazol (A02BC01), Levotiroxina/Euthyrox (H03AA01), Enoxaparin/Clexane (B01AB05), Heparina (B01AB01), Clopidogrel/Trombex (B01AC04), Fraxiparine (B01AB05), Fosamax/Alendronate (M05BA04).

`cim10_to_snomed.py` must cover minimum 50 high-frequency Romanian diagnoses, including: C43.5 (Melanom malign trunchi) \\u2192 372244006, I10 \\u2192 73410007, I21.4 (NSTEMI) \\u2192 401303003, I50.0 \\u2192 42343007, E11.9 (T2DM) \\u2192 44054006, E03.9 \\u2192 40930008. If no SNOMED mapping: return `DataAbsentCoding`.

`oncology_terms.py`: regimen acronym dict (Nivo q4w, Ipi+Nivo, FOLFOX, FOLFIRI, AC-T, BEP, CHOP, R-CHOP), response status codes (RC\\u2192CR, RP\\u2192PR, BS\\u2192SD, PD\\u2192PD), TNM prefix meanings (p=pathological, c=clinical, y=post-treatment, r=recurrence).

---

## 5. Input Data Reality: Romanian Medical Documents

### Structural Heterogeneity Across Three Document Typologies

Romanian medical documents come from many different Hospital Information Systems (HIS) and clinic templates, exhibiting high structural heterogeneity spanning decades. Three distinct typologies must be handled:

**Legacy narrative documents (2009 era — pediatric/neuropsychiatry):** Semi-unstructured discharge summaries from public county hospitals. Heavily reliant on continuous narrative prose. Lack modern digital form controls. May contain ICD-10 codes like A.88.8, G.93.2. Epicriza deeply interweaves longitudinal history with current admission. Complex pharmacological regimens with conditional, cyclical, and alternating schedules ("10 zile pe luna", "sub protectie de Fenobarbital", "alternativ cu Encephabol") that regex-based parsers cannot handle.

**Typed form documents (2010–2011 era — orthopedic):** Unstructured narrative, typed forms. Introduce clinical data structures absent in other types: invasive surgical procedures, implantable medical hardware (Ender nails, K-wires, centromedullary nails, Maquet plates), and surgical complications ("degradare montaj"). Sequential documents for the same patient require longitudinal continuity tracking.

**Modern structured documents (2026 era — private oncology, e.g., OncoHelp Timisoara):** Digitally generated, multi-column tabular demographics, Unicode checkboxes, organized epicriza with clean historical timeline separation. Employ highly specific metrics (TNM, ECOG, BRAF V600E) and treatment cycle tracking (Ciclul, Acronim).

### Document Type Mapping Summary

| Dimension | Pediatric Neuro (2009) | Orthopedic (2010/11) | Advanced Oncology (2026) |
|---|---|---|---|
| Document class | DOC_HDR | DOC_HDR | DOC_BIS |
| Encounter duration | 8 days | 17 days | Same-day (4 hrs) |
| FHIR Encounter.class | IMP | IMP | AMB |
| LOINC type | 34105-7 | 34105-7 | 34133-9 |
| Unique data vectors | Cyclical/conditional drug regimens | Implantable hardware, device failure | Genomic markers, TNM, cycle tracking |

### Raw-to-FHIR Extraction Example

From a typical Romanian discharge fragment, the pipeline must produce:

| Extracted Entity | FHIR Resource | Code System | Example Code |
|---|---|---|---|
| Patient demographics | `Patient` | — | demographics |
| Admission/discharge dates | `Encounter.period` | ISO 8601 | — |
| NSTEMI (primary Dx) | `Condition` | SNOMED CT | 401303003 |
| Hypertension Gr. II | `Condition` | SNOMED CT | 73410007 |
| Type 2 Diabetes | `Condition` | SNOMED CT | 44054006 |
| Troponin I = 1.8 ng/mL | `Observation` | LOINC | 10839-9 |
| Aspirin 100mg/day | `MedicationRequest` | ATC | B01AC06 |
| Atorvastatin 40mg/day | `MedicationRequest` | ATC | C10AA05 |
| Surgery (osteosynthesis) | `Procedure` | SNOMED CT | — |
| Ender nail implant | `Device`, `DeviceUseStatement` | SNOMED CT | — |
| Hardware failure | `AdverseEvent` | SNOMED CT | — |
| Cardiology follow-up | `CarePlan`/`ServiceRequest` | SNOMED CT | — |

---

## 6. Technical Pipeline Architecture

The pipeline is a **"Zero-Trust Data Factory."** No data SHALL be persisted without schema and terminology validation.

```
[Stage 0] PDF Forensics
  Detect: digital vs. scanned, page count, AcroForm widget presence
  PDFForensics: {is_scanned: bool, page_count: int, has_acroform_widgets: bool}
  is_scanned = True if avg chars/page < 100 after pdfplumber extraction

[Stage 1] Text Extraction (strategy selected by Stage 0)
  Digital PDF: pdfplumber — extract each page, join, strip repeated headers
  Scanned PDF: pdf2image dpi=300 -> pytesseract lang="ron"
  Always: join_pages() + strip_repeated_headers() + normalise_whitespace()
  Preserve newline structure — zone detection depends on it

[Stage 1B] Checkbox Extraction (separate pass — see HP-01)
  Try in order: AcroForm (pymupdf) -> Unicode (U+2612/U+2610) -> OCR ASCII ([X]/[ ])
  Output: list[CheckboxGroup]

[Stage 2] Document Classification (MUST complete before anything else — Rule R8)
  Output: DocumentType enum {DOC_HDR, DOC_BIS, DOC_SM, UNKNOWN}
  Drives zone anchor set selection for all subsequent stages

[Stage 3] Zone Detection
  Split on type-specific anchor strings (diacritic-insensitive matching)
  DOC_HDR anchors: DATE PACIENT, DIAGNOSTIC LA INTERNARE,
    DIAGNOSTIC PRINCIPAL LA EXTERNARE, DIAGNOSTICE SECUNDARE,
    STARE LA EXTERNARE, EPICRIZA, TRATAMENT LA EXTERNARE, RECOMANDARI
  DOC_BIS anchors: Diagnostic, Investigatii efectuate, Tratament, Epicriza,
    Recomandari + virtual zones: APPOINTMENT_BLOCK, CHECKBOX_BLOCKS,
    Calea de transmitere
  Missing anchor -> key maps to "" — no exception raised

[Stage 4A] Structured Fields — demographics, dates, CIM-10, identifiers
  HP-02: Multi-column table parsing for demographics header
  HP-06: All 7 Romanian date formats -> ISO 8601 with Romania tz offset
  HP-08: FO number + contract number dual identifier on same line
  HP-13: Blank/redacted fields -> DataAbsentReason, derive from CNP

[Stage 4B] Lab Panel Extraction
  HP-03: Superscript repair ("5.79 109/L" -> 5.79 x 10^9/L -> UCUM "10*9/L")
  HP-04: Asterisk-flagged values -> Observation.interpretation = "A"
  HP-05: Separate hemoleucograma (bracket-wrapped) from biochemistry
  HP-16: Romanian decimal comma normalisation (context-limited, never global)

[Stage 4C] Checkbox Semantic Mapping
  HP-01: map extracted CheckboxGroups -> typed AdminCheckboxes fields
  None (group absent) != False (group present, "not issued" checked)

[Stage 4D] Appointment Block Extraction
  HP-09: "Sunteti programat in data:" -> Appointment FHIR resource

[Stage 4E] Epicriza / Narrative Extraction via Claude API
  HP-07: Page break artifacts stripped before sending to LLM
  HP-12: LLM explicitly instructed to separate current_visit from history_timeline
  HP-18: Extract structured imaging results per entry (modality, date, institution, conclusion)
  Procedures/surgeries: extract each as {date, description, anatomical_site, implants}
  Schema enforced via Pydantic — on JSON parse failure: all fields None/[], emit LLMParseError
  Model: claude-sonnet-4-20250514, max_tokens=3000

[Stage 4F] Medication / Treatment Line Parsing
  Standard linear lines only: "Drug - Dose - Frequency - Duration"
  Complex regimens (conditional, cyclical, alternating) MUST route to Stage 4E LLM
  Detect "DT" suffix (doza totala) -> dose_is_total=True

[Stage 4G] Oncology-Specific Fields
  HP-10: Ciclul, Acronim, ECOG, response status (RC/RP/BS/PD)
  HP-11: TNM staging string parsing -> individual SNOMED-coded Observations

[Stage 5] Merge + Pydantic Sentry Validation
  R7 Core Set validation (CoreSetError = blocks pipeline)
  Compute overall_confidence score; aggregate all_warnings

[Stage 6] FHIR R4 Resource Assembly
  HP-17: Same-day encounter (duration < 24h) -> Encounter.class = AMB
  HP-04: flagged lab values -> Observation.interpretation = "A"
  Build: Patient, Encounter, Condition, MedicationRequest, Observation,
         Procedure, Device, DeviceUseStatement, AdverseEvent,
         DiagnosticReport, CarePlan, Appointment, AllergyIntolerance,
         Practitioner, PractitionerRole, Provenance

[Stage 7] Bundle Assembly
  HP-15: Composition.type LOINC selected by doc_type (34105-7 or 34133-9)
  Entry 0: Composition | Entry 1: Patient | Entries 2..N: all referenced resources
  Bundle.meta.tag: "primary-use-allowed" (default)
  Bundle.timestamp: discharge datetime with Romania tz offset

[Stage 8] HAPI FHIR Upload + Opt-Out Metadata
  POST to {HAPI_FHIR_BASE_URL}, Content-Type: application/fhir+json
  HTTP 200/201 -> success; 4xx/5xx -> raise UploadError

[Stage 9] Provenance (previously missing)
  Generate Provenance resource: timestamp, AI model version, SHA-256(source PDF)
  Extract signatory data -> populate Composition.attester
```

### Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| API / Backend | Python 3.12 + FastAPI | Pydantic native, async support |
| AI Extraction | Anthropic SDK (`claude-sonnet-4-20250514`) | Structured JSON, anti-hallucination via schema |
| FHIR Modeling | `fhir.resources` (PyPI, \\u22657.0) | Native R4 Pydantic models |
| Validation | Pydantic v2 strict + HAPI FHIR Validator | Schema + terminology enforcement |
| PDF (digital) | pdfplumber | Text extraction + table detection |
| PDF (forms) | pymupdf (fitz) | AcroForm widget/checkbox extraction |
| PDF (scanned) | pytesseract lang="ron" + pdf2image dpi=300 | OCR for legacy scanned docs |
| FHIR Server | HAPI FHIR (Docker) on localhost:8080 | Open-source, R4-compliant |
| Database | PostgreSQL + JSONB (asyncpg) | |
| Environment | Ubuntu 22.04 LTS (server) | |

```bash
# HAPI FHIR local server
docker run -p 8080:8080 hapiproject/hapi:latest
# FHIR base URL: http://localhost:8080/fhir
```

---

## 7. Hard Problems (HP): Real Failure Modes from Observed Documents

Each problem was observed in a real Romanian clinical document. Every one MUST be implemented with no stubs, no TODOs, no deferral.

### HP-01: Checkbox State Extraction (CRITICAL)

Checkboxes appear in three technical forms. **Form A** — Unicode characters (\\u2612 U+2612 = checked, \\u2610 U+2610 = unchecked) inline in pdfplumber text stream. **Form B** — AcroForm PDF widget annotations, NOT in text stream; requires `pymupdf`: iterate `page.widgets()` where `widget.field_type == PDF_WIDGET_TYPE_CHECKBOX`, read `widget.field_value` ("Yes" or "Off"). **Form C** — Scanned OCR producing `[X]` or `[ ]` ASCII equivalents.

Detection order: (1) pymupdf AcroForm widgets present \\u2192 Form B; (2) \\u22652 Unicode checkbox chars \\u2192 Form A; (3) `[X]`/`[ ]` present \\u2192 Form C; (4) none \\u2192 emit `CheckboxExtractionWarning`, return `[]`.

Semantic mapping: split checkbox zone into lines; each checkbox character appears inline with its option label; group consecutive option lines under the preceding header line (header ends with `:`, no checkbox character). Output: `list[CheckboxGroup]`.

Known DOC_BIS checkbox groups: (1) "Indicatie de revenire pentru internare" \\u2192 `Encounter.extension` readmission indicator + timeframe extracted from label via `r"(\\d+)\\s*saptamani"`; (2) "Prescriptie medicala" \\u2192 `prescription_issued: bool | None`; (3) "Concediu medical la externare" \\u2192 `sick_leave_issued: bool | None`; (4) "Recomandare pentru ingrijiri medicale la domiciliu" \\u2192 `home_care_referral`; (5) "Prescriptie pentru dispozitive medicale" \\u2192 `medical_device_prescription`; (6) "Calea de transmitere" — uses literal `X` text, not Unicode; regex: `r"X\\s*-\\s*(prin asigurat|prin posta)"`.

Validate: each group must have exactly one `checked=True`. Zero or multiple \\u2192 `CheckboxStateWarning` — do NOT raise, continue with warning. None (group absent from document) vs. False (group present, "not issued" was checked) must remain distinct values.

### HP-02: Multi-Column Demographics Table (HIGH)

DOC_BIS demographics is a 3-column printed table. Column 1 (left): Nume, CNP, Varsta|Sex, Grup sangvin|RH. Column 2 (mid): Domiciliu, Alergii. Column 3 (right): Data internare (with time), Data externare (with time), Sectia, Medic. Strategy: attempt `pdfplumber.page.extract_tables()` first; if no visible grid borders (common in HIS PDFs), fall back to coordinate-based word clustering by y-band and x-band using configurable (not hardcoded) column x-thresholds stored in a config file. The `|` character in "Varsta: [V] | Sex: [M]" is a visual form separator, NOT a data delimiter — parse with `r"Varsta:\\s*(\\d+)\\s*\\|\\s*Sex:\\s*([MF])"`.

### HP-03: Superscript Loss in Lab Values (HIGH)

Superscripts in scientific notation are dropped by PDF extractors: `"5.79 109/L"` instead of `"5.79 x 10\\u2079/L"`. Apply normalization regex BEFORE any lab parsing: `r"(\\d+\\.?\\d*)\\s+(10)(\\d{1,2})/([Ll])"` \\u2192 `r"\\1 x 10^\\3/\\4"`. Store `value_numeric`, `unit_raw`, and `unit_ucum` (UCUM notation) separately.

### HP-04: Asterisk-Flagged Lab Values (MEDIUM)

An asterisk `*` prefix on a test name signals an out-of-reference-range value (e.g., `*(RDW-CV)`, `*(PCT)`, `*IMG%`). Set `flagged=True` on the `LabValue` model. FHIR mapping: `Observation.interpretation = CodeableConcept(code="A", display="Abnormal")` from system `http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation`. For unflagged values, omit the interpretation field entirely — do not set it to "N" (Normal), which requires knowing the reference range.

### HP-05: Lab Panel Boundary Detection (HIGH)

A single text block contains multiple sub-panels without explicit delimiters. Strategy: (1) Find `"Hemoleucograma completa:"` anchor; (2) extract everything inside the following `[...]` block as CBC (may span multiple lines); (3) after the closing `]`, parse comma-separated `"key=value unit"` pairs as biochemistry. Store panels separately: `LabResults(cbc, biochemistry, hormones, other)`. Observed lab value formats include: key with bracket prefix `"(WBC) Leucocite=5.79"`, slash in key `"TGO/AST=22.34 UI/l"`, comma decimal `"cortizol seric= 0,46 ng/dl"`.

### HP-06: Date Format Heterogeneity (HIGH)

Seven formats coexist in a single document: `DD/MM/YYYY HH:MM` (header table), `DD.MM.YYYY` (epicriza narrative), `DD MonthName YYYY` (appointment block — Romanian month names: Ianuarie through Decembrie). All normalize to ISO 8601. Datetimes include Romania\'s UTC offset: DST active (last Sunday March \\u2192 last Sunday October) = `+02:00`; DST inactive = `+03:00`. Ambiguity defaults to `+02:00` with `ParseWarning`. Implement `parse_romanian_date(raw) -> date` and `parse_romanian_datetime(raw) -> datetime`. Both raise `DateParseError` (not `ValueError`) with the raw string in the message.

### HP-07: Multi-Page Epicriza (HIGH)

Epicriza splits across page breaks causing: (1) missing space at join point; (2) repeated clinic header injected mid-narrative; (3) page number artifacts ("2 / 3"). Fix: join pages with `"\\n"`, strip repeated header occurrences (matched against first 3 non-empty lines of page 1), collapse 3+ consecutive newlines to 2, preserve single newlines (zone detection depends on them).

### HP-08: Dual Identifier on Same Line (MEDIUM)

`"Nr. contract/conventie: VII/SP/22   FO: 16628"` contains two distinct identifiers. `contract_number` "VII/SP/22" maps to `Encounter.identifier(system="urn:ro:cnas:contract")`; `fo_number` "16628" maps to `Encounter.identifier(system=urn:oid:2.16.840.1.113883.2.24.1.3)`. These are different and must be extracted separately.

### HP-09: Appointment Block Extraction (MEDIUM)

DOC_BIS contains large bold text: `"Sunteti programat in data: 21 Mai 2026 ora: 09:10"`. Regex: `r"Sunteti programat in data:\\s+(.+?)\\s+ora:\\s+(\\d{2}:\\d{2})"`. Parse date using `parse_romanian_date()`. Map to `Appointment(status="booked", start="2026-05-21T09:10:00+03:00")`, referenced from `CarePlan.activity.reference`.

### HP-10: Oncology-Specific Fields (HIGH)

`"Ciclul: 38 Acronim: Nivo q4w"` \\u2192 extract `cycle_number` (int) and `regimen_acronym` (str). `"DT"` suffix = "doza totala" (total dose) \\u2192 `dose_is_total=True` (not a standard frequency designation). ECOG/IP/PS regex: `r"(?:IP|ECOG|PS)\\s*[=:]\\s*(\\d)\\s*(?:ECOG)?"` \\u2192 `Observation(code=LOINC 89247-1, valueInteger=N)`. `"RC"` = "Remisiune Completa" \\u2192 LOINC 88040-1 with SNOMED 550001003.

### HP-11: TNM Staging Notation Parsing (HIGH)

Input example: `"pT2n0(0+/3 GS)m0 braf mutant st. I B op."` (case-insensitive). Regex: `r"([pcyr]?T[0-4X][a-z]?)\\s*([Nn][0-3X])(?:\\(([^)]+)\\))?\\s*([Mm][01X])"`. Extract: t_category, n_category, n_detail (sentinel node info "0+/3 GS"), m_category, stage_group, prefix (p/c/y/r), modifiers (["braf mutant", "op."]). Each component maps to its own SNOMED-coded `Observation` resource (T\\u21920385356007, N\\u2192385382003, M\\u2192385380006, Stage\\u2192385361009). BRAF V600E: regex `r"BRAF\\s+V600E|BRAF\\s+mutant"` \\u2192 LOINC 51971-4.

### HP-12: Longitudinal History in Epicriza (HIGH)

The Epicriza does NOT limit itself to the current visit. It may contain the patient\'s complete history spanning years. The Claude API extraction prompt MUST explicitly instruct the LLM to produce: (a) `current_visit` — data for THIS admission only, signaled by "Actual, se prezinta...", "Se administreaza...", or the most recent dated event; (b) `history_timeline` — array of `{date, event_type, description}` for all prior events. Current visit \\u2192 `Encounter`, `Observation`, `MedicationRequest`. History timeline \\u2192 `Condition.onsetDateTime`, `Procedure.performedDateTime`, `DiagnosticReport` per historical imaging. Never mix historical imaging with current investigation results.

### HP-13: Blank/Redacted Mandatory Fields (HIGH)

Rules: (1) CNP present \\u2192 derive `date_of_birth` (positions 2–7: YYMMDD + century prefix where 1/2=1900s, 5/6=2000s), `sex` (position 1: 1/3=M, 2/4=F), `county_code` (positions 8–9) via `utils/cnp_parser.py`; (2) CNP blank AND Nume blank \\u2192 `CoreSetError` (blocks); (3) CNP blank but Nume present \\u2192 `DataAbsentReason` on `Patient.identifier`, continue with `ParseWarning`; (4) Medic blank \\u2192 `DataAbsentReason` on `Practitioner`, NEVER fabricate name; (5) Allergy field "NU CUNOASTE" or empty \\u2192 do not create `AllergyIntolerance`, add note to `Patient.text`.

### HP-14: Blood Transfusion Table (LOW)

DOC_BIS contains the table `"Grupa sange | RH | Tip | Nr pungii | Data"` which may be empty (no transfusion) or filled. Empty \\u2192 `transfusions=[]`. Filled rows \\u2192 each row \\u2192 `Procedure(code=SNOMED 116877001 "Administration of blood product")`.

### HP-15: Document-Type-Specific LOINC Code (MEDIUM)

DOC_HDR \\u2192 `Composition.type: 34105-7`. DOC_BIS \\u2192 `Composition.type: 34133-9`. The document classifier output MUST be passed to the bundle assembler. Never hardcode one value for all document types. This is not a cosmetic difference — it determines the semantic interpretation of the entire document at every receiving system.

### HP-16: Romanian Decimal Comma (MEDIUM)

Romanian clinical documents use comma as decimal separator: `"0,46 ng/dl"`, `"3,4210 mUI/L"`, `"Breslow=1,5 mm"`. Critical: do NOT apply global comma\\u2192period replacement on the entire document (corrupts list separators). Only call `normalise_romanian_decimal()` on isolated extracted value strings. Pattern: `r"(\\d+),(\\d+)(?!\\s*\\d{3})"` \\u2192 `r"\\1.\\2"`.

### HP-17: Same-Day Encounter (MEDIUM)

When admission and discharge share the same date (e.g., `23/04/2026 10:06` \\u2192 `14:21`), this is NOT an error — it is a day-hospital encounter. Logic: `duration_hours = (discharge_dt - admission_dt).total_seconds() / 3600`; if `< 24` \\u2192 `Encounter.class = "AMB"`; else \\u2192 `"IMP"`. Naively assuming multi-day = inpatient silently misclassifies ambulatory DOC_BIS documents.

### HP-18: Imaging Result Extraction from Epicriza (MEDIUM)

Imaging results are embedded inline in narrative: `"PET CT ( 26.05.2023 - Medima): Concluzii: Multiple fixari..."`, `"CT TAP (Oncohelp 01.09.2023): ..."`. The LLM must extract each as `ImagingResult(modality, date, institution, conclusion, is_current_visit: bool)`. Map each to a `DiagnosticReport` resource. Historical reports (`is_current_visit=False`) \\u2192 `status="final"`. Reference from Composition section LOINC 18748-4.

### Critical Architectural Gaps (Beyond HP-01 Through HP-18)

**Surgical and procedural extraction was completely missing.** The `EpicrizaExtracted` Pydantic model must include a `procedures` array capturing: intervention type, date, anatomical site, implants inserted, implants removed. All surgical verbs and hardware references must be explicitly hunted in the epicriza. Map to FHIR `Procedure` with SNOMED CT codes, referenced in Composition section LOINC 47519-4.

**Complex pharmacological parsing.** The regex-based medication parser is structurally incapable of parsing conditional ("sub protectie de Fenobarbital"), cyclical ("10 zile pe luna"), and alternating ("alternativ cu Encephabol") regimens. These MUST be sent to Stage 4E LLM with an explicit schema mapping to `MedicationRequest.dosageInstruction` using `Timing.repeat.boundsPeriod`, `Timing.repeat.frequency`, and `Timing.repeat.periodUnit`. Non-pharmacological therapies (medical gymnastics, kinetotherapy) must be extracted and mapped to `ServiceRequest` and `CarePlan`.

**Adverse event tracking was absent.** Causal linkages in the narrative ("intrerupt datorita toxicitatii", "degradare montaj", "hipofizita autoimuna G1") must map to `AdverseEvent` resources with an explicit causal reference to the suspected `Medication` or `Procedure`/`Device`. Required for EHDS pharmacovigilance and device safety reporting.

**Temporal handling of relative dates.** The pipeline must not force absolute dates for relative temporal expressions ("la varsta de 3 saptamani", "dupa un interval liber de aprox. 12 ani"). If the absolute date cannot be computed without hallucinating (e.g., CNP is redacted, so birth date is unknown), use FHIR\'s `Procedure.performedAge` or `Condition.onsetAge` with the `Age` datatype. Never fabricate a `DateTime` for a relative expression.

**Document layout analysis fragility.** The coordinate-based column clustering fallback (HP-02) is brittle across different HIS rendering engines (Crystal Reports, JasperReports). The long-term resilient approach is to use document layout analysis models (LayoutLMv3 or YOLO-based parsers) to semantically segment pages into bounding boxes. Column x-thresholds MUST be in config files, never hardcoded.

**Cryptographic provenance was missing.** `stage9_provenance.py` must generate a `Provenance` resource for every bundle: extraction timestamp, AI model version, SHA-256 hash of source PDF, and `Composition.attester` populated from extracted signatory data ("Medic curant" / "Medic Sef de Sectie").

---

## 8. Internal Data Models (models/internal.py)

Every field that can be absent from the source document is `Optional[X] = None`. Never use default values that imply clinical meaning.

```python
class CheckboxOption(BaseModel):
    label: str
    checked: bool
    raw_marker: str            # exact character/text detected: "\\u2612", "X", "[X]"

class CheckboxGroup(BaseModel):
    header: str
    options: list[CheckboxOption]
    extraction_method: str     # "unicode" | "acroform" | "ocr_ascii" | "unknown"

class DiagnosticEntry(BaseModel):
    denumire: str
    cod_cim10: str | None      # e.g. "I21.4"

class LabValue(BaseModel):
    test_name: str
    test_abbreviation: str | None
    value_raw: str
    value_numeric: float | None
    unit_raw: str | None
    unit_ucum: str | None
    flagged: bool = False      # HP-04: asterisk prefix
    loinc_code: str | None

class LabResults(BaseModel):
    bulletin_date: date | None
    cbc: dict[str, LabValue]
    biochemistry: dict[str, LabValue]
    hormones: dict[str, LabValue]
    other: dict[str, LabValue]

class ImagingResult(BaseModel):
    modality: str
    date: date | None
    institution: str | None
    conclusion: str
    is_current_visit: bool     # HP-12: True only if from THIS admission

class TNMStaging(BaseModel):
    t_category: str | None     # "pT2"
    n_category: str | None
    n_detail: str | None       # sentinel node info "0+/3 GS"
    m_category: str | None
    stage_group: str | None    # "I B"
    prefix: str | None         # "p", "c", "y", "r"
    modifiers: list[str]       # ["braf mutant", "op."]

class OncologyFields(BaseModel):
    cycle_number: int | None
    regimen_acronym: str | None
    ecog_score: int | None
    response_status: str | None   # "CR", "PR", "SD", "PD" — normalized codes
    tnm: TNMStaging | None
    molecular_markers: dict[str, str]  # {"BRAF": "V600E"}

class TransfusionRecord(BaseModel):
    blood_group: str
    rh: str
    product_type: str
    bag_number: str
    date: date | None

class AdminCheckboxes(BaseModel):
    readmission_required: bool | None
    readmission_timeframe_weeks: int | None
    prescription_issued: bool | None
    prescription_serial: str | None
    sick_leave_issued: bool | None
    sick_leave_serial: str | None
    home_care_referral_issued: bool | None
    medical_device_prescription_issued: bool | None
    document_transmission: str | None
    raw_groups: list[CheckboxGroup]

class AppointmentBlock(BaseModel):
    datetime_raw: str
    datetime_parsed: datetime | None
    location: str | None

class StructuredFields(BaseModel):
    doc_type: str                     # "DOC_HDR" | "DOC_BIS"
    nr_focg: str | None
    contract_number: str | None       # HP-08
    cnp: str | None
    dob_from_cnp: date | None         # HP-13: derived
    sex_from_cnp: str | None
    varsta: int | None
    sex_explicit: str | None
    grup_sangvin: str | None
    rh: str | None
    alergii: str | None
    data_internarii: datetime | None
    data_externarii: datetime | None
    sectia: str | None
    medic: str | None
    stare_externare: str | None
    diagnostic_principal: DiagnosticEntry | None
    diagnostice_secundare: list[DiagnosticEntry]
    confidence_score: float
    parsing_warnings: list[str]

class ProcedureEntry(BaseModel):       # new — previously missing
    date: date | None
    performed_age: str | None          # for relative temporal expressions
    description: str
    anatomical_site: str | None
    implants_inserted: list[str]
    implants_removed: list[str]

class EpicrizaExtracted(BaseModel):
    # current visit only (HP-12)
    motive_internare: list[str]
    examen_obiectiv: dict[str, str | None]
    current_labs_in_narrative: list[str]
    current_treatment_narrative: str | None
    clinical_status: str | None
    # historical (HP-12)
    antecedente_heredocolaterale: str | None
    antecedente_personale: list[str]
    history_timeline: list[dict]         # [{date, event_type, description}]
    procedures: list[ProcedureEntry]     # new — surgical and procedural history
    imaging_results: list[ImagingResult] # HP-18
    administered_in_hospital: list[str]

class MedicationEntry(BaseModel):
    medicament: str
    doza: str | None
    frecventa: str | None
    durata: str | None
    atc_code: str | None
    dose_is_total: bool = False          # HP-10: "DT" suffix
    is_complex_regimen: bool = False     # LLM-parsed conditional/cyclical
    raw: str

class MergedRecord(BaseModel):
    doc_type: str
    structured: StructuredFields
    labs: LabResults | None
    checkboxes: AdminCheckboxes | None
    appointment: AppointmentBlock | None
    epicriza: EpicrizaExtracted | None
    medications: list[MedicationEntry]
    oncology: OncologyFields | None
    transfusions: list[TransfusionRecord]
    overall_confidence: float
    all_warnings: list[str]
```

---

## 9. Claude API Prompt for Epicriza Extraction (Stage 4E)

The following system prompt and schema MUST be used verbatim.

**System Prompt:**
```
You are a medical data extraction engine for an EHDS-compliant FHIR pipeline.
You receive the Epicriza section of a Romanian clinical document. The document
may span multiple years of patient history.

CRITICAL RULES:
1. Return ONLY valid JSON. No markdown. No explanation. No preamble.
2. If a value is absent from the text, return null. NEVER infer or fabricate.
3. Separate CURRENT VISIT data from HISTORICAL data:
   - "current_visit": data about THIS specific admission/session only.
     Signaled by: "Actual, se prezinta...", "Se administreaza...",
     "In prezent...", or the most recent dated event.
   - "history_timeline": all prior events mentioned in the narrative.
4. Preserve original Romanian text for all string fields. Do not translate.
5. For imaging results: extract each separately with its date.
6. For surgical/procedural events: extract each as a procedure entry with
   date (YYYY-MM-DD or null), description, anatomical_site, implants array.
7. For relative temporal expressions ("la varsta de 3 saptamani", "dupa 12 ani"):
   return date as null and populate performed_age with the relative expression.
   NEVER infer an absolute date you cannot calculate from the text.
8. ECOG/IP/PS performance status -> oncology.ecog_score as integer.
```

**JSON Schema:**
```json
{
  "current_visit": {
    "motive_internare": ["string"],
    "examen_obiectiv": {"stare_generala": "string|null", "ta": "string|null",
                        "fc": "string|null", "spo2": "string|null",
                        "alte_semne": "string|null"},
    "clinical_status": "string|null",
    "administered_in_hospital": ["string"],
    "treatment_narrative": "string|null"
  },
  "history": {
    "antecedente_heredocolaterale": "string|null",
    "antecedente_personale_patologice": ["string"],
    "history_timeline": [
      {"date": "YYYY-MM-DD|null", "event_type": "diagnosis|surgery|treatment|imaging|lab|other",
       "description": "string"}
    ],
    "procedures": [
      {"date": "YYYY-MM-DD|null", "performed_age": "string|null",
       "description": "string", "anatomical_site": "string|null",
       "implants_inserted": ["string"], "implants_removed": ["string"]}
    ],
    "imaging_results": [
      {"modality": "string", "date": "YYYY-MM-DD|null", "institution": "string|null",
       "conclusion": "string", "is_current_visit": false}
    ]
  },
  "oncology": {
    "ecog_score": "integer|null",
    "response_status": "string|null",
    "tnm": {"t_category": "string|null", "n_category": "string|null",
            "n_detail": "string|null", "m_category": "string|null",
            "stage_group": "string|null", "modifiers": ["string"]},
    "molecular_markers": {}
  }
}
```

---

## 10. Absolute Rules (Never Violate)

**R1 — Fail Closed. No Hallucination.** If the source document does not contain data to populate a field, output `DataAbsentReason` or `null`. NEVER infer or synthesize clinical data. Use extension `"data-absent-reason"` with `valueCode "unknown"` for missing mandatory fields. Zero exceptions.

**R2 — CodeableConcept Integrity.** All clinical codes MUST be expressed as `CodeableConcept` with `system` (canonical URL), `code` (validated string), and `display` (human label). Raw strings in clinical coding fields are FORBIDDEN.

**R3 — Temporal Precision.** Datetimes MUST include Romania\'s UTC offset (`+02:00` or `+03:00`). Date-only fields use `YYYY-MM-DD`. All Romanian date formats normalize to ISO 8601 via `utils/date_parser.py`.

**R4 — UUID per Resource.** Every FHIR resource gets `uuid.uuid4()` as its id, formatted as `"urn:uuid:..."`. Never reuse or hardcode UUIDs.

**R5 — No Custom Extensions.** Only use FHIR extensions from `https://hl7.eu/fhir/extensions`. No bespoke extension URLs.

**R6 — CIM-10 Dual Coding.** Romanian CIM-10 codes \\u2192 SNOMED CT primary + ICD-10 secondary within the same `CodeableConcept`. ICD-10 is for billing traceability only; SNOMED CT is the clinical truth for cross-border exchange. Never use DRG administrative codes as deterministic SNOMED CT mappings.

**R7 — Core Set Validation Gate.** Missing `Patient` (no CNP AND no Nume) \\u2192 `CoreSetError` (blocks). Missing admission date \\u2192 `CoreSetError` (blocks). Missing narrative/epicriza \\u2192 `CoreSetError` (blocks). Missing `Practitioner` \\u2192 `ParseWarning` (non-blocking, `DataAbsentReason`).

**R8 — Document Classification First.** Zone detection, field extraction, and FHIR assembly MUST NOT begin until Stage 2 classification has successfully completed.

**R9 — Never Hardcode Clinical Values.** Reference ranges, normal values, drug dosages, or any clinical reference data MUST NOT be hardcoded in pipeline logic. The pipeline extracts only what is IN the document.

---

## 11. Project File Structure

```
ehds-pipeline/
├── pyproject.toml
├── .env.example                         # ANTHROPIC_API_KEY, DATABASE_URL,
│                                        # HAPI_FHIR_BASE_URL, PDF_OCR_LANG=ron
├── docker-compose.yml                   # HAPI FHIR (8080) + PostgreSQL (5432)
│
├── app/
│   ├── main.py
│   ├── config.py                        # Pydantic Settings
│   ├── api/v1/routes.py                 # POST /extract, GET /bundle/{id}
│   │
│   ├── pipeline/
│   │   ├── stage0_forensics.py          # PDF type detection
│   │   ├── stage1_extract.py            # Text extraction + page join (HP-07)
│   │   ├── stage1b_checkboxes.py        # HP-01: All 3 checkbox forms
│   │   ├── stage2_classify.py           # HP-15/R8: Document classification
│   │   ├── stage3_zones.py              # Type-specific zone detection
│   │   ├── stage4a_structured.py        # HP-02/08/13: Demographics + dates
│   │   ├── stage4b_labs.py              # HP-03/04/05/16: Lab extraction
│   │   ├── stage4c_checkboxgroups.py    # HP-01: Checkbox semantic mapping
│   │   ├── stage4d_appointment.py       # HP-09: Appointment extraction
│   │   ├── stage4e_epicriza.py          # HP-07/12/18: Claude API extraction
│   │   ├── stage4f_medications.py       # Simple linear medication parsing
│   │   ├── stage4g_oncology.py          # HP-10/11: Oncology-specific fields
│   │   ├── stage5_merge.py              # HP-13/R7: Pydantic Sentry
│   │   ├── stage6_fhir.py               # HP-17: FHIR resource builders
│   │   ├── stage7_bundle.py             # HP-15: Bundle assembly
│   │   ├── stage8_upload.py             # HAPI FHIR upload
│   │   └── stage9_provenance.py         # NEW: Provenance + SHA-256 + attester
│   │
│   ├── models/
│   │   ├── internal.py                  # All Pydantic intermediate models
│   │   └── fhir_profiles.py             # EEHRxF constraints on fhir.resources
│   │
│   ├── terminology/
│   │   ├── cim10_to_snomed.py
│   │   ├── atc_lookup.py
│   │   ├── loinc_map.py
│   │   └── oncology_terms.py
│   │
│   └── utils/
│       ├── date_parser.py               # HP-06
│       ├── cnp_parser.py                # HP-13
│       ├── numeric.py                   # HP-16
│       └── text_clean.py                # HP-07
│
└── tests/
    ├── fixtures/
    │   ├── oncohelp_bilet_de_iesire.txt
    │   ├── bilet_de_externare.txt
    │   └── expected_bundles/
    ├── test_stage1_checkboxes.py        # All 3 forms; None vs False
    ├── test_stage2_classify.py          # DOC_HDR, DOC_BIS, DOC_SM, UNKNOWN
    ├── test_stage4a_structured.py       # Dates (all 7), FO+contract, blank fields
    ├── test_stage4b_labs.py             # Superscript repair, asterisk flag, decimal
    ├── test_stage4c_checkboxgroups.py   # Semantic mapping, None vs False
    ├── test_stage4e_epicriza.py         # Current vs historical; procedures
    ├── test_stage4g_oncology.py         # TNM, ECOG, cycle, response
    ├── test_stage5_merge.py             # CoreSetError conditions
    └── test_bundle.py                   # End-to-end: Composition.type, Encounter.class
```

---

## 12. Security, Authentication & Pillar 2 Anonymization

### SMART on FHIR (Pillar 1)

OAuth 2.0 Authorization Code Grant with PKCE (S256) is mandatory. The `fhirUser` claim within the OIDC ID token resolves session identity to a specific `Practitioner` or `Patient` resource. Token validation: `iss` (validate issuer), `aud` (verify matches FHIR base URL), `exp` (enforce short-lived tokens). Granular scopes: `patient/Condition.read`, never broad `user/*.read`. EEHRxF mandates: IHE MHD (document operations), IHE PDQm (patient matching), HL7 SMART Backend Services / IHE IUA (system-to-system authorization).

### Pillar 2 De-identification Layer

Simply scrubbing `Patient.name` and CNP is insufficient. The remaining structured clinical timeline acts as a cryptographic fingerprint. Full compliance requires a dedicated post-FHIR-assembly layer implementing: (1) **PII Stripping** of names, addresses, identifiers; (2) **Temporal Shifting (\\u0394t)** — all dates per patient shifted by a consistent random integer; (3) **Categorical Generalization** — rare diagnoses generalized to parent SNOMED concepts via the `is-a` hierarchy traversal until k-anonymity threshold is met; (4) **K-Anonymity Enforcement** — any quasi-identifier combination identifying fewer than k individuals must be suppressed or generalized.

---

## 13. Synthetic Data Strategy: Synthea

Synthea (MITRE Corporation) generates complete medical histories in HL7 FHIR R4 format with no privacy restrictions. It is the mandated synthetic data source for all development and testing.

**Development loop:** (1) Take a Synthea FHIR R4 bundle; (2) prompt Claude API to render it as a realistic Romanian free-text discharge note; (3) feed that free text into the extraction pipeline; (4) compare output FHIR bundle against the original Synthea bundle — measurable input\\u2192output loop.

| Dataset | URL |
|---|---|
| 1K Sample Patients (FHIR R4) | https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_fhir_r4_sep2019.zip |
| Main downloads page | https://synthea.mitre.org/downloads |
| GitHub (generate custom) | https://github.com/synthetichealth/synthea |

---

## 14. Validation Resources & Reference URLs

| Resource | URL |
|---|---|
| HL7 Europe HDR IG | https://hl7.eu/fhir/hdr/ |
| HL7 IPS IG | https://hl7.org/fhir/uv/ips/ |
| HL7 Europe Base R4 | https://hl7.eu/fhir/base |
| FHIR R4 Resource Index | https://hl7.org/fhir/R4/resourcelist.html |
| HAPI FHIR Validator | https://hapifhir.io |
| Official FHIR Validator | https://validator.fhir.org |
| SNOMED CT Browser | https://browser.ihtsdotools.org |
| LOINC Search | https://loinc.org/search |
| UCUM Units | https://ucum.org/ucum |
| ATC Index WHO | https://www.whocc.no/atc_ddd_index/ |
| EU Health Data API (EEHRxF) | https://euridice.org/eu-health-data-api/ |
| HAPI FHIR Docker | https://hub.docker.com/r/hapiproject/hapi |
| fhir.resources (PyPI) | https://pypi.org/project/fhir.resources/ |
| pymupdf (fitz) | https://pymupdf.readthedocs.io |
| pdfplumber | https://github.com/jsvine/pdfplumber |
| Synthea | https://github.com/synthetichealth/synthea |

---

*This document is the definitive Source of Truth for the EHDS-compliant medical document pipeline. Failure to adhere to these specifications constitutes a regulatory breach. All architectural decisions must be traceable to the regulatory, semantic, and technical constraints defined here.*
