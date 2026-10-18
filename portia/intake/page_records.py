"""#59 Slice 5: attributed, retry-safe Portia Page Record receipts.

One Core-retained physical source page can create at most one receipt within
its owning Capture Batch. No behavior-domain work, OCR, or interpretation is
performed. Failed pages never invalidate an earlier successful page.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pds_core.routes import safe_module_work_descendant

from portia.capture.batches import FileCaptureBatchService
from portia.capture.contracts import CaptureAuthorization
from portia.intake.contracts import RetainedPageIdentity
from portia.intake.dispatch import (
    FilePageRouteDispatchService,
    PageRouteOutcome,
    SourceRouteOutcomes,
    VerifiedPageRoute,
)
from portia.intake.recognition import PageQrDiscovery
from portia.models import PageRecordV1
from portia.models.errors import PortiaModelError
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create, read_bytes

PageReceiptStatus = Literal[
    "created", "reused", "needs_attention", "retryable", "conflict"
]
_MAX_RECEIPTS_PER_BATCH = 4096
_RECEIPT_ID = re.compile(r"prec_[A-Za-z0-9][A-Za-z0-9_-]*\Z")


@dataclass(frozen=True, slots=True)
class PageReceiptOutcome:
    """Privacy-minimized result with optional exact persisted operational record."""

    identity: RetainedPageIdentity
    status: PageReceiptStatus
    reason: str
    record: PageRecordV1 | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RetainedPageIdentity):
            raise ValueError("receipt outcome requires a retained source-page identity")
        if self.status in {"created", "reused"}:
            if not isinstance(self.record, PageRecordV1):
                raise ValueError("accepted receipt outcome requires PageRecordV1")
        elif self.record is not None:
            raise ValueError("unaccepted page cannot expose a receipt")
        if not self.reason or len(self.reason) > 80:
            raise ValueError("receipt reason must be a bounded status code")


@dataclass(frozen=True, slots=True)
class SourceReceiptOutcomes:
    """One outcome for every original physical page, in source order."""

    source_routes: SourceRouteOutcomes
    pages: tuple[PageReceiptOutcome, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_routes, SourceRouteOutcomes):
            raise ValueError("receipts require a routed, retained source")
        if len(self.pages) != len(self.source_routes.pages):
            raise ValueError("receipt count must match original page count")
        for route, receipt in zip(self.source_routes.pages, self.pages):
            if route.identity != receipt.identity:
                raise ValueError("receipt changed original source page identity")

    @property
    def accepted(self) -> int:
        return sum(page.status in {"created", "reused"} for page in self.pages)

    @property
    def completed_with_exceptions(self) -> bool:
        return self.accepted != len(self.pages)


class FilePageRecordService:
    """Persist only freshly verified Core/Portia routes under Capture Batches.

    Core keeps original bytes and registration history. The same receipt ID is
    recomputed from retained-source identity and physical page number, *not*
    from QR route, printed target index, page ordinal, or present processing
    state. An attempt to reassign a physical page conflicts instead of forking
    a second receipt. Batch lifecycle and record creation share an exact lock.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root).absolute()
        self.batches = FileCaptureBatchService(self.root)
        self.dispatch = FilePageRouteDispatchService(self.root)

    def record(
        self,
        routed: SourceRouteOutcomes,
        *,
        authorization: CaptureAuthorization,
    ) -> SourceReceiptOutcomes:
        """Replay-safe page receipts; no all-or-nothing file transaction.

        Redo Core's read-only dispatch before any writing; an earlier route
        snapshot, authorization, or retained-source digest is not durable
        permission to write later. Every accepted page rechecks inside the
        Capture Batch lifecycle lock to defeat normal batch/route races.
        """
        if not isinstance(routed, SourceRouteOutcomes):
            raise TypeError("Page Record persistence requires SourceRouteOutcomes")
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("trusted CaptureAuthorization is required")
        refreshed = self.dispatch.verify(routed.discovery, authorization=authorization)
        results: list[PageReceiptOutcome] = []
        for discovery, page in zip(routed.discovery.pages, refreshed.pages):
            if page.status != "verified":
                results.append(
                    PageReceiptOutcome(page.identity, "needs_attention", page.status)
                )
                continue
            results.append(self._record_one(discovery, page, routed, authorization))
        # A source that changed across processing cannot be called completely
        # accepted. Already durable receipts are not erased; caller must stop.
        self.dispatch._verify_custody(
            refreshed.discovery.source.core_source,
            refreshed.discovery.source.byte_count,
        )
        return SourceReceiptOutcomes(refreshed, tuple(results))

    def _record_one(
        self,
        discovery: PageQrDiscovery,
        page: PageRouteOutcome,
        routed: SourceRouteOutcomes,
        authorization: CaptureAuthorization,
    ) -> PageReceiptOutcome:
        verified = page.verified
        if not isinstance(verified, VerifiedPageRoute):
            return PageReceiptOutcome(
                page.identity, "needs_attention", "unverified_route"
            )
        locator = verified.locator
        try:
            self.batches._authorize(
                locator.class_id, "capture_intake.page_record", authorization
            )
            # Never create a new lock for missing/unreadable operational work.
            self.batches._read(locator.class_id, locator.work_id)
        except PermissionError:
            return PageReceiptOutcome(
                page.identity, "needs_attention", "authorization_denied"
            )
        except (PortiaStorageError, ValueError, OSError):
            return PageReceiptOutcome(
                page.identity, "needs_attention", "batch_unavailable"
            )

        try:
            with self.batches._lifecycle_lock(locator.class_id, locator.work_id):
                batch, _ = self.batches._read(locator.class_id, locator.work_id)
                if batch.status == "cancelled":
                    return PageReceiptOutcome(
                        page.identity, "needs_attention", "batch_cancelled"
                    )
                # The Core registration, Page Target and class permission must
                # remain exact *inside* the same batch lifecycle lock.
                current = self.dispatch._one(
                    discovery, routed.discovery.source.core_source, authorization
                )
                if current.status != "verified" or current.verified != verified:
                    return PageReceiptOutcome(
                        page.identity, "needs_attention", "route_changed"
                    )
                self.dispatch._verify_custody(
                    routed.discovery.source.core_source,
                    routed.discovery.source.byte_count,
                )
                return self._read_or_create(current, authorization)
        except PermissionError:
            return PageReceiptOutcome(
                page.identity, "needs_attention", "authorization_denied"
            )
        except PortiaRecoveryRequiredError:
            return PageReceiptOutcome(
                page.identity, "retryable", "operation_lock_requires_recovery"
            )
        except (PortiaCorruptionError, PortiaPathError, PortiaConflictError):
            return PageReceiptOutcome(
                page.identity, "conflict", "persisted_state_conflict"
            )
        except (PortiaStorageError, OSError):
            return PageReceiptOutcome(
                page.identity, "retryable", "persistence_interrupted"
            )

    def _read_or_create(
        self,
        current: PageRouteOutcome,
        authorization: CaptureAuthorization,
    ) -> PageReceiptOutcome:
        verified = current.verified
        if not isinstance(verified, VerifiedPageRoute):
            raise PortiaCorruptionError("missing exact route within receipt lock")
        loc = verified.locator
        identifier = _receipt_id(current.identity)
        collection = self._collection(loc.class_id, loc.work_id)
        path = self.batches._safe(collection / f"{identifier}.json")
        existing = self._scan_receipts(collection)
        # Detect unknown competing IDs and contradictions before creating a
        # new deterministic receipt for a previously accepted source page.
        for item in existing:
            if item.class_id != loc.class_id or item.work_id != loc.work_id:
                raise PortiaCorruptionError("receipt is in the wrong Capture Batch")
            source = item.to_dict()["source_ref"]
            if not isinstance(source, dict):
                raise PortiaCorruptionError("stored receipt lacks source reference")
            if (
                source.get("source_scan_id") == current.identity.source_scan_id
                and source.get("source_page_number")
                == current.identity.source_page_number
                and item.logical_id != identifier
            ):
                raise PortiaConflictError(
                    "competing receipt ID for retained source page"
                )
        for item in existing:
            if item.logical_id == identifier:
                self._require_exact(item, current)
                return PageReceiptOutcome(
                    current.identity,
                    "reused",
                    "existing_" + str(item.field("processing_state")),
                    item,
                )

        if len(existing) >= _MAX_RECEIPTS_PER_BATCH:
            raise PortiaCorruptionError("Page Record inventory limit reached")

        now = datetime.now(timezone.utc).isoformat()
        actor = self.batches._actor(authorization)
        receipt = PageRecordV1(
            {
                "schema_version": "1",
                "record_type": "capture_page_record",
                "module_id": "portia",
                "class_id": loc.class_id,
                "work_id": loc.work_id,
                "page_target_id": verified.target.logical_id,
                "page_record_id": identifier,
                "route_id": loc.route_id,
                "source_ref": current.identity.page_record_source_ref(),
                "processing_state": "received",
                "created_at": now,
                "created_by": actor,
                "updated_at": now,
                "updated_by": actor,
            }
        )
        self.batches._safe(path)
        exclusive_create(path, canonical_json_bytes(receipt.to_dict()))
        saved = _read_receipt(path)
        if saved.to_dict() != receipt.to_dict():
            raise PortiaCorruptionError("Page Record readback changed after write")
        return PageReceiptOutcome(current.identity, "created", "received", saved)

    def _collection(self, class_id: str, work_id: str) -> Path:
        return self.batches._safe(
            safe_module_work_descendant(
                self.root,
                self.batches._work(class_id, work_id),
                "records/capture_page_record",
            )
        )

    def _scan_receipts(self, collection: Path) -> tuple[PageRecordV1, ...]:
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError("Page Record collection is not a directory")
        children = tuple(collection.iterdir())
        if len(children) > _MAX_RECEIPTS_PER_BATCH:
            raise PortiaCorruptionError("Page Record count exceeds bounded inventory")
        result: list[PageRecordV1] = []
        names: set[str] = set()
        for path in sorted(children, key=lambda child: child.name):
            self.batches._safe(path)
            if not path.is_file() or path.suffix != ".json":
                raise PortiaCorruptionError("unexpected Page Record collection item")
            if _RECEIPT_ID.fullmatch(path.stem) is None:
                raise PortiaCorruptionError("unrecognized Page Record name")
            folded = path.name.casefold()
            if folded in names:
                raise PortiaCorruptionError("Page Record casefold collision")
            names.add(folded)
            saved = _read_receipt(path)
            if saved.logical_id != path.stem:
                raise PortiaCorruptionError(
                    "Page Record filename differs from identity"
                )
            result.append(saved)
        return tuple(result)

    @staticmethod
    def _require_exact(saved: PageRecordV1, current: PageRouteOutcome) -> None:
        verified = current.verified
        if not isinstance(verified, VerifiedPageRoute):
            raise PortiaCorruptionError("missing verified route")
        data = saved.to_dict()
        expected = {
            "class_id": verified.locator.class_id,
            "work_id": verified.locator.work_id,
            "page_target_id": verified.target.logical_id,
            "route_id": verified.locator.route_id,
            "source_ref": current.identity.page_record_source_ref(),
        }
        if any(data.get(key) != value for key, value in expected.items()):
            raise PortiaConflictError(
                "source, route or target differs from existing receipt"
            )
        if data.get("processing_state") not in {
            "received",
            "processing",
            "processed",
            "failed",
        }:
            raise PortiaCorruptionError("unsupported historical processing state")


def _receipt_id(identity: RetainedPageIdentity) -> str:
    # Stable opaque ID: no raw student, source filename, route, class or page
    # number in the actual persisted identifier.
    digest = hashlib.sha256(
        canonical_json_bytes([identity.source_scan_id, identity.source_page_number])
    ).hexdigest()
    return "prec_" + digest[:40]


def _read_receipt(path: Path) -> PageRecordV1:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate Page Record key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError("invalid JSON constant")

    try:
        raw = json.loads(
            read_bytes(path).decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=invalid_constant,
        )
        if not isinstance(raw, dict):
            raise ValueError("Page Record must be a JSON object")
        return PageRecordV1(raw)
    except PortiaNotFoundError:
        raise
    except (UnicodeError, TypeError, ValueError, PortiaModelError) as exc:
        raise PortiaCorruptionError("untrusted persisted Page Record") from exc
