# Market Research: EHDS Legal Compliance System for Small Clinics in Romania

> **Product:** Platform for converting medical documents (DOCX / PDF / image) into the EHDS standard format  
> **Geographic focus:** Romania (primary market), with EU expansion potential  
> **Report date:** May 2026

---

## 1. Regulatory Context — What Is EHDS and Why It Matters Now

### 1.1 Regulation (EU) 2025/327

The European Health Data Space Regulation (EHDS) was published in the Official Journal of the EU on **5 March 2025** and entered into force on **26 March 2025**. It is the most ambitious digital health legislative framework in EU history and affects **every healthcare provider** — public or private, large or small.

### 1.2 Compliance Timeline — The Window of Opportunity

| Deadline | Obligation |
|---|---|
| **June 2025** | Each EU member state must appoint a National Digital Health Authority |
| **January 2026** | EHR vendors must begin certifying systems for interoperability compliance |
| **March 2027** | Full regulation enforcement; penalties for non-compliance |
| **March 2029** | Mandatory exchange of first priority data group (patient summaries, ePrescriptions) across the entire EU |
| **March 2031** | Second priority data group: medical images, lab results, hospital discharge reports |

**The critical window for clinics is 2026–2027.** Non-compliant systems must be replaced or updated before enforcement penalties kick in.

### 1.3 Mandated Technical Standard

EHDS mandates the adoption of **EEHRxF** (*European Electronic Health Record Exchange Format*), with HL7 FHIR as the primary technical standard, alongside DICOM (imaging) and ISO/IEC 27001 (security). The delegated acts that will precisely define the format must be adopted by **26 March 2027**.

HL7 Europe published the EHDS-specific FHIR implementation guides in **January 2026** — meaning specifications are now stable and solutions can be built on top of them.

### 1.4 Penalties for Non-Compliance

Penalties are calibrated after the GDPR model:

- **Up to €10 million** or **2% of global annual turnover** for moderate infringements
- **Up to €20 million** or **4% of global annual turnover** for serious infringements

For a small clinic with €500,000/year in revenue, a 2% fine amounts to **€10,000** — far more than the cost of a compliance solution subscription.

---

## 2. The Exact Problem the Product Solves

### 2.1 The Compliance Gap

Small clinics in Romania generate dozens of medical documents daily — consultations, lab results, images, referral letters — in **non-standard formats**: Word, scanned PDF, JPEG, proprietary equipment formats. EHDS requires this data to be available in EEHRxF/HL7 FHIR format so it can be:

1. Accessed by the patient (a right guaranteed by EHDS)
2. Exchanged with other medical providers across the EU
3. Integrated into the national Electronic Health Record (EHR/DES)

**The concrete problem:** a small clinic lacks the technical resources to re-implement its existing IT system from scratch. It needs an intermediary layer (*compliance middleware*) that transforms existing documents into the required format without disrupting the current workflow.

### 2.2 Why Small Clinics Cannot Solve This on Their Own

- **Lack of IT resources:** 40% of Romanian medical units lack the minimum required IT infrastructure
- **Lack of expertise:** HL7 FHIR and EEHRxF standards are technically complex and continuously evolving
- **Prohibitive cost of enterprise solutions:** Complete platforms (Dedalus, InterSystems) are sized for large hospitals, with implementation costs in the hundreds of thousands of euros
- **Document fragmentation:** clinics receive documents from patients and partners in any format — there is no unified workflow

### 2.3 The State of the National EHR (DES) in Romania

Romania's national Electronic Health Record (DES) is active for ~17 million patients, but **only 30% of public-sector doctors** use it regularly. The system has chronic technical issues. Private clinics are largely **outside the DES ecosystem**, making them extremely vulnerable to EHDS interoperability requirements.

---

## 3. The Market — Size and Structure

### 3.1 How Many Healthcare Units Exist in Romania

According to the National Institute of Statistics (INS), 2024 data:

| Category | Number of units (2024) |
|---|---|
| Total healthcare units | **69,000+** |
| Independent specialty medical practices | **~15,500** |
| Independent dental practices | **~17,000** |
| Family medicine practices | **~10,000** |
| Private clinics and medical centers (networks) | **600+** |

The **primary target segment** of the product is independent specialty practices and small private clinics with 1–10 doctors — **estimated at 12,000–15,000 units** in Romania.

### 3.2 Romania's Private Healthcare Services Market

- **Estimated value in 2025:** €3.5–4 billion (the market doubled in 5 years, from €1.7B in 2017)
- **Annual growth:** 10–12% (average over the last 5 years)
- **Top players:** MedLife (€630M revenue in 2025), Regina Maria, Medicover, Sanador — controlling ~40% of the market through large networks
- **The remaining ~60%** consists of small and medium independent clinics — **this is the relevant TAM**

### 3.3 European Market for Healthcare Interoperability and Compliance

| Indicator | Value |
|---|---|
| Europe Health Information Exchange Market (2025) | **$394M** |
| Projection 2033 | **$777M** (CAGR 8.86%) |
| EHDS middleware market projection (2027) | **€7 billion** |
| Healthcare Document Management (CAGR 2025–2033) | **14.1%** |
| European hospitals with EHDS-compliant middleware (2025) | **only 31%** |

The market opportunity in Romania, extrapolated proportionally from European data, is estimated at **€15–25M/year** for SME-focused compliance middleware solutions — an emerging market with no clear leader.

---

## 4. The Target Customer and Their Profile

### 4.1 Market Segmentation

**Primary segment — Small Independent Private Clinic:**

- 1–5 specialist doctors, possibly 1 receptionist/assistant
- Annual revenue: €100,000–800,000
- Predominantly urban location (13,700 out of 15,500 specialty practices are in urban areas)
- Existing software: local solutions (Hipocrate Clinic, MedSoft, Excel sheets, Word), or nothing digital
- IT budget: **under €5,000/year** — price-sensitive
- Purchase decision-maker: the lead physician or clinic administrator
- Primary purchase motivation: **mandatory legal compliance + avoided fines**

**Secondary segment — Medical Center with 5–20 Doctors:**

- Annual revenue: €500,000 – €3,000,000
- Already has medical software, but it is not EHDS-compliant
- Looking for an integration layer, not a full replacement
- IT budget: €5,000–25,000/year
- Decision horizon: 6–12 months

**Tertiary segment — Regional Networks (20–100 locations):**

- Have internal IT departments; can become partners or referral sources
- More complex purchasing process, long sales cycle

### 4.2 Market Weight by Segment

| Segment | Estimated units (Romania) | Share of target market | Estimated WTP/month |
|---|---|---|---|
| Individual practice / small clinic (1–5 doctors) | 10,000–12,000 | **~70%** | €30–80 |
| Medium medical center (5–20 doctors) | 2,000–3,000 | **~20%** | €100–300 |
| Regional network / mid-to-large clinic | 300–600 | **~10%** | €500–2,000 |

### 4.3 Psychographic Profile of the Primary Customer

The lead physician of a small clinic:

- **Motivated by fear** (EHDS fines) more than by competitive advantage
- **Skeptical of IT solutions** — bad past experiences with the DES, failed previous implementations
- **Has no time** to understand technical standards — wants a plug-and-play solution
- **Trusts recommendations** — purchases happen mostly through word of mouth and professional associations (Colegiul Medicilor din România / College of Physicians)
- **Price-sensitive** — low monthly SaaS subscription preferred over large annual licenses

---

## 5. Competition

### 5.1 The Competitive Landscape in Romania

**Local clinic management solutions (not EHDS-native, but incumbents):**

| Vendor | Profile | Gap vs. EHDS |
|---|---|---|
| **Hipocrate (RSC)** | Market leader in public hospital systems, present in private sector too; complex solution | No EEHRxF/FHIR conversion for legacy documents |
| **MedSoft** | SaaS solution for small private clinics; modern UI, management-focused | No EHDS compliance module |
| **Softmedica** | Integrated system for medium clinics and hospitals | Enterprise pricing, too expensive for small clinics |
| **Generic ERP solutions** (Saga, WinMedic) | Used by individual practices for billing | No standardized medical functionality whatsoever |

**Key conclusion:** **There is no dedicated EHDS compliance solution for small clinics** on the Romanian market in 2026. Incumbents have not adapted their products — a clear greenfield opportunity.

### 5.2 European Competition (Medium-Term Risk)

| Vendor | Origin | Positioning |
|---|---|---|
| **Better** (Think!EHR) | Slovenia/UK | openEHR-native, API-first; scalable but not localized for Romania |
| **Marand** | Slovenia | EHDS middleware, too technical/enterprise for SMEs |
| **Dedalus** | Italy/France | Re-architected for EHDS; addresses large hospitals |
| **InterSystems IRIS** | USA (EU deployment) | NHS/Ireland focus, long sales cycles, enterprise pricing |

These European players are focused on large hospitals and national systems. **Small clinics in Romania are not on their radar** in 2026–2027.

---

## 6. Key Business Metrics

### 6.1 Market Size (Romania)

| Indicator | Estimate |
|---|---|
| **TAM** (total addressable market) | 12,000–15,000 small clinics in Romania |
| **SAM** (realistically addressable segment in 3 years) | 2,000–4,000 clinics (those with at least some existing software) |
| **SOM** (realistic Year 1 target) | 200–500 clinics |
| **Year 1 ARR target** (at €50/month average) | **€120,000–300,000** |
| **Year 3 ARR target** (500–2,000 clinics) | **€300,000–1,200,000** |

### 6.2 Recommended Operational Metrics

**Acquisition:**
- **CAC (Customer Acquisition Cost)** — target under €150; primary channels are professional medical associations, EHDS webinars, partnerships with existing medical software vendors
- **Time to First Value** — under 48 hours from onboarding (if not achieved, churn explodes in the SME segment)

**Retention:**
- **Monthly Churn Rate** — target under 2%/month (for medical SaaS, norm is 1–3%)
- **NPS** — critical, as word-of-mouth is the primary sales channel among doctors
- **Documents Processed/Month per Client** — usage metric and churn predictor

**Compliance:**
- **% of onboarded clinics that achieved EHDS compliance** — the product's primary KPI; this is the customer's "aha moment"
- **Audit Trail Completeness Rate** — percentage of documents with complete traceability as required by EHDS

**Growth:**
- **Expansion Revenue** — clinics adding locations or doctors (upsell)
- **Referral Rate** — % of new customers acquired through referral; in Romanian private medicine, estimated at 30–40% if the product works well

### 6.3 Risk Indicators

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Delay in EHDS implementation by Romanian authorities | Medium | High | Build DES + GDPR compliance into the product in addition to EHDS |
| Incumbents (Hipocrate, MedSoft) launching EHDS modules | Medium-High | Medium | Fast time-to-market, lock-in through processed data |
| Slow adoption (IT skepticism among small clinics) | High | Medium | Channel through medical associations, freemium or trial model |
| Complexity of FHIR standards (frequent iterations) | Medium | Medium | Modular architecture, automatic updates |

---

## 7. Conclusions and Strategic Recommendations

### Correct Product Positioning

The product should not be sold as "interoperability software" — doctors don't know what that means. It should be sold as:

> **"Stay clear of EHDS fines. We automatically convert your medical documents into the EU-required legal format — without changing anything about the way you work."**

### Go-to-Market Prioritization

1. **Partnerships with professional associations** (Colegiul Medicilor din România, Asociația Medicilor de Familie) — instant credibility and access to their member database
2. **Integration with local incumbents** (MedSoft, Hipocrate) as an add-on module — not as a rival
3. **Active market education** — EHDS is largely unknown among small clinics; whoever educates the market also wins the trusted advisor position
4. **Transparent, accessible pricing** — €39–79/month (below the psychological €100 threshold) with a 30-day free trial

### Timing

The golden window is **2026–2027**: regulations are clear, technical standards are published, but the market has no solutions. Companies entering now have a first-mover advantage on a segment of ~12,000 potential customers facing a real, legally enforced deadline.

---

## Sources

- [Regulation (EU) 2025/327 — EHDS | EY Greece](https://www.ey.com/en_gr/technical/tax/tax-alerts/regulation-2025-327-establishing-ehds)
- [EHDS Regulation Timeline | Securiti.ai](https://securiti.ai/infographics/european-health-data-space-timeline-and-implementation-roadmap/)
- [EHDS Rights, Obligations and Deadlines | SRD Rechtsanwälte](https://www.srd-rechtsanwaelte.de/en/blog/ehds-rights-health-data)
- [HL7 Europe FHIR Implementation Guides for EHDS | HL7 News (Jan. 2026)](https://hl7news.hl7.org/2026/01/02/new-hl7-europe-fhir-implementation-guides-to-support-the-european-health-data-space/)
- [Black Book Research — EHDS Interoperability Vendors Study](https://www.newswire.com/news/black-book-research-unveils-first-pan-european-study-of-ehds-22630969)
- [INS: Over 69,000 healthcare units in Romania (2024) | MedicalManager.ro](https://www.medicalmanager.ro/ins-peste-69-000-de-unitati-sanitare-functionau-in-romania-in-2024-doar-12-000-se-aflau-in-mediul-rural/)
- [Private healthcare services market — doubled in 5 years | 360medical.ro](https://360medical.ro/stiri/studiu-piata-serviciilor-medicale-private-din-romania-s-a-dublat-in-5-ani-depasind-3-miliarde-euro/2022/12/07/)
- [MedLife — €630M revenue in 2025 | Revista Cariere](https://www.revistacariere.ro/noutati/medlife-atinge-630-milioane-de-euro-cifra-de-afaceri-pro-forma-in-2025-si-continua-investitiile-in-genetica-si-ai)
- [Healthcare digitalization lagging in Romania | Business Review](https://business-review.eu/business/healthcare/healthcare-digitalization-lagging-in-romania-despite-available-eu-support-horvath-analysis-finds-285864)
- [Romania National Health Digitalization Strategy 2026–2030 | Trade.gov](https://www.trade.gov/market-intelligence/romania-national-health-digitalization-strategy-2026-2030)
- [Europe Health Information Exchange Market | MarketDataForecast](https://www.marketdataforecast.com/market-reports/europe-healthcare-information-exchange-market)
- [Electronic Health Record accessible to patients from summer 2026 | ValidSoftware](https://validsoftware.ro/dosarul-electronic-de-sanatate-devine-accesibil-pacientilor-din-vara-2026-ce-inseamna-pentru-sistemul-medical-din-romania/)
- [Data Act & EHDS — What clinics need to know | Heise Online](https://www.heise.de/en/background/Data-Act-EHDS-What-clinics-MedTech-and-software-manufacturers-need-to-know-10641825.html)
