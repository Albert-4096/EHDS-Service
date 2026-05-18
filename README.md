<div align="center">
  <img src="assets/banner.svg" alt="EHDS Service" width="100%">
</div>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19.2-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![FHIR](https://img.shields.io/badge/HL7_FHIR-R4-E8002D?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMSAxNEg5VjhIMTF2OHptNCAwaC0yVjhoMnY4eiIvPjwvc3ZnPg==&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)

**A production-grade AI pipeline that transforms Romanian medical records into HL7 FHIR R4 Bundles, fully compliant with EU Regulation 2025/327 (European Health Data Space).**

[Features](#features) · [Architecture](#architecture) · [Getting Started](#getting-started) · [API Reference](#api-reference) · [Roadmap](#roadmap)

</div>

---

## Overview

EHDS Service bridges the gap between legacy Romanian healthcare documents and the European Health Data Space (EHDS) by converting scanned PDFs, typed forms, and digital records into standards-compliant **HL7 FHIR R4 Bundles** — ready for cross-border exchange via the **MyHealth@EU** infrastructure.

The system implements a **9-stage AI extraction pipeline** and supports the two pillars defined under EU Regulation 2025/327:

| Pillar | Purpose | Data Handling |
|--------|---------|---------------|
| **Pillar 1** | Direct patient care | Full fidelity, no anonymization |
| **Pillar 2** | Research & analytics | k-anonymity, temporal shifting, opt-out enforcement |

> Designed to meet the **March 2031 mandate** for electronic Hospital Discharge Reports across all EU member states.

---

## Demo

<div align="center">
  <video src="assets/demo.mp4" controls width="100%"></video>
</div>

---

## Features

- **Multi-format resilience** — Handles scanned PDFs (2009+), typed forms (2010-2011), and modern digital documents in a unified pipeline
- **9-stage AI pipeline** — Forensic detection → OCR → Classification → Zone segmentation → LLM extraction → FHIR assembly
- **Dual-pillar compliance** — Pillar 1 (direct care) and Pillar 2 (research) with automated k-anonymity and patient opt-out enforcement
- **15+ FHIR R4 resource types** — Patient, Encounter, Condition, Procedure, Observation, Medication, Device, AllergyIntolerance, and more
- **SNOMED CT terminology validation** — Real-time validation against a live Snowstorm FHIR terminology server
- **Role-based UI** — Doctors see full records; Analysts see labs; Statisticians see aggregates
- **Romanian language OCR** — Tesseract with Romanian diacritics support and text normalization
- **Background HAPI upload** — Non-blocking async upload to the FHIR server after every extraction

---

## Architecture

<div align="center">
  <img src="assets/architecture.svg" alt="Pipeline Architecture" width="80%">
</div>

### Pipeline Stages

```
Stage 0  →  Forensics         PDF type detection, AcroForm widget identification
Stage 1  →  Text Extraction   pdfplumber (digital) / pytesseract + OCR (scanned)
Stage 1b →  Checkbox Mapping  AcroForm fields → Unicode checkbox symbols
Stage 2  →  Classification    Document type: HDR / BIS / SM
Stage 3  →  Zone Detection    Anchor-based field segmentation per document type
Stage 4  →  LLM Extraction    Gemini 2.5 Flash via OpenRouter + instructor (structured output)
Stage 5  →  Validation        Pydantic schemas + SNOMED CT + CoreSetError detection
Stage 6  →  FHIR Assembly     15+ resource types from validated structured data
Stage 7  →  Bundle Build      Composition + FHIR Bundle packaging
Stage 8  →  Anonymization     k-anonymity, temporal shifting (Pillar 2 only)
Stage 9  →  HAPI Upload       Async background upload to HAPI FHIR R4 server
```

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose                        │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │    │   Pipeline   │    │  HAPI FHIR   │  │
│  │  React + TS  │───▶│  FastAPI     │───▶│   Server     │  │
│  │  Port 8018   │    │  Port 8000   │    │  Port 8080   │  │
│  └──────────────┘    └──────┬───────┘    └──────────────┘  │
│                             │                               │
│                      ┌──────▼───────┐                       │
│                      │  PostgreSQL  │                       │
│                      │  Port 5432   │                       │
│                      └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
          OpenRouter API          Snowstorm API
        (Gemini 2.5 Flash)      (SNOMED CT Terms)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI 0.115+ · Uvicorn | Async REST API, multipart upload |
| **Extraction** | pdfplumber · PyMuPDF · pytesseract | PDF parsing and OCR |
| **AI / LLM** | Gemini 2.5 Flash via OpenRouter | Structured medical field extraction |
| **Validation** | Pydantic v2 · instructor | Schema validation + structured LLM output |
| **FHIR** | fhir.resources 8.0+ | HL7 FHIR R4 resource construction |
| **Terminology** | Snowstorm (SNOMED CT) | Medical terminology validation |
| **Database** | PostgreSQL 16 · asyncpg | Async persistence |
| **Frontend** | React 19 · TypeScript · Vite | Role-based SPA |
| **Styling** | Tailwind CSS 4.3 · Framer Motion | UI and animations |
| **Infrastructure** | Docker Compose · Nginx | Container orchestration |

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2+
- An [OpenRouter](https://openrouter.ai/) API key (for Gemini 2.5 Flash)
- Tesseract OCR with Romanian language pack (for local dev without Docker)

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/<your-username>/EHDS-Service.git
cd EHDS-Service
```

**2. Configure environment**

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
OPENROUTER_API_KEY=sk-or-...
DATABASE_URL=postgresql+asyncpg://ehds:ehds@postgres:5432/ehds_db
FHIR_BASE_URL=http://hapi-fhir:8080/fhir
LLM_MODEL=google/gemini-2.5-flash-lite
OCR_LANGUAGE=ron
LLM_MAX_TOKENS=8192
```

**3. Start the full stack**

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend (Doctor view) | http://localhost:8018 |
| API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| HAPI FHIR Server | http://localhost:8080/fhir |

---

## API Reference

### `POST /api/v1/extract/primary`
Upload a Romanian medical PDF and receive a full HL7 FHIR R4 Bundle (Pillar 1 — direct care, no anonymization).

```bash
curl -X POST http://localhost:8000/api/v1/extract/primary \
  -F "file=@discharge_report.pdf" \
  -H "Accept: application/json"
```

**Response:** `200 OK` — FHIR R4 Bundle (JSON)

```json
{
  "resourceType": "Bundle",
  "type": "document",
  "entry": [
    { "resource": { "resourceType": "Composition", ... } },
    { "resource": { "resourceType": "Patient", ... } },
    { "resource": { "resourceType": "Encounter", ... } },
    ...
  ]
}
```

---

### `POST /api/v1/extract/secondary`
Upload a PDF and receive an anonymized FHIR Bundle (Pillar 2 — research). Enforces patient opt-out (CNP ending in `0000` is blocked).

```bash
curl -X POST http://localhost:8000/api/v1/extract/secondary \
  -F "file=@discharge_report.pdf" \
  -H "Accept: application/json"
```

**Response:** `200 OK` — Anonymized FHIR R4 Bundle with:
- Temporal shifts applied to all dates
- Categorical generalization (age ranges, regional codes)
- Direct identifiers removed

---

## Role-Based UI

The frontend adapts its view based on the selected role:

| Role | Access Level | Visible Data |
|------|-------------|-------------|
| **Doctor** | Full access | Complete FHIR Bundle — all clinical fields |
| **Analyst** | Partial access | Laboratory results, diagnoses, procedures |
| **Statistician** | Aggregate only | Population-level statistics, no PII |

---

## Supported Document Types

| Code | Document | LOINC Code |
|------|----------|-----------|
| `DOC_HDR` | Hospital Discharge Report | 34105-7 |
| `DOC_BIS` | Outpatient Visit Summary | 34133-9 |
| `DOC_SM` | Specialty Medical Summary | — |

---

## FHIR Resources Produced

`Patient` · `Encounter` · `Condition` · `Procedure` · `Observation` · `MedicationStatement` · `MedicationAdministration` · `AllergyIntolerance` · `DiagnosticReport` · `Device` · `DeviceUseStatement` · `Practitioner` · `Organization` · `Composition` · `Bundle`

---

## Regulatory Compliance

| Regulation | Status | Deadline |
|-----------|--------|---------|
| EU Regulation 2025/327 (EHDS) | Implemented | Force: March 26, 2025 |
| Hospital Discharge Reports (Pillar 1) | Implemented | Mandatory by March 2031 |
| Secondary Use / Research (Pillar 2) | Implemented | Progressive rollout 2027+ |
| MyHealth@EU / EEHRxF format | FHIR R4 compliant | Active |
| eHealth Network Guidelines HDR 1.1 | Implemented | Active |

---

## Roadmap

- [ ] ICD-10 / ICD-11 code mapping and validation
- [ ] Additional Romanian document types (lab reports, radiology)
- [ ] Patient-facing consent management portal
- [ ] Multi-language support (Hungarian, German dialects spoken in Romania)
- [ ] MyHealth@EU gateway integration for live cross-border submission
- [ ] Audit trail and GDPR Article 30 processing records
- [ ] Batch processing mode for hospital bulk digitization
- [ ] Support for additional EU member state document formats

---

## License

This project is **proprietary software**. All rights reserved.

Copyright © 2026 Albert G.

Unauthorized copying, use, modification, distribution, or implementation of this software — in whole or in part — is strictly prohibited without prior written permission from the author.

See the [LICENSE](LICENSE) file for full terms.

---

## Contact

**Albert G.**
- Email: [albert1024@proton.me](mailto:albert1024@proton.me)
- Project: [EHDS-Service](https://github.com/<your-username>/EHDS-Service)

For licensing inquiries, partnership proposals, or integration support — reach out directly.

---

<div align="center">
  <sub>Built for the European Health Data Space · Powered by HL7 FHIR R4 · Made in Romania</sub>
</div>
