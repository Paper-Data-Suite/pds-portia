from __future__ import annotations

import ast
import importlib.util
import json
from dataclasses import fields
from pathlib import Path
from typing import Any, cast

from portia.attention.models import OpaqueAttentionSourceRef, PortiaAttentionItem
from portia.storage.generated_paths import (
    GENERATED_PATH_TOKEN_LENGTH,
    build_generated_path_token,
)
from portia.views.policy import projection_rule

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_privacy_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_privacy_audit", path)
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


def _obligation_status(finding_id: str) -> str | None:
    for raw_obligation in _audit()["inherited_foundation_obligations"]:
        assert isinstance(raw_obligation, dict)
        if raw_obligation["finding_id"] == finding_id:
            status = raw_obligation["status"]
            assert isinstance(status, str)
            return status
    return None


def test_issue54_slice4_validator_accepts_privacy_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_privacy_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("sensitive_data_minimization_privacy") == "pass"
    assert audit["synthetic_only_confirmation"] is True
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_pf_aud_006_waits_for_workload_audit() -> None:
    assert _obligation_status("PF-AUD-006") == "pending_reaudit"


def test_issue54_student_view_policy_keeps_sensitive_fields_bounded() -> None:
    account = projection_rule("account", "2")
    communication = projection_rule("communication", "1")
    assert "content" in account.manual_review_fields
    assert "source" in account.withheld_fields
    assert "recipients" in communication.withheld_fields
    assert "attachments" in communication.withheld_fields
    assert "relations" in communication.withheld_fields


def test_issue54_attention_contract_remains_low_density() -> None:
    assert tuple(field.name for field in fields(PortiaAttentionItem)) == (
        "code", "source_ref", "context", "reason_codes", "timing"
    )
    assert tuple(field.name for field in fields(OpaqueAttentionSourceRef)) == (
        "kind", "identifier"
    )


def test_issue54_generated_path_tokens_do_not_embed_sensitive_identity_text() -> None:
    sensitive = "PRIVATE STUDENT NAME / private@example.invalid / narrative"
    token = build_generated_path_token("issue54_privacy_probe", sensitive)
    assert len(token) == GENERATED_PATH_TOKEN_LENGTH
    assert "PRIVATE" not in token
    assert "student" not in token.casefold()
    assert "example" not in token.casefold()
    assert sensitive not in token


def test_issue54_runtime_has_no_network_capable_imports() -> None:
    validator = _load_validator()
    assert validator._forbidden_runtime_imports(ROOT) == []


def test_issue54_urllib_parse_is_allowed_but_urllib_request_is_blocked() -> None:
    validator = _load_validator()
    allowed = ast.parse("from urllib.parse import urldefrag, urlsplit")
    allowed_names = validator._network_import_names(allowed.body[0])
    assert allowed_names == ("urllib.parse",)
    assert not any(
        validator._is_forbidden_network_import(name) for name in allowed_names
    )

    blocked = ast.parse("from urllib import request")
    blocked_names = validator._network_import_names(blocked.body[0])
    assert blocked_names == ("urllib.request",)
    assert any(
        validator._is_forbidden_network_import(name) for name in blocked_names
    )


def test_issue54_export_and_integrity_contracts_preserve_minimization_language() -> None:
    export_schema = (
        ROOT / "schemas" / "v1" / "exports" / "deliberate-export.schema.json"
    ).read_text(encoding="utf-8")
    integrity_schema = (
        ROOT / "schemas" / "v1" / "projections" / "integrity-finding.schema.json"
    ).read_text(encoding="utf-8")
    assert "It is not a disclosure, delivery, receipt, consent record" in export_schema
    assert "Exact withheld or unavailable source identities are intentionally not persisted here." in export_schema
    assert "Narrative payloads, names, Statements of Disagreement" in integrity_schema


def test_issue54_slice4_opens_no_privacy_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    privacy_findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "sensitive_data_minimization_privacy"
    ]
    assert privacy_findings == []
