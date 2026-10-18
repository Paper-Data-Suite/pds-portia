"""Portia scan-intake contracts and Core-owned retain-first source service."""

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
from portia.intake.retention import (
    FileRetainFirstIntakeService,
    IntakeSourceError,
    RetainedIntakeSource,
    SourcePreflight,
)

__all__ = [
    "FileRetainFirstIntakeService",
    "IntakeSourceError",
    "RetainedIntakeSource",
    "SourcePreflight",
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
