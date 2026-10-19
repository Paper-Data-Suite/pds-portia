"""#59 Slice 6: one-file returned-paper intake for the teacher-facing workflow.

Core owns original-source custody and generic route dispatch. Portia checks
historical Page Targets and writes only operational Page Record receipts.
There is no OCR, roster matching, interpretation or behavior-domain assertion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from portia.capture.contracts import CaptureAuthorization
from portia.intake.contracts import RetainedPageIdentity
from portia.intake.dispatch import FilePageRouteDispatchService
from portia.intake.page_records import FilePageRecordService
from portia.intake.recognition import FilePageQrDiscoveryService
from portia.intake.recovery import (
    FileCoreRetainedSourceRecoveryService,
    RetainedSourceCandidate,
)
from portia.intake.retention import (
    FileRetainFirstIntakeService,
    RetainedIntakeSource,
    SourcePreflight,
)
from portia.storage.errors import PortiaStorageError

TeacherPageState = Literal[
    "recorded", "already_recorded", "needs_attention", "retryable", "conflict"
]
TeacherSourceState = Literal[
    "completed", "completed_with_exceptions", "retained_needs_attention"
]


@dataclass(frozen=True, slots=True)
class TeacherPageResult:
    """One numbered physical page, with no scanned text or QR payload."""

    identity: RetainedPageIdentity
    status: TeacherPageState
    reason: str
    class_id: str | None = None
    form_name: str | None = None
    page_target_index: int | None = None
    template_page_ordinal: int | None = None
    receipt_id: str | None = None
    work_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RetainedPageIdentity):
            raise ValueError("teacher page requires Core source-page identity")
        if self.status not in {
            "recorded",
            "already_recorded",
            "needs_attention",
            "retryable",
            "conflict",
        }:
            raise ValueError("invalid returned-paper page status")
        if not self.reason or len(self.reason) > 80:
            raise ValueError("status reason must be a bounded diagnostic code")
        if self.status in {"recorded", "already_recorded"} and not self.receipt_id:
            raise ValueError("accepted page requires exact Page Record identity")
        if self.status not in {"recorded", "already_recorded"} and self.receipt_id:
            raise ValueError("unaccepted page cannot disclose a receipt")


@dataclass(frozen=True, slots=True)
class TeacherSourceResult:
    """Retained source with one page outcome for every physical source page."""

    source: RetainedIntakeSource
    pages: tuple[TeacherPageResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source, RetainedIntakeSource):
            raise ValueError("teacher result requires Core retained source")
        if len(self.pages) != self.source.page_count:
            raise ValueError("all original source pages must be reported")
        for index, page in enumerate(self.pages, 1):
            if page.identity != self.source.page_identity(index):
                raise ValueError("teacher result changed source page order")

    @property
    def accepted(self) -> int:
        return sum(p.status in {"recorded", "already_recorded"} for p in self.pages)

    @property
    def requires_attention(self) -> int:
        return len(self.pages) - self.accepted

    @property
    def status(self) -> TeacherSourceState:
        if not self.requires_attention:
            return "completed"
        if self.accepted:
            return "completed_with_exceptions"
        return "retained_needs_attention"


class TeacherReturnedPaperService:
    """One submitted source, all pages, Core custody, exact routes and receipts.

    No class is inferred from filename or form order. Each discovered PDS2
    locator is authorized separately before class-specific records are read.
    Failure after custody preserves Core bytes; the caller can retry the SAME
    retained-source instance (rather than creating a second scan identity).
    """

    def __init__(
        self, root: str | Path, *, authorization: CaptureAuthorization
    ) -> None:
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("CaptureAuthorization is required")
        self.root = Path(root).absolute()
        self.authorization = authorization
        self.retention = FileRetainFirstIntakeService(self.root)
        self.discovery = FilePageQrDiscoveryService(self.root)
        self.dispatch = FilePageRouteDispatchService(self.root)
        self.records = FilePageRecordService(self.root)
        self.recovery = FileCoreRetainedSourceRecoveryService(self.root)

    def recent_retained(self) -> tuple[RetainedSourceCandidate, ...]:
        """Find prior Core scan identities without re-retaining their bytes."""
        return self.recovery.recent()

    def resume_recovered(
        self, candidate: RetainedSourceCandidate
    ) -> TeacherSourceResult:
        """Verify and resume one exact retained source after process restart."""
        return self.resume_retained(self.recovery.load(candidate))

    def inspect(self, file: str | Path) -> SourcePreflight:
        """Read-only source validation, suitable before explicit confirmation."""
        return self.retention.preflight(file)

    def process_file(self, file: str | Path) -> TeacherSourceResult:
        """Retain the whole source first, then independently process each page."""
        retained = self.retention.admit_and_retain(file)
        return self.resume_retained(retained)

    def resume_retained(self, source: RetainedIntakeSource) -> TeacherSourceResult:
        """Replay the same retained-source identity, preserving durable receipts."""
        if not isinstance(source, RetainedIntakeSource):
            raise TypeError("resume requires a typed Core-retained intake source")
        try:
            discoveries = self.discovery.discover(source)
        except (OSError, ValueError, RuntimeError, PortiaStorageError):
            return self._interrupted(source, "page_discovery_unavailable")
        try:
            verified = self.dispatch.verify(
                discoveries, authorization=self.authorization
            )
        except (OSError, ValueError, RuntimeError, PortiaStorageError, PermissionError):
            return self._interrupted(source, "route_verification_unavailable")
        try:
            receipts = self.records.record(verified, authorization=self.authorization)
        except (OSError, ValueError, RuntimeError, PortiaStorageError, PermissionError):
            # Some pages may already have durable receipts; never claim the
            # whole source failed without effects or roll back Core custody.
            return self._interrupted(source, "page_receipts_need_recovery")
        pages: list[TeacherPageResult] = []
        for route, receipt in zip(receipts.source_routes.pages, receipts.pages):
            owner = route.verified
            target = owner.target if owner is not None else None
            identity = target.to_dict().get("template_identity") if target else None
            if not isinstance(identity, dict):
                identity = {}
            page_index = target.field("page_index") if target else None
            ordinal = identity.get("page_ordinal")
            if receipt.status == "created":
                status: TeacherPageState = "recorded"
            elif receipt.status == "reused":
                status = "already_recorded"
            else:
                status = receipt.status
            pages.append(
                TeacherPageResult(
                    identity=receipt.identity,
                    status=status,
                    reason=receipt.reason,
                    class_id=owner.locator.class_id if owner else None,
                    work_id=owner.locator.work_id if owner else None,
                    form_name=(
                        str(identity["template_id"])
                        if isinstance(identity.get("template_id"), str)
                        else None
                    ),
                    page_target_index=(page_index if type(page_index) is int else None),
                    template_page_ordinal=(ordinal if type(ordinal) is int else None),
                    receipt_id=(receipt.record.logical_id if receipt.record else None),
                )
            )
        return TeacherSourceResult(source, tuple(pages))

    @staticmethod
    def _interrupted(source: RetainedIntakeSource, reason: str) -> TeacherSourceResult:
        return TeacherSourceResult(
            source,
            tuple(
                TeacherPageResult(source.page_identity(index), "retryable", reason)
                for index in range(1, source.page_count + 1)
            ),
        )
