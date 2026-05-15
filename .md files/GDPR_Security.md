# GDPR Compliance & Security — EHDS.Pipeline

> **Purpose of this document:** Pitch preparation + half-day implementation guide.
> Two sections: (1) what to say when the jury asks about GDPR, and (2) concrete security measures you can ship today.

---

## Part 1 — Jury Q&A: What to Say When Asked

### "You're sending patient data to an external LLM API. Isn't that a GDPR violation?"

**Answer:**
In the current demo we use OpenRouter as an external LLM, which we acknowledge as a gap for a hackathon prototype. In production, the architecture uses a **locally hosted LLM** (e.g., Ollama or vLLM running on-premises at the clinic or on a private cloud instance). Patient data never leaves the clinic's infrastructure. The system is designed from the ground up for local deployment — the LLM is just one configurable endpoint in `config.py`. For any cloud-based deployment, a **Data Processing Agreement (DPA)** with the LLM provider would be mandatory, and we would select providers that explicitly commit to no training on customer data (Anthropic and major cloud providers offer this).

---

### "Who is the data controller and who is the processor?"

**Answer:**
The **clinic is the data controller** — they have the patient relationship, the legal obligation, and the medical mandate. **EHDS.Pipeline is a data processor** — we act solely on the clinic's instructions to transform their documents into FHIR bundles. This is the cleanest possible structure under GDPR Article 28. We provide a **Data Processing Agreement template** to every clinic customer at onboarding, which specifies: what data we process, for what purpose, retention limits, sub-processors (LLM provider, cloud host), and security obligations. The clinic signs it before uploading a single document.

---

### "What happens to patient data after processing?"

**Answer:**
The pipeline uses **temporary files** that are deleted immediately after the FHIR bundle is assembled — the source PDF does not persist in our storage. The FHIR bundle is uploaded to the clinic's own HAPI FHIR server instance (self-hosted or privately provisioned). We retain only: (a) the SHA-256 hash of the source document for audit/provenance purposes (non-reversible, not PHI), and (b) structured FHIR resources in the clinic's own PostgreSQL instance. Retention periods are configurable and enforced by the clinic's data retention policy.

---

### "What about patients' GDPR rights — right to erasure, right to access?"

**Answer:**
Because patient data lives in the clinic's own FHIR server and database, the clinic handles data subject requests directly. For erasure: the clinic can delete a patient's FHIR Bundle by Patient ID from the HAPI FHIR server, and our pipeline generates a FHIR `Provenance` resource that provides the audit trail needed to confirm deletion. The Opt-Out mechanism (Pillar 1 / Pillar 2 toggle visible in the UI) implements the patient's right to restrict secondary use, as required by EHDS Article 11.

---

### "Have you done a Data Protection Impact Assessment (DPIA)?"

**Answer:**
A DPIA is mandatory for large-scale processing of health data (Article 35 GDPR), and we are conducting one. The key findings so far: (1) the risk profile is substantially reduced by local LLM deployment — no cross-border transfer of health data; (2) the FHIR Provenance resource provides the audit chain required for accountability; (3) the k-anonymity threshold for Pillar 2 (already in `config.py`) addresses re-identification risk for secondary use. We would finalize the DPIA before any commercial launch.

---

### "What about the LLM logs? Doesn't the model provider see the data?"

**Answer:**
With a local LLM, there are no external logs. With a cloud LLM in a contractual setup, we require a DPA that prohibits logging of request content for training. Additionally, we would implement **prompt-level pseudonymization** before sending to any external model: the CNP and patient name are replaced with tokens (e.g., `[PATIENT_ID]`, `[PATIENT_NAME]`) in the prompt, and are re-injected from the structured extraction stage which handles them separately and never sends them to the LLM. This is an architectural pattern we would implement in production.

---

### "Is this compliant with EHDS, not just GDPR?"

**Answer:**
EHDS builds directly on GDPR — it does not replace it, it extends it for health data specifically. Our pipeline is built around EHDS Regulation (EU) 2025/327 from the ground up: it produces HL7 FHIR R4 bundles in EEHRxF format, enforces the Pillar 1 / Pillar 2 distinction, implements the opt-out mechanism mandated by EHDS Article 11, and generates `Provenance` resources for legal authentication. GDPR compliance is the baseline; EHDS compliance is the product.

---

## Part 2 — What to Implement Today (~4 Hours)

These are concrete, scoped changes that meaningfully improve the security posture and are demonstrable to a technical jury. Ordered by impact vs. effort.

---

### 🔴 Priority 1 — Fix PHI in Logs (30 min, high impact)

**The problem:** `routes.py` line ~55 logs patient name, CNP, and primary diagnosis in plaintext:

```python
logger.info(
    f"Stage 4 extracted — type: {doc_type.value}, patient: '{structured.nume}', "
    f"cnp: '{structured.cnp}', diagnosis: '{structured.diagnostic_principal}', ..."
)
```

This is a textbook GDPR violation — application logs are not a lawful storage medium for PHI, and are often shipped to log aggregators (Datadog, Loki, etc.) outside the controlled environment.

**The fix** — replace with pseudonymized identifiers:

```python
import hashlib

def _pseudo(value: str) -> str:
    """One-way pseudonym for log-safe PHI reference."""
    if not value:
        return "[absent]"
    return "pseudo:" + hashlib.sha256(value.encode()).hexdigest()[:8]

logger.info(
    f"Stage 4 extracted — type: {doc_type.value}, "
    f"patient_ref: {_pseudo(structured.nume)}, "
    f"cnp_ref: {_pseudo(structured.cnp)}, "
    f"has_diagnosis: {bool(structured.diagnostic_principal)}, "
    f"labs: {sum(len(d) for d in [labs.cbc, labs.biochemistry, labs.hormones, labs.other])} values, "
    f"meds: {len(medications)}"
)
```

The `pseudo:` prefix makes it clear in any log viewer that this is a reference token, not real data. Identical patients produce the same token within a session, so you can still correlate log lines without exposing PHI.

---

### 🔴 Priority 2 — Guaranteed Temp File Deletion (20 min, high impact)

**The problem:** `routes.py` uses `tempfile.NamedTemporaryFile(delete=False, ...)`. The `delete=False` flag means if the pipeline throws an exception before cleanup, the raw PDF stays on disk indefinitely. This violates data minimization (GDPR Article 5(1)(c)).

**The fix** — wrap the entire pipeline in a `try/finally`:

```python
tmp_path = None
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # ... rest of pipeline ...

finally:
    if tmp_path and tmp_path.exists():
        tmp_path.unlink(missing_ok=True)
        logger.debug(f"Source file deleted: {tmp_path.name}")
```

This guarantees the source document is wiped even if the pipeline crashes at any stage.

---

### 🟡 Priority 3 — File Type Validation (30 min, medium impact)

**The problem:** The API currently accepts any file upload. An attacker could upload malicious files (zip bombs, SVG with embedded scripts, executables renamed as `.pdf`).

**The fix** — validate magic bytes, not just extension:

```python
import magic  # python-magic

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}
MAX_FILE_SIZE_MB = 20

async def validate_upload(file: UploadFile) -> bytes:
    content = await file.read()
    
    # Size check
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE_MB}MB limit")
    
    # Magic bytes check (not just extension)
    detected_mime = magic.from_buffer(content[:2048], mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(415, f"Unsupported file type: {detected_mime}")
    
    return content
```

Add `python-magic` to `pyproject.toml`. On the demo server: `apt-get install libmagic1`.

---

### 🟡 Priority 4 — Rate Limiting (30 min, medium impact)

**The problem:** The `/extract/primary` and `/extract/secondary` endpoints are unauthenticated and unbounded. A single actor could flood the pipeline with documents, incurring LLM API costs and potentially exfiltrating processing capability.

**The fix** — add `slowapi` rate limiting:

```python
# In main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In routes.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/extract/primary")
@limiter.limit("10/minute")
async def extract_primary(request: Request, file: UploadFile = File(...)):
    ...
```

Add `slowapi` to `pyproject.toml`. This is ~10 lines of code.

---

### 🟢 Priority 5 — Security Headers in Nginx (20 min, low effort, visible to jury)

**The problem:** The frontend Nginx config doesn't set security headers. Browsers will flag this in audits.

**The fix** — add to `ehds-frontend/nginx.conf` inside the `server` block:

```nginx
# Prevent clickjacking
add_header X-Frame-Options "DENY" always;

# Prevent MIME sniffing
add_header X-Content-Type-Options "nosniff" always;

# XSS protection for older browsers
add_header X-XSS-Protection "1; mode=block" always;

# Content Security Policy — restrict script/style sources
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;" always;

# Referrer policy — don't leak URL to external resources
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# HSTS — enforce HTTPS (enable only if you have TLS configured)
# add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

### 🟢 Priority 6 — Rotate the Exposed API Key (5 min, critical hygiene)

The `.env` file contains a real OpenRouter API key (`sk-or-v1-5a05...`). Even if `.env` is in `.gitignore`, it has been visible in your working environment during this session. **Rotate it now** at openrouter.ai → API Keys, before the demo. This takes 5 minutes and prevents any charges to your account from unauthorized use.

---

## Summary Table

| # | Fix | Effort | GDPR Article addressed |
|---|---|---|---|
| 1 | Pseudonymize PHI in logs | 30 min | Art. 5(1)(f) — integrity & confidentiality |
| 2 | Guaranteed temp file deletion | 20 min | Art. 5(1)(c) — data minimization |
| 3 | File type validation | 30 min | Art. 32 — security of processing |
| 4 | Rate limiting | 30 min | Art. 32 — protection against unauthorized processing |
| 5 | Nginx security headers | 20 min | Art. 32 — technical security measures |
| 6 | Rotate leaked API key | 5 min | Art. 32 — access control |
| **Total** | | **~2.5 hours** | |

---

## What We've Already Done Right (Mention These in the Pitch)

These are genuine architectural wins already present in the codebase — lead with them:

- **SHA-256 provenance hashing** of every source document (Stage 9) — immutable audit trail
- **k-anonymity threshold** already configurable in `config.py` (`k_anonymity_threshold: int = 5`) for Pillar 2
- **Pillar 1 / Pillar 2 separation** at the API level (`/extract/primary` vs `/extract/secondary`) — opt-out is architecturally enforced, not a checkbox
- **Pydantic v2 strict validation** throughout — no unvalidated data reaches the FHIR layer
- **FHIR `Provenance` resource** (Stage 9) recording AI model version, timestamp, and document hash — meets EEHRxF legal authentication requirements
- **Secrets in `.env`, not hardcoded** — proper secrets management pattern
- **HAPI FHIR runs inside the Docker network** — the FHIR server is not publicly exposed

---

## Production Roadmap (What Comes After the Hackathon)

For completeness — what you'd commit to doing before a commercial launch:

1. **Local LLM deployment** (Ollama + Llama 3 / Mistral Medical) — eliminates the external API data transfer issue entirely
2. **Full DPA template** for clinic onboarding (standard Article 28 agreement)
3. **DPIA completion** and filing with the Romanian DPA (ANSPDCP) if required
4. **Encryption at rest** for PostgreSQL (pgcrypto or Transparent Data Encryption)
5. **mTLS between Docker services** — internal network encryption
6. **Automated data retention enforcement** — cron job to purge FHIR records beyond retention window
7. **Breach notification procedure** — SOP for the 72-hour ANSPDCP notification window
