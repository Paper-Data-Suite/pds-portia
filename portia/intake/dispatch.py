"""#59 Slice 4: authorized read-only Core dispatch of retained PDS2 pages.

Only the Core ModuleRegistry/dispatch_route may resolve a QR candidate. The
Portia route handler checks the *durable* target and frozen template snapshot.
No Page Record or behavior-domain record is created by this service.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pds_core.module_dispatch import (
    ModuleContractCompatibilityError,
    ModuleDispatchError,
    ModuleRegistrationValidationError,
    ModuleRouteHandlingError,
    RouteDispatchRequest,
    RouteStatusNotDispatchableError,
    dispatch_route,
)
from pds_core.module_profiles import (
    CORE_ROUTING_CONTRACT_VERSION,
    ModuleProfile,
    ModuleRegistry,
)
from pds_core.route_registrations import (
    RouteRegistrationIntegrityError,
    RouteRegistrationNotFoundError,
    RouteRegistrationPersistenceError,
)
from pds_core.routes import route_registration_path
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ROUTE_REGISTRATION_SCHEMA_VERSION,
    RouteLocator,
    RouteResolution,
    RoutingModelError,
)
from pds_core.scan_retention import RetainedSourceScan

from portia.capture.batches import FileCaptureBatchService
from portia.capture.contracts import CaptureAuthorization, route_binding_findings
from portia.capture.page_targets import FilePageTargetService
from portia.intake.contracts import (
    DEFAULT_SOURCE_LIMITS,
    RetainedPageIdentity,
    SourceSafetyLimits,
)
from portia.intake.recognition import PageQrDiscovery, SourceQrDiscovery
from portia.intake.retention import _assert_retained_under_root, _hash_file
from portia.models import PageTargetV1, PageTargetV2
from portia.storage.errors import PortiaNotFoundError, PortiaStorageError

PageRouteStatus = Literal[
    "verified",
    "missing_qr",
    "unreadable_qr",
    "ambiguous_qr",
    "invalid_qr",
    "foreign_module",
    "render_failed",
    "authorization_denied",
    "batch_unavailable",
    "batch_cancelled",
    "route_unavailable",
    "route_inactive",
    "registration_conflict",
    "target_unavailable",
    "target_conflict",
    "route_error",
]

_QR_FAILURES = frozenset(
    {
        "missing_qr",
        "unreadable_qr",
        "ambiguous_qr",
        "invalid_qr",
        "foreign_module",
        "render_failed",
    }
)


class PageRouteVerificationError(RuntimeError):
    """Portia exact-target verification failed inside the Core handler."""

    def __init__(self, code: Literal["target_unavailable", "target_conflict"]) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class VerifiedPageRoute:
    """Authorized, resolved Core route plus exact persisted Portia target."""

    locator: RouteLocator
    target: PageTargetV1 | PageTargetV2
    resolution: RouteResolution

    def __post_init__(self) -> None:
        if (
            not isinstance(self.locator, RouteLocator)
            or not isinstance(self.target, (PageTargetV1, PageTargetV2))
            or not isinstance(self.resolution, RouteResolution)
            or self.resolution.locator != self.locator
        ):
            raise ValueError("verified route must preserve Core resolution and target")


@dataclass(frozen=True, slots=True)
class PageRouteOutcome:
    """One physical source page's *read-only* route-dispatch result."""

    identity: RetainedPageIdentity
    status: PageRouteStatus
    verified: VerifiedPageRoute | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RetainedPageIdentity):
            raise ValueError("route outcome requires a retained physical-page identity")
        if self.status == "verified":
            if not isinstance(self.verified, VerifiedPageRoute):
                raise ValueError("verified outcome requires exact Core/Portia evidence")
        elif self.verified is not None:
            raise ValueError("unverified page must not expose a route or target")


@dataclass(frozen=True, slots=True)
class SourceRouteOutcomes:
    """Original page order is preserved even with errors and mixed QR statuses."""

    discovery: SourceQrDiscovery
    pages: tuple[PageRouteOutcome, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.discovery, SourceQrDiscovery):
            raise ValueError("route results require one retained-source discovery")
        if len(self.pages) != len(self.discovery.pages):
            raise ValueError("route outcome count does not match retained source")
        for discovered, outcome in zip(self.discovery.pages, self.pages):
            if discovered.identity != outcome.identity:
                raise ValueError("route outcome changed physical source-page identity")

    @property
    def verified_count(self) -> int:
        return sum(page.status == "verified" for page in self.pages)


class FilePageRouteDispatchService:
    """Read-only Portia adapter to Core's standard one-page module dispatcher.

    A trusted CaptureAuthorization is mandatory. Authorization precedes all
    class-specific Core route or Portia record reads, and each candidate gets
    an isolated Core module registry. No installed global profile is replaced.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        limits: SourceSafetyLimits = DEFAULT_SOURCE_LIMITS,
    ) -> None:
        if not isinstance(limits, SourceSafetyLimits):
            raise TypeError("limits must be SourceSafetyLimits")
        self.root = Path(workspace_root).absolute()
        self.limits = limits
        self.batches = FileCaptureBatchService(self.root)
        self.targets = FilePageTargetService(self.root, batch_service=self.batches)

    def verify(
        self,
        discovery: SourceQrDiscovery,
        *,
        authorization: CaptureAuthorization,
    ) -> SourceRouteOutcomes:
        """Resolve each candidate; never write, invent a route, or infer a fact."""
        if not isinstance(discovery, SourceQrDiscovery):
            raise TypeError("verification requires a SourceQrDiscovery")
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("trusted CaptureAuthorization is required")
        source = discovery.source
        if (
            source.page_count > self.limits.max_pages
            or source.byte_count > self.limits.max_source_bytes
        ):
            raise ValueError("retained scan exceeds routing policy")
        self._verify_custody(source.core_source, source.byte_count)
        results = tuple(
            self._one(page, source.core_source, authorization)
            for page in discovery.pages
        )
        # Previously resolved Page Targets must not be handed out if the Core
        # original changed during dispatch; custody is authoritative.
        self._verify_custody(source.core_source, source.byte_count)
        return SourceRouteOutcomes(discovery, results)

    def _verify_custody(self, retained: RetainedSourceScan, size: int) -> None:
        _assert_retained_under_root(self.root, retained)
        digest, actual_size = _hash_file(
            retained.retained_source_path, self.limits.max_source_bytes
        )
        if digest != retained.source_sha256 or actual_size != size:
            raise ValueError("Core-retained source integrity verification failed")

    def _one(
        self,
        page: PageQrDiscovery,
        retained: RetainedSourceScan,
        authorization: CaptureAuthorization,
    ) -> PageRouteOutcome:
        if page.status != "candidate_unverified":
            assert page.status in _QR_FAILURES
            return PageRouteOutcome(page.identity, page.status)
        locator = page.candidate_locator
        if locator is None or locator.module_id != "portia":
            return PageRouteOutcome(page.identity, "registration_conflict")

        # Class permission is checked *before* any class metadata, route, or
        # Page Target read. The batch reader also checks durable class authority.
        try:
            authorization.require_access(locator.class_id, "capture_intake.route")
        except PermissionError:
            return PageRouteOutcome(page.identity, "authorization_denied")
        try:
            batch = self.batches.load(
                locator.class_id, locator.work_id, authorization=authorization
            )
        except PermissionError:
            return PageRouteOutcome(page.identity, "authorization_denied")
        except (PortiaStorageError, ValueError, RuntimeError, OSError):
            return PageRouteOutcome(page.identity, "batch_unavailable")
        if batch.status == "cancelled":
            return PageRouteOutcome(page.identity, "batch_cancelled")

        # Preflight the Core route path with Portia's existing link/junction
        # guard because older Core versions may not reject reparse ancestors.
        try:
            self.batches._safe(route_registration_path(self.root, locator))
        except (PortiaStorageError, RoutingModelError, OSError, ValueError):
            return PageRouteOutcome(page.identity, "registration_conflict")

        def handler(
            resolution: RouteResolution,
            dispatched_source: RetainedSourceScan,
            source_page_number: int,
        ) -> VerifiedPageRoute:
            if (
                resolution.locator != locator
                or dispatched_source != retained
                or source_page_number != page.identity.source_page_number
            ):
                raise PageRouteVerificationError("target_conflict")
            registration = resolution.registration
            ref = registration.target
            if (
                ref.module_id != "portia"
                or ref.record_kind != "capture_page_target"
                or ref.contract_version not in {"1", "2"}
            ):
                raise PageRouteVerificationError("target_conflict")
            try:
                target = self.targets.load(
                    locator.class_id,
                    locator.work_id,
                    ref.record_id,
                    authorization=authorization,
                )
            except PortiaNotFoundError as exc:
                raise PageRouteVerificationError("target_unavailable") from exc
            except (PortiaStorageError, ValueError, OSError, PermissionError) as exc:
                raise PageRouteVerificationError("target_conflict") from exc
            if route_binding_findings(target, registration):
                raise PageRouteVerificationError("target_conflict")
            details = registration.module_details
            snapshot = target.to_dict().get("template_identity")
            # Route snapshot must match the durable historical template, even
            # after later versions of the installed form catalog are released.
            if (
                details.get("page_target_contract_version") != target.contract_version
                or details.get("template_identity") != snapshot
            ):
                raise PageRouteVerificationError("target_conflict")
            return VerifiedPageRoute(locator, target, resolution)

        profile = ModuleProfile(
            module_id="portia",
            display_name="Portia Paper Intake",
            supported_core_routing_contract_versions=frozenset(
                {CORE_ROUTING_CONTRACT_VERSION}
            ),
            supported_qr_schemas=frozenset({PDS2_SCHEMA}),
            supported_route_registration_schema_versions=frozenset(
                {ROUTE_REGISTRATION_SCHEMA_VERSION}
            ),
            dispatchable_route_statuses=frozenset({"active"}),
            route_handler=handler,
        )
        try:
            successful = dispatch_route(
                self.root,
                ModuleRegistry((profile,)),
                RouteDispatchRequest(
                    locator, retained, page.identity.source_page_number
                ),
            )
        except RouteRegistrationNotFoundError:
            return PageRouteOutcome(page.identity, "route_unavailable")
        except RouteRegistrationIntegrityError:
            return PageRouteOutcome(page.identity, "registration_conflict")
        except RouteRegistrationPersistenceError:
            return PageRouteOutcome(page.identity, "registration_conflict")
        except RouteStatusNotDispatchableError:
            return PageRouteOutcome(page.identity, "route_inactive")
        except ModuleRouteHandlingError as exc:
            reason = exc.__cause__
            if isinstance(reason, PageRouteVerificationError):
                return PageRouteOutcome(page.identity, reason.code)
            return PageRouteOutcome(page.identity, "route_error")
        except (ModuleRegistrationValidationError, ModuleContractCompatibilityError):
            return PageRouteOutcome(page.identity, "registration_conflict")
        except (ModuleDispatchError, RoutingModelError, ValueError, OSError):
            return PageRouteOutcome(page.identity, "route_error")
        if not isinstance(successful.module_result, VerifiedPageRoute):
            return PageRouteOutcome(page.identity, "route_error")
        return PageRouteOutcome(page.identity, "verified", successful.module_result)
