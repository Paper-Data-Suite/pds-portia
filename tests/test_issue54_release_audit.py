from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
STARTING_COMMIT = "d2cca3b7d8eb59087016d4da60e623960758a729"
STARTING_TREE = "33067ffdd35047d2c6ac575cc7d21969c2a3862b"
CORE_065_SHA256 = (
    "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
)
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


def test_issue54_core_authority_separates_current_prior_and_historical_inputs() -> None:
    audit = _audit()
    current = audit["core_qualification"]["current"]
    prior = audit["core_qualification"]["prior_release_compatibility"]
    historical = audit["core_qualification"]["historical"]
    assert current == {
        "version": "0.6.5",
        "filename": "pds_core-0.6.5-py3-none-any.whl",
        "sha256": CORE_065_SHA256,
        "source_commit": "64da9d2e4884ffe78a020aed87b1d5b9500927ad",
    }
    assert prior == {
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


def test_issue54_audit_state_binds_verified_release() -> None:
    audit = _audit()
    assert audit["phase"] == "phase_2_release_verified"
    assert audit["final_verdict"] == "RELEASED — VERIFIED"
    publication = audit["release_publication"]
    assert publication["status"] == "verified"
    assert publication["release_commit"] == "83cfe05ef6b03d8453fdb60d1a1702f138d5293d"
    assert publication["release_tree"] == "2050bd1c7aabb47ccf2df4a8285c7a61ac360f2e"
    assert publication["tag"] == "v0.2.0"
    assert publication["tag_object_sha"] == "5a32b2707400c35446d9365cc758cb49bbd6337e"
    assert publication["tag_target_sha"] == "83cfe05ef6b03d8453fdb60d1a1702f138d5293d"
    assert publication["github_release_url"] == "https://github.com/Paper-Data-Suite/pds-portia/releases/tag/v0.2.0"
    assert publication["wheel_sha256"] == "7ae545e62740b4411736fc55e572a86384ed8714f1f65346d65e36a7943f3550"
    assert publication["sdist_sha256"] == "ea78dd74b6c9bbabb7da71397c9cdc4985479428b679856040f7fb2fcbcad0c8"
    assert publication["sha256sums_sha256"] == "aa7f972a6dcc5f1113fe85298827ec7d0b2a11d08b01e8c83d77784980d93403"


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
        "PF-AUD-006": "reconciled",
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

def test_issue54_release_verification_is_complete() -> None:
    audit = _audit()
    verification = audit["release_verification"]
    assert verification["status"] == "passed"
    assert verification["release_preparation_ci"]["run_id"] == 38092134396
    assert verification["tag_ci"]["run_id"] == 38099826435
    assert verification["clean_main_cumulative"]["terminal_message"] == (
        "Portia Issue #54 cumulative repository qualification passed"
    )
    assert verification["fresh_download"]["wheel_sha256"] == "7ae545e62740b4411736fc55e572a86384ed8714f1f65346d65e36a7943f3550"
    assert verification["fresh_download"]["sdist_sha256"] == "ea78dd74b6c9bbabb7da71397c9cdc4985479428b679856040f7fb2fcbcad0c8"
    assert verification["fresh_download"]["sha256sums_sha256"] == "aa7f972a6dcc5f1113fe85298827ec7d0b2a11d08b01e8c83d77784980d93403"
    assert verification["fresh_download"]["issue53_terminal_message"] == (
        "Portia Issue #53 installed acceptance passed"
    )
    assert verification["fresh_download"]["core065_terminal_message"] == (
        "Portia Issue #54 Core 0.6.5 installed compatibility passed"
    )


def test_issue54_suite_handoff_is_exact() -> None:
    audit = _audit()
    assert audit["suite_composition_handoff"] == {
        "status": "ready_for_independent_suite_qualification",
        "component_id": "portia",
        "display_name": "Portia",
        "repository": "Paper-Data-Suite/pds-portia",
        "distribution": "pds-portia",
        "version": "0.2.0",
        "requires_python": ">=3.11",
        "core_requirement": "pds-core>=0.6.3,<0.7",
        "exact_release_wheel": "pds_portia-0.2.0-py3-none-any.whl",
        "exact_wheel_sha256": "7ae545e62740b4411736fc55e572a86384ed8714f1f65346d65e36a7943f3550",
        "github_tag": "v0.2.0",
        "console_script": "portia = portia.cli:main",
        "module_operations_entry_point": "portia = portia.pds_operations:get_module_operations_profile",
        "sibling_runtime_dependency": False,
        "publication_producer_capability": False,
        "teacher_local_launchable_application": True,
        "readiness_attention_provider_capability": True,
        "suite_manifest_modified_by_issue54": False,
        "suite_composition_qualification_owner": "pds-paper-data-suite"
}
