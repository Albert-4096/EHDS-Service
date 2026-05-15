# EHDS.Pipeline — 3-Minute Pitch Format
### HackTM 2026 · Tracks: Best AI + Best Product Innovation
> **Total duration:** 3 minutes hard stop
> **Format:** Spoken word + embedded video demo (~40 sec)
> **Scoring:** Clarity · Conviction · Time management (10%) · AI use (40% track) · Market impact (40% track)

---

## Timing Blueprint

```
[0:00 – 0:25]  Hook + Problem        25 sec   ~55 words
[0:25 – 0:55]  Solution              30 sec   ~65 words
[0:55 – 1:35]  VIDEO DEMO            40 sec   (play video — light narration only)
[1:35 – 2:00]  Why AI is essential   25 sec   ~55 words
[2:00 – 2:45]  Business case         45 sec   ~100 words
[2:45 – 3:00]  Close                 15 sec   ~30 words
────────────────────────────────────────────────
               TOTAL                 3:00 min
```

---

## Full Script

---

### HOOK + PROBLEM — [0:00 – 0:25]

> *"On March 26, 2025, a law came into force requiring every private clinic in Europe to exchange patient data in a standardized digital format. Penalties: up to €20 million. Deadline: 2029. Romania has 42,000 private medical units. Most of them generate documents like this —"*

*(gesture toward screen — show a raw Romanian PDF for 2 seconds)*

> *"— scanned PDFs, Word files, clinical notes in Romanian, with dates in seven different formats. None of it is readable by any EU health system. That is the compliance gap we close."*

**Delivery note:** Speak at conviction pace, not speed. Let "€20 million" and "2029" sit for half a beat before continuing.

---

### SOLUTION — [0:25 – 0:55]

> *"We built EHDS.Pipeline: a 9-stage AI-powered document processor that takes any Romanian medical document and outputs a fully validated HL7 FHIR R4 Bundle — the exact format EHDS mandates — complete with SNOMED CT medical codes, LOINC lab codes, ATC medication codes, and cryptographic provenance on every record.*
>
> *It handles three generations of Romanian clinical documents: legacy handwritten discharge summaries from 2009, typed orthopedic forms, and modern private oncology notes. One pipeline. All of them. Let me show you."*

**Delivery note:** The last sentence is the natural cue to start the video. Don't pause — let it flow directly into the demo.

---

### VIDEO DEMO — [0:55 – 1:35] *(40 seconds)*

**What the video must show — shoot in this exact sequence:**

| Timestamp | What's on screen | Narration (spoken lightly over video) |
|---|---|---|
| 0–5 sec | Drag a Romanian PDF into the API upload UI | *"A clinic drops in a discharge document."* |
| 5–12 sec | Pipeline stages running — show stage classifier output: `DOC_BIS` | *"The pipeline classifies it, detects zones, extracts structured fields."* |
| 12–22 sec | Claude API response JSON — show `current_visit` vs `history_timeline` separation | *"Claude separates this visit from the patient's full history — zero hallucination, schema-enforced."* |
| 22–32 sec | HAPI FHIR server — FHIR Bundle, click into `Composition`, then one `Observation` with SNOMED code | *"The output: a validated FHIR Bundle with 15 resource types."* |
| 32–37 sec | `Provenance` resource showing SHA-256 hash + model version | *"Every record is cryptographically signed."* |
| 37–40 sec | HAPI Validator: green pass | *"Fully compliant."* |

**Video production notes:**
- No music, no transitions — clean screen recording at 1080p
- Speed up the pipeline execution to fit (2–3× on the processing stages)
- Keep the FHIR Bundle view slow enough to read — this is the money shot
- Total video length: exactly 40 seconds

---

### WHY AI IS ESSENTIAL — [1:35 – 2:00]

> *"Now — why AI? Because Romanian clinical narratives contain sentences like: 'alternating with Encephabol, 10 days per month, under Phenobarbital cover.' No regex, no rule engine can parse that into a structured medication schedule with dosage intervals and drug interactions. Claude extracts it under strict schema constraints — or it fails closed and flags the record for review. The AI doesn't guess. It either produces valid FHIR or it stops."*

**Delivery note:** This answers the Best AI criterion directly — "not AI for its own sake." Make it sound like a technical fact, not a marketing claim. The phrase "fails closed" is your precision signal.

---

### BUSINESS CASE — [2:00 – 2:45]

> *"The market: Romania has 69,000 health units, 75% privately owned. We target the 8,000 to 12,000 small private specialized clinics that cannot afford enterprise FHIR platforms costing hundreds of thousands of euros.*
>
> *Our model: SaaS, €50 to €150 per clinic per month. No implementation fee. For a clinic facing a potential €10,000 GDPR-style fine, that's an easy calculation.*
>
> *Go-to-market: Timișoara and Cluj first — high private clinic density, tech-forward ecosystem. We're already here. By 2027 when enforcement activates, we want to be embedded before clinics panic.*
>
> *Competitive moat: we've reverse-engineered 18 failure modes from real Romanian patient documents. That corpus knowledge is not something an international FHIR vendor builds without years in this market. Romania alone represents €5 to €20 million ARR. The EU is a €7 billion middleware opportunity by 2027.*
>
> *Six-month roadmap: multi-tenant web UI, SMART on FHIR authentication, and Pillar 2 de-identification for research data reuse — each one tied to an EHDS enforcement deadline."*

**Delivery note:** Slow down on the numbers. "€5 to €20 million" and "€7 billion" should feel like facts being stated, not figures being rushed past. The roadmap sentence signals feasibility without needing a slide.

---

### CLOSE — [2:45 – 3:00]

> *"EHDS.Pipeline is compliance infrastructure for a regulation that is already in force. The problem is real, the code works, and the deadline is set by European law — not by us. Thank you."*

**Delivery note:** Stop at "thank you." Do not add anything. Do not smile and wait. End with stillness — it signals you're in control of the time, not the clock.

---

## Business Coverage Checklist

Verify every element below is covered before going on stage:

- [x] **Regulatory forcing function** — EHDS in force March 2025, enforcement 2027, mandatory compliance 2029
- [x] **Penalty stakes** — €20M / 4% turnover (makes the price point self-justify)
- [x] **Target customer** — small private clinics, 1–20 physicians, no IT department
- [x] **Market size** — 69,000 units / 42,000 private / 8–12k addressable target segment
- [x] **Pricing model** — €50–150/month SaaS, no implementation fee
- [x] **Revenue potential** — €5–20M ARR Romania, €7B EU middleware market by 2027
- [x] **Go-to-market** — Timișoara + Cluj first, leverage existing presence
- [x] **Competitive moat** — 18 Romanian-specific edge cases, corpus-based knowledge barrier
- [x] **Roadmap** — web UI, SMART on FHIR OAuth, Pillar 2 de-identification
- [x] **Why now** — 2027 enforcement window is closing; first-mover in this niche

---

## Q&A Preparation (top 3 judge questions)

**"Can't clinics just use an existing FHIR platform?"**
> "They can — for €200k implementation plus a vendor who has never seen a Romanian 'Bilet de Iesire.' We're the middleware for the other 42,000."

**"How accurate is the AI extraction?"**
> "We don't rely on accuracy — we rely on validation. Every extraction is checked against a Pydantic schema. If it fails, the record is rejected, not silently corrupted. We test against Synthea-generated records rendered as Romanian clinical text, which gives us a measurable input-to-output fidelity loop."

**"What's your path to revenue — how do you actually sign clinics?"**
> "Three channels: medical association events, GDPR compliance consultants who already have clinic relationships, and direct outreach timed to EHDS awareness campaigns. The 2027 enforcement date is the sales trigger — we don't create urgency, the regulation does."
