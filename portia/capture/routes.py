"""Core-owned PDS2 routing for durable Portia Capture Page Targets.

Only Core writes/loads route registrations.  This service never exposes a QR
payload until the exact Page Target and Core registration have been reloaded
and checked against each other and the original template representation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pds_core.pds2 import Pds2PayloadError, serialize_pds2_payload
from pds_core.route_ids import generate_route_id
from pds_core.route_registrations import (
    RouteRegistrationReadError,
    RouteRegistrationWriteError,
    load_route_registration,
    write_route_registration,
)
from pds_core.routes import route_registration_path, safe_module_work_descendant
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ROUTE_REGISTRATION_SCHEMA_VERSION,
    JsonValue,
    ModuleRecordRef,
    RouteLocator,
    RouteRegistration,
    RoutingModelError,
)

from portia.capture.batches import FileCaptureBatchService
from portia.capture.contracts import (
    CaptureAuthorization,
    CapturePreparationError,
    PagePreparationResult,
    route_binding_findings,
)
from portia.capture.page_targets import FilePageTargetService
from portia.models import PageTargetV2
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError

_ROUTE_ATTEMPTS = 8
_HUMAN_FALLBACK = "Portia capture page"


class FilePageRouteService:
    """Authorize, register, reload, and verify exact current Page Target routes.

    The ``register_or_load`` operation coordinates with Batch transitions and
    Page Target creation through their existing exclusive lifecycle lock.
    An ambiguous or corrupted route namespace fails closed and is never erased.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        batch_service: FileCaptureBatchService | None = None,
        page_service: FilePageTargetService | None = None,
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

    def _collection(self, class_id: str, work_id: str) -> Path:
        return self.batches._safe(
            safe_module_work_descendant(
                self.root,
                self.batches._work(class_id, work_id),
                "routes",
            )
        )

    def _registrations(
        self, class_id: str, work_id: str
    ) -> tuple[RouteRegistration, ...]:
        """Strictly inspect all durable Core routes for this operational work."""
        collection = self._collection(class_id, work_id)
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError("Core route collection is not a directory")
        registrations: list[RouteRegistration] = []
        work = self.batches._work(class_id, work_id)
        names: set[str] = set()
        for path in sorted(collection.iterdir(), key=lambda child: child.name):
            self.batches._safe(path)
            if not path.is_file() or path.suffix != ".json":
                raise PortiaCorruptionError("unexpected file in Core route collection")
            if path.stem.casefold() in names:
                raise PortiaCorruptionError("casefold Core route-ID collision")
            names.add(path.stem.casefold())
            try:
                locator = RouteLocator(PDS2_SCHEMA, work, path.stem)
                expected_path = route_registration_path(self.root, locator)
                if expected_path != path:
                    raise PortiaCorruptionError("route filename is not canonical")
                registration = load_route_registration(self.root, locator)
            except (RoutingModelError, RouteRegistrationReadError) as exc:
                raise PortiaCorruptionError("invalid persisted Core route") from exc
            registrations.append(registration)
        return tuple(registrations)

    @staticmethod
    def _result(
        target: PageTargetV2, status: str, *diagnostics: str
    ) -> PagePreparationResult:
        # The only success route is through the verified constructor below.
        if status == "retryable":
            return PagePreparationResult("retryable", target, diagnostics=diagnostics)
        if status == "conflict":
            return PagePreparationResult("conflict", target, diagnostics=diagnostics)
        return PagePreparationResult("rejected", target, diagnostics=diagnostics)

    def _inspect_exact(self, target: PageTargetV2) -> PagePreparationResult:
        """Read only; no recovered/guessed locator and no Core writes."""
        class_id, work_id, page_id = target.class_id, target.work_id, target.logical_id
        if class_id is None or work_id is None or page_id is None:
            raise CapturePreparationError("Page Target has no owner")
        batch, _ = self.batches._read(class_id, work_id)
        actual = self.pages._load_exact(class_id, work_id, page_id)
        if not isinstance(actual, PageTargetV2) or actual.to_dict() != target.to_dict():
            return self._result(target, "conflict", "page_target_changed")
        if actual.status != "active":
            return self._result(target, "rejected", "page_target_inactive")
        if batch.status == "cancelled":
            return self._result(target, "rejected", "batch_cancelled")
        try:
            registrations = self._registrations(class_id, work_id)
        except PortiaCorruptionError:
            return self._result(target, "conflict", "route_collection_corrupt")
        matches = [
            item for item in registrations if item.target.record_id == page_id
        ]
        if len(matches) > 1:
            return self._result(target, "conflict", "ambiguous_target_routes")
        if not matches:
            if batch.status != "open":
                return self._result(target, "rejected", "batch_not_open")
            return self._result(target, "retryable", "route_not_registered")
        registration = matches[0]
        if route_binding_findings(actual, registration):
            return self._result(target, "conflict", "registration_target_mismatch")
        details = registration.module_details
        if (
            details.get("page_target_contract_version") != "2"
            or details.get("template_identity") != actual.to_dict()["template_identity"]
        ):
            return self._result(target, "conflict", "template_identity_mismatch")
        try:
            payload = serialize_pds2_payload(registration.locator)
            # PagePreparationResult also re-parses and tests canonical exactness.
            return PagePreparationResult(
                "verified", actual, registration.locator, payload, registration
            )
        except (Pds2PayloadError, RoutingModelError, CapturePreparationError):
            return self._result(target, "conflict", "pds2_verification_failed")

    def inspect(
        self,
        class_id: str,
        work_id: str,
        page_target_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> PagePreparationResult:
        """Report exact current durable readiness without creating files."""
        self.batches._authorize(class_id, "page_route.inspect", authorization)
        self.batches._read(class_id, work_id)
        page = self.pages._load_exact(class_id, work_id, page_target_id)
        if not isinstance(page, PageTargetV2):
            raise CapturePreparationError("current Page Target v2 required")
        return self._inspect_exact(page)

    def register_or_load(
        self,
        target: PageTargetV2,
        *,
        authorization: CaptureAuthorization,
    ) -> PagePreparationResult:
        """Exclusively persist a single new route or verify an existing route.

        Caller must first persist the target via ``FilePageTargetService``.
        All successes are verified by Core reload before exposing a PDS2 payload.
        """
        if not isinstance(target, PageTargetV2):
            raise CapturePreparationError("route registration requires Page Target v2")
        class_id, work_id, page_id = target.class_id, target.work_id, target.logical_id
        if class_id is None or work_id is None or page_id is None:
            raise CapturePreparationError("Page Target lacks owner")
        self.batches._authorize(class_id, "page_route.register", authorization)
        self.batches._read(class_id, work_id)
        # Reject missing target without creating an orphan lock.
        self.pages._load_exact(class_id, work_id, page_id)
        with self.batches._lifecycle_lock(class_id, work_id):
            state = self._inspect_exact(target)
            if state.status != "retryable":
                return state
            # A route may only be created for an exact persisted active target
            # while its own Capture Batch remains open (checked above).
            work = self.batches._work(class_id, work_id)
            details: dict[str, JsonValue] = {
                "page_target_contract_version": "2",
                "template_identity": target.to_dict()["template_identity"],
            }
            for _ in range(_ROUTE_ATTEMPTS):
                locator = RouteLocator(PDS2_SCHEMA, work, generate_route_id())
                destination = self.batches._safe(
                    route_registration_path(self.root, locator)
                )
                # Pure route-ID collision: choose another ID. Do not overwrite.
                if destination.exists():
                    continue
                registration = RouteRegistration(
                    schema_version=ROUTE_REGISTRATION_SCHEMA_VERSION,
                    locator=locator,
                    target=ModuleRecordRef(
                        "portia", "capture_page_target", page_id, "2"
                    ),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    status="active",
                    human_fallback=_HUMAN_FALLBACK,
                    module_details=details,
                )
                # Core owns registration persistence. Its implementation may
                # create the parent directory, so recheck after the prior
                # guarded path calculation; never persist a link-alias route.
                self.batches._safe(destination.parent)
                self.batches._safe(destination)
                try:
                    write_route_registration(self.root, registration)
                except RouteRegistrationWriteError:
                    # A partial Core write is durable evidence; do not erase
                    # or claim verification. Recovery inspects exact state.
                    return self._result(target, "retryable", "route_write_incomplete")
                # Recheck observed path components before Core's reloader.
                # No viewer/temporary alias ever becomes a persisted identity.
                self.batches._safe(destination)
                # Must reload both persisted target and Core route (never trust
                # only the fresh in-memory registration constructor).
                return self._inspect_exact(target)
            raise PortiaConflictError("exhausted bounded Core route-ID allocation")
