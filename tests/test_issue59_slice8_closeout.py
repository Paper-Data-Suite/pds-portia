"""Issue #59 exact final source/packaging boundaries, no real student scans."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_issue59_closeout import INTAKE_FILES, VALIDATION_FILES, validate

ROOT = Path(__file__).resolve().parents[1]


def test_closeout_inventory_and_source_contract() -> None:
    assert len(INTAKE_FILES) == 9
    assert len(VALIDATION_FILES) >= 18
    assert not validate(ROOT)


def test_all_intake_sources_are_python() -> None:
    assert all(path.endswith(".py") for path in INTAKE_FILES)
    assert "portia/intake/recovery.py" in INTAKE_FILES
    assert "portia/intake/page_records.py" in INTAKE_FILES


def test_published_schema_is_not_redefined_for_issue59() -> None:
    source = ROOT / "schemas/v1/capture/page-record.schema.json"
    body = source.read_text(encoding="utf-8")
    assert '"source_scan_id"' in body
    assert '"source_page_number"' in body
    assert '"capture_page_record"' in body


def test_scan_optional_extra_explicitly_installed_in_wheel_smoke() -> None:
    smoke = (ROOT / "scripts/smoke_test_issue59_scan_wheel.py").read_text(
        encoding="utf-8"
    )
    assert 'f"{portia_wheel}[scan]"' in smoke
    assert "FileCoreRetainedSourceRecoveryService" in smoke
    assert "FilePageQrDiscoveryService" in smoke
