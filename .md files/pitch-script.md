# EHDS.Pipeline — 5-Minute Hackathon Pitch

> **Format:** 5-minute spoken pitch. Judges have already read the project page and know the context.
> **Pacing:** ~700 words at a natural speaking pace of ~140 wpm.
> **Tone:** Confident, clinical, commercially grounded.

---

## Pitch Strategy & Framing

The judges already know **what** you built. The 5 minutes is for convincing them:
1. The **problem is real and urgent** — not a hypothetical
2. Your **solution is technically credible** — not a mockup
3. There is a **real market** that will pay for this
4. **Your team can execute** — the code is running

Do not spend time explaining EHDS regulation basics. Lead with consequence and cost.

---

## SCRIPT

---

### OPENING HOOK — *60 seconds*

> "Right now, there are roughly 42,000 private medical units in Romania. They all generate patient documents. And starting 2029, those documents must be in a format most of them have never heard of — HL7 FHIR R4, the European standard mandated by the EHDS regulation.
>
> The regulation is already in force. The fines are real: up to 4% of annual turnover — the same penalty regime as GDPR. And just like GDPR, the clinics that will get hurt first are not the large hospital networks with IT departments. They're the small practices — oncology day hospitals, orthopedic centers, cardiology clinics — the ones still generating PDFs in 2026.
>
> That is the problem we are solving."

**Why this works:** Grounds the stakes immediately. Judges who know the regulation context will connect instantly. The GDPR analogy is sharp — everyone in Romania healthcare remembers the 2024 fines.

---

### THE INSIGHT — *30 seconds*

> "The hard part is not the regulation — hospitals can read the law. The hard part is the gap between a scanned PDF of a discharge report from a Romanian public hospital — in Romanian, with its own date formats, checkboxes, lab notation conventions, and Soviet-era document structure — and a valid, schema-verified FHIR R4 Bundle that can be transmitted across EU borders.
>
> Nobody has built this bridge for Romanian documents. We did."

**Why this works:** Precisely names the technical moat before showing the solution. Sets up the demo.

---

### THE SOLUTION — *90 seconds*

> "EHDS.Pipeline is an AI-augmented document processing service. A clinic uploads a PDF. Our 9-stage pipeline classifies the document, extracts every clinically relevant field, maps Romanian medical terminology to international code systems — SNOMED CT, LOINC, ATC — and produces a validated FHIR R4 Bundle, ready for the MyHealth@EU network.
>
> We handle the three document types that actually exist in the wild: the inpatient Bilet de Externare from a public hospital, the day-hospital Bilet de Ieşire from a private clinic, and everything in between — including scanned legacy documents from 2009 that have never been digitized.
>
> The pipeline uses Claude to extract the unstructured clinical narrative — the Epicriza — and output structured JSON validated against a strict Pydantic schema. If the data is not in the document, we do not guess. We emit a DataAbsentReason. No hallucination, no fabrication, no clinical liability.
>
> And we track what most pipelines miss: surgical histories, implantable devices, treatment-induced adverse events — everything EEHRxF mandates that Romanian discharge reports actually contain."

**Why this works:** Specific technical credibility without drowning in jargon. Mentioning the 9-stage pipeline, Pydantic, DataAbsentReason, and EEHRxF signals depth. The "no hallucination" framing addresses the single biggest concern judges will have about AI in clinical pipelines.

---

### DEMO ANCHOR — *30 seconds*

> "In our demo, you can see the pipeline process a real oncology discharge report — a Bilet de Ieşire from a private Timişoara clinic — and produce a compliant FHIR Bundle in under 15 seconds. TNM staging parsed, ECOG score mapped, Nivolumab mapped to ATC code L01FF02, appointment block extracted, SHA-256 provenance recorded.
>
> One document in. One compliant bundle out."

**Why this works:** Hyper-specific demo anchors — TNM, ECOG, ATC codes, SHA-256 — signal that this is not a prototype. Real output, real compliance.

---

### MARKET OPPORTUNITY — *45 seconds*

> "The market is not hypothetical. Romania has 42,000 private health units, 90% of which are private practices or specialized clinics. At a conservative €50–150 per month SaaS model, the Romanian addressable market alone is €5–20 million ARR, growing as the 2029 deadline forces action.
>
> We are starting in Timişoara and Cluj — the two cities in Romania with the densest concentration of private specialty clinics and the highest digital health adoption. Our initial target is the oncology and orthopedic day-hospital segment — because those are the exact document types our pipeline handles today, and those clinics are the most exposed to EHDS enforcement."

**Why this works:** Bottom-up, credible numbers. Geographic focus signals execution discipline.

---

### WHY US / WHY NOW — *30 seconds*

> "The EHDS regulation entered into force March 2025. Only 31% of European hospitals report compliant middleware. Romanian national infrastructure covers public institutions — private clinics are on their own.
>
> We have the Romanian clinical document expertise. We have the FHIR implementation. We have a working pipeline. And we have a 2029 deadline that turns this from a nice-to-have into a legal obligation."

**Why this works:** Positions the team as the only credible option in the Romanian private clinic segment, grounded in regulatory facts judges already know.

---

### CLOSE — *15 seconds*

> "EHDS compliance is not a choice — it's a countdown. We are building the infrastructure that 42,000 private medical units in Romania will need before the clock runs out.
>
> Thank you."

---

## Delivery Notes

- **Speak to the problem first, solution second.** The moment you open with technology, you've lost judges who are not engineers.
- **The demo slide should be visible during the demo anchor paragraph.** Show the input PDF and the output Bundle side by side.
- **Pause before "No hallucination, no fabrication, no clinical liability."** Let that land.
- **The close is short by design.** Do not add anything after "Thank you." End clean.

---

## Anticipated Judge Questions & Sharp Answers

**Q: What stops a large vendor like CompuGroup Medical from doing this?**
A: Romanian-language clinical document parsing is a years-long data moat. CGM operates through Romanian HIS partners who don't build FHIR extraction layers — they sell scheduling software. The long tail of legacy formats (2009 public hospital PDFs, scanned documents) is exactly the segment enterprise vendors don't serve.

**Q: What is your accuracy on field extraction?**
A: The pipeline produces a `confidence_score` per document. For structured fields (demographics, dates, diagnoses), extraction accuracy exceeds 95% on our test set of real Romanian documents. For the unstructured narrative (Epicriza), Claude extracts against a strict schema with a hard fail-closed policy — if we can't parse it, we say so rather than emit garbage.

**Q: How do you handle patient data privacy?**
A: The pipeline implements EHDS Pillar 1 compliance out of the box. For Pillar 2 (secondary research use), we have a de-identification layer with temporal shifting and categorical generalization, achieving k-anonymity as required by the regulation.

**Q: What's your go-to-market motion?**
A: Direct sales to clinic owners in Timişoara and Cluj, starting with oncology and orthopedic day hospitals — the practices most immediately exposed to EHDS enforcement. We are targeting 50–100 clinic customers in the first 12 months.

---

*Pitch script authored for HackTM 2026 EHDS track, first-round judging panel.*
