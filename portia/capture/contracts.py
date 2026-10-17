"""Issue #57 preparation boundaries and exact, non-mutating PDS2 checks.

These are service interfaces, NOT persistence or printable-readiness services.
The implementations in later slices must authorize requests and reload durable
Page Target and Core route state before reporting ``verified``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from pds_core.pds2 import Pds2PayloadError, parse_pds2_payload, serialize_pds2_payload
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ROUTE_REGISTRATION_SCHEMA_VERSION,
    RouteLocator,
    RouteRegistration,
    RoutingModelError,
    validate_route_registration,
)

from portia.models import CaptureBatchV1, PageTargetV1, PageTargetV2

PreparationStatus = Literal["verified", "retryable", "conflict", "rejected"]
CaptureBatchTransition = Literal["closed", "cancelled"]


class CapturePreparationError(ValueError):
    """A request violates a pre-print contract; no side effects are authorized."""


@dataclass(frozen=True, slots=True)
class CapturePreparationRequest:
    """Exact current-version pre-print models, not generated domain work.

    The batch is the Core work root. Any existing Event/Support Process context
    remains an independent, explicit field of each Page Target.
    """

    batch: CaptureBatchV1
    targets: tuple[PageTargetV2, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.batch, CaptureBatchV1):
            raise CapturePreparationError("batch must be capture_batch@1")
        if not isinstance(self.targets, tuple) or not self.targets:
            raise CapturePreparationError("at least one Page Target is required")
        if self.batch.status != "open":
            raise CapturePreparationError("Capture Batch must be open for preparation")
        seen_ids: set[str] = set()
        seen_indices: set[int] = set()
        for target in self.targets:
            if not isinstance(target, PageTargetV2):
                raise CapturePreparationError("preparation requires page_target@2")
            if (
                target.class_id != self.batch.class_id
                or target.work_id != self.batch.work_id
            ):
                raise CapturePreparationError(
                    "Page Target class/work must match operational Capture Batch"
                )
            if target.status != "active":
                raise CapturePreparationError("Page Target must be active")
            target_id = target.logical_id
            index = target.field("page_index")
            if not isinstance(target_id, str) or not isinstance(index, int):
                raise CapturePreparationError("Page Target identity/index is missing")
            if target_id in seen_ids or index in seen_indices:
                raise CapturePreparationError(
                    "Page Target IDs and page indices must be unique per request"
                )
            seen_ids.add(target_id)
            seen_indices.add(index)


@dataclass(frozen=True, slots=True)
class PagePreparationResult:
    """One page's explicit state; no route is exposed for incomplete results.

    A service may construct ``verified`` ONLY after reloading the persisted
    target and the exact active Core registration from the workspace.
    Pure consistency checks alone do not prove durability.
    """

    status: PreparationStatus
    target: PageTargetV2
    locator: RouteLocator | None = None
    payload: str | None = None
    registration: RouteRegistration | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"verified", "retryable", "conflict", "rejected"}:
            raise CapturePreparationError("invalid preparation status")
        if not isinstance(self.target, PageTargetV2):
            raise CapturePreparationError("result requires current Page Target v2")
        if not isinstance(self.diagnostics, tuple) or len(self.diagnostics) > 16:
            raise CapturePreparationError("diagnostics must be a bounded tuple")
        if any(
            not isinstance(message, str) or len(message) > 256
            for message in self.diagnostics
        ):
            raise CapturePreparationError("invalid diagnostic entry")
        if self.status != "verified":
            if (
                self.locator is not None
                or self.payload is not None
                or self.registration is not None
            ):
                raise CapturePreparationError(
                    "unverified result must not expose a printable locator/payload"
                )
            return
        if (
            self.locator is None
            or self.payload is None
            or self.registration is None
        ):
            raise CapturePreparationError(
                "verified result needs locator, payload, and registration"
            )
        if self.registration.locator != self.locator:
            raise CapturePreparationError("verified registration/locator mismatch")
        if route_binding_findings(self.target, self.registration):
            raise CapturePreparationError("verified registration/target mismatch")
        try:
            if parse_pds2_payload(self.payload) != self.locator:
                raise CapturePreparationError("verified PDS2 payload/locator mismatch")
            if serialize_pds2_payload(self.locator) != self.payload:
                raise CapturePreparationError("verified PDS2 payload is not canonical")
        except (Pds2PayloadError, RoutingModelError) as exc:
            raise CapturePreparationError("invalid verified PDS2 payload") from exc
        if (
            self.locator.module_id != "portia"
            or self.locator.class_id != self.target.class_id
            or self.locator.work_id != self.target.work_id
        ):
            raise CapturePreparationError("verified locator/target owner mismatch")


@dataclass(frozen=True, slots=True)
class CapturePreparationResult:
    batch: CaptureBatchV1
    pages: tuple[PagePreparationResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.batch, CaptureBatchV1):
            raise CapturePreparationError("result requires Capture Batch v1")
        if not isinstance(self.pages, tuple):
            raise CapturePreparationError("result pages must be a tuple")
        for page in self.pages:
            if (
                page.target.class_id != self.batch.class_id
                or page.target.work_id != self.batch.work_id
            ):
                raise CapturePreparationError("result Page Target has wrong batch")

    @property
    def ready_for_rendering(self) -> bool:
        return self.batch.status == "open" and bool(self.pages) and all(
            page.status == "verified" for page in self.pages
        )


def route_binding_findings(
    target: PageTargetV1 | PageTargetV2,
    registration: RouteRegistration,
) -> tuple[str, ...]:
    """Pure exact-registration audit, applicable to current and historical targets.

    Does NOT establish that the registration or target was reloaded from disk.
    Callers must use Core ``load_route_registration`` and Portia's durable
    Page Target reader before using these findings in a ready-to-render decision.
    """
    if not isinstance(target, (PageTargetV1, PageTargetV2)):
        raise CapturePreparationError("route target must be page_target@1 or @2")
    if not isinstance(registration, RouteRegistration):
        raise CapturePreparationError("registration must be a Core model")
    findings: list[str] = []
    try:
        validate_route_registration(registration)
    except RoutingModelError:
        findings.append("registration_invalid")
        return tuple(findings)
    loc = registration.locator
    ref = registration.target
    if registration.schema_version != ROUTE_REGISTRATION_SCHEMA_VERSION:
        findings.append("registration_version_mismatch")
    if registration.status != "active":
        findings.append("registration_not_active")
    if loc.schema != PDS2_SCHEMA or loc.module_id != "portia":
        findings.append("locator_module_mismatch")
    if loc.class_id != target.class_id or loc.work_id != target.work_id:
        findings.append("locator_owner_mismatch")
    if (
        ref.module_id != "portia"
        or ref.record_kind != "capture_page_target"
        or ref.record_id != target.logical_id
        or ref.contract_version != target.contract_version
    ):
        findings.append("registration_target_mismatch")
    if target.status != "active":
        findings.append("page_target_not_active")
    try:
        payload = serialize_pds2_payload(loc)
        if parse_pds2_payload(payload) != loc:
            findings.append("pds2_roundtrip_mismatch")
    except (Pds2PayloadError, RoutingModelError):
        findings.append("pds2_invalid")
    return tuple(findings)


class CaptureAuthorization(Protocol):
    """Trusted class-access gate; callers must not self-assert authorization."""

    def require_access(self, class_id: str, operation: str) -> None: ...

    def attribution(self) -> Mapping[str, object]:
        """Return the verified actor, never a self-asserted operation identity."""
        ...


class CaptureBatchService(Protocol):
    def create_or_load(
        self, batch: CaptureBatchV1, *, authorization: CaptureAuthorization
    ) -> CaptureBatchV1: ...

    def load(
        self, class_id: str, work_id: str, *, authorization: CaptureAuthorization
    ) -> CaptureBatchV1: ...

    def list_batches(
        self, class_id: str, *, authorization: CaptureAuthorization
    ) -> tuple[CaptureBatchV1, ...]: ...

    def transition(
        self,
        class_id: str,
        work_id: str,
        to_status: CaptureBatchTransition,
        *,
        authorization: CaptureAuthorization,
    ) -> CaptureBatchV1: ...


class PageTargetService(Protocol):
    def list_targets(
        self, class_id: str, work_id: str, *, authorization: CaptureAuthorization
    ) -> tuple[PageTargetV1 | PageTargetV2, ...]: ...

    def create_or_load(
        self, target: PageTargetV2, *, authorization: CaptureAuthorization
    ) -> PageTargetV2: ...

    def load(
        self,
        class_id: str,
        work_id: str,
        page_target_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> PageTargetV1 | PageTargetV2: ...


class CapturePreparationService(Protocol):
    def prepare(
        self,
        request: CapturePreparationRequest,
        *,
        authorization: CaptureAuthorization,
    ) -> CapturePreparationResult: ...

    def inspect(
        self,
        class_id: str,
        work_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> CapturePreparationResult: ...

    def recover(
        self,
        class_id: str,
        work_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> CapturePreparationResult: ...
