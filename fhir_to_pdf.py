#!/usr/bin/env python3
"""
fhir_to_pdf.py
─────────────────────
Generează fișiere PDF (Bilet de ieșire) din Bundle-uri FHIR R4 (JSON).

Usage:
    python fhir_to_pdf.py <input_path> [output_path]

    <input_path> poate fi un singur fișier .json sau un director cu fișiere .json.
    Dacă calea de ieșire este omisă, PDF-urile sunt salvate în același director,
    cu numele <nume_pacient>_bilet_iesire.pdf.

Supported FHIR resource types:
    Patient, Encounter, Condition, Procedure, MedicationRequest,
    Organization, Practitioner
"""

import json
import sys
import os
import textwrap
from datetime import datetime, date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable


# ─────────────────────────────────────────────────────────────────────────────
#  COLOUR PALETTE  (neutral medical grey-blue theme)
# ─────────────────────────────────────────────────────────────────────────────
C_BLACK      = colors.HexColor("#1A1A1A")
C_DARK_GREY  = colors.HexColor("#444444")
C_MID_GREY   = colors.HexColor("#777777")
C_LIGHT_GREY = colors.HexColor("#EEEEEE")
C_HEADER_BG  = colors.HexColor("#F0F4F8")   # very pale blue-grey
C_ACCENT     = colors.HexColor("#2C5F8A")   # hospital blue
C_WHITE      = colors.white


# ─────────────────────────────────────────────────────────────────────────────
#  PARAGRAPH STYLES
# ─────────────────────────────────────────────────────────────────────────────
def make_styles():
    base = dict(fontName="Helvetica", fontSize=9, leading=12,
                textColor=C_BLACK, spaceAfter=2)

    return {
        "hospital_name": ParagraphStyle(
            "hospital_name",
            fontName="Helvetica-Bold", fontSize=13, leading=16,
            textColor=C_ACCENT, spaceAfter=1,
        ),
        "department": ParagraphStyle(
            "department",
            fontName="Helvetica-Bold", fontSize=10, leading=13,
            textColor=C_BLACK, spaceAfter=1,
        ),
        "address_small": ParagraphStyle(
            "address_small",
            fontName="Helvetica", fontSize=8, leading=10,
            textColor=C_MID_GREY, spaceAfter=0,
        ),
        "doc_title": ParagraphStyle(
            "doc_title",
            fontName="Helvetica-Bold", fontSize=16, leading=20,
            textColor=C_ACCENT, alignment=TA_CENTER, spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Oblique", fontSize=8.5, leading=11,
            textColor=C_MID_GREY, spaceAfter=0,
        ),
        "value": ParagraphStyle(
            "value",
            fontName="Helvetica", fontSize=9, leading=11,
            textColor=C_BLACK, spaceAfter=0,
        ),
        "value_bold": ParagraphStyle(
            "value_bold",
            fontName="Helvetica-Bold", fontSize=9, leading=11,
            textColor=C_BLACK, spaceAfter=0,
        ),
        "section_title": ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold", fontSize=9.5, leading=13,
            textColor=C_BLACK, spaceAfter=3, spaceBefore=8,
            underlineWidth=0.5, underlineOffset=-1,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica", fontSize=9, leading=13,
            textColor=C_BLACK, alignment=TA_JUSTIFY,
            firstLineIndent=14, spaceAfter=3,
        ),
        "rec_num": ParagraphStyle(
            "rec_num",
            fontName="Helvetica-Bold", fontSize=9, leading=13,
            textColor=C_BLACK, spaceAfter=1,
        ),
        "rec_body": ParagraphStyle(
            "rec_body",
            fontName="Helvetica", fontSize=9, leading=13,
            textColor=C_BLACK, leftIndent=14, spaceAfter=2,
        ),
        "rec_indent": ParagraphStyle(
            "rec_indent",
            fontName="Helvetica-Oblique", fontSize=8.5, leading=12,
            textColor=C_DARK_GREY, leftIndent=28, spaceAfter=1,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica", fontSize=7.5, leading=10,
            textColor=C_MID_GREY, alignment=TA_CENTER,
        ),
        "blood_label": ParagraphStyle(
            "blood_label",
            fontName="Helvetica-Oblique", fontSize=8.5, leading=11,
            textColor=C_MID_GREY, alignment=TA_RIGHT, spaceAfter=2,
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  FHIR PARSING
# ─────────────────────────────────────────────────────────────────────────────
def parse_fhir(bundle: dict) -> dict:
    """Extract clinically relevant data from a FHIR R4 Bundle."""

    entries = {e["resource"]["resourceType"]: [] for e in bundle.get("entry", [])}
    for e in bundle.get("entry", []):
        rt = e["resource"]["resourceType"]
        entries.setdefault(rt, []).append(e["resource"])

    # ── Patient ──────────────────────────────────────────────────────────────
    patient_res = entries.get("Patient", [{}])[0]

    official = next(
        (n for n in patient_res.get("name", []) if n.get("use") == "official"),
        patient_res.get("name", [{}])[0] if patient_res.get("name") else {}
    )
    family = official.get("family", "Necunoscut")
    given  = " ".join(official.get("given", []))
    prefix = " ".join(official.get("prefix", []))
    full_name = f"{family.upper()} {given.upper()}"
    display_name = f"{prefix} {given} {family}".strip()

    dob_raw = patient_res.get("birthDate", "")
    dob_fmt  = _fmt_date(dob_raw)
    age      = _calc_age(dob_raw)

    gender_raw = patient_res.get("gender", "unknown")
    gender = {"male": "Masculin", "female": "Feminin"}.get(gender_raw, gender_raw.capitalize())

    addr = (patient_res.get("address") or [{}])[0]
    address_line = ", ".join(addr.get("line", [])) or "N/A"
    city    = addr.get("city", "N/A")
    state   = addr.get("state", "")
    zip_    = addr.get("postalCode", "")
    country = addr.get("country", "")

    phone = next(
        (t["value"] for t in patient_res.get("telecom", []) if t.get("system") == "phone"),
        "—"
    )

    mrn_id = next(
        (i["value"] for i in patient_res.get("identifier", [])
         if "MR" in str(i.get("type", {}))),
        patient_res.get("id", "N/A")
    )
    mrn_short = mrn_id[:8].upper() if len(mrn_id) > 8 else mrn_id.upper()

    # ── Encounters: pick the most clinically significant ──────────────────────
    encounter_res = _pick_encounter(entries.get("Encounter", []))

    enc_period   = encounter_res.get("period", {})
    admit_raw    = enc_period.get("start", "")
    discharge_raw= enc_period.get("end", "")
    admit_dt     = _fmt_date(admit_raw)
    discharge_dt = _fmt_date(discharge_raw)

    enc_type_text = (
        (encounter_res.get("type") or [{}])[0]
        .get("text", "Consult General")
    )

    service_provider = (
        encounter_res.get("serviceProvider", {}).get("display", "")
    )

    attending = (
        (encounter_res.get("participant") or [{}])[0]
        .get("individual", {}).get("display", "")
    )

    enc_id_short = encounter_res.get("id", "N/A")[:8].upper()

    # ── Organization ─────────────────────────────────────────────────────────
    orgs = entries.get("Organization", [])
    hospital_org = next(
        (o for o in orgs if service_provider and
         service_provider.lower() in o.get("name", "").lower()),
        orgs[0] if orgs else {}
    )
    hospital_name = hospital_org.get("name", service_provider or "Centru Medical")
    hosp_addr = (hospital_org.get("address") or [{}])[0]
    hosp_line = ", ".join(hosp_addr.get("line", []))
    hosp_city = hosp_addr.get("city", "")
    hosp_state= hosp_addr.get("state", "")
    hosp_zip  = hosp_addr.get("postalCode", "")
    hospital_address = " | ".join(filter(None, [hosp_line, f"{hosp_city}, {hosp_state} {hosp_zip}".strip(", ")]))
    hosp_phone = next(
        (t["value"] for t in hospital_org.get("telecom", []) if t.get("system") == "phone"),
        "—"
    )

    # ── Practitioner ─────────────────────────────────────────────────────────
    practitioners = entries.get("Practitioner", [])
    pract = practitioners[0] if practitioners else {}
    pract_name_obj = (pract.get("name") or [{}])[0]
    pract_prefix = " ".join(pract_name_obj.get("prefix", []))
    pract_given  = " ".join(pract_name_obj.get("given", []))
    pract_family = pract_name_obj.get("family", "")
    pract_display = attending or f"{pract_prefix} {pract_given} {pract_family}".strip()

    # ── Conditions ────────────────────────────────────────────────────────────
    conditions_all = entries.get("Condition", [])

    # Conditions active/resolved around the encounter date
    enc_conditions = _conditions_for_encounter(conditions_all, encounter_res)
    primary_dx, secondary_dx = _split_diagnoses(enc_conditions, conditions_all)

    # ── Procedures ────────────────────────────────────────────────────────────
    procedures = entries.get("Procedure", [])
    enc_procs = _procs_for_encounter(procedures, encounter_res)

    # ── Medications ──────────────────────────────────────────────────────────
    med_requests = entries.get("MedicationRequest", [])
    enc_meds = _meds_for_encounter(med_requests, encounter_res)

    # ── Epicrisis (auto-generated narrative) ──────────────────────────────────
    epicrisis = _build_epicrisis(
        display_name, age, gender, primary_dx, secondary_dx,
        enc_procs, enc_conditions, admit_raw, discharge_raw
    )

    # ── Recommendations ───────────────────────────────────────────────────────
    recommendations = _build_recommendations(primary_dx, enc_procs, enc_meds, pract_display)

    return {
        # Patient
        "patient_name":    full_name,
        "display_name":    display_name,
        "dob":             dob_fmt,
        "age":             age,
        "gender":          gender,
        "address":         address_line,
        "city":            city,
        "state":           state,
        "zip":             zip_,
        "phone":           phone,
        "mrn":             mrn_short,
        # Encounter
        "sheet_number":    enc_id_short,
        "presentation_code": mrn_short[:6],
        "admit_date":      admit_dt,
        "discharge_date":  discharge_dt,
        "encounter_type":  enc_type_text,
        # Hospital
        "hospital_name":   hospital_name.upper(),
        "hospital_address":hospital_address,
        "hospital_phone":  hosp_phone,
        "department":      _infer_department(primary_dx, enc_type_text),
        # Clinical
        "primary_dx":      primary_dx,
        "secondary_dx":    secondary_dx,
        "epicrisis":       epicrisis,
        "recommendations": recommendations,
        # Signing
        "attending":       pract_display,
        "print_date":      datetime.now().strftime("%d.%m.%Y %H:%M"),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  PARSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_date(raw: str) -> str:
    if not raw:
        return "—"
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:len(fmt) + 3].rstrip("Z"), fmt.rstrip("%z"))
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return raw[:10]


def _calc_age(dob_raw: str) -> int:
    if not dob_raw:
        return 0
    try:
        dob = datetime.strptime(dob_raw[:10], "%Y-%m-%d").date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return 0


def _parse_dt(raw: str):
    """Return a naive datetime from an ISO string, or None."""
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            s = raw[:19]
            return datetime.strptime(s, fmt[:len(s)])
        except ValueError:
            continue
    return None


def _pick_encounter(encounters: list) -> dict:
    """
    Choose the most clinically significant encounter:
    Prefer inpatient/emergency over ambulatory; within those, the most recent.
    """
    if not encounters:
        return {}
    priority = {"IMP": 0, "EMER": 1, "AMB": 2}
    def sort_key(enc):
        cls_code = enc.get("class", {}).get("code", "AMB")
        dt = _parse_dt(enc.get("period", {}).get("start", "")) or datetime.min
        return (priority.get(cls_code, 3), -dt.timestamp() if dt != datetime.min else 0)
    return sorted(encounters, key=sort_key)[0]


def _conditions_for_encounter(conditions: list, encounter: dict) -> list:
    """Return conditions recorded at or around the encounter date."""
    enc_start = _parse_dt(encounter.get("period", {}).get("start", ""))
    if not enc_start:
        return conditions

    relevant = []
    for c in conditions:
        onset = _parse_dt(c.get("onsetDateTime", "") or c.get("recordedDate", ""))
        if onset is None:
            continue
        # Within a ±90-day window around encounter start
        delta = abs((onset.replace(tzinfo=None) - enc_start.replace(tzinfo=None)).days)
        if delta <= 90:
            relevant.append(c)
    return relevant if relevant else conditions[:5]


def _split_diagnoses(enc_conditions: list, all_conditions: list) -> tuple:
    """
    Primary: most recent / first condition resolved around the encounter.
    Secondary: others.
    """
    if not enc_conditions and all_conditions:
        enc_conditions = all_conditions[:5]

    # Sort by onset descending
    def onset_key(c):
        dt = _parse_dt(c.get("onsetDateTime", "") or c.get("recordedDate", ""))
        return dt or datetime.min
    sorted_conds = sorted(enc_conditions, key=onset_key, reverse=True)

    texts = [c["code"]["text"] for c in sorted_conds if "text" in c.get("code", {})]
    texts = list(dict.fromkeys(texts))  # deduplicate, preserve order

    primary = texts[0].upper() if texts else "DIAGNOSTIC PRINCIPAL NESPECIFICAT"
    secondary = texts[1:] if len(texts) > 1 else []
    return primary, secondary


def _procs_for_encounter(procedures: list, encounter: dict) -> list:
    enc_start = _parse_dt(encounter.get("period", {}).get("start", ""))
    enc_end   = _parse_dt(encounter.get("period", {}).get("end", ""))
    if not enc_start:
        return [p["code"]["text"] for p in procedures[:5] if "text" in p.get("code", {})]

    result = []
    for p in procedures:
        perf = p.get("performedDateTime") or (p.get("performedPeriod") or {}).get("start", "")
        dt = _parse_dt(perf)
        if dt is None:
            continue
        dtn = dt.replace(tzinfo=None)
        s   = enc_start.replace(tzinfo=None)
        e   = (enc_end or enc_start).replace(tzinfo=None)
        if s - __import__("datetime").timedelta(days=1) <= dtn <= e + __import__("datetime").timedelta(days=1):
            text = p.get("code", {}).get("text", "")
            if text:
                result.append(text)
    return result or [p["code"]["text"] for p in procedures[:5] if "text" in p.get("code", {})]


def _meds_for_encounter(med_requests: list, encounter: dict) -> list:
    enc_start = _parse_dt(encounter.get("period", {}).get("start", ""))
    result = []
    for m in med_requests:
        authored = _parse_dt(m.get("authoredOn", ""))
        name = m.get("medicationCodeableConcept", {}).get("text", "")
        if not name:
            continue
        dosage_list = m.get("dosageInstruction", [])
        dosage_text = dosage_list[0].get("text", "") if dosage_list else ""

        if enc_start and authored:
            delta = abs((authored.replace(tzinfo=None) - enc_start.replace(tzinfo=None)).days)
            if delta > 365:
                continue
        result.append({"name": name, "dosage": dosage_text})
    return result


def _infer_department(primary_dx: str, enc_type: str) -> str:
    dx = primary_dx.lower()
    et = enc_type.lower()
    if any(k in dx for k in ["fracture", "bone", "clavicle", "femur", "ortho"]):
        return "ORTOPEDIE ȘI TRAUMATOLOGIE"
    if any(k in dx for k in ["cardiac", "heart", "myocardial", "coronary"]):
        return "CARDIOLOGIE"
    if any(k in dx for k in ["colon", "polyp", "rectal", "gastrointestinal"]):
        return "GASTROENTEROLOGIE"
    if "emergency" in et:
        return "MEDICINĂ DE URGENȚĂ"
    return "MEDICINĂ INTERNĂ"


def _build_epicrisis(name, age, gender, primary_dx, secondary_dx,
                     procedures, conditions, admit_raw, discharge_raw) -> str:
    admit_fmt    = _fmt_date(admit_raw)
    discharge_fmt= _fmt_date(discharge_raw)
    secondary_str = (", ".join(secondary_dx[:3]) + ".") if secondary_dx else "lipsa patologiei secundare semnificative."
    proc_str = (", ".join(procedures[:4]) + ".") if procedures else "management clinic standard."

    gender_ro = gender.lower()
    if gender_ro == "masculin":
        pacient_str = "Pacientul"
        prezinta_str = "prezintă"
    elif gender_ro == "feminin":
        pacient_str = "Pacienta"
        prezinta_str = "prezintă"
    else:
        pacient_str = "Pacientul/a"
        prezinta_str = "prezintă"

    return (
        f"{pacient_str} {name}, sex {gender_ro}, vârstă {age} ani, a fost internat(ă) la data de {admit_fmt} "
        f"și externat(ă) la data de {discharge_fmt}. "
        f"{pacient_str} se {prezinta_str} cu {primary_dx.lower()}, având în antecedente {secondary_str} "
        f"În urma examenului clinic și paraclinic, diagnosticul de externare a fost confirmat ca "
        f"{primary_dx}. "
        f"Pe durata spitalizării au fost efectuate următoarele proceduri: {proc_str} "
        f"Starea pacientului la externare este stabilă, acesta fiind informat cu privire la planul de "
        f"monitorizare ambulatorie detaliat mai jos."
    )


def _build_recommendations(primary_dx: str, procedures: list,
                            medications: list, attending: str) -> list:
    recs = []
    dx = primary_dx.lower()

    # Mobility
    if any(k in dx for k in ["fracture", "bone", "ortho"]):
        recs.append({
            "title": "Imobilizare și Mobilitate",
            "body": "Mobilizarea fără sprijin a membrului afectat timp de 6 săptămâni, utilizând o eșarfă sau un dispozitiv ortotic adecvat.",
        })
    else:
        recs.append({
            "title": "Mobilitate",
            "body": "Reluarea treptată a activității fizice normale, în limita toleranței. Se va evita efortul fizic intens timp de 2–4 săptămâni.",
        })

    # Positioning
    recs.append({
        "title": "Poziționare",
        "body": "Menținerea membrului afectat în poziție proclivă (elevată) în repaus pentru a minimiza edemul.",
    })

    # Physical therapy
    recs.append({
        "title": "Kinetoterapie",
        "body": "Program de recuperare medicală în ambulatoriu pentru restabilirea mobilității și tonifierea musculară progresivă. Inițierea se va face la 2–4 săptămâni post-externare.",
    })

    # Wound care
    if any("admission" in p.lower() or "surgery" in p.lower() or "procedure" in p.lower()
           for p in procedures):
        recs.append({
            "title": "Îngrijirea Plăgii",
            "body": "Suprimarea firelor de sutură / agrafelor la 14 zile post-procedură. Se va menține plaga curată și uscată. Raportați imediat orice semne de infecție (roșeață, secreții, febră).",
        })

    # Medications
    med_block = {"title": "Tratament Farmacologic", "body": "", "lines": []}
    if medications:
        med_block["body"] = "Se va continua următorul tratament medicamentos conform prescripției:"
        for m in medications:
            line = m["name"]
            if m["dosage"]:
                line += f"  —  {m['dosage']}"
            med_block["lines"].append(line)
    else:
        med_block["body"] = (
            "Tratament analgezic / antiinflamator la nevoie (consultați medicul înainte de a "
            "achiziționa medicamente fără rețetă dacă aveți comorbidități)."
        )
    recs.append(med_block)

    # Follow-up
    recs.append({
        "title": "Control Medical",
        "body": f"Control în ambulatoriu la dr. {attending} la 6 săptămâni post-externare (sau mai devreme dacă simptomele se agravează).",
    })

    # Sick leave / CM
    recs.append({
        "title": "Concediu Medical",
        "body": "Certificat de concediu medical eliberat pentru perioada spitalizării plus 14 zile post-externare, cu posibilitatea prelungirii prin ambulatoriul de specialitate.",
    })

    return recs


# ─────────────────────────────────────────────────────────────────────────────
#  PDF LAYOUT BUILDERS
# ─────────────────────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4          # 595.28 × 841.89 pt
MARGIN_L = 18 * mm
MARGIN_R = 18 * mm
MARGIN_T = 16 * mm
MARGIN_B = 16 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


def _hr(color=C_ACCENT, thickness=0.8, space_before=4, space_after=4):
    return HRFlowable(
        width="100%", thickness=thickness,
        color=color, spaceAfter=space_after, spaceBefore=space_before,
    )


def _section_title(text: str, styles: dict):
    return Paragraph(f"<u><b>{text}</b></u>", styles["section_title"])


def _info_table(rows: list, styles: dict) -> Table:
    """
    rows: list of (label, value, label, value) tuples — 4 columns per row.
    Columns: label | value | label | value
    """
    col_w = [CONTENT_W * 0.20, CONTENT_W * 0.30, CONTENT_W * 0.20, CONTENT_W * 0.30]

    table_data = []
    for label1, val1, label2, val2 in rows:
        v1_style = styles["value_bold"] if val1 else styles["value"]
        v2_style = styles["value_bold"] if val2 else styles["value"]
        table_data.append([
            Paragraph(label1, styles["label"]),
            Paragraph(str(val1), v1_style),
            Paragraph(label2, styles["label"]),
            Paragraph(str(val2), v2_style),
        ])

    t = Table(table_data, colWidths=col_w, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        # alternating row shading
        *[("BACKGROUND", (0, i), (-1, i), C_HEADER_BG if i % 2 == 0 else C_WHITE)
          for i in range(len(table_data))],
        ("LINEBELOW",     (0, -1), (-1, -1), 0.4, C_LIGHT_GREY),
        ("BOX",           (0, 0),  (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    return t


def build_pdf(data: dict, output_path: str):
    styles = make_styles()
    story  = []

    # ── HEADER: hospital block (left) + blood group (right) ─────────────────
    header_left = [
        Paragraph(data["hospital_name"], styles["hospital_name"]),
        Paragraph(data["department"], styles["department"]),
        Paragraph(data["hospital_address"], styles["address_small"]),
        Paragraph(f"Tel: {data['hospital_phone']}", styles["address_small"]),
    ]
    header_right = [
        Paragraph("<i>Grup sangvin:</i>  ___________   <i>Rh:</i> ___", styles["blood_label"]),
        Paragraph("<i>Alergii:</i>  ________________________________", styles["blood_label"]),
    ]

    header_table = Table(
        [[header_left, header_right]],
        colWidths=[CONTENT_W * 0.65, CONTENT_W * 0.35],
        hAlign="LEFT",
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("LINEBELOW",     (0, 0), (-1, 0), 1.0, C_ACCENT),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5 * mm))

    # ── DOCUMENT TITLE ────────────────────────────────────────────────────────
    story.append(Paragraph("BILET DE IEȘIRE / SCRISOARE MEDICALĂ", styles["doc_title"]))
    story.append(_hr(color=C_ACCENT, thickness=1.2, space_before=2, space_after=6))

    # ── PATIENT INFO GRID ────────────────────────────────────────────────────
    info_rows = [
        ("FOCG Nr.:",         data["sheet_number"],
         "Nume și Prenume:",  data["patient_name"]),
        ("Cod Prezentare:",   data["presentation_code"],
         "Sex:",              data["gender"]),
        ("Vârstă:",           f"{data['age']} ani",
         "Oraș:",             data["city"].upper()),
        ("Localitate:",       data["city"],
         "Județ:",            data["state"]),
        ("Adresă:",           data["address"],
         "Telefon:",          data["phone"]),
        ("Data Internării:",  data["admit_date"],
         "Data Externării:",  data["discharge_date"]),
    ]
    story.append(_info_table(info_rows, styles))
    story.append(Spacer(1, 4 * mm))
    story.append(_hr(color=colors.HexColor("#CCCCCC"), thickness=0.5,
                     space_before=1, space_after=4))

    # ── DISCHARGE DIAGNOSIS ───────────────────────────────────────────────────
    story.append(_section_title("Diagnostic de Externare:", styles))
    story.append(Paragraph(f"<b>{data['primary_dx']}</b>",
                            ParagraphStyle("dx", fontName="Helvetica-Bold",
                                           fontSize=9.5, textColor=C_BLACK,
                                           spaceBefore=2, spaceAfter=2)))

    if data["secondary_dx"]:
        story.append(_section_title("Diagnostice Secundare:", styles))
        for sdx in data["secondary_dx"]:
            story.append(Paragraph(sdx, styles["body"]))

    story.append(Spacer(1, 3 * mm))

    # ── EPICRISIS ─────────────────────────────────────────────────────────────
    story.append(_section_title("Epicriză:", styles))
    story.append(Paragraph(data["epicrisis"], styles["body"]))
    story.append(Spacer(1, 3 * mm))

    # ── RECOMMENDATIONS ───────────────────────────────────────────────────────
    story.append(_section_title("Recomandări:", styles))

    for i, rec in enumerate(data["recommendations"], 1):
        block = []
        block.append(Paragraph(
            f"<b>{i}.</b> {rec['title']}",
            styles["rec_num"]
        ))
        if rec.get("body"):
            block.append(Paragraph(rec["body"], styles["rec_body"]))
        for line in rec.get("lines", []):
            block.append(Paragraph(f"— {line}", styles["rec_indent"]))
        story.append(KeepTogether(block))

    story.append(Spacer(1, 6 * mm))

    # ── SIGNATURES ────────────────────────────────────────────────────────────
    sig_table = Table(
        [[
            Paragraph(f"Medic Curant: <b>{data['attending']}</b>",
                      ParagraphStyle("sig", fontName="Helvetica", fontSize=8.5,
                                     textColor=C_DARK_GREY)),
            Paragraph("Semnătură: ________________",
                      ParagraphStyle("sig2", fontName="Helvetica", fontSize=8.5,
                                     textColor=C_DARK_GREY, alignment=TA_CENTER)),
            Paragraph("Parafă",
                      ParagraphStyle("sig3", fontName="Helvetica", fontSize=8.5,
                                     textColor=C_LIGHT_GREY, alignment=TA_RIGHT)),
        ]],
        colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.30, CONTENT_W * 0.25],
        hAlign="LEFT",
    )
    sig_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("LINEBEFORE",    (1, 0), (1, 0), 0.4, C_LIGHT_GREY),
        ("LINEBEFORE",    (2, 0), (2, 0), 0.4, C_LIGHT_GREY),
        ("LINEABOVE",     (0, 0), (-1, 0), 0.5, colors.HexColor("#AAAAAA")),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 3 * mm))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(_hr(color=C_LIGHT_GREY, thickness=0.4, space_before=2, space_after=3))
    story.append(Paragraph(
        f"Generat la: {data['print_date']}  |  CNP / ID Pacient: {data['mrn']}  |  Pagina 1 din 1",
        styles["footer"]
    ))

    # ── BUILD ─────────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title="Discharge Summary",
        author=data.get("attending", ""),
        subject=f"Discharge Summary – {data['patient_name']}",
    )
    doc.build(story)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python fhir_to_pdf.py <input_path> [output_path]")
        sys.exit(1)

    input_arg = sys.argv[1]

    # Identify all files to process
    if os.path.isdir(input_arg):
        # Process all .json files in the directory
        json_files = [os.path.join(input_arg, f) for f in os.listdir(input_arg) if f.endswith(".json")]
        if not json_files:
            print(f"No .json files found in directory: {input_arg}")
            sys.exit(0)
    else:
        # Process a single file
        json_files = [input_arg]

    for input_path in json_files:
        if not os.path.exists(input_path):
            print(f"Error: file not found: {input_path}")
            continue

        try:
            with open(input_path, encoding="utf-8") as f:
                bundle = json.load(f)
        except Exception as e:
            print(f"Error reading {input_path}: {e}")
            continue

        if bundle.get("resourceType") != "Bundle":
            print(f"Warning: {input_path} does not appear to be a FHIR Bundle — attempting anyway.")

        print(f"Parsing FHIR bundle: {input_path}")
        try:
            data = parse_fhir(bundle)
        except Exception as e:
            print(f"Error parsing {input_path}: {e}")
            continue

        # Determine output path
        # If processing a directory, we ignore sys.argv[2] (if any) and save in the same dir
        # If processing a single file, we use sys.argv[2] if provided
        if len(sys.argv) >= 3 and not os.path.isdir(input_arg):
            output_path = sys.argv[2]
        else:
            safe_name = data["patient_name"].replace(" ", "_").lower()
            output_path = os.path.join(
                os.path.dirname(os.path.abspath(input_path)),
                f"{safe_name}_bilet_iesire.pdf"
            )

        print(f"Generating PDF → {output_path}")
        try:
            build_pdf(data, output_path)
        except Exception as e:
            print(f"Error generating PDF for {input_path}: {e}")
            continue

    print("Done.")


if __name__ == "__main__":
    main()
