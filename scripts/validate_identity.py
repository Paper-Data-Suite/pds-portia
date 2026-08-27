"""Validate Issue #39 Core-roster and Actor Directory identity boundaries."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from portia.identity import ActorDirectoryService, CoreRosterResolver
from portia.identity.issue22_parity import identity_parity_by_id
from portia.storage import ActorDirectoryRepository

_REQUIRED_IDENTITY_MODULES = {
    "__init__.py",
    "actors.py",
    "context.py",
    "errors.py",
    "issue22_parity.py",
    "roster.py",
}
_EXPECTED_PARITY = {"G22-005", "G22-006", "G22-007", "G22-009"}
_REQUIRED_ACTOR_METHODS = {
    "create_actor",
    "load_actor",
    "load_actor_child",
    "replace_actor",
    "create_actor_child",
    "replace_actor_child",
    "load_contact_point",
    "load_relationship",
    "list_relationships",
    "resolve_actor",
    "resolve_actor_child",
    "resolve_contact_point",
    "resolve_relationship",
    "resolve_student_relationship",
}
_REQUIRED_REPOSITORY_METHODS = {
    "list_actor_children",
    "load_actor_directory_removal",
    "list_actor_directory_removals",
}
_FORBIDDEN_IDENTITY_IO_TOKENS = (
    ".read_text(",
    ".write_text(",
    ".iterdir(",
    ".unlink(",
    ".open(",
    "read_json(",
    "exclusive_create(",
    "guarded_replace(",
)
_FORBIDDEN_AUTHORITATIVE_RESOLUTION_TOKENS = {
    "resolve_by_name",
    "lookup_by_name",
    "find_best_match",
    "fuzzy_match",
}
_FORBIDDEN_ACTOR_RECORD_DICTIONARY_TOKENS = (
    "record.to_dict(",
)


def _metadata_findings(root: Path) -> list[str]:
    with (root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    dependencies = data["project"]["dependencies"]
    if dependencies != ["pds-core>=0.6.3,<0.7"]:
        return [
            "Issue #39 requires the exact active Core floor pds-core>=0.6.3,<0.7; "
            f"found {dependencies!r}"
        ]
    return []


def _source_findings(root: Path) -> list[str]:
    findings: list[str] = []
    identity_root = root / "portia" / "identity"
    present = {path.name for path in identity_root.glob("*.py")}
    missing = sorted(_REQUIRED_IDENTITY_MODULES - present)
    if missing:
        findings.append(f"identity package is missing required modules: {missing}")

    production_paths = sorted(identity_root.glob("*.py"))
    production_paths.append(root / "portia" / "storage" / "actor_directory.py")
    for path in production_paths:
        if not path.is_file():
            findings.append(f"required identity/storage source is missing: {path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        if "pds_core._" in text:
            findings.append(f"{path.name} imports a private Core module")
        if "schema_validation" in text or "tests." in text:
            findings.append(f"{path.name} imports test-only validation code")
        for token in _FORBIDDEN_AUTHORITATIVE_RESOLUTION_TOKENS:
            if token in text:
                findings.append(
                    f"{path.name} exposes forbidden name/fuzzy authoritative resolver token: {token}"
                )
        if path.parent.name == "identity":
            for token in _FORBIDDEN_IDENTITY_IO_TOKENS:
                if token in text:
                    findings.append(
                        f"{path.name} performs forbidden direct identity-layer filesystem I/O: {token}"
                    )
        if path.name == "actors.py":
            for token in _FORBIDDEN_ACTOR_RECORD_DICTIONARY_TOKENS:
                if token in text:
                    findings.append(
                        "actors.py converts a public Actor-family record to an anonymous "
                        f"dictionary for business logic: {token}"
                    )
    roster_text = (identity_root / "roster.py").read_text(encoding="utf-8")
    for required in ("load_class_roster", "student_lookup", "Roster", "StudentRecord"):
        if required not in roster_text:
            findings.append(f"roster resolver does not use required public Core surface: {required}")
    return findings


def _api_findings() -> list[str]:
    findings: list[str] = []
    for method in ("load_roster", "resolve", "resolve_reference"):
        if not hasattr(CoreRosterResolver, method):
            findings.append(f"CoreRosterResolver is missing {method}")
    missing_actor = sorted(
        method for method in _REQUIRED_ACTOR_METHODS if not hasattr(ActorDirectoryService, method)
    )
    if missing_actor:
        findings.append(f"ActorDirectoryService is missing methods: {missing_actor}")
    missing_repo = sorted(
        method
        for method in _REQUIRED_REPOSITORY_METHODS
        if not hasattr(ActorDirectoryRepository, method)
    )
    if missing_repo:
        findings.append(f"ActorDirectoryRepository is missing methods: {missing_repo}")
    return findings


def _parity_findings() -> list[str]:
    parity = identity_parity_by_id()
    actual = set(parity)
    findings: list[str] = []
    if actual != _EXPECTED_PARITY:
        findings.append(
            "Issue #39 identity parity drift: "
            f"missing={sorted(_EXPECTED_PARITY - actual)}, extra={sorted(actual - _EXPECTED_PARITY)}"
        )
    for scenario_id in ("G22-005", "G22-006", "G22-007"):
        if parity.get(scenario_id) is None or parity[scenario_id].disposition != "covered_by_39":
            findings.append(f"{scenario_id} must be production-covered by Issue #39")
    if parity.get("G22-009") is None or parity["G22-009"].disposition != "bounded_shared_boundary":
        findings.append("G22-009 must preserve the bounded resolver-owned/shared boundary")
    return findings


def _documentation_findings(root: Path) -> list[str]:
    findings: list[str] = []
    path = root / "docs" / "identity-and-actor-directory.md"
    if not path.is_file():
        return ["identity architecture documentation is missing"]
    text = path.read_text(encoding="utf-8")
    required = (
        "class_id + student_id",
        "Names are display data",
        "Actor–Student Relationship",
        "Quarantine",
        "validation context",
        "pds-core>=0.6.3,<0.7",
    )
    findings.extend(
        f"identity documentation is missing required statement: {item}"
        for item in required
        if item not in text
    )

    readme = (root / "README.md").read_text(encoding="utf-8")
    if "### Issue #39 current implementation" not in readme:
        findings.append("README does not describe the Issue #39 current implementation")
    stale = "Live Core-backed identity resolution and teacher-facing workflows remain assigned"
    if stale in readme:
        findings.append("README still claims live Core-backed identity resolution is deferred")

    runtime_models = (root / "docs" / "runtime-models.md").read_text(encoding="utf-8")
    if "Issue #39 provides that production bridge" not in runtime_models:
        findings.append("runtime-model documentation does not describe the Issue #39 bridge")
    return findings


def validate(root: Path) -> tuple[str, ...]:
    findings: list[str] = []
    findings.extend(_metadata_findings(root))
    findings.extend(_source_findings(root))
    findings.extend(_api_findings())
    findings.extend(_parity_findings())
    findings.extend(_documentation_findings(root))
    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"Identity validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #39 identity validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
