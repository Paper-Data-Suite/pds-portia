from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_checker():
    path = ROOT / "scripts" / "check_issue54_release_package.py"
    spec = importlib.util.spec_from_file_location("issue54_release_package", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue54_release_package_names_are_exact() -> None:
    checker = _load_checker()
    assert checker.EXPECTED_WHEEL == "pds_portia-0.2.0-py3-none-any.whl"
    assert checker.EXPECTED_SDIST == "pds_portia-0.2.0.tar.gz"
    assert checker.EXPECTED_SDIST_ROOT == "pds_portia-0.2.0"


def test_issue54_release_package_requires_audit_evidence_in_sdist() -> None:
    checker = _load_checker()
    assert {
        "RELEASE_NOTES_v0.2.0.md",
        "docs/audits/portia-v0.2.0-release-audit.json",
        "docs/audits/portia-v0.2.0-release-audit.md",
        "docs/audits/portia-v0.2.0-release-findings.md",
        "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
        "scripts/check_issue54_release_package.py",
        "scripts/validate_issue54_release_mechanics.py",
    } <= checker.REQUIRED_SDIST_EVIDENCE


def test_issue54_release_package_rejects_extra_dist_files(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / checker.EXPECTED_WHEEL).write_bytes(b"not-a-wheel")
    (tmp_path / checker.EXPECTED_SDIST).write_bytes(b"not-an-sdist")
    (tmp_path / "extra.whl").write_bytes(b"extra")
    findings = checker.validate_target(tmp_path)
    assert len(findings) == 1
    assert "exactly the two Issue #54 candidate artifacts" in findings[0]


def test_issue54_release_package_keeps_hashes_explicitly_nonfinal() -> None:
    source = (ROOT / "scripts" / "check_issue54_release_package.py").read_text(
        encoding="utf-8"
    )
    assert "candidate wheel SHA-256 (NOT FINAL)" in source
    assert "candidate sdist SHA-256 (NOT FINAL)" in source
    assert "Phase 2 must rebuild from exact qualified main" in source
