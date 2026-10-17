"""Slice 5: real persisted-route PDF rendering, no fictional QR authority."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from test_issue57_slice6_preparation import CLASS, WORK, Authorized, batch, page, setup

from portia.capture.contracts import CapturePreparationRequest
from portia.capture.form_catalog import capture_pages_for_form
from portia.capture.pdf_rendering import (
    CapturePdfRenderError,
    _route_fallback,
    render_verified_capture_batch_pdf,
)
from portia.models import PageTargetV2


def target(number: int, form: str = "daily_classroom_observation") -> PageTargetV2:
    resource = capture_pages_for_form(form)
    spec = resource[0]
    if form == "daily_classroom_observation" and number > 1:
        spec = resource[1]
    raw = page(number).to_dict()
    raw["template_identity"] = spec.template_identity()
    raw["entry_layout"] = spec.entry_layout()
    raw["page_purpose"] = spec.page_purpose
    raw["capture_mode"] = spec.capture_mode
    return PageTargetV2(raw)


def prepared(tmp_path: Path, *forms: str):
    service, auth = setup(tmp_path)
    targets = tuple(target(i, form) for i, form in enumerate(forms, 1))
    result = service.prepare(
        CapturePreparationRequest(batch(), targets), authorization=auth
    )
    assert result.ready_for_rendering
    return service, auth, result


def assert_vector_pdf(pdf: bytes, count: int) -> None:
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == count
    assert b"/Subtype /Image" not in pdf  # QR and checkboxes are PDF vector shapes.


def test_one_core_form_renders_exact_verified_core_route(tmp_path: Path) -> None:
    service, auth, result = prepared(tmp_path, "focused_monitoring")
    rendered = render_verified_capture_batch_pdf(
        service, CLASS, WORK, authorization=auth
    )
    assert rendered.page_count == 1
    assert_vector_pdf(rendered.pdf_bytes, 1)
    assert rendered.sha256 == hashlib.sha256(rendered.pdf_bytes).hexdigest()
    assert rendered.pages[0].pds2_payload == result.pages[0].payload
    assert rendered.pages[0].page_target_id == result.pages[0].target.logical_id
    assert dict(rendered.pages[0].template_identity) == (
        capture_pages_for_form("focused_monitoring")[0].template_identity()
    )
    assert "capture_form.render" in auth.actions
    replay = render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)
    assert replay.pdf_bytes == rendered.pdf_bytes


def test_daily_continuation_pages_have_distinct_route_and_number(
    tmp_path: Path,
) -> None:
    service, auth, result = prepared(
        tmp_path,
        "daily_classroom_observation",
        "daily_classroom_observation",
        "daily_classroom_observation",
    )
    rendered = render_verified_capture_batch_pdf(
        service, CLASS, WORK, authorization=auth
    )
    assert_vector_pdf(rendered.pdf_bytes, 3)
    assert [page.page_index for page in rendered.pages] == [1, 2, 3]
    assert len(set(page.pds2_payload for page in rendered.pages)) == 3
    assert [page.pds2_payload for page in rendered.pages] == [
        page.payload for page in result.pages
    ]
    assert rendered.pages[1].template_identity == rendered.pages[2].template_identity
    assert rendered.pages[0].template_identity != rendered.pages[1].template_identity


def test_partial_preparation_cannot_be_printed(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    service.batches.create_or_load(batch(), authorization=auth)
    service.pages.create_or_load(target(1), authorization=auth)
    with pytest.raises(CapturePdfRenderError, match="fully verified"):
        render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)


def test_closed_batch_cannot_be_printed_even_with_valid_routes(tmp_path: Path) -> None:
    service, auth, _ = prepared(tmp_path, "communication_log")
    service.batches.transition(CLASS, WORK, "closed", authorization=auth)
    with pytest.raises(CapturePdfRenderError, match="fully verified"):
        render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)


def test_gap_in_page_indices_is_not_treated_as_printable_packet(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    result = service.prepare(
        CapturePreparationRequest(batch(), (target(1), target(3))),
        authorization=auth,
    )
    assert result.ready_for_rendering
    with pytest.raises(CapturePdfRenderError, match="consecutive"):
        render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)


def test_mixed_daily_and_other_form_is_not_guessed_into_packet(tmp_path: Path) -> None:
    service, auth, _ = prepared(
        tmp_path, "daily_classroom_observation", "focused_monitoring"
    )
    with pytest.raises(CapturePdfRenderError, match="cannot mix"):
        render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)


def test_self_declared_authorization_cannot_bypass_trusted_access(
    tmp_path: Path,
) -> None:
    service, _auth, _ = prepared(tmp_path, "focused_monitoring")
    denied = Authorized(())
    with pytest.raises(PermissionError):
        render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=denied)


def test_fake_service_cannot_claim_verified_route(tmp_path: Path) -> None:
    _service, auth, _ = prepared(tmp_path, "focused_monitoring")
    with pytest.raises(CapturePdfRenderError, match="real FileCapture"):
        render_verified_capture_batch_pdf(  # type: ignore[arg-type]
            object(), CLASS, WORK, authorization=auth
        )


def test_final_reinspection_blocks_lifecycle_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, auth, _ = prepared(tmp_path, "focused_monitoring")
    original = service.inspect
    reads = 0

    def changed(class_id: str, work_id: str, *, authorization: Authorized):
        nonlocal reads
        reads += 1
        if reads == 2:
            service.batches.transition(CLASS, WORK, "closed", authorization=auth)
        return original(class_id, work_id, authorization=authorization)

    monkeypatch.setattr(service, "inspect", changed)
    with pytest.raises(CapturePdfRenderError, match="fully verified"):
        render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)
    assert reads == 2


def test_no_domain_work_or_render_output_created_in_workspace(tmp_path: Path) -> None:
    service, auth, _ = prepared(tmp_path, "focused_monitoring")
    before = tuple(sorted(
        p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()
    ))
    render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)
    after = tuple(sorted(
        p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()
    ))
    assert before == after
    assert not (tmp_path / "portia" / "operations").exists()


def test_human_fallback_is_not_truncated() -> None:
    from portia.capture.form_catalog import CaptureRectangle

    class RecordingCanvas:
        def __init__(self) -> None:
            self.parts: list[str] = []

        def setFont(self, *args: object) -> None:
            return None

        def setFillColorRGB(self, *args: object) -> None:
            return None

        def drawString(self, x: object, y: object, part: str) -> None:
            self.parts.append(part)

    canvas = RecordingCanvas()
    payload = "PDS2:" + "a" * 140
    _route_fallback(  # type: ignore[arg-type]
        canvas, CaptureRectangle(40, 115, 400, 20), payload
    )
    assert "".join(canvas.parts) == payload
    assert len(canvas.parts) in (1, 2)
    with pytest.raises(CapturePdfRenderError, match="fallback"):
        _route_fallback(  # type: ignore[arg-type]
            canvas, CaptureRectangle(40, 115, 400, 20), "X" * 500
        )
