from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_DOMAIN = "teacher_local_authority"

ADR_MARKERS: dict[str, tuple[str, ...]] = {
    "docs/decisions/0010-define-actor-directory-domain-model-and-lifecycle.md": (
        "A teacher-recorded parent, guardian, counselor, administrator, or support\nrelationship does not independently prove legal or institutional authority.",
        "Roster-student and Actor identity authorities remain distinct.",
    ),
    "docs/decisions/0012-define-review-classification-hypothesis-and-determination-domain-models.md": (
        "### 8. Teacher-local and recorded-institutional authority are distinct",
        "It does not mean PDS authenticated the person or proved the authority legally sufficient.",
        "Actor title/category, organization, contact information, local-operator status, or recorder identity never confer authority.",
        "A source reference does not prove applicability or correct application.",
    ),
    "docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md": (
        "Recipient entitlement | does not decide | does not decide | owns authoritative decision | consumes",
        "Retention durations | does not own | does not own | owns | consumes",
        "Legal/preservation holds | consumes authoritative input | does not adjudicate | owns | consumes",
        "Destruction approval | does not create legal authority | does not create legal authority | owns | consumes",
        "Rejected because audience/purpose does not establish requester identity,",
        "Rejected because Portia cannot authoritatively establish the legal/institutional",
    ),
}

RUNTIME_MARKERS: dict[str, tuple[str, ...]] = {
    "portia/workflows/determinations.py": (
        "teacher-local Determination requires local-operator decision-maker",
        "unsupported Determination authority context",
        "recorded-institutional Determination requires school-staff ",
        "institutional decision-maker; authority provenance remains separate.",
    ),
    "portia/workflows/response_common.py": (
        "teacher-local consequence requires an eligible human provider",
        "recorded-institutional consequence requires an identified ",
        "recorded-institutional consequence requires Determination context",
    ),
    "portia/menu/judgment.py": (
        "This is provenance and represented-human attribution, not authentication.",
        "authority and does not imply institutional adjudication or downstream action.",
        '"Authority: Teacher-local review"',
    ),
    "portia/exports/preparation.py": (
        "Local teacher reference only; this export is not a disclosure or official institutional record.",
        "Participant-specific scope does not establish recipient or disclosure authorization.",
    ),
    "SECURITY.md": (
        "It is not a hosted service, identity provider, compliance certification, student-information system, or substitute for an institution's approved safeguarding, records-management, incident-response, or legal processes.",
        "This project does not itself establish compliance with FERPA, COPPA, GDPR, HIPAA, state student-privacy laws, records-retention rules, accessibility requirements, collective agreements, or institutional policy.",
    ),
}

EXPECTED_MODULE_PROFILE_KEYWORDS = (
    "module_id",
    "supported_core_operations_contract_versions",
    "readiness_provider",
    "attention_provider",
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


def _foundation_statuses(audit: dict[str, Any]) -> dict[str, str]:
    raw_items = audit.get("inherited_foundation_obligations")
    if not isinstance(raw_items, list):
        return {}
    result: dict[str, str] = {}
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item = cast(dict[str, Any], raw)
        finding_id = item.get("finding_id")
        status = item.get("status")
        if isinstance(finding_id, str) and isinstance(status, str):
            result[finding_id] = status
    return result


def _missing_markers(root: Path, path: str, markers: tuple[str, ...]) -> list[str]:
    source = _read(root, path)
    return [marker for marker in markers if marker not in source]


def _module_profile_keywords(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    for walk_node in ast.walk(tree):
        if not isinstance(walk_node, ast.Call):
            continue
        func = walk_node.func
        if not isinstance(func, ast.Name) or func.id != "ModuleOperationsProfile":
            continue
        return tuple(
            keyword.arg for keyword in walk_node.keywords if keyword.arg is not None
        )
    return ()


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, AUTHORITY_DOMAIN) != "pass":
        errors.append(f"{AUTHORITY_DOMAIN} must be recorded as pass")

    expected_foundation = {
        "PF-AUD-005": "pending_reaudit",
        "PF-AUD-006": "pending_reaudit",
        "PF-AUD-007": "pending_reaudit",
        "PF-AUD-008": "reconciled",
        "PF-AUD-009": "pending_reaudit",
        "PF-AUD-010": "pending_reaudit",
        "PF-AUD-011": "pending_reaudit",
        "PF-AUD-012": "reconciled",
    }
    actual_foundation = _foundation_statuses(audit)
    if actual_foundation != expected_foundation:
        errors.append(
            "Slice 3 foundation re-audit dispositions drifted: "
            f"expected={expected_foundation!r}, actual={actual_foundation!r}"
        )

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 3 must not advance the final release verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        errors.append("Slice 3 must not advance release publication state")

    for path, markers in ADR_MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing accepted-authority marker {marker!r}")

    for path, markers in RUNTIME_MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing authority-boundary marker {marker!r}")

    try:
        operations_source = _read(root, "portia/pds_operations.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read Portia module-operations profile: {exc}")
    else:
        keywords = _module_profile_keywords(operations_source)
        if keywords != EXPECTED_MODULE_PROFILE_KEYWORDS:
            errors.append(
                "Portia module-operations profile must remain bounded to discovery/readiness/attention; "
                f"found keyword surface {keywords!r}"
            )

    findings = audit.get("findings")
    if isinstance(findings, list):
        authority_findings = [
            finding
            for finding in findings
            if isinstance(finding, dict)
            and finding.get("audit_domain") == AUTHORITY_DOMAIN
        ]
        if authority_findings:
            errors.append(
                "Slice 3 records no teacher-local-authority defect; authority findings must remain empty"
            )
    else:
        errors.append("release audit findings must be a list")

    doc_checks = {
        "docs/audits/portia-v0.2.0-release-audit.md": (
            "## Slice 3 — Teacher-local authority and external authority boundaries",
            "Domain result: **PASS**",
            "PF-AUD-008 and PF-AUD-012 are reconciled by this slice.",
            "No `P54-AUD-*` defect was identified in this domain.",
            "No production runtime code changed in Slice 3.",
        ),
        "docs/audits/portia-v0.2.0-release-findings.md": (
            "## Slice 3 audit result",
            "No `P54-AUD-*` finding was opened for the teacher-local-authority domain.",
            "PF-AUD-008",
            "PF-AUD-012",
        ),
        "docs/validation/issue-54-v0.2.0-release-audit-validation.md": (
            "## Slice 3 — Teacher-local authority and external authority boundaries",
            "Portia Issue #54 teacher-local authority audit validation passed",
            "No production runtime code is changed by Slice 3.",
        ),
    }
    for path, markers in doc_checks.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 3 audit marker {marker!r}")

    try:
        pyproject = _read(root, "pyproject.toml")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read pyproject.toml: {exc}")
    else:
        if '"scripts/validate_issue54_authority_audit.py"' not in pyproject:
            errors.append("authority audit validator must remain in strict mypy scope")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 teacher-local authority audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 teacher-local authority audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
