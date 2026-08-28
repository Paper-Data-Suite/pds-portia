"""Mechanically validate the Issue #40/#41 production workflow boundary."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from portia.storage import PortiaRepository
from portia.workflows import (
    AccountWorkflowService,
    EventBundleWorkflowService,
    EventWorkflowService,
    ObservationWorkflowService,
    ParticipantWorkflowService,
    RoleWorkflowService,
    WorkRelationshipService,
    account_reference,
    observation_reference,
)
from portia.workflows.issue22_parity import workflow_issue22_parity

_REQUIRED_MODULES = {
    "__init__.py",
    "account_relations.py",
    "accounts.py",
    "common.py",
    "context.py",
    "coordinated.py",
    "errors.py",
    "events.py",
    "evidence.py",
    "evidence_artifacts.py",
    "evidence_lifecycle.py",
    "evidence_supersession.py",
    "evidence_transition.py",
    "issue22_parity.py",
    "observations.py",
    "participants.py",
    "relationships.py",
    "roles.py",
}
_REQUIRED_REPOSITORY_METHODS = {
    "list_accounts",
    "list_events",
    "list_event_participants",
    "list_event_participant_roles",
    "list_observations",
    "list_work_records",
    "list_work_records_mixed_versions",
    "list_work_relationships",
}
_FORBIDDEN_CALLS = {
    "write_text",
    "write_bytes",
    "unlink",
    "replace",
    "open",
}
_FORBIDDEN_CLASSES = {
    "WorkflowTransaction",
    "WorkflowLock",
    "WorkflowJournal",
    "EvidenceTransaction",
    "EvidenceLock",
    "EvidenceJournal",
}
_EVIDENCE_MODULES = {
    "account_relations.py",
    "accounts.py",
    "evidence.py",
    "evidence_artifacts.py",
    "evidence_lifecycle.py",
    "evidence_supersession.py",
    "evidence_transition.py",
    "observations.py",
}
_LATER_DOMAIN_IMPORT_TOKENS = {
    "classification",
    "determination",
    "hypothesis",
    "review",
}
_LATER_EXECUTION_IMPORT_TOKENS = {
    "capture_materialization",
    "capture_review",
    "import_materialization",
    "import_review",
    "paper_capture",
}


def _imported_module_names(tree: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return tuple(names)


def _source_findings(root: Path) -> list[str]:
    findings: list[str] = []
    package = root / "portia" / "workflows"
    present = {path.name for path in package.glob("*.py")}
    missing = sorted(_REQUIRED_MODULES - present)
    if missing:
        findings.append(f"workflow package is missing modules: {missing}")

    for path in sorted(package.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        if "pds_core._" in text:
            findings.append(f"{path.name} imports a private Core module")
        if "load_class_roster" in text or "student_lookup" in text:
            findings.append(f"{path.name} parses or searches Core roster data directly")
        if "resolve_by_name" in text or "fuzzy_match" in text:
            findings.append(f"{path.name} exposes a name/fuzzy identity resolver")
        if "ActorDirectoryRepository" in text:
            findings.append(f"{path.name} bypasses ActorDirectoryService")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in _FORBIDDEN_CLASSES:
                findings.append(f"{path.name} defines forbidden {node.name}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in _FORBIDDEN_CALLS:
                    findings.append(
                        f"{path.name} performs forbidden direct canonical I/O: {node.func.attr}"
                    )

        if path.name in _EVIDENCE_MODULES:
            imported = _imported_module_names(tree)
            for module in imported:
                segments = set(module.split("."))
                if segments & _LATER_DOMAIN_IMPORT_TOKENS:
                    findings.append(
                        f"{path.name} imports later interpretation/judgment workflow authority: {module}"
                    )
                if segments & _LATER_EXECUTION_IMPORT_TOKENS:
                    findings.append(
                        f"{path.name} imports deferred paper/import execution authority: {module}"
                    )

    context = (package / "context.py").read_text(encoding="utf-8")
    for required in ("CoreRosterResolver", "ActorDirectoryService"):
        if required not in context:
            findings.append(f"workflow context does not consume #39 {required}")

    common = (package / "common.py").read_text(encoding="utf-8")
    for required in (
        'EVENT_VERSION = "2"',
        'PARTICIPANT_VERSION = "3"',
        'ROLE_VERSION = "3"',
        'RELATIONSHIP_VERSION = "2"',
        "EVENT_STATUS_TRANSITIONS",
        "CHILD_STATUS_TRANSITIONS",
        "require_revision_invariants",
        "validate_record_graph",
    ):
        if required not in common:
            findings.append(f"workflow common boundary is missing: {required}")

    evidence = (package / "evidence.py").read_text(encoding="utf-8")
    for required in (
        'ACCOUNT_VERSION = "2"',
        'OBSERVATION_VERSION = "2"',
        'ACCOUNT_READ_VERSIONS = frozenset({"1", "2"})',
        'OBSERVATION_READ_VERSIONS = frozenset({"1", "2"})',
        "require_digital_entry_creation",
    ):
        if required not in evidence:
            findings.append(f"evidence writer/reader policy is missing: {required}")

    accounts = (package / "accounts.py").read_text(encoding="utf-8")
    observations = (package / "observations.py").read_text(encoding="utf-8")
    if "AccountV2" not in accounts:
        findings.append("Account writer is not visibly constrained to AccountV2")
    if "ObservationV2" not in observations:
        findings.append("Observation writer is not visibly constrained to ObservationV2")

    exports = (package / "__init__.py").read_text(encoding="utf-8")
    for required in (
        "AccountWorkflowService",
        "ObservationWorkflowService",
        "account_reference",
        "observation_reference",
    ):
        if required not in exports:
            findings.append(f"public workflow package is missing export: {required}")
    return findings


def _api_findings() -> list[str]:
    findings: list[str] = []
    expected = {
        EventWorkflowService: {"create", "load_exact", "replace", "list", "require_current_use"},
        ParticipantWorkflowService: {
            "create",
            "load_exact",
            "replace",
            "list",
            "resolve_person",
            "require_role_eligibility",
            "require_current_use",
        },
        RoleWorkflowService: {
            "create",
            "load_exact",
            "replace",
            "list",
            "list_for_participant",
            "require_current_use",
        },
        WorkRelationshipService: {
            "create",
            "load_exact",
            "replace",
            "list",
            "resolve_endpoints",
            "require_current_use",
        },
        EventBundleWorkflowService: {"commit"},
        AccountWorkflowService: {
            "create",
            "load_exact",
            "list",
            "require_current_use",
            "transition_lifecycle",
            "correct",
            "retract",
        },
        ObservationWorkflowService: {
            "create",
            "load_exact",
            "list",
            "require_current_use",
            "transition_lifecycle",
            "correct",
        },
    }
    for service, methods in expected.items():
        missing = sorted(method for method in methods if not hasattr(service, method))
        if missing:
            findings.append(f"{service.__name__} is missing methods: {missing}")
    for helper, name in (
        (account_reference, "account_reference"),
        (observation_reference, "observation_reference"),
    ):
        if not callable(helper):
            findings.append(f"public workflow helper is not callable: {name}")
    missing_repo = sorted(
        method for method in _REQUIRED_REPOSITORY_METHODS if not hasattr(PortiaRepository, method)
    )
    if missing_repo:
        findings.append(f"PortiaRepository is missing bounded evidence reads: {missing_repo}")
    return findings


def _parity_findings() -> list[str]:
    actual = {entry.scenario_id for entry in workflow_issue22_parity()}
    required = {
        "P22-01",
        "P22-02",
        "P22-03",
        "P22-04",
        "P22-10",
        "G22-009",
        "G22-010",
        "G22-011",
        "G22-017",
        "G22-035",
    }
    missing = sorted(required - actual)
    return [f"workflow Issue #22 parity is missing: {missing}"] if missing else []


def _documentation_findings(root: Path) -> list[str]:
    required = (
        root / "docs" / "event-participant-role-and-relationship-workflows.md",
        root / "docs" / "account-and-observation-workflows.md",
        root
        / "docs"
        / "validation"
        / "issue-40-event-participant-role-and-relationship-workflows-validation.md",
        root
        / "docs"
        / "validation"
        / "issue-41-account-and-observation-workflows-validation.md",
    )
    return [
        f"required workflow documentation is missing: {path}"
        for path in required
        if not path.is_file()
    ]


def validate(root: Path) -> tuple[str, ...]:
    findings = _source_findings(root)
    findings.extend(_api_findings())
    findings.extend(_parity_findings())
    findings.extend(_documentation_findings(root))
    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, SyntaxError, TypeError, ValueError) as exc:
        print(f"Workflow validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #41 workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
