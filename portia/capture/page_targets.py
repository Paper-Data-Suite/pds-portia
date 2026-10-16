"""Issue #57 exact Page Target persistence, backed by Capture Batch authority.

Only new page_target@2 records may be created.  Existing @1 records remain
readable without migration.  A Page Target is a durable pre-print routing target,
not a printed page, observation, student identity, or behavior-domain event.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

from pds_core.routes import safe_module_work_descendant

from portia.capture.batches import FileCaptureBatchService
from portia.capture.contracts import CaptureAuthorization, CapturePreparationError
from portia.models import PageTargetV1, PageTargetV2
from portia.models.errors import PortiaModelError
from portia.models.identifiers import validate_external_id
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaPathError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create, read_bytes

_PAGE_ID = re.compile(r"ptgt_[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_RECORD_KIND = "capture_page_target"


def _page_id(value: str) -> str:
    validate_external_id(value, "page_target_id")
    if _PAGE_ID.fullmatch(value) is None:
        raise CapturePreparationError("Page Target requires a ptgt_ identifier")
    return value


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key in persisted Page Target")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid non-JSON number: {value}")


def _parse_page(content: bytes, path: Path) -> PageTargetV1 | PageTargetV2:
    try:
        raw = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_keys,
            parse_constant=_reject_constant,
        )
        if not isinstance(raw, dict):
            raise ValueError("Page Target must be an object")
        version = raw.get("schema_version")
        if version == "1":
            return PageTargetV1(raw)
        if version == "2":
            return PageTargetV2(raw)
        raise ValueError("unsupported Page Target version")
    except (ValueError, UnicodeError, TypeError, PortiaModelError) as exc:
        raise PortiaCorruptionError(
            f"persisted Page Target is invalid or has unknown version: {path}"
        ) from exc


class FilePageTargetService:
    """Store immutable Page Targets beneath a verified operational Capture Batch.

    Creates and batch lifecycle transitions share one exclusive mutation lock.
    The lock is Portia-owned; Core route registrations are not touched here.
    Link-like paths and unexpected files fail closed.  Race-resistant protection
    against adversarial filesystem mutation is a later #57 security slice.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        batch_service: FileCaptureBatchService | None = None,
    ) -> None:
        self.batches = (
            FileCaptureBatchService(workspace_root)
            if batch_service is None
            else batch_service
        )
        self.root = self.batches.root
        if Path(workspace_root).absolute() != self.root:
            raise CapturePreparationError(
                "Page Target and Capture Batch services must share the workspace"
            )

    def _path(self, class_id: str, work_id: str, page_target_id: str) -> Path:
        return self.batches._safe(
            safe_module_work_descendant(
                self.root,
                self.batches._work(class_id, work_id),
                f"records/{_RECORD_KIND}/{_page_id(page_target_id)}.json",
            )
        )

    def _collection(self, class_id: str, work_id: str) -> Path:
        return self.batches._safe(
            safe_module_work_descendant(
                self.root,
                self.batches._work(class_id, work_id),
                f"records/{_RECORD_KIND}",
            )
        )

    def _load_exact(
        self, class_id: str, work_id: str, page_target_id: str
    ) -> PageTargetV1 | PageTargetV2:
        path = self._path(class_id, work_id, page_target_id)
        content = read_bytes(path)
        page = _parse_page(content, path)
        if (
            page.class_id != class_id
            or page.work_id != work_id
            or page.logical_id != page_target_id
            or page.module_id != "portia"
            or page.record_type != _RECORD_KIND
        ):
            raise PortiaCorruptionError("Page Target/path ownership mismatch")
        return page

    def _scan(
        self, class_id: str, work_id: str
    ) -> tuple[PageTargetV1 | PageTargetV2, ...]:
        collection = self._collection(class_id, work_id)
        if not collection.exists():
            if collection.is_symlink():
                raise PortiaPathError("link-like Page Target directory denied")
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError("Page Target collection is not a directory")
        pages: list[PageTargetV1 | PageTargetV2] = []
        seen_indices: set[int] = set()
        seen_names: set[str] = set()
        for child in sorted(collection.iterdir(), key=lambda path: path.name):
            self.batches._safe(child)
            if child.suffix != ".json" or not child.is_file():
                raise PortiaCorruptionError(
                    "unexpected artifact in Page Target collection"
                )
            try:
                page_id = _page_id(child.stem)
            except (ValueError, CapturePreparationError) as exc:
                raise PortiaCorruptionError("invalid Page Target filename") from exc
            folded = page_id.casefold()
            if folded in seen_names:
                raise PortiaCorruptionError("case-insensitive Page Target ID collision")
            seen_names.add(folded)
            page = self._load_exact(class_id, work_id, page_id)
            index = page.field("page_index")
            if not isinstance(index, int) or isinstance(index, bool):
                raise PortiaCorruptionError("Page Target has invalid page index")
            if index in seen_indices:
                raise PortiaCorruptionError("Page Target page index collision")
            seen_indices.add(index)
            pages.append(page)
        return tuple(
            sorted(pages, key=lambda page: cast(int, page.field("page_index")))
        )

    def create_or_load(
        self, target: PageTargetV2, *, authorization: CaptureAuthorization
    ) -> PageTargetV2:
        if not isinstance(target, PageTargetV2):
            raise CapturePreparationError("only page_target@2 may be created")
        class_id, work_id, page_id = (
            target.class_id,
            target.work_id,
            target.logical_id,
        )
        if class_id is None or work_id is None or page_id is None:
            raise CapturePreparationError("Page Target lacks exact owner/identity")
        self.batches._authorize(class_id, "page_target.create", authorization)
        _page_id(page_id)
        if target.status != "active":
            raise CapturePreparationError("new Page Target must be active")
        actor = self.batches._actor(authorization)
        if (
            target.to_dict().get("created_by") != actor
            or target.to_dict().get("updated_by") != actor
        ):
            raise CapturePreparationError("Page Target creation attribution mismatch")
        # Load before lock, so a missing batch cannot manufacture an orphan lock.
        self.batches._read(class_id, work_id)
        # Batch terminal transitions use the same lock.  Do not rely on a stale
        # open status observed before the lock was acquired.
        with self.batches._lifecycle_lock(class_id, work_id):
            batch, _ = self.batches._read(class_id, work_id)
            existing = self._scan(class_id, work_id)
            for page in existing:
                if page.logical_id == page_id:
                    if (
                        isinstance(page, PageTargetV2)
                        and page.to_dict() == target.to_dict()
                    ):
                        return page  # Exact retry (including after close).
                    raise PortiaConflictError(
                        "Page Target identity already has different historical state"
                    )
                if (
                    page.logical_id is not None
                    and page.logical_id.casefold() == page_id.casefold()
                ):
                    raise PortiaConflictError("Page Target ID case collision")
            if batch.status != "open":
                raise PortiaConflictError(
                    "new Page Target requires an open Capture Batch"
                )
            requested_index = target.field("page_index")
            if any(page.field("page_index") == requested_index for page in existing):
                raise PortiaConflictError("Page Target page index already allocated")
            path = self._path(class_id, work_id, page_id)
            # Exclusively persist the exact immutable semantic representation.
            exclusive_create(path, canonical_json_bytes(target.to_dict()))
            saved = self._load_exact(class_id, work_id, page_id)
            if (
                not isinstance(saved, PageTargetV2)
                or saved.to_dict() != target.to_dict()
            ):
                raise PortiaCorruptionError("Page Target write/readback disagreement")
            return saved

    def load(
        self,
        class_id: str,
        work_id: str,
        page_target_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> PageTargetV1 | PageTargetV2:
        self.batches._authorize(class_id, "page_target.load", authorization)
        self.batches._read(class_id, work_id)
        return self._load_exact(class_id, work_id, _page_id(page_target_id))

    def list_targets(
        self, class_id: str, work_id: str, *, authorization: CaptureAuthorization
    ) -> tuple[PageTargetV1 | PageTargetV2, ...]:
        self.batches._authorize(class_id, "page_target.list", authorization)
        self.batches._read(class_id, work_id)
        return self._scan(class_id, work_id)
