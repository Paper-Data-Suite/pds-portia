from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_release_mechanics.py"
    spec = importlib.util.spec_from_file_location(
        "issue54_release_mechanics",
        path,
    )
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


def test_issue54_slice14_validator_accepts_mechanical_state() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_slice14_passes_only_release_contract_domain() -> None:
    statuses = {
        entry["domain_id"]: entry["status"]
        for entry in _audit()["audit_domains"]
    }
    assert statuses["release_contract_mechanical"] == "pass"
    assert statuses["cumulative_repository_qualification"] == "pending"
    assert statuses["python_platform_qualification"] == "pending"


def test_issue54_slice14_does_not_freeze_publication_identity() -> None:
    audit = _audit()
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
    assert audit["final_verdict"] == "PENDING"


def test_issue54_slice14_retains_zero_unresolved_findings() -> None:
    audit = _audit()
    assert audit["unresolved_finding_ids"] == []
    assert audit["finding_counts"]["BLOCKER"] == 0
    assert audit["finding_counts"]["MAJOR"] == 0
    assert audit["finding_counts"]["MINOR"] == 1


def test_issue54_generic_package_checker_requires_release_mechanics_evidence() -> None:
    source = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    assert "_ISSUE54_REQUIRED_SDIST_FILES" in source
    for marker in (
        '"RELEASE_NOTES_v0.2.0.md"',
        '"docs/audits/portia-v0.2.0-release-audit.json"',
        '"scripts/check_issue54_release_package.py"',
        '"scripts/validate_issue54_release_mechanics.py"',
        '"tests/test_issue54_release_package.py"',
        '"tests/test_issue54_release_mechanics.py"',
    ):
        assert marker in source
