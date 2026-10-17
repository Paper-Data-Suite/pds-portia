"""Read-only, verified PDS2 vector-PDF rendering for frozen Portia form pages.

This is a byte-producing service, NOT managed storage or a print claim. Every
physical page requires its own persisted current Page Target and active Core
route, reloaded at entry and rechecked before bytes leave this boundary.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import TypeAlias, cast

import qrcode
from pds_core.pds2 import parse_pds2_payload, serialize_pds2_payload
from qrcode.constants import ERROR_CORRECT_M
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from portia.capture.contracts import (
    CaptureAuthorization,
    CapturePreparationResult,
    PagePreparationResult,
    route_binding_findings,
)
from portia.capture.core_form_layout import (
    CoreFieldDrawing,
    CoreFormDrawing,
    plan_core_capture_form,
)
from portia.capture.form_catalog import (
    CapturePageSpec,
    CaptureRectangle,
    resolve_capture_page_spec,
)
from portia.capture.observation_layout import (
    FieldDrawing,
    ObservationPageDrawing,
    TextRun,
    plan_daily_classroom_observation,
)
from portia.capture.preparation import FileCapturePreparationService
from portia.capture.purposes import (
    resolve_existing_capture_context,
    validate_page_purpose,
)
from portia.capture.recovery import audit_capture_route_inventory
from portia.models import PageTargetV2

PDF_RENDER_VERSION = "portia_pds2_vector_pdf_v1"
MAX_PDF_PAGES = 24
PAGE_WIDTH, PAGE_HEIGHT = 612, 792
MIN_QR_MODULE_POINTS = 1.55


class CapturePdfRenderError(ValueError):
    """PDF output is not authorized, complete, exact, or safely printable."""


@dataclass(frozen=True, slots=True)
class RenderedCapturePage:
    page_index: int
    page_target_id: str
    template_identity: tuple[tuple[str, str | int], ...]
    pds2_payload: str


@dataclass(frozen=True, slots=True)
class RenderedCapturePdf:
    """Transient bytes only; neither a persisted artifact nor a print receipt."""

    pdf_bytes: bytes
    sha256: str
    pages: tuple[RenderedCapturePage, ...]
    renderer_version: str = PDF_RENDER_VERSION

    @property
    def page_count(self) -> int:
        return len(self.pages)


PageDrawing: TypeAlias = ObservationPageDrawing | CoreFormDrawing


def _top_rect(canvas: Canvas, rect: CaptureRectangle, *, fill: int = 0) -> None:
    canvas.rect(
        rect.x,
        PAGE_HEIGHT - rect.y - rect.height,
        rect.width,
        rect.height,
        fill=fill,
        stroke=1,
    )


def _text(canvas: Canvas, run: TextRun) -> None:
    font = "Helvetica-Bold" if run.weight == "bold" else "Helvetica"
    width = stringWidth(run.text, font, run.font_size)
    if width > run.max_width + 0.01:
        raise CapturePdfRenderError("text exceeds historical reserved width")
    if not 0 <= run.x < PAGE_WIDTH or not 0 <= run.baseline_y <= PAGE_HEIGHT:
        raise CapturePdfRenderError("text baseline outside page")
    canvas.setFont(font, run.font_size)
    canvas.setFillColorRGB(0.13, 0.20, 0.29)
    canvas.drawString(run.x, PAGE_HEIGHT - run.baseline_y, run.text)


def _field(canvas: Canvas, field: FieldDrawing | CoreFieldDrawing) -> None:
    # Both frozen drawing models intentionally use these identical primitives.
    rect = field.rectangle
    canvas.setStrokeColorRGB(0.72, 0.75, 0.79)
    canvas.setLineWidth(0.48)
    _top_rect(canvas, rect)
    _text(canvas, field.label)
    canvas.setStrokeColorRGB(0.63, 0.67, 0.72)
    canvas.setLineWidth(0.35)
    for rule in field.writing_rules:
        canvas.line(
            rule.x_start,
            PAGE_HEIGHT - rule.y,
            rule.x_end,
            PAGE_HEIGHT - rule.y,
        )
    for mark in field.mark_options:
        canvas.setStrokeColorRGB(0.22, 0.28, 0.34)
        canvas.setLineWidth(0.65)
        _top_rect(canvas, mark.checkbox)
        _text(canvas, mark.label)


def _vector_qr(canvas: Canvas, box: CaptureRectangle, payload: str) -> None:
    """Paint only PDF vector rectangles, including a real blank quiet zone."""
    if not payload or not payload.isascii() or len(payload) > 512:
        raise CapturePdfRenderError("invalid printable PDS2 data")
    if box != CaptureRectangle(468, 40, 108, 108):
        raise CapturePdfRenderError("QR reservation differs from frozen layout")
    code = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=4)
    code.add_data(payload, optimize=0)
    code.make(fit=True)
    matrix: list[list[bool]] = code.get_matrix()
    side = len(matrix)
    if side != len(matrix[0]) or any(len(row) != side for row in matrix):
        raise CapturePdfRenderError("QR matrix has invalid geometry")
    pitch = box.width / side
    if pitch < MIN_QR_MODULE_POINTS:
        raise CapturePdfRenderError("PDS2 locator exceeds scannable vector QR space")
    if any(any(row[:4] + row[-4:]) for row in matrix):
        raise CapturePdfRenderError("QR horizontal quiet zone missing")
    if any(any(matrix[n]) for n in (*range(4), *range(side - 4, side))):
        raise CapturePdfRenderError("QR vertical quiet zone missing")
    canvas.setFillColorRGB(1, 1, 1)
    canvas.rect(
        box.x,
        PAGE_HEIGHT - box.y - box.height,
        box.width,
        box.height,
        stroke=0,
        fill=1,
    )
    canvas.setFillColorRGB(0, 0, 0)
    for y, row in enumerate(matrix):
        start: int | None = None
        for x, active in enumerate((*row, False)):
            if active and start is None:
                start = x
            elif not active and start is not None:
                canvas.rect(
                    box.x + start * pitch,
                    PAGE_HEIGHT - box.y - (y + 1) * pitch,
                    (x - start) * pitch,
                    pitch,
                    stroke=0,
                    fill=1,
                )
                start = None


def _route_fallback(canvas: Canvas, box: CaptureRectangle, payload: str) -> None:
    """Print every canonical locator byte; never abbreviate/truncate a fallback."""
    if box != CaptureRectangle(40, 115, 400, 20):
        raise CapturePdfRenderError("fallback area differs from drawing plan")
    font, size = "Helvetica", 6.7
    chunks: list[str] = []
    remaining = payload
    while remaining:
        fit = 0
        for length in range(1, len(remaining) + 1):
            if stringWidth(remaining[:length], font, size) > box.width:
                break
            fit = length
        if not fit:
            raise CapturePdfRenderError("no room for PDS2 human fallback")
        chunks.append(remaining[:fit])
        remaining = remaining[fit:]
    if len(chunks) > 2 or "".join(chunks) != payload:
        raise CapturePdfRenderError("PDS2 fallback exceeds two printable lines")
    canvas.setFont(font, size)
    canvas.setFillColorRGB(0.08, 0.15, 0.24)
    for index, chunk in enumerate(chunks):
        canvas.drawString(box.x, PAGE_HEIGHT - (box.y + 8 + 9 * index), chunk)


def _draw_page(
    canvas: Canvas,
    drawing: PageDrawing,
    payload: str,
    *,
    index: int,
    count: int,
) -> None:
    canvas.setPageSize(letter)
    canvas.setFillColorRGB(1, 1, 1)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    _text(canvas, drawing.title)
    for line in drawing.instructions:
        _text(canvas, line)
    for entry in drawing.entries:
        if entry.heading is not None:
            _text(canvas, entry.heading)
        for field in entry.fields:
            _field(canvas, field)
    _text(canvas, drawing.footer)
    if isinstance(drawing, CoreFormDrawing):
        _text(
            canvas, TextRun(f"Page {index} of {count}", 460, 753, 7.2, "regular", 112)
        )
    _vector_qr(canvas, drawing.qr_area, payload)
    _route_fallback(canvas, drawing.route_text_area, payload)
    canvas.showPage()


def _validate_inventory(
    service: FileCapturePreparationService,
    snapshot: CapturePreparationResult,
    class_id: str,
    work_id: str,
) -> tuple[tuple[PagePreparationResult, ...], tuple[CapturePageSpec, ...]]:
    if not snapshot.ready_for_rendering:
        raise CapturePdfRenderError("Capture Batch is not fully verified and open")
    pages = snapshot.pages
    if not 1 <= len(pages) <= MAX_PDF_PAGES:
        raise CapturePdfRenderError("Capture Batch has unsupported page count")
    if snapshot.batch.class_id != class_id or snapshot.batch.work_id != work_id:
        raise CapturePdfRenderError("Capture Batch identity changed")
    if any(type(p.target.field("page_index")) is not int for p in pages):
        raise CapturePdfRenderError("Page Target has invalid physical index")
    ordered = sorted(pages, key=lambda p: cast(int, p.target.field("page_index")))
    if tuple(page.target.field("page_index") for page in ordered) != tuple(
        range(1, len(ordered) + 1)
    ):
        raise CapturePdfRenderError("physical page indices must be consecutive from 1")
    ids = [p.target.logical_id for p in ordered]
    if any(value is None for value in ids):
        raise CapturePdfRenderError("Page Target identity is missing")
    if len({(value or "").casefold() for value in ids}) != len(ordered):
        raise CapturePdfRenderError("duplicate Page Target identity")
    if len({p.payload for p in ordered}) != len(ordered):
        raise CapturePdfRenderError("physical pages do not have unique Core locators")
    specs: list[CapturePageSpec] = []
    for page in ordered:
        target = page.target
        if not isinstance(target, PageTargetV2):
            raise CapturePdfRenderError("current Page Target v2 required")
        if target.class_id != class_id or target.work_id != work_id:
            raise CapturePdfRenderError("Page Target owner differs from Batch")
        if page.locator is None or page.registration is None or page.payload is None:
            raise CapturePdfRenderError("route is not verified")
        if (
            route_binding_findings(target, page.registration)
            or serialize_pds2_payload(page.locator) != page.payload
            or parse_pds2_payload(page.payload) != page.locator
        ):
            raise CapturePdfRenderError("Core route and printable payload disagree")
        identity = target.to_dict()["template_identity"]
        if not isinstance(identity, dict):
            raise CapturePdfRenderError("Page Target template identity is invalid")
        spec = resolve_capture_page_spec(identity)
        spec.assert_page_target_exact(target)
        validate_page_purpose(target)
        resolve_existing_capture_context(
            target, repository=service.repository, path_guard=service.batches._safe
        )
        specs.append(spec)
    # Include orphan, extra, malformed and duplicate Core registrations, not
    # just the requested target's registered route.
    audit_capture_route_inventory(
        tuple(page.target for page in ordered),
        service.routes._registrations(class_id, work_id),
    )
    daily = [spec.form_id == "daily_classroom_observation" for spec in specs]
    if any(daily) and not all(daily):
        raise CapturePdfRenderError("Daily pages cannot mix with other capture forms")
    if all(daily):
        if len(specs) > 9 or tuple(spec.page_role for spec in specs) != (
            "classroom_observation",
            *(["observation_continuation"] * (len(specs) - 1)),
        ):
            raise CapturePdfRenderError("Daily page roles are not a complete packet")
    return tuple(ordered), tuple(specs)


def _identity(snapshot: CapturePreparationResult) -> tuple[object, ...]:
    return (
        snapshot.batch.to_dict(),
        tuple(
            (
                page.status,
                page.target.to_dict(),
                page.locator,
                page.registration,
                page.payload,
            )
            for page in snapshot.pages
        ),
    )


def render_verified_capture_batch_pdf(
    service: FileCapturePreparationService,
    class_id: str,
    work_id: str,
    *,
    authorization: CaptureAuthorization,
) -> RenderedCapturePdf:
    """Return one vector PDF only after durable, exact Core PDS2 readback.

    The caller must never provide printable routes. This method asks Portia's
    real service to reload the persisted Batch, Page Targets, and Core routes
    itself. It performs no filesystem writes, print handoff, or artifact claim.
    Output management and reprints require separate Slice 6 policy.
    """
    if not isinstance(service, FileCapturePreparationService):
        raise CapturePdfRenderError("real FileCapturePreparationService required")
    service.batches._authorize(class_id, "capture_form.render", authorization)
    initial = service.inspect(class_id, work_id, authorization=authorization)
    pages, specs = _validate_inventory(service, initial, class_id, work_id)
    if all(spec.form_id == "daily_classroom_observation" for spec in specs):
        packet = plan_daily_classroom_observation(continuation_pages=len(pages) - 1)
        drawings: tuple[PageDrawing, ...] = packet.pages
    else:
        drawings = tuple(plan_core_capture_form(spec.form_id) for spec in specs)
    for page, drawing in zip(pages, drawings, strict=True):
        drawing.assert_target_exact(page.target)

    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=letter, pageCompression=1, invariant=1)
    canvas.setTitle("Portia — Paper Capture Forms")
    canvas.setAuthor("Paper Data Suite / Portia")
    for index, (page, drawing) in enumerate(zip(pages, drawings, strict=True), 1):
        assert page.payload is not None
        _draw_page(canvas, drawing, page.payload, index=index, count=len(pages))
    canvas.save()
    data = stream.getvalue()
    if not data.startswith(b"%PDF-") or not data.endswith(b"%%EOF\n"):
        raise CapturePdfRenderError("vector PDF output is incomplete")

    # Catch changes during rendering (including terminal Batch transition and
    # route replacement). No PDF bytes escape if the durable authority changed.
    service.batches._authorize(class_id, "capture_form.render", authorization)
    final = service.inspect(class_id, work_id, authorization=authorization)
    _validate_inventory(service, final, class_id, work_id)
    if _identity(initial) != _identity(final):
        raise CapturePdfRenderError("durable capture authority changed during render")
    manifest = tuple(
        RenderedCapturePage(
            page_index=index,
            page_target_id=page.target.logical_id or "",
            template_identity=tuple(spec.template_identity().items()),
            pds2_payload=page.payload or "",
        )
        for index, (page, spec) in enumerate(zip(pages, specs, strict=True), 1)
    )
    return RenderedCapturePdf(data, hashlib.sha256(data).hexdigest(), manifest)
