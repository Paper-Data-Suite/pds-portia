"""Slice 6: real guarded, immutable, restartable PDF/receipt publication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from test_issue57_slice6_preparation import CLASS, WORK, Authorized
from test_issue58_slice5_pdf_rendering import prepared

from portia.capture.managed_pdf import (
    ARTIFACT_RECEIPT_VERSION,
    FileCapturePdfArtifactService,
    ManagedCapturePdfError,
    _validate_pdf,
)
from portia.capture.pdf_rendering import render_verified_capture_batch_pdf
from portia.storage.errors import (
    PortiaConflictError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)


def generator(tmp_path: Path, *forms: str):
    service, auth, _state = prepared(tmp_path, *(forms or ("focused_monitoring",)))
    return FileCapturePdfArtifactService(service), auth


def names(root: Path) -> tuple[str, ...]:
    base = root / "portia" / "capture_forms"
    return tuple(
        sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())
    )


def test_managed_packet_receipt_and_readback(tmp_path: Path) -> None:
    generator_service, auth = generator(
        tmp_path, "daily_classroom_observation", "daily_classroom_observation"
    )
    result = generator_service.generate(CLASS, WORK, authorization=auth)
    assert result.state == "created"
    assert result.page_count == 2
    assert len(result.page_target_ids) == 2
    assert result.pdf_path.read_bytes().startswith(b"%PDF-")
    assert result.sha256 == hashlib.sha256(result.pdf_path.read_bytes()).hexdigest()
    record = json.loads(result.receipt_path.read_bytes())
    assert record["receipt_version"] == ARTIFACT_RECEIPT_VERSION
    assert record["status"] == "pdf_ready_not_printed"
    assert record["pdf_sha256"] == result.sha256
    assert record["page_count"] == 2
    assert len(set(page["pds2_payload"] for page in record["pages"])) == 2
    assert "capture_form.generate" in auth.actions
    assert not (tmp_path / "portia" / "actors").exists()
    assert not list(result.pdf_path.parent.glob(".*.stage-*"))
    assert not list(result.pdf_path.parent.glob("*.lock"))


def test_exact_reprint_reuses_immutable_bytes_and_no_route_churn(
    tmp_path: Path,
) -> None:
    generator_service, auth = generator(tmp_path)
    first = generator_service.generate(CLASS, WORK, authorization=auth)
    before = names(tmp_path)
    original_pdf = first.pdf_path.read_bytes()
    original_receipt = first.receipt_path.read_bytes()
    next_result = generator_service.generate(CLASS, WORK, authorization=auth)
    assert next_result.state == "reused"
    assert first.sha256 == next_result.sha256
    assert names(tmp_path) == before
    assert first.pdf_path.read_bytes() == original_pdf
    assert first.receipt_path.read_bytes() == original_receipt
    assert (
        generator_service.inspect(CLASS, WORK, authorization=auth).state == "verified"
    )


def test_interrupted_pdf_without_receipt_requires_explicit_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator_service, auth = generator(tmp_path)
    real_install = generator_service._install
    counter = 0

    def fail_second(path: Path, content: bytes) -> None:
        nonlocal counter
        counter += 1
        if counter == 2:
            raise PortiaStorageError("synthetic receipt write failure")
        real_install(path, content)

    monkeypatch.setattr(generator_service, "_install", fail_second)
    with pytest.raises(PortiaStorageError, match="synthetic"):
        generator_service.generate(CLASS, WORK, authorization=auth)
    pdf, receipt, lock = generator_service._locations(CLASS, WORK)
    assert pdf.exists() and not receipt.exists() and not lock.exists()
    with pytest.raises(PortiaRecoveryRequiredError, match="explicitly recover"):
        generator_service.generate(CLASS, WORK, authorization=auth)
    monkeypatch.setattr(generator_service, "_install", real_install)
    result = generator_service.recover(CLASS, WORK, authorization=auth)
    assert result.state == "recovered"
    assert pdf.exists() and receipt.exists() and not lock.exists()


def test_interrupted_receipt_without_pdf_can_be_completed_exactly(
    tmp_path: Path,
) -> None:
    generator_service, auth = generator(tmp_path)
    prepared_render = render_verified_capture_batch_pdf(
        generator_service.preparation, CLASS, WORK, authorization=auth
    )
    from portia.capture.managed_pdf import _receipt

    pdf, receipt, _lock = generator_service._locations(CLASS, WORK)
    receipt.parent.mkdir(parents=True)
    receipt.write_bytes(_receipt(prepared_render, CLASS, WORK))
    with pytest.raises(PortiaRecoveryRequiredError):
        generator_service.generate(CLASS, WORK, authorization=auth)
    assert (
        generator_service.recover(CLASS, WORK, authorization=auth).state == "recovered"
    )
    assert pdf.read_bytes() == prepared_render.pdf_bytes


def test_mismatched_persisted_bytes_never_overwritten(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    first = generator_service.generate(CLASS, WORK, authorization=auth)
    first.pdf_path.write_bytes(b"%PDF-damaged\n%%EOF\n")
    with pytest.raises(PortiaConflictError):
        generator_service.generate(CLASS, WORK, authorization=auth)
    with pytest.raises(PortiaConflictError):
        generator_service.recover(CLASS, WORK, authorization=auth)
    assert first.pdf_path.read_bytes().startswith(b"%PDF-damaged")


def test_changed_receipt_rejected_without_repair(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    first = generator_service.generate(CLASS, WORK, authorization=auth)
    first.receipt_path.write_bytes(b"{}\n")
    with pytest.raises(PortiaConflictError, match="receipt"):
        generator_service.generate(CLASS, WORK, authorization=auth)
    assert first.receipt_path.read_bytes() == b"{}\n"


def test_closed_batch_blocks_generation_and_inspection(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    saved = generator_service.generate(CLASS, WORK, authorization=auth)
    generator_service.preparation.batches.transition(
        CLASS, WORK, "closed", authorization=auth
    )
    with pytest.raises(ValueError, match="verified"):
        generator_service.generate(CLASS, WORK, authorization=auth)
    with pytest.raises(ValueError, match="verified"):
        generator_service.inspect(CLASS, WORK, authorization=auth)
    assert saved.pdf_path.exists()
    assert saved.receipt_path.exists()


def test_authorization_denial_leaves_no_artifacts(tmp_path: Path) -> None:
    generator_service, _auth = generator(tmp_path)
    with pytest.raises(PermissionError):
        generator_service.generate(CLASS, WORK, authorization=Authorized(()))
    assert not (tmp_path / "portia" / "capture_forms").exists()


def test_already_present_lock_is_not_auto_cleared(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    _pdf, _receipt, lock = generator_service._locations(CLASS, WORK)
    lock.parent.mkdir(parents=True)
    lock.write_bytes(b"interrupted-other-operator")
    with pytest.raises(PortiaRecoveryRequiredError, match="manual review"):
        generator_service.generate(CLASS, WORK, authorization=auth)
    assert lock.read_bytes() == b"interrupted-other-operator"


def test_cannot_use_cross_class_or_traversal_destination(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    with pytest.raises((ValueError, PortiaPathError)):
        generator_service.generate(CLASS, "../outside", authorization=auth)
    assert not (tmp_path.parent / "outside").exists()
    with pytest.raises(PermissionError):
        generator_service.generate("class_other", WORK, authorization=auth)


def test_output_symlink_denied_before_file_write(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    parent = tmp_path / "portia" / "capture_forms" / CLASS
    parent.mkdir(parents=True)
    outside = tmp_path.parent / "outside-slice6-target"
    outside.mkdir(exist_ok=True)
    try:
        (parent / WORK).symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symlinks not available for unprivileged account")
    with pytest.raises(PortiaPathError):
        generator_service.generate(CLASS, WORK, authorization=auth)
    assert list(outside.iterdir()) == []


def test_atomic_publish_failure_leaves_no_final(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    generator_service, auth = generator(tmp_path)
    import portia.capture.managed_pdf as managed

    original_link = managed.os.link

    def failed_link(src: Path, dst: Path) -> None:
        raise OSError("synthetic link unavailable")

    monkeypatch.setattr(managed.os, "link", failed_link)
    with pytest.raises(PortiaStorageError, match="publication unavailable"):
        generator_service.generate(CLASS, WORK, authorization=auth)
    pdf, receipt, lock = generator_service._locations(CLASS, WORK)
    assert not pdf.exists() and not receipt.exists() and not lock.exists()
    assert not list(pdf.parent.glob("*.stage-*"))
    monkeypatch.setattr(managed.os, "link", original_link)
    assert (
        generator_service.generate(CLASS, WORK, authorization=auth).state == "created"
    )


def test_partial_route_does_not_publish_pdf(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    pdf, receipt, _lock = generator_service._locations(CLASS, WORK)
    # Deliberately remove only a synthetic route; no final result may be issued.
    registration = (
        generator_service.preparation.inspect(CLASS, WORK, authorization=auth)
        .pages[0]
        .locator
    )
    assert registration is not None
    from pds_core.routes import route_registration_path

    route_registration_path(tmp_path, registration).unlink()
    with pytest.raises(ValueError):
        generator_service.generate(CLASS, WORK, authorization=auth)
    assert not pdf.exists() and not receipt.exists()


def test_no_orphan_cleanup_or_false_print_status(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    result = generator_service.generate(CLASS, WORK, authorization=auth)
    record = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert "printed_at" not in record
    assert "returned_at" not in record
    assert "student_id" not in record
    assert "pdf_ready_not_printed" == record["status"]
    # A second physical copy is permitted without new Core registrations.
    assert generator_service.generate(CLASS, WORK, authorization=auth).state == "reused"


def test_unexpected_pdf_envelope_or_digest_rejected(tmp_path: Path) -> None:
    generator_service, auth = generator(tmp_path)
    result = render_verified_capture_batch_pdf(
        generator_service.preparation, CLASS, WORK, authorization=auth
    )
    import dataclasses

    wrong = dataclasses.replace(result, sha256="0" * 64)
    with pytest.raises(ManagedCapturePdfError, match="digest"):
        _validate_pdf(result.pdf_bytes, wrong)
    with pytest.raises(ManagedCapturePdfError):
        _validate_pdf(b"%PDF-1.4\n%%EOF", result)
