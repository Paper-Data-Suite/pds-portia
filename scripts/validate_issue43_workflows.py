"""Mechanically validate the Issue #43 Response/Communication workflow surface."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

_REQUIRED_EXPORTS = {
    "CommunicationWorkflowService",
    "ModuleCommunicationAttachmentAuthority",
    "ResponseWorkflowService",
    "communication_reference",
    "response_reference",
}
_REQUIRED_RESPONSE_METHODS = {
    "correct",
    "create",
    "list_responses",
    "require_current_use",
    "transition_lifecycle",
}
_REQUIRED_COMMUNICATION_METHODS = {
    "correct",
    "create",
    "list_communications",
    "require_current_use",
    "transition_lifecycle",
}
_REQUIRED_RUNTIME = {
    "portia/workflows/action_common.py",
    "portia/workflows/action_transition.py",
    "portia/workflows/communication_attachments.py",
    "portia/workflows/communication_common.py",
    "portia/workflows/communication_lifecycle.py",
    "portia/workflows/communication_relations.py",
    "portia/workflows/communication_supersession.py",
    "portia/workflows/communications.py",
    "portia/workflows/response_common.py",
    "portia/workflows/response_lifecycle.py",
    "portia/workflows/response_supersession.py",
    "portia/workflows/responses.py",
}
_REQUIRED_PARITY_TESTS = {
    "tests/test_workflow_issue17_runtime_parity.py",
    "tests/test_workflow_issue22_p22_07_runtime_parity.py",
}
_REQUIRED_CLOSEOUT = {
    "scripts/check_issue43_package.py",
    "scripts/smoke_test_issue43_wheel.py",
    "scripts/validate_repository.py",
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _exports(path: Path) -> set[str]:
    for node in _tree(path).body:
        if not isinstance(node, ast.Assign):
            continue
        is_all = any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
        if not is_all:
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
        _REQUIRED_RUNTIME | _REQUIRED_PARITY_TESTS | _REQUIRED_CLOSEOUT
    ):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #43 file: {relative}")

    init_path = root / "portia/workflows/__init__.py"
    if not init_path.is_file():
        errors.append("missing public workflow package: portia/workflows/__init__.py")
    else:
        missing = sorted(_REQUIRED_EXPORTS - _exports(init_path))
        if missing:
            errors.append(f"missing Issue #43 public exports: {missing}")

    response_path = root / "portia/workflows/responses.py"
    if response_path.is_file():
        methods = _class_methods(response_path, "ResponseWorkflowService")
        missing = sorted(_REQUIRED_RESPONSE_METHODS - methods)
        if missing:
            errors.append(f"ResponseWorkflowService missing methods: {missing}")
        amendment_methods = {name for name in methods if "amend" in name.lower()}
        if amendment_methods:
            errors.append("ResponseWorkflowService must not expose v1 Amendment")
        tree = _tree(response_path)
        has_reference = any(
            isinstance(node, ast.FunctionDef) and node.name == "response_reference"
            for node in tree.body
        )
        if not has_reference:
            errors.append("responses.py is missing response_reference")

    communication_path = root / "portia/workflows/communications.py"
    if communication_path.is_file():
        methods = _class_methods(communication_path, "CommunicationWorkflowService")
        missing = sorted(_REQUIRED_COMMUNICATION_METHODS - methods)
        if missing:
            errors.append(f"CommunicationWorkflowService missing methods: {missing}")
        amendment_methods = {name for name in methods if "amend" in name.lower()}
        if amendment_methods:
            errors.append("CommunicationWorkflowService must not expose v1 Amendment")
        tree = _tree(communication_path)
        has_reference = any(
            isinstance(node, ast.FunctionDef)
            and node.name == "communication_reference"
            for node in tree.body
        )
        if not has_reference:
            errors.append("communications.py is missing communication_reference")

    docs = root / "docs/response-and-communication-workflows.md"
    validation = (
        root
        / "docs"
        / "validation"
        / "issue-43-response-and-communication-workflows-validation.md"
    )
    readme = root / "README.md"
    required_docs = {
        docs: (
            "Communication != mutable message thread",
            "Response != evidence",
            "ModuleCommunicationAttachmentAuthority",
            "Issue #44",
            "later communication attempt is not a correction",
        ),
        validation: (
            "76",
            "P22-07",
            "233",
            "244",
            "validate_issue43_workflows.py",
            "validate_repository.py",
            "installed-wheel",
        ),
        readme: (
            "### Issue #43 current implementation",
            "ResponseWorkflowService",
            "CommunicationWorkflowService",
        ),
    }
    for path, phrases in required_docs.items():
        if not path.is_file():
            errors.append(f"missing Issue #43 documentation: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                errors.append(
                    f"{path.relative_to(root)} missing required phrase: {phrase}"
                )

    repository_validator = root / "scripts/validate_repository.py"
    if repository_validator.is_file():
        repository_text = repository_validator.read_text(encoding="utf-8")
        for phrase in (
            "scripts/validate_issue43_workflows.py",
            "scripts/check_issue43_package.py",
            "scripts/smoke_test_issue43_wheel.py",
            "Portia Issue #43 repository qualification passed",
        ):
            if phrase not in repository_text:
                errors.append(
                    "scripts/validate_repository.py missing Issue #43 closeout step: "
                    f"{phrase}"
                )
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
    print("Portia Issue #43 workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
