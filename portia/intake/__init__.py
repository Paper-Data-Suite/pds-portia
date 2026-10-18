"""Read-only Portia paper intake contracts; no source custody or routing yet."""

from portia.intake.contracts import (
    DEFAULT_SOURCE_LIMITS,
    HARD_MAX_PAGE_PIXELS,
    HARD_MAX_PAGES,
    HARD_MAX_SOURCE_BYTES,
    PDF_HEADER_PROBE_BYTES,
    IntakeContractError,
    RetainedPageIdentity,
    SourceAdmission,
    SourceAdmissionCode,
    SourceFormat,
    SourceSafetyLimits,
    assess_source_signature,
)

__all__ = [
    "DEFAULT_SOURCE_LIMITS",
    "HARD_MAX_PAGE_PIXELS",
    "HARD_MAX_PAGES",
    "HARD_MAX_SOURCE_BYTES",
    "PDF_HEADER_PROBE_BYTES",
    "IntakeContractError",
    "RetainedPageIdentity",
    "SourceAdmission",
    "SourceAdmissionCode",
    "SourceFormat",
    "SourceSafetyLimits",
    "assess_source_signature",
]
