from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

from portia.models.references import ExactPortiaWorkRef
from portia.storage.generated_paths import (
    GENERATED_PATH_TOKEN_LENGTH,
    STORAGE_REVISION_LEAF_LENGTH,
    build_generated_path_token,
    build_work_storage_revision_leaf,
)
from portia.storage.paths import (
    legacy_work_storage_history_path,
    work_storage_history_path,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_storage_compat_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_storage_compat_audit", path)
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


def _domain_status(domain_id: str) -> str | None:
    for raw_domain in _audit()["audit_domains"]:
        assert isinstance(raw_domain, dict)
        if raw_domain["domain_id"] == domain_id:
            status = raw_domain["status"]
            assert isinstance(status, str)
            return status
    return None


def _obligation_statuses() -> dict[str, str]:
    return {
        entry["finding_id"]: entry["status"]
        for entry in _audit()["inherited_foundation_obligations"]
    }


def test_issue54_slice7_validator_accepts_storage_compat_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_storage_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("storage_path_history_compatibility") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_slice7_handoff_obligations_remain_explicit() -> None:
    statuses = _obligation_statuses()
    assert "PF-AUD-005" in statuses
    assert "PF-AUD-007" in statuses


def test_issue54_generated_path_tokens_remain_fixed_length() -> None:
    short = build_generated_path_token("path_budget_probe", "a")
    long = build_generated_path_token("path_budget_probe", "x" * 4096)
    assert len(short) == GENERATED_PATH_TOKEN_LENGTH == 35
    assert len(long) == GENERATED_PATH_TOKEN_LENGTH
    assert short != long


def test_issue54_storage_revision_leaf_remains_bounded() -> None:
    digest = "a" * 64
    short = build_work_storage_revision_leaf("account", "acct_a", digest)
    long = build_work_storage_revision_leaf(
        "record_" + "x" * 4096,
        "id_" + "y" * 4096,
        digest,
    )
    assert len(short) == STORAGE_REVISION_LEAF_LENGTH == 40
    assert len(long) == STORAGE_REVISION_LEAF_LENGTH
    assert short != long


def test_issue54_bounded_writer_and_legacy_reader_paths_remain_distinct(
    tmp_path: Path,
) -> None:
    work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_example",
        work_kind="event",
        contract_version="2",
    )
    digest = "b" * 64
    bounded = work_storage_history_path(
        tmp_path,
        work,
        "account",
        "acct_example",
        digest,
    )
    legacy = legacy_work_storage_history_path(
        tmp_path,
        work,
        "account",
        "acct_example",
        digest,
    )
    assert bounded != legacy
    assert bounded.name.startswith("pt_")
    assert bounded.name.endswith(".json")
    assert legacy.name == f"{digest}.json"


def test_issue54_migration_store_retains_exact_no_implicit_migration_contract() -> None:
    source = (
        ROOT / "portia" / "storage" / "migration_representations.py"
    ).read_text(encoding="utf-8")
    assert "never migrates during reads" in source
    assert "never a version winner" in source
    assert "without implicit migration" in source


def test_issue54_issue92_compatibility_tests_remain_present() -> None:
    derived = (ROOT / "tests" / "test_derived_paths_issue92.py").read_text(
        encoding="utf-8"
    )
    generated = (ROOT / "tests" / "test_generated_paths_issue92.py").read_text(
        encoding="utf-8"
    )
    assert "test_legacy_derived_generation_loads_without_migration" in derived
    assert "test_new_generation_cuts_over_from_legacy_without_rewriting_legacy" in derived
    assert "test_storage_revision_leaf_does_not_expand_with_record_identity" in generated


def test_issue54_core_current_and_historical_compatibility_authorities_stay_split() -> None:
    core = _audit()["core_qualification"]
    assert core["current"]["version"] == "0.6.4"
    assert core["historical"]["version"] == "0.6.3"


def test_issue54_slice7_opens_no_storage_compat_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "storage_path_history_compatibility"
    ]
    assert findings == []
