"""Mechanically validate the Issue #40 workflow architecture boundary."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from portia.storage import PortiaRepository
from portia.workflows import (
    EventBundleWorkflowService,
    EventWorkflowService,
    ParticipantWorkflowService,
    RoleWorkflowService,
    WorkRelationshipService,
)
from portia.workflows.issue22_parity import workflow_issue22_parity

_REQUIRED_MODULES = {
    "__init__.py",
    "common.py",
    "context.py",
    "coordinated.py",
    "errors.py",
    "events.py",
    "issue22_parity.py",
    "participants.py",
    "relationships.py",
    "roles.py",
}
_REQUIRED_REPOSITORY_METHODS = {
    "list_events",
    "list_event_participants",
    "list_event_participant_roles",
    "list_work_relationships",
    "list_work_records",
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
    "AccountWorkflowService",
    "ObservationWorkflowService",
}


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
    }
    for service, methods in expected.items():
        missing = sorted(method for method in methods if not hasattr(service, method))
        if missing:
            findings.append(f"{service.__name__} is missing methods: {missing}")
    missing_repo = sorted(
        method for method in _REQUIRED_REPOSITORY_METHODS if not hasattr(PortiaRepository, method)
    )
    if missing_repo:
        findings.append(f"PortiaRepository is missing bounded reads: {missing_repo}")
    return findings


def _parity_findings() -> list[str]:
    actual = {entry.scenario_id for entry in workflow_issue22_parity()}
    required = {"P22-01", "P22-03", "G22-009", "G22-010", "G22-017"}
    missing = sorted(required - actual)
    return [f"workflow Issue #22 parity is missing: {missing}"] if missing else []


def _documentation_findings(root: Path) -> list[str]:
    required = (
        root / "docs" / "event-participant-role-and-relationship-workflows.md",
        root
        / "docs"
        / "validation"
        / "issue-40-event-participant-role-and-relationship-workflows-validation.md",
    )
    return [f"required workflow documentation is missing: {path}" for path in required if not path.is_file()]


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
    print("Portia Issue #40 workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
