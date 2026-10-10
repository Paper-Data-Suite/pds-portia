from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
CORE_065_SHA256 = "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"


def _load(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit() -> dict[str, Any]:
    raw: object = json.loads(
        (ROOT / "docs" / "audits" / "portia-v0.2.0-release-audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(raw, dict)
    return cast(dict[str, Any], raw)


def test_issue54_slice15_validator_accepts_cumulative_state() -> None:
    validator = _load(
        "scripts/validate_issue54_cumulative_qualification.py",
        "issue54_cumulative_qualification",
    )
    assert validator.validate_repo(ROOT) == []


def test_issue54_slice15_advances_only_cumulative_domain() -> None:
    statuses = {
        entry["domain_id"]: entry["status"]
        for entry in _audit()["audit_domains"]
    }
    assert statuses["release_contract_mechanical"] == "pass"
    assert statuses["cumulative_repository_qualification"] == "pass"
    assert statuses["python_platform_qualification"] == "pending"


def test_issue54_current_core_authority_is_065_with_prior_history_retained() -> None:
    core = _audit()["core_qualification"]
    assert core["current"] == {
        "version": "0.6.5",
        "filename": "pds_core-0.6.5-py3-none-any.whl",
        "sha256": CORE_065_SHA256,
        "source_commit": "64da9d2e4884ffe78a020aed87b1d5b9500927ad",
    }
    assert core["prior_release_compatibility"]["version"] == "0.6.4"
    assert core["historical"]["version"] == "0.6.3"


def test_issue54_core_verifier_authenticates_065() -> None:
    verifier = _load("scripts/verify_core_wheel.py", "issue54_core_verifier")
    assert verifier.KNOWN_WHEELS["pds_core-0.6.5-py3-none-any.whl"] == (
        "0.6.5",
        CORE_065_SHA256,
    )


def test_issue54_authoritative_repository_gate_is_promoted() -> None:
    source = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    assert (
        "Run the complete Portia repository qualification through Issue #54 "
        "cumulative qualification."
    ) in source
    assert "Portia Issue #54 cumulative repository qualification passed" in source
    assert "_ISSUE53_CLOSEOUT_COMPATIBILITY_MARKERS" in source
    assert "--prior-core-wheel" in source


def test_issue54_authoritative_gate_runs_every_issue54_validator_before_full_pytest() -> None:
    source = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    validators = (
        "scripts/validate_issue54_release_audit.py",
        "scripts/validate_issue54_ethics_audit.py",
        "scripts/validate_issue54_authority_audit.py",
        "scripts/validate_issue54_privacy_audit.py",
        "scripts/validate_issue54_identity_audit.py",
        "scripts/validate_issue54_architecture_audit.py",
        "scripts/validate_issue54_storage_compat_audit.py",
        "scripts/validate_issue54_recovery_integrity_audit.py",
        "scripts/validate_issue54_usability_audit.py",
        "scripts/validate_issue54_menu_terminology_audit.py",
        "scripts/validate_issue54_read_only_audit.py",
        "scripts/validate_issue54_packaging_audit.py",
        "scripts/validate_issue54_documentation_audit.py",
        "scripts/validate_issue54_release_mechanics.py",
        "scripts/validate_issue54_cumulative_qualification.py",
    )
    positions = [source.index(marker) for marker in validators]
    full_pytest = source.index('[sys.executable, "-m", "pytest"]')
    assert positions == sorted(positions)
    assert all(position < full_pytest for position in positions)
    assert source.count('[sys.executable, "-m", "pytest"]') == 1


def test_issue54_cumulative_gate_uses_three_tier_core_authority() -> None:
    source = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    assert "0.6.5" in source
    assert "--prior-core-wheel" in source
    assert "--historical-core-wheel" in source
    assert "scripts/smoke_test_issue54_core065_wheel.py" in source


def test_issue54_ci_qualifies_current_prior_and_historical_core() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert 'current_core: "0.6.5"' in workflow
    assert 'prior_core: "0.6.4"' in workflow
    assert 'core: "0.6.3"' in workflow
    assert '--prior-core-wheel "$env:PDS_PRIOR_CORE_WHEEL"' in workflow


def test_issue54_slice15_does_not_freeze_release_identity() -> None:
    audit = _audit()
    assert audit["final_verdict"] == "PENDING"
    publication = audit["release_publication"]
    assert publication["status"] == "not_started"
    for field in (
        "release_commit",
        "release_tree",
        "tag",
        "github_release_url",
        "wheel_filename",
        "wheel_sha256",
        "sdist_filename",
        "sdist_sha256",
        "sha256sums_sha256",
    ):
        assert publication[field] is None
