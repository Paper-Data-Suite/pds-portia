"""Issue #57 Capture Batch persistence on Core's canonical Portia work paths.

Capture Batches are operational work roots, never Event/Support Process records.
The file service requires a trusted class-access/attribution provider, uses
exclusive create, and retains exact pre-transition bytes before guarded replace.
It writes no Page Targets or Core routes (those belong to later slices).
"""

from __future__ import annotations

import json
import re
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from pds_core.class_metadata import (
    ClassMetadataError,
    load_class_metadata_for_class,
)
from pds_core.routes import (
    class_metadata_path,
    module_work_collection_dir,
    safe_module_work_descendant,
)
from pds_core.routing_models import ModuleWorkRef

from portia.capture.contracts import (
    CaptureAuthorization,
    CaptureBatchTransition,
    CapturePreparationError,
)
from portia.models import CaptureBatchV1
from portia.models.errors import PortiaModelError
from portia.models.identifiers import validate_external_id
from portia.models.json_values import JsonValue, freeze_json_mapping, thaw_json_mapping
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.generated_paths import build_work_storage_revision_leaf
from portia.storage.io import exclusive_create, guarded_replace, read_bytes

_BATCH_ID = re.compile(r"cbat_[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_LOCK_NAME = ".capture-batch-lifecycle.lock"


def _batch_id(value: str) -> str:
    validate_external_id(value, "capture_batch.work_id")
    if _BATCH_ID.fullmatch(value) is None:
        raise CapturePreparationError("Capture Batch requires a cbat_ work_id")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key in persisted Capture Batch")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid non-JSON numeric constant: {value}")


def _parse_batch(content: bytes, path: Path) -> CaptureBatchV1:
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
        return CaptureBatchV1.from_dict(value)  # type: ignore[return-value]
    except (ValueError, UnicodeError, PortiaModelError, TypeError) as exc:
        raise PortiaCorruptionError(
            f"Capture Batch manifest is invalid or contradictory: {path}"
        ) from exc


def _is_link_like(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise PortiaPathError(f"cannot inspect capture path: {path}") from exc
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


class FileCaptureBatchService:
    """Authorized v1 batch create/load/list/terminal lifecycle operations.

    This service shares Core's operational work-root topology, but does not use
    the canonical Event/Support Process repository or broaden domain work refs.
    An interrupted lock must be explicitly inspected; it is never age-expired.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root).absolute()

    def _safe(self, destination: Path) -> Path:
        """Reject observed symlinks/junctions in the managed workspace path.

        A separate recovery/security slice will harden races against an
        adversary who can replace a directory *between* preflight and IO.
        """
        try:
            components = destination.relative_to(self.root).parts
        except ValueError as exc:
            raise PortiaPathError("Capture Batch path escapes workspace") from exc
        nodes = (self.root,) + tuple(
            self.root.joinpath(*components[:index])
            for index in range(1, len(components) + 1)
        )
        for current in nodes:
            if _is_link_like(current):
                raise PortiaPathError(f"link-like Capture Batch path denied: {current}")
            if current.exists() and current != destination and not current.is_dir():
                raise PortiaPathError(f"non-directory Capture Batch ancestor: {current}")
        return destination

    def _authorize(
        self, class_id: str, operation: str, authorization: CaptureAuthorization
    ) -> None:
        validate_external_id(class_id, "class_id")
        authorization.require_access(class_id, operation)
        metadata_path = self._safe(class_metadata_path(self.root, class_id))
        if not metadata_path.is_file():
            raise CapturePreparationError("Core class metadata is required")
        try:
            metadata = load_class_metadata_for_class(self.root, class_id)
        except ClassMetadataError as exc:
            raise CapturePreparationError("Core class metadata is invalid") from exc
        if metadata.class_id != class_id:
            raise CapturePreparationError("Core class metadata does not match class")

    def _work(self, class_id: str, work_id: str) -> ModuleWorkRef:
        validate_external_id(class_id, "class_id")
        return ModuleWorkRef("portia", class_id, _batch_id(work_id))

    def _manifest(self, class_id: str, work_id: str) -> Path:
        return self._safe(
            safe_module_work_descendant(
                self.root, self._work(class_id, work_id), "work.json"
            )
        )

    def _read(self, class_id: str, work_id: str) -> tuple[CaptureBatchV1, bytes]:
        path = self._manifest(class_id, work_id)
        content = read_bytes(path)
        batch = _parse_batch(content, path)
        if (
            batch.class_id != class_id
            or batch.work_id != work_id
            or batch.work_kind != "capture_batch"
            or batch.module_id != "portia"
        ):
            raise PortiaCorruptionError("Capture Batch manifest/path identity mismatch")
        return batch, content

    def _actor(self, authorization: CaptureAuthorization) -> dict[str, JsonValue]:
        value = authorization.attribution()
        if not isinstance(value, Mapping) or not value:
            raise CapturePreparationError("trusted actor attribution is required")
        if any(not isinstance(key, str) for key in value):
            raise CapturePreparationError("invalid trusted actor attribution")
        try:
            return thaw_json_mapping(freeze_json_mapping(value))
        except PortiaModelError as exc:
            raise CapturePreparationError("invalid trusted actor attribution") from exc

    def create_or_load(
        self, batch: CaptureBatchV1, *, authorization: CaptureAuthorization
    ) -> CaptureBatchV1:
        if not isinstance(batch, CaptureBatchV1):
            raise CapturePreparationError("Capture Batch v1 is required")
        class_id = batch.class_id
        work_id = batch.work_id
        if class_id is None or work_id is None:
            raise CapturePreparationError("Capture Batch lacks exact owner")
        self._authorize(class_id, "capture_batch.create", authorization)
        if batch.status != "open":
            raise CapturePreparationError("new Capture Batch must be open")
        actor = self._actor(authorization)
        if batch.to_dict().get("created_by") != actor or batch.to_dict().get("updated_by") != actor:
            raise CapturePreparationError("creation attribution must match trusted actor")
        path = self._manifest(class_id, work_id)
        if path.exists():
            saved, _ = self._read(class_id, work_id)
            if saved.to_dict() != batch.to_dict():
                raise PortiaConflictError("Capture Batch identity already has different state")
            return saved
        if path.parent.exists():
            # Do not adopt an orphaned route/record directory as a new batch.
            if any(path.parent.iterdir()):
                if path.exists():  # A concurrent identical create may just have won.
                    saved, _ = self._read(class_id, work_id)
                    if saved.to_dict() != batch.to_dict():
                        raise PortiaConflictError(
                            "Capture Batch identity already has different state"
                        )
                    return saved
                raise PortiaRecoveryRequiredError(
                    "Capture Batch work root exists without a manifest"
                )
        self._safe(path)
        try:
            exclusive_create(path, canonical_json_bytes(batch.to_dict()))
        except PortiaConflictError:
            # A concurrent identical exclusive creation is an ordinary retry.
            saved, _ = self._read(class_id, work_id)
            if saved.to_dict() != batch.to_dict():
                raise
            return saved
        saved, _ = self._read(class_id, work_id)
        if saved.to_dict() != batch.to_dict():
            raise PortiaCorruptionError("Capture Batch create readback mismatch")
        return saved

    def load(
        self, class_id: str, work_id: str, *, authorization: CaptureAuthorization
    ) -> CaptureBatchV1:
        self._authorize(class_id, "capture_batch.load", authorization)
        return self._read(class_id, work_id)[0]

    def list_batches(
        self, class_id: str, *, authorization: CaptureAuthorization
    ) -> tuple[CaptureBatchV1, ...]:
        self._authorize(class_id, "capture_batch.list", authorization)
        collection = self._safe(module_work_collection_dir(self.root, class_id, "portia"))
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError("Portia work collection is not a directory")
        result: list[CaptureBatchV1] = []
        for child in sorted(collection.iterdir(), key=lambda value: value.name):
            if not child.name.startswith("cbat_"):
                continue  # Event and Support Process roots remain separate.
            self._safe(child)
            _batch_id(child.name)
            if not child.is_dir():
                raise PortiaCorruptionError("Capture Batch work root is not a directory")
            batch, _ = self._read(class_id, child.name)
            result.append(batch)
        return tuple(result)

    @contextmanager
    def _lifecycle_lock(self, class_id: str, work_id: str) -> Iterator[None]:
        path = self._safe(
            safe_module_work_descendant(
                self.root, self._work(class_id, work_id), _LOCK_NAME
            )
        )
        content = canonical_json_bytes(
            {"operation": "capture_batch.transition", "class_id": class_id, "work_id": work_id}
        )
        try:
            exclusive_create(path, content)
        except PortiaConflictError as exc:
            raise PortiaRecoveryRequiredError(
                "Capture Batch lifecycle lock exists; explicit recovery is required"
            ) from exc
        try:
            yield
        finally:
            if self._safe(path).is_file() and read_bytes(path) == content:
                try:
                    path.unlink()
                except OSError as exc:
                    raise PortiaRecoveryRequiredError(
                        "Capture Batch lock could not be released"
                    ) from exc
            else:
                raise PortiaRecoveryRequiredError(
                    "Capture Batch lock changed or disappeared; manual recovery required"
                )

    def _preserve_prior(
        self, class_id: str, work_id: str, content: bytes
    ) -> None:
        digest = fingerprint_bytes(content).digest
        leaf = build_work_storage_revision_leaf("capture_batch", work_id, digest)
        history_path = self._safe(
            safe_module_work_descendant(
                self.root,
                self._work(class_id, work_id),
                f"history/storage_revisions/{leaf}",
            )
        )
        try:
            exclusive_create(history_path, content)
        except PortiaConflictError:
            if read_bytes(self._safe(history_path)) != content:
                raise PortiaCorruptionError("Capture Batch history identity collision")

    def transition(
        self,
        class_id: str,
        work_id: str,
        to_status: CaptureBatchTransition,
        *,
        authorization: CaptureAuthorization,
    ) -> CaptureBatchV1:
        self._authorize(class_id, "capture_batch.transition", authorization)
        if to_status not in {"closed", "cancelled"}:
            raise CapturePreparationError("Capture Batch supports only terminal transitions")
        actor = self._actor(authorization)
        self._read(class_id, work_id)  # Missing work must not create orphan lock state.
        with self._lifecycle_lock(class_id, work_id):
            old, old_bytes = self._read(class_id, work_id)
            if old.status == to_status:
                return old
            if old.status != "open":
                raise PortiaConflictError("a terminal Capture Batch cannot transition again")
            now = datetime.now(timezone.utc)
            old_updated = old.to_dict()["updated_at"]
            if not isinstance(old_updated, str):
                raise PortiaCorruptionError("Capture Batch timestamp missing")
            if now <= datetime.fromisoformat(old_updated):
                raise PortiaConflictError("clock has not advanced beyond batch history")
            successor_data = old.to_dict()
            successor_data.update(
                status=to_status, updated_at=now.isoformat(), updated_by=actor
            )
            successor = CaptureBatchV1(cast(Mapping[str, object], successor_data))
            self._preserve_prior(class_id, work_id, old_bytes)
            path = self._manifest(class_id, work_id)
            guarded_replace(
                path, canonical_json_bytes(successor.to_dict()),
                expected=fingerprint_bytes(old_bytes),
            )
            saved, _ = self._read(class_id, work_id)
            if saved.to_dict() != successor.to_dict():
                raise PortiaCorruptionError("Capture Batch transition readback mismatch")
            return saved
