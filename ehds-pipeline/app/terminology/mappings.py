"""Backward-compatible re-exports; prefer cim10_to_snomed directly."""

from app.terminology.cim10_to_snomed import (
    CIM10_TO_SNOMED,
    SNOMED_GENERALIZATION,
    DATA_ABSENT_CODING,
    get_snomed_for_cim10,
    generalize_snomed,
    should_suppress_for_k_anonymity,
)
