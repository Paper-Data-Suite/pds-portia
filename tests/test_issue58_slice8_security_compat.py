"""Issue #58 Slice 8: adversarial managed-PDF and historical-route gates.

These tests use only synthetic Core classes, Page Targets and paper packets.
The separate physical printer/scanner gate cannot be satisfied by pytest.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pds_core.pds2 import parse_pds2_payload, serialize_pds2_payload
from pds_core.route_registrations import load_route_registration
from test_issue57_slice6_preparation import CLASS, WORK
from test_issue58_slice5_pdf_rendering import prepared
from test_issue58_slice6_managed_pdf import generator

from portia.capture.pdf_rendering import render_verified_capture_batch_pdf
from portia.capture.teacher_flow import (
    TeacherCaptureFlowError,
    TeacherCaptureService,
    _open_verified_local_path,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
)


def test_registered_daily_continuations_have_independent_durable_routes(
    tmp_path: Path,
) -> None:
    service, auth, state = prepared(
        tmp_path,
        "daily_classroom_observation",
        "daily_classroom_observation",
        "daily_classroom_observation",
    )
    packet = render_verified_capture_batch_pdf(service, CLASS, WORK, authorization=auth)
    assert packet.page_count == 3
    assert len({page.pds2_payload for page in packet.pages}) == 3
    assert len({page.page_target_id for page in packet.pages}) == 3
    for page, prepared_page in zip(packet.pages, state.pages, strict=True):
        parsed = parse_pds2_payload(page.pds2_payload)
        assert serialize_pds2_payload(parsed) == page.pds2_payload
        persisted = load_route_registration(tmp_path, parsed)
        assert persisted.target.record_id == page.page_target_id
        assert persisted.module_details["template_identity"] == dict(
            page.template_identity
        )
        assert prepared_page.registration == persisted
    assert len({page.template_identity for page in packet.pages[1:]}) == 1
    assert packet.pages[0].template_identity != packet.pages[1].template_identity


def test_managed_pdf_rejects_attacker_modified_route_receipt_and_pdf(
    tmp_path: Path,
) -> None:
    service, auth = generator(tmp_path, "focused_monitoring")
    saved = service.generate(CLASS, WORK, authorization=auth)
    original_pdf = saved.pdf_path.read_bytes()
    receipt = json.loads(saved.receipt_path.read_text(encoding="utf-8"))
    receipt["pages"][0]["pds2_payload"] = "PDS2|m=portia|c=invalid|w=bad|r=bad"
    saved.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(PortiaConflictError, match="receipt"):
        service.inspect(CLASS, WORK, authorization=auth)
    assert saved.pdf_path.read_bytes() == original_pdf
    assert saved.receipt_path.read_text(encoding="utf-8") != ""
    # Never silently reset modified bytes to make the packet appear valid.
    with pytest.raises(PortiaConflictError):
        service.generate(CLASS, WORK, authorization=auth)


def test_stale_generation_lock_preserved_after_declined_retry(
    tmp_path: Path,
) -> None:
    service, auth = generator(tmp_path, "communication_log")
    _, _, lock = service._locations(CLASS, WORK)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_bytes(b"preserve-for-human-recovery")
    with pytest.raises(PortiaRecoveryRequiredError):
        service.generate(CLASS, WORK, authorization=auth)
    with pytest.raises(PortiaRecoveryRequiredError):
        service.recover(CLASS, WORK, authorization=auth)
    assert lock.read_bytes() == b"preserve-for-human-recovery"
    assert not (lock.parent / "capture-packet.pdf").exists()


def test_deep_onedrive_like_workspace_keeps_canonical_output_and_routes(
    tmp_path: Path,
) -> None:
    root = tmp_path.joinpath(
        "OneDrive - Example Board of Education",
        "2026-2027",
        "Paper-Data-Suite",
        "teacher_workspace_" + "x" * 48,
        "module_data_" + "y" * 36,
    )
    root.mkdir(parents=True)
    service, auth = generator(root, "focused_monitoring")
    saved = service.generate(CLASS, WORK, authorization=auth)
    assert saved.pdf_path.is_file() and saved.receipt_path.is_file()
    assert saved.pdf_path.is_relative_to(root)
    assert saved.pdf_path.stat().st_size > 1000
    assert service.inspect(CLASS, WORK, authorization=auth).sha256 == saved.sha256
    assert service.generate(CLASS, WORK, authorization=auth).state == "reused"


def test_unverified_preview_never_calls_viewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, auth = generator(tmp_path, "focused_monitoring")
    gateway = TeacherCaptureService(
        tmp_path, authorization=auth, preparation=service.preparation
    )
    attempts: list[Path] = []

    def fake_open(path: Path) -> Path:
        attempts.append(path)
        return path

    monkeypatch.setattr(
        "portia.capture.teacher_flow._open_verified_local_path", fake_open
    )
    with pytest.raises(PortiaRecoveryRequiredError):
        gateway.preview(CLASS, WORK)
    assert attempts == []
    stored = gateway.reprint(CLASS, WORK)
    assert gateway.preview(CLASS, WORK) == stored.pdf_path
    assert attempts == [stored.pdf_path]


def test_preview_missing_core_open_feature_fails_without_fabrication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "pds_core.local_open", None)
    with pytest.raises(TeacherCaptureFlowError, match="compatible Core"):
        _open_verified_local_path(tmp_path / "never_created.pdf")
    assert not (tmp_path / "never_created.pdf").exists()


def test_wrong_class_never_generates_or_previews_pdf(tmp_path: Path) -> None:
    service, auth = generator(tmp_path, "focused_monitoring")
    gateway = TeacherCaptureService(
        tmp_path, authorization=auth, preparation=service.preparation
    )
    with pytest.raises(PermissionError):
        gateway.reprint("class_wrong", WORK)
    with pytest.raises(PermissionError):
        gateway.preview("class_wrong", WORK)
    assert not (tmp_path / "portia" / "capture_forms").exists()


def test_linked_capture_output_directory_is_rejected_without_external_writes(
    tmp_path: Path,
) -> None:
    service, auth = generator(tmp_path, "focused_monitoring")
    class_dir = tmp_path / "portia" / "capture_forms" / CLASS
    class_dir.mkdir(parents=True)
    external = tmp_path.parent / ("slice8-external-" + tmp_path.name)
    external.mkdir(exist_ok=False)
    link = class_dir / WORK
    if os.name == "nt":
        command = (
            "$ErrorActionPreference='Stop'; "
            "New-Item -ItemType Junction -Path $env:PDS_TEST_LINK "
            "-Target $env:PDS_TEST_TARGET -ErrorAction Stop | Out-Null"
        )
        env = dict(os.environ)
        env["PDS_TEST_LINK"] = str(link)
        env["PDS_TEST_TARGET"] = str(external)
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    else:
        link.symlink_to(external, target_is_directory=True)
    try:
        with pytest.raises(PortiaPathError):
            service.generate(CLASS, WORK, authorization=auth)
        assert list(external.iterdir()) == []
    finally:
        if os.name == "nt":
            link.rmdir()  # Remove junction only, never recurse into destination.
        else:
            link.unlink()


def test_all_nine_form_families_keep_immutable_historical_lookup() -> None:
    from portia.capture.form_catalog import (
        capture_pages_for_form,
        list_supported_capture_forms,
        resolve_capture_page_spec,
    )

    families = list_supported_capture_forms()
    assert len(families) == 9
    assert len({name for name, _ in families}) == 9
    assert sum(len(capture_pages_for_form(name)) for name, _ in families) == 10
    for name, _label in families:
        for spec in capture_pages_for_form(name):
            assert resolve_capture_page_spec(spec.template_identity()) == spec
            assert all(
                not field.required for entry in spec.entries for field in entry.fields
            )
