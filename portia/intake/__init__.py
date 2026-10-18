"""Core-retained paper intake, routed page verification and receipts."""

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
from portia.intake.dispatch import (
    FilePageRouteDispatchService,
    PageRouteOutcome,
    PageRouteStatus,
    PageRouteVerificationError,
    SourceRouteOutcomes,
    VerifiedPageRoute,
)
from portia.intake.page_records import (
    FilePageRecordService,
    PageReceiptOutcome,
    PageReceiptStatus,
    SourceReceiptOutcomes,
)
from portia.intake.recognition import (
    FilePageQrDiscoveryService,
    PageQrDiscovery,
    PageQrStatus,
    QrDiscoveryError,
    SourceQrDiscovery,
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
    "FilePageQrDiscoveryService",
    "PageQrDiscovery",
    "PageQrStatus",
    "QrDiscoveryError",
    "SourceQrDiscovery",
    "FilePageRecordService",
    "PageReceiptOutcome",
    "PageReceiptStatus",
    "SourceReceiptOutcomes",
    "FilePageRouteDispatchService",
    "PageRouteOutcome",
    "PageRouteStatus",
    "PageRouteVerificationError",
    "SourceRouteOutcomes",
    "VerifiedPageRoute",
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
