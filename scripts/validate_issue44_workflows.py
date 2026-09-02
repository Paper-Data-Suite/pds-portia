"""Mechanically validate the Issue #44 Support planning workflow surface."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

_REQUIRED_EXPORTS = {
    "InterventionWorkflowService",
    "SupportGoalWorkflowService",
    "SupportNeedWorkflowService",
    "SupportProcessParticipantWorkflowService",
    "SupportProcessWorkflowService",
    "SupportWorkflowService",
    "intervention_reference",
    "support_goal_reference",
    "support_need_reference",
    "support_process_participant_reference",
    "support_process_reference",
    "support_reference",
}

_REQUIRED_RUNTIME = {
    "portia/workflows/intervention_lifecycle.py",
    "portia/workflows/intervention_supersession.py",
    "portia/workflows/interventions.py",
    "portia/workflows/support_goal_lifecycle.py",
    "portia/workflows/support_goal_supersession.py",
    "portia/workflows/support_goals.py",
    "portia/workflows/support_lifecycle.py",
    "portia/workflows/support_need_lifecycle.py",
    "portia/workflows/support_need_supersession.py",
    "portia/workflows/support_needs.py",
    "portia/workflows/support_process_continuation.py",
    "portia/workflows/support_process_initiation.py",
    "portia/workflows/support_process_lifecycle.py",
    "portia/workflows/support_process_participant_lifecycle.py",
    "portia/workflows/support_process_participant_supersession.py",
    "portia/workflows/support_process_participants.py",
    "portia/workflows/support_process_supersession.py",
    "portia/workflows/support_processes.py",
    "portia/workflows/support_supersession.py",
    "portia/workflows/supports.py",
    "portia/workflows/work_transition.py",
}

_REQUIRED_ACCEPTANCE = {
    "tests/test_workflow_issue18_planning_runtime_parity_guard.py",
    "tests/test_workflow_issue22_support_planning_runtime_parity.py",
    "tests/test_workflow_issue44_final_runtime_acceptance.py",
    "tests/test_workflow_support_process_continuation.py",
    "tests/test_workflow_support_process_evidence_integration.py",
}
_REQUIRED_CLOSEOUT = {
    "scripts/check_issue44_package.py",
    "scripts/smoke_test_issue44_wheel.py",
    "scripts/validate_repository.py",
    "tests/test_issue44_repository_qualification.py",
}

_SERVICE_FILES = {
    "SupportProcessWorkflowService": "portia/workflows/support_processes.py",
    "SupportProcessParticipantWorkflowService": (
        "portia/workflows/support_process_participants.py"
    ),
    "SupportNeedWorkflowService": "portia/workflows/support_needs.py",
    "SupportGoalWorkflowService": "portia/workflows/support_goals.py",
    "SupportWorkflowService": "portia/workflows/supports.py",
    "InterventionWorkflowService": "portia/workflows/interventions.py",
}

_REQUIRED_SOURCE_TOKENS = {
    "SupportProcessWorkflowService": {
        "def create(",
        "def require_current_use(",
        "def correct(",
        "workflow_state",
    },
    "SupportProcessParticipantWorkflowService": {
        "def create(",
        "def require_current_use(",
        "def correct(",
        "list_participants = list",
    },
    "SupportNeedWorkflowService": {
        "def create(",
        "def require_current_use(",
        "def correct(",
        "list_support_needs",
    },
    "SupportGoalWorkflowService": {
        "def create(",
        "def require_current_use(",
        "def correct(",
        "list_support_goals",
    },
    "SupportWorkflowService": {
        "def create(",
        "def require_current_use(",
        "def correct(",
        "def adapt(",
        "plan_state",
        "list_supports",
    },
    "InterventionWorkflowService": {
        "def create(",
        "def require_current_use(",
        "def correct(",
        "def adapt(",
        "plan_state",
        "list_interventions",
    },
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _exports(path: Path) -> set[str]:
    for node in _tree(path).body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, (ast.List, ast.Tuple)):
            return {
                item.value
                for item in node.value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
    return set()


def _class_methods(path: Path, class_name: str) -> set[str]:
    for node in _tree(path).body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    return set()


def findings(root: Path) -> list[str]:
    errors: list[str] = []

    for relative in sorted(
        _REQUIRED_RUNTIME | _REQUIRED_ACCEPTANCE | _REQUIRED_CLOSEOUT
    ):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #44 file: {relative}")

    init_path = root / "portia/workflows/__init__.py"
    if not init_path.is_file():
        errors.append("missing public workflow package: portia/workflows/__init__.py")
    else:
        missing = sorted(_REQUIRED_EXPORTS - _exports(init_path))
        if missing:
            errors.append(f"missing Issue #44 public exports: {missing}")

    for service, relative in _SERVICE_FILES.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        methods = _class_methods(path, service)
        if not methods:
            errors.append(f"{relative} is missing class {service}")
            continue
        amendment = {name for name in methods if "amend" in name.lower()}
        if amendment:
            errors.append(f"{service} must not expose v1 Amendment: {sorted(amendment)}")
        for token in sorted(_REQUIRED_SOURCE_TOKENS[service]):
            if token not in text:
                errors.append(f"{service} missing required workflow surface token: {token}")

    docs = root / "docs/support-process-support-intervention-workflows.md"
    validation = (
        root
        / "docs"
        / "validation"
        / "issue-44-support-process-support-intervention-workflows-validation.md"
    )
    readme = root / "README.md"
    response_doc = root / "docs/response-and-communication-workflows.md"

    required_docs = {
        docs: (
            "planned != implemented",
            "SupportProcessWorkflowService",
            "InterventionWorkflowService",
            "53 frozen valid planning scenarios",
            "82 schema-valid/application-invalid planning scenarios",
            "Issue #45",
            "Issue #46",
            "Support-Process-owned `communication@1`",
        ),
        validation: (
            "135",
            "P22-08",
            "P22-11",
            "active-recurring-assigned",
            "cross-class",
            "validate_issue44_workflows.py",
            "Slice 15b observed distribution qualification",
            "Portia Issue #44 repository qualification passed",
        ),
        readme: (
            "### Issue #44 current implementation",
            "SupportProcessWorkflowService",
            "InterventionWorkflowService",
            "Support-Process-owned Communication",
        ),
        response_doc: (
            "Issue #44 now supplies",
            "Support Process Communication",
        ),
    }
    for path, phrases in required_docs.items():
        if not path.is_file():
            errors.append(f"missing Issue #44 documentation: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                errors.append(
                    f"{path.relative_to(root)} missing required phrase: {phrase}"
                )

    if response_doc.is_file():
        text = response_doc.read_text(encoding="utf-8")
        stale = (
            "new active/current Support Process Communication fails closed until "
            "Issue #44"
        )
        if stale in text:
            errors.append(
                "Issue #43 documentation still contains the temporary "
                "Support Process Communication deferral"
            )

    repository_validator = root / "scripts/validate_repository.py"
    if repository_validator.is_file():
        repository_text = repository_validator.read_text(encoding="utf-8")
        for phrase in (
            "scripts/validate_issue44_workflows.py",
            "scripts/check_issue44_package.py",
            "scripts/smoke_test_issue44_wheel.py",
            "Portia Issue #44 repository qualification passed",
        ):
            if phrase not in repository_text:
                errors.append(
                    "scripts/validate_repository.py missing Issue #44 closeout step: "
                    f"{phrase}"
                )

    ci = root / ".github/workflows/ci.yml"
    if ci.is_file():
        ci_text = ci.read_text(encoding="utf-8")
        if "Run complete repository qualification" not in ci_text:
            errors.append("CI is missing durable repository qualification label")
        if "Run complete Issue 39 qualification" in ci_text:
            errors.append("CI retains stale issue-specific qualification label")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--root", type=Path, default=default_root)
    args = parser.parse_args()
    errors = findings(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Portia Issue #44 workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
