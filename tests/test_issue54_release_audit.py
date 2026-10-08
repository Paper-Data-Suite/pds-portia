from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
STARTING_COMMIT = "d2cca3b7d8eb59087016d4da60e623960758a729"
STARTING_TREE = "33067ffdd35047d2c6ac575cc7d21969c2a3862b"
CORE_064_SHA256 = (
    "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"
)
CORE_063_SHA256 = (
    "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5"
)


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_release_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_release_audit", path)
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


def test_issue54_slice1_validator_accepts_current_audit_foundation() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_audit_binds_exact_phase0_handoff() -> None:
    audit = _audit()
    assert audit["starting_portia_commit"] == STARTING_COMMIT
    assert audit["starting_portia_tree"] == STARTING_TREE
    baseline = audit["baseline_qualification"]
    assert baseline["status"] == "passed_before_slice_1"
    assert baseline["qualified_commit"] == STARTING_COMMIT
    assert baseline["qualified_tree"] == STARTING_TREE
    assert baseline["terminal_message"] == "Portia Issue #53 repository qualification passed"


def test_issue54_core_authority_separates_current_and_historical_inputs() -> None:
    audit = _audit()
    current = audit["core_qualification"]["current"]
    historical = audit["core_qualification"]["historical"]
    assert current == {
        "version": "0.6.4",
        "filename": "pds_core-0.6.4-py3-none-any.whl",
        "sha256": CORE_064_SHA256,
        "source_commit": "152d1c65064c4f8fe55249ff2ca3379d7c4d6ccb",
    }
    assert historical == {
        "version": "0.6.3",
        "filename": "pds_core-0.6.3-py3-none-any.whl",
        "sha256": CORE_063_SHA256,
    }


def test_issue54_audit_state_does_not_prematurely_claim_release() -> None:
    audit = _audit()
    assert audit["phase"] == "phase_1_audit_in_progress"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"
    assert audit["release_publication"]["wheel_sha256"] is None
    assert audit["release_publication"]["sdist_sha256"] is None
    assert audit["release_publication"]["github_release_url"] is None


def test_issue54_foundation_reaudit_obligations_are_explicit() -> None:
    audit = _audit()
    ids = tuple(
        entry["finding_id"] for entry in audit["inherited_foundation_obligations"]
    )
    assert ids == (
        "PF-AUD-005",
        "PF-AUD-006",
        "PF-AUD-007",
        "PF-AUD-008",
        "PF-AUD-009",
        "PF-AUD-010",
        "PF-AUD-011",
        "PF-AUD-012",
    )
    statuses = {
        entry["finding_id"]: entry["status"]
        for entry in audit["inherited_foundation_obligations"]
    }
    assert statuses == {
        "PF-AUD-005": "reconciled",
        "PF-AUD-006": "pending_reaudit",
        "PF-AUD-007": "reconciled",
        "PF-AUD-008": "reconciled",
        "PF-AUD-009": "reconciled",
        "PF-AUD-010": "reconciled",
        "PF-AUD-011": "reconciled",
        "PF-AUD-012": "reconciled",
    }


def test_issue54_release_contract_remains_exact() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["name"] == "pds-portia"
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == ["pds-core>=0.6.3,<0.7"]
    assert project["scripts"] == {"portia": "portia.cli:main"}
    assert project["entry-points"]["paper_data_suite.module_operations"] == {
        "portia": "portia.pds_operations:get_module_operations_profile"
    }
    assert "paper_data_suite.publication_producers" not in project["entry-points"]


def test_issue54_validator_is_in_strict_mypy_scope() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    assert "scripts/validate_issue54_release_audit.py" in data["tool"]["mypy"]["files"]


def test_issue54_docs_index_the_audit_and_validation_records() -> None:
    docs = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    audits = (ROOT / "docs" / "audits" / "README.md").read_text(encoding="utf-8")
    assert "audits/portia-v0.2.0-release-audit.md" in docs
    assert "validation/issue-54-v0.2.0-release-audit-validation.md" in docs
    assert "portia-v0.2.0-release-audit.json" in audits
    assert "portia-v0.2.0-release-findings.md" in audits
