from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_python_platform_qualification.py"
    spec = importlib.util.spec_from_file_location(
        "issue54_python_platform_qualification",
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


def test_issue54_slice16_validator_accepts_platform_state() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_slice16_completes_all_audit_domains() -> None:
    statuses = {
        entry["domain_id"]: entry["status"]
        for entry in _audit()["audit_domains"]
    }
    assert statuses
    assert set(statuses.values()) == {"pass"}
    assert statuses["python_platform_qualification"] == "pass"


def test_issue54_python_support_syntax_is_broader_than_tested_matrix() -> None:
    audit = _audit()
    assert audit["release_contract"]["requires_python"] == ">=3.11"

    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    versions = re.findall(
        r'^\s+python:\s*"([^"]+)"\s*$',
        ci,
        flags=re.MULTILINE,
    )
    assert versions == ["3.11", "3.11"]
    assert ci.count("os: ubuntu-latest") == 1
    assert ci.count("os: windows-latest") == 1


def test_issue54_platform_matrix_retains_three_core_authorities() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert ci.count('current_core: "0.6.5"') == 2
    assert ci.count('prior_core: "0.6.4"') == 2
    assert ci.count('core: "0.6.3"') == 2


def test_issue54_normal_push_workflow_does_not_exclude_release_tags() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "  push:\n" in ci
    assert "tags-ignore:" not in ci


def test_issue54_release_notes_state_platform_boundary_truthfully() -> None:
    notes = (ROOT / "RELEASE_NOTES_v0.2.0.md").read_text(encoding="utf-8")
    assert "Release qualification matrix: Python 3.11 on Windows and Ubuntu." in notes
    assert "`Requires-Python >=3.11` is package compatibility syntax" in notes
    assert "Python minors other than 3.11 are not claimed as release-tested" in notes


def test_issue54_slice16_state_is_prepublication_or_verified() -> None:
    audit = _audit()
    publication = audit["release_publication"]
    assert (audit["final_verdict"], publication["status"]) in {
        ("PENDING", "not_started"),
        ("RELEASED — VERIFIED", "verified"),
    }
