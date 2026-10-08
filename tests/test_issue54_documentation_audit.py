from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_documentation_audit.py"
    spec = importlib.util.spec_from_file_location(
        "issue54_documentation_audit",
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


def test_issue54_slice13_validator_accepts_reconciled_docs() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_documentation_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    domains = {
        entry["domain_id"]: entry["status"]
        for entry in audit["audit_domains"]
    }
    assert domains["documentation_reconciliation"] == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_documentation_finding_is_resolved_minor() -> None:
    audit = _audit()
    findings = {
        entry["finding_id"]: entry
        for entry in audit["findings"]
    }
    finding = findings["P54-AUD-001"]
    assert finding["audit_domain"] == "documentation_reconciliation"
    assert finding["classification"] == "MINOR"
    assert finding["status"] == "resolved"
    assert audit["finding_counts"]["MINOR"] == 1
    assert audit["unresolved_finding_ids"] == []


def test_issue54_readme_no_longer_claims_implemented_v02_work_is_future() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Deferred Beyond v0.2.0" in readme
    assert "Likely next work includes:" not in readme
    assert (
        "implementing the accepted ADR 0009, ADR 0010, and ADR 0011 persistence"
        not in readme
    )
    assert "ADRs 0001–0020" in readme
    assert "Portia is licensed under the MIT License." in readme


def test_issue54_security_heading_is_not_duplicated() -> None:
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert security.count("## Identity and Cross-Module Boundaries") == 1


def test_issue54_release_notes_are_candidate_scoped_not_publication_claim() -> None:
    notes = (ROOT / "RELEASE_NOTES_v0.2.0.md").read_text(encoding="utf-8")
    assert (
        "Status: **release candidate; publication pending Issue #54 Phase 2 verification**"
        in notes
    )
    assert "RELEASED — VERIFIED" in notes
    assert "not an official institutional record" in notes
    assert "No publication-producer capability" in notes


def test_issue54_release_notes_are_sdist_not_wheel_repository_surface() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    checker = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    assert "include RELEASE_NOTES_v0.2.0.md" in manifest
    assert '"RELEASE_NOTES_v0.2.0.md"' in checker
    assert 'name.startswith(("docs/", "schemas/", "scripts/", "tests/", ".github/"))' in checker


def test_issue54_changelog_has_fresh_unreleased_and_v020_section() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.startswith("# Changelog\n\n## Unreleased\n\nNo changes yet.\n\n## 0.2.0\n")
    assert "Issue #54 release-audit evidence through documentation reconciliation" in changelog


def test_issue54_docs_index_has_no_em_dash_mojibake() -> None:
    docs = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "â€”" not in docs
    assert "../RELEASE_NOTES_v0.2.0.md" in docs
    assert "Slice 1 through Slice 13" in docs
