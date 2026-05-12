# Technical Blueprint and Source of Truth: EHDS-Compliant Health Information System

---

## 1. Regulatory Guardrails: EHDS & EEHRxF Framework

System architecture MUST align with the European Health Data Space (EHDS) regulatory timeline to ensure market access and cross-border trust. The EHDS Regulation (EU) 2025/327 was adopted February 11, 2025, published March 5, 2025, and entered into force on **March 26, 2025**. Compliance with its harmonized legal and technical standards serves as the non-negotiable baseline for the internal market. The MyHealth@EU infrastructure demands immediate architectural readiness for the European Electronic Health Record Exchange Format (EEHRxF), which dictates the data lifecycle from capture to secondary repurposing.

### Pillar 1 (Primary Use) vs. Pillar 2 (Secondary Use)

The EHDS Regulation establishes a strict legal and operational dichotomy between primary and secondary data utilization:

- **Pillar 1 (Primary Use):** Governs data exchange for healthcare delivery. Systems SHALL facilitate individual access and sharing of health data (Patient Summaries, ePrescriptions) across Union borders. Access is limited to authorized health professionals for direct patient care, aiming to eliminate duplicative testing and administrative friction.
- **Pillar 2 (Secondary Use, EHDS2):** Governs data reuse for research, innovation, and policy-making. Access is strictly contingent upon a "data permit" from a Health Data Access Body (HDAB). Data MUST be processed within a Secure Processing Environment (SPE). Using data for detrimental purposes — such as insurance premium hikes or predatory marketing — is strictly prohibited and carries severe legal penalties.

**The "Opt-Out" Impact:** The platform MUST implement a robust "Opt-Out" mechanism. While patients hold the right to restrict cross-border primary use and secondary research use, the system MUST maintain granular metadata to reflect these preferences. From a technical perspective, the "Opt-Out" choice determines the availability of records in the discovery layer, requiring dynamic filtering in the ingestion and egress pipelines.

### Implementation Timeline

| Milestone Date | Requirement / Event |
|---|---|
| March 26, 2025 | EHDS Regulation enters into force. Beginning of the transition phase. |
| March 2027 | Deadline for the Commission to adopt key implementing acts and EEHRxF technical specifications. |
| March 2029 | **Mandatory:** Patient Summaries & ePrescriptions/eDispensations exchange operational in all EU member states. Secondary use rules apply for most EHR data categories. |
| March 2031 | **Mandatory:** Hospital Discharge Reports, medical images, and laboratory results operational for primary use. Remaining secondary use categories (e.g. genomic data) activate. |
| March 2034 | Third countries and international organizations may apply to join HealthData@EU for secondary use. |

---

## 2. The Six Priority Data Categories (EEHRxF Scope)

The EHDS defines six priority categories of health data subject to EEHRxF compliance. Each maps to a specific HL7 Europe FHIR Implementation Guide (IG). These are the **exact input types this system is designed to process**.

| EHDS Priority Category | HL7 FHIR Implementation Guide | Rollout Wave |
|---|---|---|
| Patient Summaries | HL7 International Patient Summary (IPS) v2.0 | 2029 |
| Electronic Prescriptions | HL7 Europe Medication Prescription & Dispense | 2029 |
| Electronic Dispensations | HL7 Europe Medication Prescription & Dispense | 2029 |
| Medical Imaging Studies & Reports | HL7 Europe Imaging Report | 2031 |
| Lab Results / Diagnostic Reports | HL7 Europe Laboratory Report (v0.1.1) | 2031 |
| **Hospital Discharge Reports** | **HL7 Europe Hospital Discharge Report (v0.1.0-ballot)** | **2031** |

This system targets the **Patient Summary** and **Hospital Discharge Report** categories as its primary scope, as these represent both the highest-frequency clinical documents and the most information-dense transformation challenge (unstructured free text → structured FHIR).

### Key Implementation Guide URLs

| IG | URL |
|---|---|
| HL7 IPS (Patient Summary) | https://hl7.org/fhir/uv/ips/ |
| HL7 Europe Hospital Discharge Report | https://hl7.eu/fhir/hdr/ |
| HL7 Europe Lab Report | https://hl7.eu/fhir/laboratory/ |
| HL7 Europe Base & Core FHIR IG (R4) | https://hl7.eu/fhir/base |
| HL7 Europe Extensions | https://hl7.eu/fhir/extensions |
| EU Health Data API (EEHRxF interop spec) | https://euridice.org/eu-health-data-api/ |
| FHIR R4 Specification | https://hl7.org/fhir/R4/ |
| HAPI FHIR Public Test Server | https://hapi.fhir.org/baseR4 |

---

## 3. The Interoperability Schema: Pillar 1 Data Modeling

HL7 FHIR R4 is the technical backbone of EHDS. Systems MUST ensure absolute semantic consistency to enable machine-to-machine understanding across different linguistic and clinical contexts.

### FHIR Document Structure

A FHIR Document is a `Bundle` resource with `type: document`. The structure is always:
- **Entry 0:** `Composition` resource — the "table of contents" and document spine. This is what the clinician signs. It references all other entries.
- **Entries 1..N:** All referenced FHIR resources (Patient, Condition, MedicationRequest, etc.)

The `Composition` is the single most critical resource to implement correctly. It SHALL include a status of `"final"` and a LOINC document type code to identify the document category (e.g., HDR vs. Patient Summary).

### International Patient Summary (IPS) — Required Sections & FHIR Resources

An IPS document is an electronic health record extract containing essential, minimal, specialty-agnostic healthcare information about a subject of care (ISO 27269 / EN 17269).

| IPS Section | Corresponding FHIR Resource(s) | Binding |
|---|---|---|
| Patient demographics | `Patient` | Mandatory |
| Current problems / diagnoses | `Condition` | SNOMED CT (GPS) |
| Allergies & intolerances | `AllergyIntolerance` | SNOMED CT |
| Current medications | `MedicationStatement` / `MedicationRequest` | ATC / RxNorm |
| History of procedures | `Procedure` | SNOMED CT |
| Immunizations | `Immunization` | SNOMED CT |
| Lab results / observations | `Observation`, `DiagnosticReport` | LOINC |
| Medical devices | `DeviceUseStatement` | SNOMED CT |
| Vital signs | `Observation` | LOINC |
| Functional status | `ClinicalImpression` / `Observation` | SNOMED CT |
| Advance directives | `Consent` | — |
| Alerts | `Flag` | — |
| History of pregnancy | `Observation` (LOINC-coded) | LOINC |

### Hospital Discharge Report (HDR) — Required Sections & FHIR Resources

The HDR builds on the IPS but adds admission/discharge context. All sections below are part of the HL7 Europe HDR IG.

| HDR Section | FHIR Resource(s) | Notes |
|---|---|---|
| Patient identification | `Patient` | Mandatory (EEHRxF A.1.1) |
| Responsible clinician | `Practitioner`, `PractitionerRole` | Mandatory (EEHRxF A.1.4) |
| Admission & discharge info | `Encounter` | Mandatory (EEHRxF A.2.1): dates, reason |
| Narrative clinical summary | `Composition.section.text` | Mandatory (EEHRxF A.2.0): free text block |
| Admission diagnosis | `Condition` (encounter-diagnosis) | SNOMED CT |
| Discharge diagnosis (primary + secondary) | `Condition` | SNOMED CT |
| Hospital course / procedures | `Procedure` | SNOMED CT |
| Discharge medications (with changes) | `MedicationRequest` | ATC / SNOMED CT |
| Lab results during admission | `Observation`, `DiagnosticReport` | LOINC |
| Follow-up instructions | `CarePlan`, `ServiceRequest` | — |
| Referrals | `ServiceRequest` | — |
| Functional status at discharge | `Observation` / `ClinicalImpression` | SNOMED CT |

### EEHRxF Mandatory Fields for Discharge Reports — "Core Set"

To mitigate clinician burnout while ensuring interoperability, the XpanDH and EEHRxF guidelines establish a "Core Set" of mandatory elements. The "Full Set" (e.g., A.1.6 Nursing Notes) represents a target for future maturity but MUST NOT block transmission of a valid HDR if unavailable.

**Mandatory Core Set Elements:**
- **A.1.1 Patient Identification:** Mandatory demographics and identifiers.
- **A.1.4 Health Professional:** Identification of the clinician responsible for the report.
- **A.2.1 Admission and Discharge Information:** Mandatory dates, reason for encounter, and summary findings.
- **A.2.0 Narrative Report:** The full free-text form of the report — the primary human-readable clinical summary.

> **Architectural Rule:** The "Core Set" is the only hard validation gate in the pipeline. Architects SHALL prioritize automated extraction and validation of these fields. Optional "Full Set" elements MUST NOT block transmission of a valid HDR if unavailable.

### Core FHIR R4 Resource Constraints

Development teams SHALL implement the following resource constraints based on IPS and EEHRxF profiles:

- **Patient:**
  - `birthTime` SHALL be precise to the Year (CONF: 1198-5299).
  - `birthTime` SHOULD be precise to the Day (CONF: 1198-5300).
  - Mandatory administrative gender and unique European identifiers are required.
- **Composition:** SHALL include `status: "final"` and a LOINC document type code (SCALE = DOC).
- **Condition:** SHALL include `clinicalStatus` (active/resolved) and `verificationStatus`.
- **MedicationStatement:** SHALL express medication intent and timing. If intent is missing from source data, the system SHALL return a `NullFlavor`.

### Semantic Interoperability & Terminology Bindings

To facilitate automated processing across European languages, terminology bindings are mandatory:

- **SNOMED CT:** Mandatory for clinical findings, disorders, and procedures. Systems SHALL prioritize the Global Patient Set (GPS) and the CORE Problem List Subset.
- **LOINC:** Mandatory for identifying document types and laboratory observations.
- **ATC (WHO Anatomical Therapeutic Chemical):** Used for medication coding where RxNorm is not available.

### Document Architecture: Narrative vs. Entry

The system SHALL treat the Narrative block (`Composition.section.text`) as the authenticated content (human-readable). The Entry blocks (FHIR resources) provide machine-readable discrete data.

- **Narrative:** What the clinician signs. The legal clinical record.
- **Entry:** What the system uses for automated safety checks (e.g., drug-drug interactions, duplicate detection, cross-border access).

---

## 4. Input Data Reality: Raw Text to FHIR

### What "Raw" Medical Data Looks Like

Hospitals today produce discharge reports and patient summaries as **free-text documents** (PDFs, Word docs, proprietary EHR exports, printed scans). A realistic discharge report fragment:

```
RAPORT DE EXTERNARE
Pacient: Ion Popescu, 67 ani, M
Internat: 12.04.2025 | Externat: 17.04.2025
Diagnostic principal: Infarct miocardic fără supradenivelare ST (NSTEMI)
Comorbidități: HTA grad II, Diabet zaharat tip 2
Investigații: Troponina I = 1.8 ng/mL (crescut), EKG: modificări în V3-V5
Tratament la externare: Aspirina 100mg/zi, Atorvastatina 40mg/zi, Bisoprolol 5mg/zi
Recomandări: Control cardiologie peste 4 săptămâni.
```

### What the Pipeline Must Extract and Map

From the above, the system must produce:

| Extracted Entity | FHIR Resource | Code System | Code |
|---|---|---|---|
| Patient: Ion Popescu, 67M | `Patient` | — | demographics |
| Admission date: 12.04.2025 | `Encounter.period.start` | — | ISO 8601 |
| Discharge date: 17.04.2025 | `Encounter.period.end` | — | ISO 8601 |
| NSTEMI (primary Dx) | `Condition` | SNOMED CT | `401303003` |
| Hypertension Gr. II | `Condition` | SNOMED CT | `73410007` |
| Type 2 Diabetes | `Condition` | SNOMED CT | `44054006` |
| Troponin I = 1.8 ng/mL | `Observation` | LOINC | `10839-9` |
| ECG finding V3-V5 | `DiagnosticReport` | LOINC | `11524-6` |
| Aspirin 100mg/day | `MedicationRequest` | ATC | `B01AC06` |
| Atorvastatin 40mg/day | `MedicationRequest` | ATC | `C10AA05` |
| Bisoprolol 5mg/day | `MedicationRequest` | ATC | `C07AB07` |
| Cardiology follow-up | `CarePlan` / `ServiceRequest` | SNOMED CT | — |

The assembled output is a `Bundle` of type `document` containing a `Composition` referencing all of the above resources.

---

## 5. Synthetic Data Strategy: Synthea

Since real patient data cannot be used for development, **Synthea** is the mandated synthetic data source for all development, testing, and demonstration purposes.

**Synthea** (developed by MITRE Corporation) is an open-source synthetic patient generator that produces complete medical histories — medications, allergies, medical encounters, social determinants of health — exported in HL7 FHIR R4 format. The resulting data carries no cost, privacy, or security restrictions.

### Download Sources

| Dataset | URL | Notes |
|---|---|---|
| 1K Sample Patients (FHIR R4) | https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_fhir_r4_sep2019.zip | Best starting point |
| Synthea main downloads page | https://synthea.mitre.org/downloads | Multiple sizes and formats |
| GitHub (generate custom data) | https://github.com/synthetichealth/synthea | Java, run locally |
| Coherent Dataset (9GB) | https://registry.opendata.aws/synthea-coherent-data/ | Includes DICOM, ECG, clinical notes |
| Bulk FHIR sample datasets | https://github.com/smart-on-fhir/sample-bulk-fhir-datasets | ndjson format, 100-patient sets |

### Synthea FHIR R4 Bundle Structure

Each Synthea patient export is a `Bundle` of type `transaction` containing:
- One `Patient` resource (first entry)
- `Organization`, `Practitioner`
- `Encounter` (one per clinical visit)
- `Condition` (per diagnosis)
- `Observation` (vitals, labs — many entries)
- `MedicationRequest`
- `Procedure`
- `CarePlan`, `Immunization`, `AllergyIntolerance`

### Hackathon Data Pipeline Strategy

Use Synthea-generated FHIR R4 bundles as **ground-truth output**. To generate realistic unstructured input for the extraction demo:
1. Take a Synthea FHIR bundle for a patient.
2. Prompt an LLM (Claude API) to render it as a realistic free-text discharge note in the appropriate clinical language (Romanian or English).
3. Feed that free text back into the extraction pipeline.
4. Compare the pipeline's FHIR output against the original Synthea bundle — this gives you a measurable, demonstrable input→output loop.

---

## 6. Technical Pipeline Architecture

The ingestion pipeline functions as a **"Zero-Trust Data Factory."** No data SHALL be persisted without schema and terminology validation.

### Ingestion-to-Bundle Logic Gate

```
[INPUT LAYER]
Raw discharge PDF / plaintext / CDA/XML
         ↓
[UNSTRUCTURED CONTENT GATE]
If non-XML (PDF/A-1b): wrap in nonXMLBody component
  └── text element: type ED (Encapsulated Data)
  └── @representation="B64", @mediaType="application/pdf"
  └── (CONF: 1198-7624, CONF: 1198-7623)
If structured XML/JSON: proceed directly to mapping
         ↓
[AI EXTRACTION LAYER]  ← Core intelligence
OpenRouter API (medgemma-27b / Claude sonnet 4)
  ├── Named Entity Recognition: diagnoses, medications, dates, vitals, clinicians
  ├── Terminology Mapping: entity text → SNOMED CT / LOINC / ATC codes
  ├── Missing data handling: return DataAbsentReason / NullFlavor — NEVER infer
  └── Output: structured JSON matching FHIR resource schemas
         ↓
[MAPPING LAYER]
Structured JSON → FHIR R4 Resources
  ├── Patient, Practitioner, PractitionerRole
  ├── Encounter (admission/discharge)
  ├── Condition (diagnoses with SNOMED CT codes)
  ├── MedicationRequest (with ATC codes)
  ├── Observation (labs, vitals with LOINC codes)
  ├── Procedure, DiagnosticReport
  └── CarePlan, ServiceRequest (follow-up)
         ↓
[VALIDATION LAYER: "Pydantic Sentry"]
Strict Pydantic schemas enforce FHIR StructureDefinitions
  ├── EEHRxF Core Set fields validated (A.1.1, A.1.4, A.2.0, A.2.1)
  ├── Terminology codes validated against SNOMED CT + LOINC versions
  ├── Missing mandatory field → DataAbsentReason (UNK / NA) — NOT hallucination
  └── "Terminology Error" → flag for manual remediation workflow
         ↓
[ASSEMBLY LAYER]
Build FHIR Bundle (type: document)
  ├── Entry 0: Composition (signed document, references all entries)
  ├── Entry 1: Patient
  └── Entries 2..N: all referenced resources
         ↓
[OUTPUT]
Valid FHIR R4 Document (JSON)
+ Human-readable HTML narrative rendering
+ FHIR server upload (HAPI FHIR)
+ Opt-Out metadata flags attached to Bundle.meta
```

### Recommended Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| API / Backend | Python + FastAPI | Rapid development, Pydantic native, async support |
| AI Extraction | Claude API (`claude-sonnet-4-20250514`) with tool use | Structured JSON output, anti-hallucination control |
| FHIR Resource Modeling | `fhir.resources` Python library | Native R4 Pydantic models |
| Validation | Pydantic v2 + HAPI FHIR Validator | Schema + terminology enforcement |
| FHIR Server (local demo) | HAPI FHIR (Docker) | Open-source, R4-compliant, free |
| Frontend | React + Next.js | Upload UI, FHIR Bundle viewer |
| Synthetic Data | Synthea FHIR R4 exports | Privacy-free ground truth |
| Terminology APIs | SNOMED CT browser + LOINC search | Code validation |

**HAPI FHIR Docker (local server for demo):**
```bash
docker run -p 8080:8080 hapiproject/hapi:latest
# FHIR base URL: http://localhost:8080/fhir
```

---

## 7. Anonymization & Security Protocol: Pillar 2 Compliance

### De-identification and PII Stripping

The pipeline SHALL remove all PII (Names, Addresses, IDs) before data enters the SPE. Following the Synthea/Denver synthetic population models, the system SHALL replace actual PII with realistic but synthetic demographic patterns (name, address, contact info) to support identity matching system testing without exposing real-world identities.

- **K-Anonymity:** Data MUST be aggregated or suppressed if a specific attribute combination identifies fewer than k individuals.
- **Re-identification:** Strictly FORBIDDEN. The system SHALL log and terminate any research session attempting to join datasets that could lead to identity disclosure.

### SMART on FHIR Security Implementation

The platform SHALL implement the OAuth 2.0 Authorization Code Grant Flow with the following mandates:

1. **PKCE:** Proof Key for Code Exchange (S256) is mandatory for all clients.
2. **Identity Resolution:** The system SHALL use the `fhirUser` claim within the OpenID Connect (OIDC) ID token to resolve the session identity to a specific `Practitioner` or `Patient` resource.
3. **Token Validation Checklist:**
   - `iss`: Validate the token issuer.
   - `aud`: Verify the audience matches the FHIR base URL.
   - `exp`: Enforce short-lived access tokens.
4. **Granular Scopes:** "Minimum Necessary Access." Systems SHALL request `patient/Condition.read` rather than broad `user/*.read` unless system-wide research permits are explicitly granted.

The EEHRxF interoperability specification mandates the following protocols per the EU Health Data API:
- **IHE MHD** — for publishing, searching, and retrieving EEHRxF FHIR Documents
- **IHE PDQm** — for patient matching across systems
- **HL7 IPA / IHE QEDm** — for querying individual FHIR resources
- **HL7 SMART Backend Services / IHE IUA** — for secure OAuth 2.0 system-to-system authorization

---

## 8. Agentic Protocol: Implementation Rules for AI & Engineers

These rules are non-negotiable for all human developers and AI coding agents.

### Strict Structural Rules

1. **CodeableConcept Integrity:** All clinical codes MUST be `CodeableConcept`, containing both the `system` (OID/URL) and the `code`. Raw strings in clinical fields are FORBIDDEN.
2. **Temporal Precision:** Dates and times MUST include time-zone offsets (e.g., `+01:00`) if the precision is higher than a day (CONF: 81-10130).
3. **Extension Control:** Custom extensions SHALL NOT be used unless registered in the EHDS central registry.
4. **Identifiers:** Every document and resource MUST include a globally unique identifier (UUID/OID).

### Terminology Enforcement

All codes SHALL be validated against current SNOMED CT and LOINC versions. If a code falls outside the mandatory value set, the system SHALL flag a "Terminology Error" and trigger a manual remediation workflow or return a `NullFlavor`.

### Anti-Hallucination Guardrail — "Fail Closed"

> **Command: "Fail Closed."** If the source context is insufficient to populate a mandatory EEHRxF field, the agent SHALL output the appropriate `DataAbsentReason` code. NEVER infer or synthesize clinical data.

- Use `UNK` (Unknown) for missing mandatory information.
- Use `NA` (Not Applicable) where the data element is not relevant to the case.
- This "Fail Closed" state prevents LLM hallucinations by ensuring clinical summaries are derived exclusively from verified, non-null data points.

---

## 9. Validation Resources & Tooling

| Tool | Purpose | URL |
|---|---|---|
| HAPI FHIR Validator | Validate FHIR R4 Bundle against StructureDefinitions | https://hapifhir.io |
| Official FHIR Validator (HL7) | CLI/web validator against any IG | https://validator.fhir.org |
| SNOMED CT Browser | Look up SNOMED codes (GPS/CORE subset) | https://browser.ihtsdotools.org |
| LOINC Search | Look up LOINC codes for labs / document types | https://loinc.org/search |
| HL7 Europe IG Ecosystem | All EU FHIR IGs in one place | https://hl7.eu |
| Synthea GitHub | Generate custom synthetic patient populations | https://github.com/synthetichealth/synthea |
| FHIR R4 Resource Index | Full list of resource types and schemas | https://hl7.org/fhir/R4/resourcelist.html |

---

*This blueprint constitutes the definitive Source of Truth for the safety, legality, and interoperability of the platform within the European Health Data Space. Failure to adhere to these specifications constitutes a regulatory breach.*
