from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_ethics_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_ethics_audit", path)
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
    for raw in _audit()["audit_domains"]:
        assert isinstance(raw, dict)
        if raw["domain_id"] == domain_id:
            status = raw["status"]
            assert isinstance(status, str)
            return status
    return None


def _function_create_services(path: Path, function_name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    target = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    values: list[str] = []
    for node in ast.walk(target):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "create":
            continue
        owner = func.value
        if (
            isinstance(owner, ast.Call)
            and isinstance(owner.func, ast.Name)
        ):
            values.append(owner.func.id)
    return tuple(values)


def test_issue54_slice2_validator_accepts_ethics_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_ethics_domain_is_pass_without_premature_release_claim() -> None:
    audit = _audit()
    assert _domain_status("ethical_neutrality_epistemic_distinctions") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_account_observation_authority_remains_distinct() -> None:
    adr = (
        ROOT
        / "docs"
        / "decisions"
        / "0011-define-account-and-observation-domain-models.md"
    ).read_text(encoding="utf-8")
    assert "A human report of what the person says they observed remains an Account" in adr
    assert "Relations do not establish truth or corroboration." in adr
    assert "Observation has no canonical positive/neutral/concerning, severity, violation," in adr


def test_issue54_judgment_stages_do_not_auto_create_later_judgments() -> None:
    path = ROOT / "portia" / "menu" / "judgment.py"
    assert _function_create_services(path, "record_review_once") == ("ReviewWorkflowService",)
    assert _function_create_services(path, "record_classification_once") == (
        "ClassificationWorkflowService",
    )
    assert _function_create_services(path, "record_hypothesis_once") == (
        "HypothesisWorkflowService",
    )
    assert _function_create_services(path, "record_determination_once") == (
        "DeterminationWorkflowService",
    )


def test_issue54_response_and_communication_do_not_infer_later_states() -> None:
    menu = (ROOT / "portia" / "menu" / "response_communication.py").read_text(
        encoding="utf-8"
    )
    assert "it does not establish effectiveness or an Outcome." in menu
    assert "Participation still does not establish reading, understanding, or agreement." in menu
    assert (
        "This record does not infer delivery, reading, understanding, agreement, or support participation."
        in menu
    )


def test_issue54_support_implementation_fidelity_and_follow_up_are_separate() -> None:
    support = (ROOT / "portia" / "menu" / "support.py").read_text(encoding="utf-8")
    delivery = (ROOT / "portia" / "menu" / "support_delivery.py").read_text(
        encoding="utf-8"
    )
    follow_up = (ROOT / "portia" / "menu" / "follow_up.py").read_text(
        encoding="utf-8"
    )
    assert "A Need is a planning record. It does not establish diagnosis, eligibility," in support
    assert "A Goal describes planned future direction. It does not record progress, attainment," in support
    assert "Implementation records an actual occurrence. It does not prove Fidelity," in delivery
    assert "Fidelity records plan adherence only. It does not establish effectiveness," in delivery
    assert "Completion records the Follow-Up workflow fact only." in follow_up
    assert "It does not establish success, improvement, resolution, effectiveness, or an Outcome." in follow_up


def test_issue54_attention_contract_has_no_score_or_ranking_field() -> None:
    taxonomy = (ROOT / "portia" / "attention" / "taxonomy.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(taxonomy)
    definition = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PortiaAttentionDefinition"
    )
    fields = tuple(
        item.target.id
        for item in definition.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert fields == (
        "code",
        "label",
        "count_unit",
        "attention_class",
        "definition_order",
        "semantic_authority",
        "timing_classification",
    )
    assert "urgency, severity, risk, or a recommendation ranking." in taxonomy


def test_issue54_slice2_opens_no_ethics_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    ethics_findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "ethical_neutrality_epistemic_distinctions"
    ]
    assert ethics_findings == []
