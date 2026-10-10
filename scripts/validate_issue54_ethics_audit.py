"""Validate Issue #54 Slice 2 ethical and epistemic release-audit evidence."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
ETHICS_DOMAIN = "ethical_neutrality_epistemic_distinctions"

ADR_MARKERS: dict[str, tuple[str, ...]] = {
    "docs/decisions/0011-define-account-and-observation-domain-models.md": (
        "A human report of what the person says they observed remains an Account",
        "Relations do not establish truth or corroboration.",
        "Portia does not automatically convert source evidence, repetition, agreement,",
    ),
    "docs/decisions/0012-define-review-classification-hypothesis-and-determination-domain-models.md": (
        "Review completion does not imply a finding.",
        "Hypothesis remains explicitly tentative",
        "Determination is one bounded attributed human decision",
        "Software may not automatically classify prose, infer intent/function",
    ),
    "docs/decisions/0013-define-response-and-communication-domain-models.md": (
        "Response v1 contains no action severity score, student-risk score, culpability",
        "A completed handoff does not establish that a later Support or Intervention was",
        "It does not describe whether the action was:",
        "It does not establish delivery, reading, identity verification, understanding,",
    ),
    "docs/decisions/0014-define-support-process-support-intervention-implementation-and-fidelity-contracts.md": (
        "A Need is not a diagnosis, disability determination, behavioral-function",
        "Goal does not contain current progress, attainment, Outcome, academic Grade,",
        "Implementation never contains `successful`, `effective`, `compliant`,",
        "There is no Portia-defined universal fidelity score and no automatic conversion",
    ),
    "docs/decisions/0015-define-follow-up-outcome-reentry-and-repair-domain-models.md": (
        "completed Follow-Up",
        "≠ favorable Outcome",
        "It is not:",
        "Outcome is not a mutable progress log, raw evidence container, Fidelity record,",
    ),
}

SURFACE_MARKERS: dict[str, tuple[str, ...]] = {
    "portia/menu/judgment.py": (
        "consideration; it does not establish truth, credibility, or weight.",
        "This does not create a Classification, Hypothesis, or Determination.",
        "Hypothesis, Determination, policy violation, severity, or discipline.",
        "A Hypothesis remains provisional ",
        "authority and does not imply institutional adjudication or downstream action.",
    ),
    "portia/menu/response_communication.py": (
        "it does not establish effectiveness or an Outcome.",
        "Participation still does not establish reading, understanding, or agreement.",
        "This record does not infer delivery, reading, understanding, agreement, or support participation.",
    ),
    "portia/menu/support.py": (
        "504 plan, clinical plan, diagnosis, eligibility decision, risk label, or Outcome.",
        "A Need is a planning record. It does not establish diagnosis, eligibility,",
        "A Goal describes planned future direction. It does not record progress, attainment,",
    ),
    "portia/menu/support_delivery.py": (
        "Implementation records an actual occurrence. It does not prove Fidelity,",
        "Fidelity asks whether implementation matched the plan. It does not rate",
        "Fidelity records plan adherence only. It does not establish effectiveness,",
    ),
    "portia/menu/follow_up.py": (
        "Completion records the Follow-Up workflow fact only.",
        "It does not establish success, improvement, resolution, effectiveness, or an Outcome.",
        "Completion applies only to the exact selected Follow-Up and is not an Outcome.",
    ),
    "portia/attention/taxonomy.py": (
        "Definition order is deterministic presentation order only. It is not",
        "urgency, severity, risk, or a recommendation ranking.",
    ),
    "portia/menu/attention.py": (
        "Attention remains workflow state,",
        "not a student ranking or risk assessment.",
    ),
    "portia/workflows/responses.py": (
        "Create and resolve bounded Event-local Responses without inferring outcome.",
    ),
    "portia/workflows/support_needs.py": (
        "Author and resolve bounded Needs without diagnostic or outcome inference.",
    ),
    "portia/workflows/support_goals.py": (
        "Author and resolve bounded Goals without progress or outcome inference.",
    ),
}

JUDGMENT_CREATE_EXPECTATIONS: dict[str, str] = {
    "record_review_once": "ReviewWorkflowService",
    "record_classification_once": "ClassificationWorkflowService",
    "record_hypothesis_once": "HypothesisWorkflowService",
    "record_determination_once": "DeterminationWorkflowService",
}

ATTENTION_FIELDS = (
    "code",
    "label",
    "count_unit",
    "attention_class",
    "definition_order",
    "semantic_authority",
    "timing_classification",
)


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _load_audit(root: Path) -> dict[str, Any]:
    raw: object = json.loads(
        _read(root, "docs/audits/portia-v0.2.0-release-audit.json")
    )
    if not isinstance(raw, dict):
        raise ValueError("release audit JSON must be an object")
    return cast(dict[str, Any], raw)


def _domain_status(audit: dict[str, Any], domain_id: str) -> str | None:
    domains = audit.get("audit_domains")
    if not isinstance(domains, list):
        return None
    for raw in domains:
        if not isinstance(raw, dict):
            continue
        item = cast(dict[str, Any], raw)
        if item.get("domain_id") == domain_id:
            status = item.get("status")
            return status if isinstance(status, str) else None
    return None


def _missing_markers(root: Path, path: str, markers: tuple[str, ...]) -> list[str]:
    text = _read(root, path)
    return [marker for marker in markers if marker not in text]


def _call_owner_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    return None


def _create_service_targets(source: str, function_name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    target: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            target = node
            break
    if target is None:
        return ()

    services: list[str] = []
    for walk_node in ast.walk(target):
        if not isinstance(walk_node, ast.Call):
            continue
        func = walk_node.func
        if not isinstance(func, ast.Attribute) or func.attr != "create":
            continue
        owner = _call_owner_name(func.value)
        if owner is not None:
            services.append(owner)
    return tuple(services)


def _attention_definition_fields(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "PortiaAttentionDefinition":
            fields: list[str] = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
            return tuple(fields)
    return ()


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, ETHICS_DOMAIN) != "pass":
        errors.append(f"{ETHICS_DOMAIN} must be recorded as pass")

    for path, markers in ADR_MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing accepted-semantics marker {marker!r}")

    for path, markers in SURFACE_MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing executable-boundary marker {marker!r}")

    try:
        judgment_source = _read(root, "portia/menu/judgment.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read judgment menu: {exc}")
    else:
        for function_name, expected_service in JUDGMENT_CREATE_EXPECTATIONS.items():
            actual = _create_service_targets(judgment_source, function_name)
            if actual != (expected_service,):
                errors.append(
                    f"{function_name}: expected exactly one {expected_service}.create call; "
                    f"found {actual!r}"
                )

    try:
        attention_source = _read(root, "portia/attention/taxonomy.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read attention taxonomy: {exc}")
    else:
        fields = _attention_definition_fields(attention_source)
        if fields != ATTENTION_FIELDS:
            errors.append(
                "PortiaAttentionDefinition must remain a workflow-attention contract "
                f"without score/risk/ranking fields; found {fields!r}"
            )

    audit_doc_markers = (
        "## Slice 2 — Ethical neutrality and epistemic distinctions",
        "Domain result: **PASS**",
        "No `P54-AUD-*` defect was identified in this domain.",
        "No production runtime code changed in Slice 2.",
    )
    validation_markers = (
        "## Slice 2 — Ethical neutrality and epistemic distinctions",
        "Portia Issue #54 ethical/epistemic audit validation passed",
        "No production runtime code is changed by Slice 2.",
    )
    findings_markers = (
        "## Slice 2 audit result",
        "No `P54-AUD-*` finding was opened for the ethical-neutrality / epistemic-distinction domain.",
    )
    for path, markers in (
        ("docs/audits/portia-v0.2.0-release-audit.md", audit_doc_markers),
        ("docs/validation/issue-54-v0.2.0-release-audit-validation.md", validation_markers),
        ("docs/audits/portia-v0.2.0-release-findings.md", findings_markers),
    ):
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 2 audit marker {marker!r}")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 ethical/epistemic audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 ethical/epistemic audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
