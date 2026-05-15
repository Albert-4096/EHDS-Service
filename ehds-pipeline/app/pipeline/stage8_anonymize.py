import hashlib
import re
from copy import deepcopy
from datetime import timedelta, datetime
from app.config import settings
from app.models.internal import MergedRecord, DiagnosticEntry
from app.terminology.cim10_to_snomed import (
    get_snomed_for_cim10,
    generalize_snomed,
    should_suppress_for_k_anonymity,
)
from app.utils.time_shifter import TimeShifter

REGEX_PHONE = re.compile(r"(\+40|0)?(7\d{8}|2\d{8}|3\d{8})\b")
REGEX_CNP_TEXT = re.compile(r"\b\d{13}\b")
REGEX_NAME_PREFIX = re.compile(
    r"(Nume|Prenume|Pacient)(?:\s+pacient)?[:\s]+[A-ZĂÂÎȘȚa-zăâîșț\-\s]+",
    re.IGNORECASE,
)
REGEX_ADDRESS = re.compile(
    r"(Strada|Str\.|Bd\.|Bulevardul|Aleea)[:\s]+[A-Za-z0-9\s\.-]+", re.IGNORECASE
)


def _scrub_text(text: str | None) -> str | None:
    if not text:
        return text
    t = REGEX_PHONE.sub("[REDACTED PHONE]", text)
    t = REGEX_CNP_TEXT.sub("[REDACTED CNP]", t)
    t = REGEX_NAME_PREFIX.sub(r"\1: [REDACTED NAME]", t)
    t = REGEX_ADDRESS.sub(r"\1 [REDACTED ADDRESS]", t)
    return t


def _hash_cnp(cnp: str | None) -> str | None:
    if not cnp:
        return None
    return hashlib.sha256(cnp.encode("utf-8")).hexdigest()


def anonymize_record(record: MergedRecord) -> MergedRecord:
    """
    EHDS Pillar 2 Compliance: scrubs PII, shifts dates, applies k-anonymity generalization.
    """
    anon = deepcopy(record)

    if anon.structured.cnp:
        seed_str = anon.structured.cnp
        anon.structured.cnp = _hash_cnp(anon.structured.cnp)
    else:
        seed_str = anon.structured.nr_focg or "unknown"

    shifter = TimeShifter(seed_str)

    if anon.structured.dob_from_cnp:
        anon.structured.dob_from_cnp = anon.structured.dob_from_cnp + timedelta(
            days=shifter.offset_days
        )

    anon.structured.data_internarii = shifter.shift_datetime(anon.structured.data_internarii)
    anon.structured.data_externarii = shifter.shift_datetime(anon.structured.data_externarii)

    if anon.appointment and anon.appointment.datetime_parsed:
        anon.appointment.datetime_parsed = shifter.shift_datetime(anon.appointment.datetime_parsed)
        anon.appointment.datetime_raw = "[REDACTED DATE]"

    if anon.epicriza:
        for img in anon.epicriza.imaging_results:
            if img.date:
                shifted = shifter.shift_datetime(
                    datetime(img.date.year, img.date.month, img.date.day)
                )
                if shifted:
                    img.date = shifted.date()

    anon.structured.medic = "[REDACTED]"
    anon.structured.nume = "[REDACTED]"

    if anon.epicriza:
        anon.epicriza.antecedente_heredocolaterale = _scrub_text(
            anon.epicriza.antecedente_heredocolaterale
        )
        anon.epicriza.current_treatment_narrative = _scrub_text(
            anon.epicriza.current_treatment_narrative
        )
        anon.epicriza.motive_internare = [
            _scrub_text(m) for m in anon.epicriza.motive_internare if m
        ]
        anon.epicriza.antecedente_personale = [
            _scrub_text(a) for a in anon.epicriza.antecedente_personale if a
        ]

    if anon.structured.contract_number:
        anon.structured.contract_number = "[REDACTED]"

    k = settings.k_anonymity_threshold

    def _generalize_diagnosis(diag: DiagnosticEntry) -> DiagnosticEntry:
        snomed_info = get_snomed_for_cim10(diag.cod_cim10) if diag.cod_cim10 else None
        snomed_code = snomed_info["code"] if snomed_info else None
        if should_suppress_for_k_anonymity(
            diag.cod_cim10, snomed_code, cohort_count=1, k_threshold=k
        ):
            if snomed_code:
                generalized = generalize_snomed(snomed_code)
                if generalized:
                    return DiagnosticEntry(
                        denumire=f"[GENERALIZED] {generalized['display']}",
                        cod_cim10=None,
                    )
            return DiagnosticEntry(denumire="[REDACTED RARE DIAGNOSIS]", cod_cim10=None)
        return diag

    if anon.structured.diagnostic_principal:
        anon.structured.diagnostic_principal = _generalize_diagnosis(
            anon.structured.diagnostic_principal
        )

    anon.structured.diagnostice_secundare = [
        _generalize_diagnosis(d) for d in anon.structured.diagnostice_secundare
    ]

    return anon
