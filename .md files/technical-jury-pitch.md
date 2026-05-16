# EHDS.Pipeline — Semi-Technical Jury Pitch
### HackTM 2026 · Technical Jury · Table Visit (3–5 min) + On-Stage (3 min)

---

## The Problem in One Sentence

Romanian private clinics generate patient records in a format no EU health system can read — and a law already in force mandates the conversion by 2029 or faces €20M penalties.

---

## Why This Is a Hard Engineering Problem

The regulation is straightforward: output HL7 FHIR R4 Bundles that conform to the EEHRxF spec. The gap is in the input.

Romanian medical documents span three generations of technology and no common schema:

| Era | Document type | What makes it hard |
|---|---|---|
| 2009 — public hospitals | Scanned PDF, narrative prose | OCR + free-text only, cyclical drug regimens, no structure |
| 2010–2011 — orthopedic | Typed forms | Surgical hardware tracking, multi-column tables, no field delimiters |
| 2026 — private oncology | Digitally generated | TNM staging notation, treatment cycle tracking, Unicode checkboxes |

A single pipeline must handle all three. Regex breaks on the first. Template parsing breaks on the second. LLM-only breaks on all three (hallucinated clinical codes).

---

## Architecture: 9 Stages, Each with a Distinct Responsibility

```
Stage 0  PDF Forensics        digital vs. scanned, AcroForm widget detection
Stage 1  Text Extraction       pdfplumber (digital) | pytesseract lang=ron (scanned)
Stage 1B Checkbox Extraction   AcroForm → Unicode (U+2612) → OCR [X] — in that order
Stage 2  Classification        DOC_HDR / DOC_BIS / DOC_SM — MUST complete before anything else
Stage 3  Zone Detection        type-specific anchor matching; missing anchor → "" not exception
Stage 4  Field Extraction      structured fields · labs · checkboxes · appointments ·
                               LLM narrative · medications · oncology (7 parallel sub-stages)
Stage 5  Pydantic Sentry       CoreSetError (blocks) vs. ParseWarning (non-blocking)
Stage 6  FHIR Assembly         15 resource types: Patient, Encounter, Condition,
                               MedicationRequest, Observation, Procedure, Device,
                               DeviceUseStatement, AdverseEvent, DiagnosticReport,
                               CarePlan, Appointment, AllergyIntolerance,
                               Practitioner, PractitionerRole
Stage 7  Bundle Assembly       Composition as legal spine; LOINC doc type per class
Stage 8  HAPI FHIR Upload      validated against HAPI Validator before POST
Stage 9  Provenance            SHA-256(source PDF) + model version + attester
```

The stage ordering is not arbitrary. Classification at Stage 2 gates everything downstream — the wrong document type means wrong zone anchors, which silently corrupts all extracted data.

---

## Where AI Fits — and Where It Deliberately Does Not

### What the LLM does

Stage 4 uses Claude (claude-sonnet-4-6) via structured extraction with Instructor + Pydantic. The LLM receives the Epicriza zone and outputs JSON conforming to a strict schema.

The LLM extracts **text only** — never codes.

```
Input:  "alternativ cu Encephabol, 10 zile pe luna, sub protectie de Fenobarbital"
LLM output: { "drug": "Encephabol", "schedule": "10 zile pe luna",
              "concurrent_medication": "Fenobarbital" }
Code resolution: ATC lookup → deterministic map, never LLM
```

A regex parser or rule engine cannot handle conditional, cyclical, and alternating regimens from 2009 public hospital narrative. The LLM can. But the LLM is explicitly forbidden from emitting SNOMED CT codes, LOINC codes, or ATC codes — it does not know if the code is current or hallucinated.

The LLM also separates `current_visit` from `history_timeline` — critical because an Epicriza can contain 10 years of patient history interleaved with the current admission. Mixing historical imaging with current results is a patient safety error.

### What deterministic code does

Terminology resolution is fully deterministic:

| Code system | Resolved by |
|---|---|
| LOINC | `terminology/loinc_map.py` — static map, 40+ lab tests |
| ATC | `terminology/atc_lookup.py` — Romanian trade name → WHO ATC |
| SNOMED CT | `terminology/cim10_to_snomed.py` — CIM-10 → SNOMED (50+ diagnoses) |
| SNOMED fallback | Snowstorm public FHIR server query — only for unmapped codes |

No code is emitted from the LLM. Every code either hits the local map or returns `DataAbsentReason`. **The AI doesn't guess. It either produces valid FHIR or it stops.**

---

## The 5 Hardest Problems Solved

**1. Superscript loss in lab values**
PDF extractors drop superscripts: `"5.79 109/L"` instead of `5.79 × 10⁹/L`. A normalization regex runs before any lab parsing and reconstructs the scientific notation, then maps to UCUM unit `"10*9/L"`. Global find-and-replace is banned — it corrupts comma list separators.

**2. Three checkbox extraction methods in one document**
DOC_BIS forms contain administrative checkboxes that can appear as: (a) AcroForm PDF widgets (not in text stream — requires pymupdf page.widgets()), (b) Unicode characters U+2612/U+2610 in the pdfplumber stream, or (c) OCR-produced `[X]`/`[ ]`. The pipeline tries all three in order and emits a warning only if none are found. `None` (group absent) and `False` (group present, unchecked) are semantically distinct values that must never collapse.

**3. Multi-column demographics tables without grid borders**
DOC_BIS headers are 3-column printed tables. When pdfplumber finds no table borders, the fallback is coordinate-based word clustering by y-band and x-band. Column thresholds are in a config file, never hardcoded — different HIS rendering engines (Crystal Reports, JasperReports) produce different column widths.

**4. TNM oncology staging notation**
Input: `"pT2n0(0+/3 GS)m0 braf mutant st. I B op."` — case-insensitive, with prefix, sentinel node detail, and modifiers inline. One regex captures T/N/M/Stage/prefix/modifiers. Each component maps to its own SNOMED-coded Observation resource. BRAF V600E maps to LOINC 51971-4. This is not cosmetic — these are the codes that determine treatment eligibility at receiving EU health systems.

**5. Longitudinal history separation**
An Epicriza is not limited to the current admission — it can contain 10+ years of history. The LLM prompt explicitly enforces the separation via `current_visit` vs. `history_timeline` schema fields, with signal phrases (`"Actual, se prezinta..."`, `"Se administreaza..."`) as anchors. Historical imaging populates separate DiagnosticReport resources, never mixed with current-visit Observations.

---

## Fail-Closed Design (the clinical safety architecture)

The pipeline validates at Stage 5 with a hard gate:

```python
CoreSetError (pipeline blocks) if:
  - Patient has no CNP AND no name
  - Admission date is absent
  - Epicriza/narrative is absent

ParseWarning (non-blocking) if:
  - Practitioner name is absent → DataAbsentReason on Practitioner
  - Any non-mandatory field is missing

DataAbsentReason everywhere else
```

A document that fails the CoreSet gate does not produce a partial FHIR Bundle with null fields. It returns an error with the exact blocking reason. Partial compliance is worse than no compliance — a downstream system that consumes a bundle missing the patient identifier is a patient safety incident, not a UX issue.

---

## What the Demo Shows

A real oncology Bilet de Ieșire from a private Timișoara clinic enters the pipeline:

1. Classifier outputs `DOC_BIS` → selects correct zone anchors and LOINC `34133-9`
2. Stage 4B: CBC with superscript repair, asterisk-flagged values → `Observation.interpretation = "A"`
3. Stage 4E: Claude separates 3 years of melanoma history from the current Nivolumab cycle (cycle 38)
4. Stage 4G: `pT2n0m0 st. IB` → 4 separate SNOMED-coded Observation resources
5. Output: validated FHIR Bundle, 15 resource types, SHA-256 provenance, HAPI Validator green pass

End-to-end: under 15 seconds.

---

## Stack Summary

| Layer | Technology |
|---|---|
| API | Python 3.12 + FastAPI |
| LLM extraction | Anthropic SDK — claude-sonnet-4-6, Instructor, Pydantic v2 |
| FHIR modeling | `fhir.resources` ≥7.0 (native R4 Pydantic models) |
| PDF digital | pdfplumber |
| PDF forms | pymupdf (AcroForm widgets) |
| PDF scanned | pytesseract lang=ron + pdf2image dpi=300 |
| FHIR server | HAPI FHIR (Docker, localhost:8080) |
| Terminology | Local maps + Snowstorm public FHIR fallback |

---

## Technical Q&A

**"Why not a single LLM call for the whole document?"**
An LLM processing a raw 6-page discharge report produces inconsistently structured output and cannot be validated field-by-field. The 9-stage architecture gives each layer a narrow, testable contract. The LLM handles only the zone where structure is semantically unavailable — the narrative Epicriza — and even there it outputs a Pydantic-validated schema, not free-form JSON.

**"How do you prevent SNOMED code hallucination?"**
By architectural constraint. The LLM schema has no field typed as `snomed_code`, `loinc_code`, or `atc_code`. It is structurally impossible for the LLM to emit a code. Codes are assigned in a separate deterministic pass after extraction completes.

**"How do you test a pipeline that depends on an LLM?"**
We use Synthea FHIR R4 bundles as ground truth. Claude renders each synthetic bundle as a realistic Romanian clinical note; we run the pipeline on that note and compare the output bundle against the original Synthea input. This gives a measurable extraction fidelity loop with no real patient data and no manual labeling.

**"What's the FHIR compliance story — is this IPS or HDR?"**
Both. The pipeline targets two EEHRxF priority categories: Patient Summary (HL7 IPS v2.0, deadline 2029) and Hospital Discharge Report (HL7 Europe HDR v0.1.0-ballot, deadline 2031). The `Composition.type` LOINC code is set per document class at bundle assembly time — `34105-7` for inpatient HDR, `34133-9` for ambulatory summaries.

**"What about Pillar 2 — secondary use / research data?"**
Pillar 2 requires de-identification beyond name removal. A patient with a rare diagnosis and exact surgery dates at a specific hospital has k=1 even after PII stripping. The roadmap includes: temporal shifting (consistent per-patient Δt applied to all dates), categorical generalization (rare SNOMED codes generalized up the `is-a` hierarchy until k-anonymity threshold is met), and explicit patient Opt-Out gating in the ingestion pipeline. This is a post-FHIR-assembly layer, not a property of the extraction pipeline.

---

*Technical jury reference document — HackTM 2026.*
