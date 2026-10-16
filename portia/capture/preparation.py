"""Bounded multi-page preparation over persisted Capture Batch/Page Target routes.

This service coordinates the already-qualified services. It does not render
forms, create domain evidence, invent student identity, or repair Core history.
Only a reloaded Core registration can produce a verified printable PDS2 value.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from portia.capture.batches import FileCaptureBatchService
from portia.capture.contracts import (
    CaptureAuthorization,
    CapturePreparationError,
    CapturePreparationRequest,
    CapturePreparationResult,
    PagePreparationResult,
    PreparationStatus,
)
from portia.capture.page_targets import FilePageTargetService
from portia.capture.purposes import (
    resolve_existing_capture_context,
    validate_page_purpose,
)
from portia.capture.routes import FilePageRouteService
from portia.models import PageTargetV1, PageTargetV2
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.storage.repository import PortiaRepository


def _incomplete(
    target: PageTargetV2, status: PreparationStatus, diagnostic: str
) -> PagePreparationResult:
    return PagePreparationResult(status, target, diagnostics=(diagnostic,))


class FileCapturePreparationService:
    """Prepare a batch in page-index order, preserving partial durable results.

    Validation and available-state planning happen before any new Page Target or
    Core route. Each page is then independently persisted and verified. There is
    deliberately no pretend multi-file transaction: an interrupted page stops
    further writes, and an exact retry continues from durable evidence.

    ``recover`` is read-only at this slice; explicit recovery and conflict
    resolution are the responsibility of Issue #57 Slice 7.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        batch_service: FileCaptureBatchService | None = None,
        page_service: FilePageTargetService | None = None,
        route_service: FilePageRouteService | None = None,
    ) -> None:
        self.batches = (
            FileCaptureBatchService(workspace_root)
            if batch_service is None
            else batch_service
        )
        self.root = self.batches.root
        if self.root != Path(workspace_root).absolute():
            raise CapturePreparationError("Capture Batch workspace mismatch")
        self.pages = (
            FilePageTargetService(self.root, batch_service=self.batches)
            if page_service is None
            else page_service
        )
        if self.pages.root != self.root:
            raise CapturePreparationError("Page Target workspace mismatch")
        self.routes = (
            FilePageRouteService(
                self.root, batch_service=self.batches, page_service=self.pages
            )
            if route_service is None
            else route_service
        )
        if self.routes.root != self.root:
            raise CapturePreparationError("Route workspace mismatch")
        self.repository = PortiaRepository(self.root)

    def _plan(
        self,
        request: CapturePreparationRequest,
        authorization: CaptureAuthorization,
    ) -> tuple[PageTargetV2, ...]:
        """Check all requested purposes/identities before any persistence."""
        if not isinstance(request, CapturePreparationRequest):
            raise CapturePreparationError("CapturePreparationRequest required")
        class_id = request.batch.class_id
        if class_id is None:
            raise CapturePreparationError("batch class_id missing")
        # Check all three permission scopes before the first operation. The
        # component services will reauthorize each individual operation.
        for action in (
            "capture_batch.create",
            "page_target.create",
            "page_route.register",
        ):
            self.batches._authorize(class_id, action, authorization)
        seen_casefold: set[str] = set()
        ordered: list[PageTargetV2] = []
        for target in request.targets:
            page_id = target.logical_id
            if page_id is None:
                raise CapturePreparationError("Page Target ID missing")
            folded = page_id.casefold()
            if folded in seen_casefold:
                raise CapturePreparationError(
                    "case-insensitive requested target collision"
                )
            seen_casefold.add(folded)
            validate_page_purpose(target)
            resolve_existing_capture_context(
                target, repository=self.repository, path_guard=self.batches._safe
            )
            ordered.append(target)
        return tuple(sorted(ordered, key=lambda t: cast(int, t.field("page_index"))))

    def _check_existing(
        self,
        ordered: tuple[PageTargetV2, ...],
        authorization: CaptureAuthorization,
    ) -> None:
        """Fail before page writes on conflicts already visible on disk."""
        batch = ordered[0]
        class_id, work_id = batch.class_id, batch.work_id
        if class_id is None or work_id is None:
            raise CapturePreparationError("requested Page Target missing owner")
        existing = self.pages.list_targets(
            class_id, work_id, authorization=authorization
        )
        by_id: dict[str, PageTargetV1 | PageTargetV2] = {}
        for item in existing:
            item_id = item.logical_id
            if item_id is None:
                raise PortiaCorruptionError("persisted Page Target lacks identity")
            by_id[item_id.casefold()] = item
        by_index = {cast(int, item.field("page_index")): item for item in existing}
        for target in ordered:
            key = (target.logical_id or "").casefold()
            same = by_id.get(key)
            if same is not None and (
                not isinstance(same, PageTargetV2)
                or same.logical_id != target.logical_id
                or same.to_dict() != target.to_dict()
            ):
                raise PortiaConflictError("existing Page Target identity conflicts")
            index_owner = by_index.get(cast(int, target.field("page_index")))
            if index_owner is not None and index_owner.logical_id != target.logical_id:
                raise PortiaConflictError("existing Page Target index conflicts")
        # A known malformed route namespace is not allowed to receive fresh
        # Page Targets before the teacher sees the contradiction.
        self.routes._registrations(class_id, work_id)

    def prepare(
        self,
        request: CapturePreparationRequest,
        *,
        authorization: CaptureAuthorization,
    ) -> CapturePreparationResult:
        """Prepare pages and expose only verified, reloaded route identities."""
        ordered = self._plan(request, authorization)
        persisted_batch = self.batches.create_or_load(
            request.batch, authorization=authorization
        )
        self._check_existing(ordered, authorization)
        outcomes: list[PagePreparationResult] = []
        stopped = False
        for target in ordered:
            if stopped:
                outcomes.append(_incomplete(target, "retryable", "not_attempted"))
                continue
            try:
                persisted = self.pages.create_or_load(
                    target, authorization=authorization
                )
                page_result = self.routes.register_or_load(
                    persisted, authorization=authorization
                )
            except PortiaRecoveryRequiredError:
                page_result = _incomplete(target, "conflict", "requires_recovery")
            except (PortiaConflictError, PortiaCorruptionError):
                page_result = _incomplete(target, "conflict", "durable_state_conflict")
            except PortiaNotFoundError:
                page_result = _incomplete(target, "retryable", "readback_missing")
            except PortiaStorageError:
                page_result = _incomplete(target, "retryable", "storage_unavailable")
            # Invalid request and access-denied failures propagate, not relabelled
            # as a recoverable storage problem.
            outcomes.append(page_result)
            stopped = page_result.status != "verified"
        # Reload latest lifecycle rather than returning the caller's open model.
        actual_batch = self.batches.load(
            persisted_batch.class_id or "",
            persisted_batch.work_id or "",
            authorization=authorization,
        )
        return CapturePreparationResult(actual_batch, tuple(outcomes))

    def inspect(
        self,
        class_id: str,
        work_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> CapturePreparationResult:
        """Read exact persisted pages/routes without creating new artifacts."""
        batch = self.batches.load(class_id, work_id, authorization=authorization)
        pages = self.pages.list_targets(class_id, work_id, authorization=authorization)
        if any(isinstance(item, PageTargetV1) for item in pages):
            raise CapturePreparationError(
                "historical page_target@1 needs separate historical inspection"
            )
        results: list[PagePreparationResult] = []
        for page in pages:
            if not isinstance(page, PageTargetV2):
                raise CapturePreparationError("unsupported persisted Page Target")
            page_id = page.logical_id
            if page_id is None:
                raise CapturePreparationError("persisted Page Target ID missing")
            results.append(
                self.routes.inspect(
                    class_id, work_id, page_id, authorization=authorization
                )
            )
        return CapturePreparationResult(batch, tuple(results))

    def recover(
        self,
        class_id: str,
        work_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> CapturePreparationResult:
        """Read-only recovery assessment; Slice 7 owns explicit mutation."""
        return self.inspect(class_id, work_id, authorization=authorization)
