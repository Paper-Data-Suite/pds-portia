"""Issue #58 Slice 7 guided preparation, exact reuse and preview boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_issue57_slice6_preparation import CLASS, Authorized, setup

from portia.capture.teacher_flow import (
    TeacherCaptureFlowError,
    TeacherCaptureRequest,
    TeacherCaptureService,
)
from portia.menu.capture_forms import LocalWorkspaceCaptureAuthority
from portia.menu.main import render_main_menu
from portia.models import ExactPortiaWorkRef

STAMP = "2026-10-17T17:15:00-04:00"


def service_at(root: Path) -> tuple[TeacherCaptureService, Authorized]:
    preparation, auth = setup(root)
    return TeacherCaptureService(
        root, authorization=auth, preparation=preparation
    ), auth


def plan_for(service: TeacherCaptureService, form: str, count: int = 0):
    return service.plan(
        TeacherCaptureRequest(CLASS, form, count),
        batch_id="cbat_slice7_work",
        page_ids=tuple(f"ptgt_slice7_{i}" for i in range(count + 1)),
        timestamp=STAMP,
    )


def test_daily_plan_has_exact_independent_targets_and_no_domain_fact(
    tmp_path: Path,
) -> None:
    service, auth = service_at(tmp_path)
    plan = plan_for(service, "daily_classroom_observation", 2)
    assert [item.field("page_index") for item in plan.targets] == [1, 2, 3]
    assert len({item.logical_id for item in plan.targets}) == 3
    assert tuple(
        item.to_dict()["template_identity"]["page_role"] for item in plan.targets
    ) == (
        "classroom_observation",
        "observation_continuation",
        "observation_continuation",
    )
    assert plan.batch.to_dict()["created_by"] == auth.attribution()
    assert all("existing_work_context" not in page.to_dict() for page in plan.targets)
    assert not (tmp_path / "portia" / "capture_forms").exists()
    assert not (tmp_path / "classes" / CLASS / "modules" / "portia").exists()


@pytest.mark.parametrize(
    "form",
    [
        "focused_monitoring",
        "communication_log",
        "event_information",
        "multi_event_information",
        "support_implementation",
        "follow_up",
    ],
)
def test_standalone_form_plans_without_domain_objects(
    tmp_path: Path, form: str
) -> None:
    service, _auth = service_at(tmp_path)
    plan = plan_for(service, form)
    assert len(plan.targets) == 1
    assert plan.targets[0].to_dict()["page_purpose"].endswith("_capture")
    assert "existing_work_context" not in plan.targets[0].to_dict()


@pytest.mark.parametrize("bad_count", [-1, 9, 1.0, True, "2"])
def test_unsupported_continuation_count_denied(
    tmp_path: Path, bad_count: object
) -> None:
    service, _auth = service_at(tmp_path)
    with pytest.raises((TeacherCaptureFlowError, ValueError)):
        service.plan(
            TeacherCaptureRequest(CLASS, "daily_classroom_observation", bad_count),  # type: ignore[arg-type]
            batch_id="cbat_bad",
            page_ids=("ptgt_bad",),
            timestamp=STAMP,
        )


def test_required_existing_work_rejected_without_canonical_record(
    tmp_path: Path,
) -> None:
    service, _auth = service_at(tmp_path)
    with pytest.raises(TeacherCaptureFlowError, match="requires an exact"):
        plan_for(service, "event_evidence")
    fake = ExactPortiaWorkRef(CLASS, "evt_absent", "event", "2")
    request = TeacherCaptureRequest(CLASS, "event_evidence", 0, fake)
    plan = service.plan(
        request, batch_id="cbat_bound", page_ids=("ptgt_bound",), timestamp=STAMP
    )
    assert plan.targets[0].to_dict()["existing_work_context"] == fake.to_dict()
    with pytest.raises(Exception):
        service.generate(plan)  # Preflight refuses non-existent exact Event.
    assert not (tmp_path / "portia" / "capture_forms").exists()


def test_end_to_end_generation_reprint_and_verified_preview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, auth = service_at(tmp_path)
    plan = plan_for(service, "daily_classroom_observation", 1)
    outcome = service.generate(plan)
    assert outcome.status == "pdf_ready"
    assert outcome.pdf is not None and outcome.pdf.page_count == 2
    assert outcome.pdf.state == "created"
    original = outcome.pdf.pdf_path.read_bytes()
    result = service.reprint(CLASS, outcome.batch_id)
    assert result.state == "reused"
    assert result.pdf_path.read_bytes() == original
    opened: list[Path] = []
    monkeypatch.setattr(
        "portia.capture.teacher_flow._open_verified_local_path",
        lambda path: opened.append(Path(path)) or Path(path),
    )
    assert service.preview(CLASS, outcome.batch_id) == result.pdf_path
    assert opened == [result.pdf_path]
    assert "capture_form.preview" in auth.actions
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "pdf_ready_not_printed"
    assert not list(tmp_path.rglob("event.json"))


def test_preview_fails_closed_on_corrupt_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _auth = service_at(tmp_path)
    outcome = service.generate(plan_for(service, "focused_monitoring"))
    assert outcome.pdf is not None
    outcome.pdf.pdf_path.write_bytes(b"damaged")
    monkeypatch.setattr(
        "portia.capture.teacher_flow._open_verified_local_path",
        lambda path: pytest.fail("viewer must not launch for damaged PDF"),
    )
    with pytest.raises(Exception):
        service.preview(CLASS, outcome.batch_id)


def test_no_permission_to_plan_or_generate(tmp_path: Path) -> None:
    service, _auth = service_at(tmp_path)
    service.authorization = Authorized(())
    with pytest.raises(PermissionError):
        plan_for(service, "focused_monitoring")
    assert not (tmp_path / "portia" / "capture_forms").exists()


def test_local_workspace_authorization_is_class_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from portia.menu import capture_forms
    from portia.menu.selectors import ClassOption

    monkeypatch.setattr(
        capture_forms,
        "class_options",
        lambda _root: (ClassOption(CLASS, "2026-2027", 0),),
    )
    authority = LocalWorkspaceCaptureAuthority(tmp_path)
    authority.require_access(CLASS, "page_route.inspect")
    with pytest.raises(PermissionError):
        authority.require_access("class_other", "page_route.inspect")
    with pytest.raises(PermissionError):
        authority.require_access(CLASS, "student_identity.override")
    assert authority.attribution()["type"] == "system_process"


def test_menu_addition_does_not_change_existing_option_numbers() -> None:
    menu = render_main_menu()
    assert "9. Advanced Portia tools" in menu
    assert "10. Create Paper Capture Forms" in menu


def test_cross_class_work_and_wrong_page_count_rejected(tmp_path: Path) -> None:
    service, _auth = service_at(tmp_path)
    wrong = ExactPortiaWorkRef("class_other", "evt_absent", "event", "2")
    with pytest.raises(TeacherCaptureFlowError, match="different class"):
        service.plan(
            TeacherCaptureRequest(CLASS, "event_evidence", 0, wrong),
            batch_id="cbat_wrong",
            page_ids=("ptgt_wrong",),
            timestamp=STAMP,
        )
    plan = plan_for(service, "daily_classroom_observation", 1)
    with pytest.raises(TeacherCaptureFlowError, match="own ID"):
        service.plan(
            plan.request,
            batch_id="cbat_wrong",
            page_ids=("ptgt_only",),
            timestamp=STAMP,
        )
