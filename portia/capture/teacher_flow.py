"""Teacher-local capture generation with exact catalog, preparation and preview.

Class access is supplied by a trusted authorization adapter. A remembered menu
operator label is NEVER class authorization or institutional authentication.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from portia.capture.contracts import (
    CaptureAuthorization,
    CapturePreparationRequest,
    CapturePreparationResult,
)
from portia.capture.core_form_layout import plan_core_capture_form
from portia.capture.form_catalog import (
    CapturePageSpec,
)
from portia.capture.managed_pdf import (
    FileCapturePdfArtifactService,
    ManagedCapturePdf,
)
from portia.capture.observation_layout import (
    MAX_CONTINUATION_PAGES,
    plan_daily_classroom_observation,
)
from portia.capture.preparation import FileCapturePreparationService
from portia.models import CaptureBatchV1, ExactPortiaWorkRef, PageTargetV2


class TeacherCaptureFlowError(ValueError):
    """An interactive capture generation request is invalid or unsupported."""


def _open_verified_local_path(path: Path) -> Path:
    """Load Core's viewer helper on demand to preserve older Core imports."""
    try:
        from pds_core.local_open import LocalOpenError, open_local_path
    except ImportError as exc:
        raise TeacherCaptureFlowError(
            "PDF preview requires a compatible Core local-opening capability"
        ) from exc
    try:
        return open_local_path(path)
    except LocalOpenError as exc:
        raise TeacherCaptureFlowError("PDF preview handoff was not accepted") from exc


@dataclass(frozen=True, slots=True)
class TeacherCaptureRequest:
    """Source-free form selection; generation does not capture student facts."""

    class_id: str
    form_id: str
    continuation_pages: int = 0
    existing_work: ExactPortiaWorkRef | None = None


@dataclass(frozen=True, slots=True)
class TeacherCapturePlan:
    request: TeacherCaptureRequest
    batch: CaptureBatchV1
    targets: tuple[PageTargetV2, ...]


@dataclass(frozen=True, slots=True)
class TeacherCaptureResult:
    """A teacher-facing state; never asserts physical printing or viewing."""

    status: Literal["pdf_ready", "needs_attention"]
    batch_id: str
    pdf: ManagedCapturePdf | None
    diagnostics: tuple[str, ...]


def _planned_specs(request: TeacherCaptureRequest) -> tuple[CapturePageSpec, ...]:
    if type(request.continuation_pages) is not int:
        raise TeacherCaptureFlowError("continuation page count must be an integer")
    if request.form_id == "daily_classroom_observation":
        if not 0 <= request.continuation_pages <= MAX_CONTINUATION_PAGES:
            raise TeacherCaptureFlowError("daily form supports 0–8 continuations")
        packet = plan_daily_classroom_observation(
            continuation_pages=request.continuation_pages
        )
        specs = tuple(page.spec for page in packet.pages)
    else:
        if request.continuation_pages != 0:
            raise TeacherCaptureFlowError("this form does not support continuations")
        drawing = plan_core_capture_form(request.form_id)
        specs = (drawing.spec,)
    required = {
        "event_evidence_capture": "event",
        "support_process_evidence_capture": "support_process",
    }
    prohibited = {
        "classroom_observation_capture",
        "new_event_capture",
        "multi_entry_event_capture",
    }
    for spec in specs:
        expected = required.get(spec.page_purpose)
        if expected is not None and (
            request.existing_work is None or request.existing_work.work_kind != expected
        ):
            raise TeacherCaptureFlowError(
                f"{request.form_id} requires an exact existing {expected}"
            )
        if spec.page_purpose in prohibited and request.existing_work is not None:
            raise TeacherCaptureFlowError(
                "new/observation forms cannot bind existing work"
            )
    if request.existing_work is not None and (
        request.existing_work.class_id != request.class_id
    ):
        raise TeacherCaptureFlowError("selected work belongs to a different class")
    return specs


class TeacherCaptureService:
    """Typed generate/reuse/recover/open workflow over qualified #57/#58 layers."""

    def __init__(
        self,
        root: str | Path,
        *,
        authorization: CaptureAuthorization,
        preparation: FileCapturePreparationService | None = None,
    ) -> None:
        self.preparation = preparation or FileCapturePreparationService(root)
        if self.preparation.root != Path(root).absolute():
            raise TeacherCaptureFlowError("preparation workspace differs")
        self.authorization = authorization
        self.artifacts = FileCapturePdfArtifactService(self.preparation)

    def plan(
        self,
        request: TeacherCaptureRequest,
        *,
        batch_id: str,
        page_ids: tuple[str, ...],
        timestamp: str,
    ) -> TeacherCapturePlan:
        """Pure validated plan; requires trusted attribution but writes no files."""
        if not isinstance(request, TeacherCaptureRequest):
            raise TeacherCaptureFlowError("TeacherCaptureRequest required")
        self.authorization.require_access(request.class_id, "capture_form.plan")
        specs = _planned_specs(request)
        if len(specs) != len(page_ids) or len(set(page_ids)) != len(page_ids):
            raise TeacherCaptureFlowError("each physical page requires its own ID")
        actor_raw = self.authorization.attribution()
        if not isinstance(actor_raw, Mapping) or not actor_raw:
            raise TeacherCaptureFlowError("trusted attribution required")
        actor = dict(actor_raw)
        batch = CaptureBatchV1(
            {
                "schema_version": "1",
                "record_type": "portia_work",
                "work_kind": "capture_batch",
                "module_id": "portia",
                "class_id": request.class_id,
                "work_id": batch_id,
                "status": "open",
                "created_at": timestamp,
                "created_by": actor,
                "updated_at": timestamp,
                "updated_by": actor,
            }
        )
        targets: list[PageTargetV2] = []
        for n, (spec, page_id) in enumerate(zip(specs, page_ids, strict=True), 1):
            raw: dict[str, object] = {
                "schema_version": "2",
                "record_type": "capture_page_target",
                "module_id": "portia",
                "class_id": request.class_id,
                "work_id": batch_id,
                "page_target_id": page_id,
                "page_index": n,
                "page_purpose": spec.page_purpose,
                "template_identity": spec.template_identity(),
                "capture_mode": spec.capture_mode,
                "entry_layout": spec.entry_layout(),
                "status": "active",
                "created_at": timestamp,
                "created_by": actor,
                "updated_at": timestamp,
                "updated_by": actor,
            }
            if request.existing_work is not None:
                raw["existing_work_context"] = request.existing_work.to_dict()
            target = PageTargetV2(raw)
            spec.assert_page_target_exact(target)
            targets.append(target)
        return TeacherCapturePlan(request, batch, tuple(targets))

    def generate(self, plan: TeacherCapturePlan) -> TeacherCaptureResult:
        """Prepare exact routes first; never publish an incomplete packet."""
        self.authorization.require_access(
            plan.request.class_id, "capture_form.generate"
        )
        prepared = self.preparation.prepare(
            CapturePreparationRequest(plan.batch, plan.targets),
            authorization=self.authorization,
        )
        if not prepared.ready_for_rendering:
            messages = tuple(
                ", ".join(page.diagnostics) or page.status
                for page in prepared.pages
                if page.status != "verified"
            )
            return TeacherCaptureResult(
                "needs_attention", plan.batch.work_id or "", None, messages
            )
        batch_id = plan.batch.work_id
        if batch_id is None:
            raise TeacherCaptureFlowError("prepared batch has no ID")
        pdf = self.artifacts.generate(
            plan.request.class_id, batch_id, authorization=self.authorization
        )
        return TeacherCaptureResult("pdf_ready", batch_id, pdf, ())

    def reprint(self, class_id: str, batch_id: str) -> ManagedCapturePdf:
        """Exact byte-identical reuse; never a new layout under an old route."""
        return self.artifacts.generate(
            class_id, batch_id, authorization=self.authorization
        )

    def recover_routes(self, class_id: str, batch_id: str) -> CapturePreparationResult:
        """Explicit route recovery, not automatic repair or new page creation."""
        return self.preparation.recover(
            class_id, batch_id, authorization=self.authorization
        )

    def recover_pdf(self, class_id: str, batch_id: str) -> ManagedCapturePdf:
        return self.artifacts.recover(
            class_id, batch_id, authorization=self.authorization
        )

    def preview(self, class_id: str, batch_id: str) -> Path:
        """Read-only verify then request Core viewer handoff; not proof displayed."""
        self.authorization.require_access(class_id, "capture_form.preview")
        pdf = self.artifacts.inspect(
            class_id, batch_id, authorization=self.authorization
        )
        self.preparation.batches._safe(pdf.pdf_path)
        # Core may use a temporary viewer alias; its return is canonical only.
        return _open_verified_local_path(pdf.pdf_path)
