"""Validate Issue #38 canonical storage and guarded-persistence boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository
from portia.storage.errors import PortiaPathError
from portia.storage.issue22_parity import storage_parity_by_id
from portia.storage.locks import derive_lock_id
from portia.storage.paths import derived_current_path, work_manifest_path
from portia.validation.issue22_parity import parity_by_id

_REQUIRED_STORAGE_MODULES = {
    "__init__.py",
    "acknowledgements.py",
    "derived.py",
    "errors.py",
    "fingerprint.py",
    "integrity.py",
    "io.py",
    "issue22_parity.py",
    "locks.py",
    "orchestration.py",
    "paths.py",
    "quarantine.py",
    "recovery.py",
    "repository.py",
    "series.py",
    "staging.py",
}

_REQUIRED_REPOSITORY_METHODS = {
    "load_work",
    "create_work",
    "replace_work",
    "load_work_record",
    "create_work_record",
    "replace_work_record",
    "load_actor",
    "create_actor",
    "replace_actor",
    "load_actor_child",
    "create_actor_child",
    "replace_actor_child",
    "create_actor_directory_removal",
}

_EXPECTED_COVERED_PARITY = {
    "P22-14",
    "G22-002",
    "G22-003",
    "G22-028",
    "G22-029",
    "G22-036",
}


def _path_contract_findings(root: Path) -> list[str]:
    findings: list[str] = []
    work = ExactPortiaWorkRef(
        class_id="class_storage_validation",
        work_id="evt_storage_validation",
        work_kind="event",
        contract_version="2",
    )
    expected = (
        root
        / "classes"
        / "class_storage_validation"
        / "modules"
        / "portia"
        / "work"
        / "evt_storage_validation"
        / "work.json"
    )
    if work_manifest_path(root, work) != expected:
        findings.append("canonical work root no longer matches the Core-backed path contract")

    try:
        derived_current_path(root, "class_summary", {"scope": "workspace"})
    except PortiaPathError:
        pass
    else:
        findings.append("workspace-derived paths manufacture a workspace identity")

    target = {
        "kind": "work",
        "work_ref": {
            "module_id": "portia",
            "class_id": "class_english10_p2",
            "work_id": "evt_example",
            "work_kind": "event",
            "contract_version": "2",
        },
    }
    expected_lock = (
        "lock_fa7db2eeed2ed3dc58cb12f945306b0a3311a22c54ed10fda0c9cecc35cb6fa2"
    )
    if derive_lock_id("work", target) != expected_lock:
        findings.append("lock-key derivation drifted from the accepted Issue #13 fixture")
    return findings


def _parity_findings() -> list[str]:
    findings: list[str] = []
    runtime = parity_by_id()
    expected = {
        scenario_id
        for scenario_id, entry in runtime.items()
        if entry.disposition == "outside_37_runtime_boundary"
    }
    storage = storage_parity_by_id()
    actual = set(storage)
    if actual != expected:
        findings.append(
            "Issue #22 storage parity drift: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    covered = {
        scenario_id
        for scenario_id, entry in storage.items()
        if entry.disposition == "covered_by_38"
    }
    if covered != _EXPECTED_COVERED_PARITY:
        findings.append(
            "Issue #22 storage coverage claim drift: "
            f"expected={sorted(_EXPECTED_COVERED_PARITY)}, actual={sorted(covered)}"
        )
    if storage.get("P22-13") is None or storage["P22-13"].disposition != "shared_boundary":
        findings.append("P22-13 must preserve the derived/retention/custody shared boundary")
    if storage.get("G22-037") is None or storage["G22-037"].disposition != "external_boundary":
        findings.append("G22-037 must remain outside Portia local custody authority")
    return findings


def _source_boundary_findings(root: Path) -> list[str]:
    findings: list[str] = []
    storage_root = root / "portia" / "storage"
    present = {path.name for path in storage_root.glob("*.py")}
    missing = sorted(_REQUIRED_STORAGE_MODULES - present)
    if missing:
        findings.append(f"storage package is missing required modules: {missing}")

    for path in sorted(storage_root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "pds_core._" in text:
            findings.append(f"{path.name} imports a Core-private module")
        for sibling in ("scoreform", "quillan", "concord", "meridian", "vitrine"):
            if f"import {sibling}" in text or f"from {sibling}" in text:
                findings.append(f"{path.name} imports sibling-private runtime code: {sibling}")
    return findings


def validate(root: Path) -> tuple[str, ...]:
    findings: list[str] = []
    findings.extend(_source_boundary_findings(root))
    findings.extend(_path_contract_findings(root))
    findings.extend(_parity_findings())

    missing_methods = sorted(
        method for method in _REQUIRED_REPOSITORY_METHODS if not hasattr(PortiaRepository, method)
    )
    if missing_methods:
        findings.append(f"PortiaRepository is missing guarded facade methods: {missing_methods}")
    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Storage validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #38 storage validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
