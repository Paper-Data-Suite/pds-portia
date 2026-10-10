from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
PRIVACY_DOMAIN = "sensitive_data_minimization_privacy"

FORBIDDEN_NETWORK_MODULES = frozenset(
    {
        "aiohttp",
        "boto3",
        "botocore",
        "ftplib",
        "http.client",
        "httpx",
        "paramiko",
        "requests",
        "smtplib",
        "socket",
        "urllib.request",
        "urllib3",
    }
)

MARKERS: dict[str, tuple[str, ...]] = {
    "portia/views/policy.py": (
        "Issue #48 keeps the student timeline/work view derived and fail-closed.",
        '"operational_excluded"',
        '"export_excluded"',
        'manual=("content", "elicitation_context")',
        'withheld=("sender", "recipients", "attachments", "relations")',
    ),
    "portia/views/projection.py": (
        "One policy-allowed field decision; never a raw nested source object.",
        "Privacy-minimized representation traceable to one exact source.",
        "absent/withheld/unavailable item cannot expose projected fields",
        "Assembled current-frontier projection with no absent-source side channel.",
    ),
    "portia/attention/models.py": (
        "Privacy-safe opaque identity for technical attention sources.",
        "Low-density class/work context, never a student dossier.",
        "One bounded current attention fact.",
    ),
    "portia/attention_provider.py": (
        "_NOTICE_SUMMARIES[PORTIA_ATTENTION_UNAVAILABLE_NOTICE]",
        "_NOTICE_SUMMARIES[notice.code]",
        "_NOTICE_SUMMARIES[PORTIA_ATTENTION_PARTIAL_NOTICE]",
    ),
    "portia/readiness_provider.py": (
        "The requested Portia class is missing or structurally invalid.",
        "Classify one canonical Core path without following unsafe links.",
    ),
    "portia/exports/preparation.py": (
        "Local teacher reference only; this export is not a disclosure or official institutional record.",
        "Participant-specific scope does not establish recipient or disclosure authorization.",
        'artifact_path = f"portia/exports/{export_id}/artifact.html"',
        'provenance_path = f"portia/exports/{export_id}/export.json"',
    ),
    "portia/storage/generated_paths.py": (
        "Return one fixed-length opaque token for Portia-owned filesystem use.",
        "canonical identity/provenance inputs, not display labels.",
        "intentionally not embedded in the temporary leaf.",
    ),
    "schemas/v1/projections/integrity-finding.schema.json": (
        "Minimal machine-readable facts needed to explain detection.",
        "Narrative payloads, names, Statements of Disagreement, removed content, credentials, and secrets are prohibited by application validation.",
    ),
    "schemas/v1/exports/deliberate-export.schema.json": (
        "It is not a disclosure, delivery, receipt, consent record, legal authorization decision, student dossier, or behavior-domain fact.",
        "Privacy-minimized counts of projection-item dispositions.",
        "Exact withheld or unavailable source identities are intentionally not persisted here.",
    ),
    "SECURITY.md": (
        "Real student or staff data is prohibited in this repository",
        "Use synthetic data only.",
        "Local-first means Portia does not itself provide hosted storage.",
        "Do not present hashes or fingerprints as anonymization.",
    ),
}

ATTENTION_ITEM_FIELDS = ("code", "source_ref", "context", "reason_codes", "timing")
OPAQUE_ATTENTION_FIELDS = ("kind", "identifier")


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _load_audit(root: Path) -> dict[str, Any]:
    raw: object = json.loads(_read(root, "docs/audits/portia-v0.2.0-release-audit.json"))
    if not isinstance(raw, dict):
        raise ValueError("release audit JSON must be an object")
    return cast(dict[str, Any], raw)


def _domain_status(audit: dict[str, Any], domain_id: str) -> str | None:
    domains = audit.get("audit_domains")
    if not isinstance(domains, list):
        return None
    for raw_domain in domains:
        if not isinstance(raw_domain, dict):
            continue
        domain = cast(dict[str, Any], raw_domain)
        if domain.get("domain_id") == domain_id:
            status = domain.get("status")
            return status if isinstance(status, str) else None
    return None


def _obligation_status(audit: dict[str, Any], finding_id: str) -> str | None:
    obligations = audit.get("inherited_foundation_obligations")
    if not isinstance(obligations, list):
        return None
    for raw_obligation in obligations:
        if not isinstance(raw_obligation, dict):
            continue
        obligation = cast(dict[str, Any], raw_obligation)
        if obligation.get("finding_id") == finding_id:
            status = obligation.get("status")
            return status if isinstance(status, str) else None
    return None


def _missing_markers(root: Path, path: str, markers: tuple[str, ...]) -> list[str]:
    content = _read(root, path)
    return [marker for marker in markers if marker not in content]


def _dataclass_fields(source: str, class_name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    for top_level in tree.body:
        if not isinstance(top_level, ast.ClassDef) or top_level.name != class_name:
            continue
        fields: list[str] = []
        for class_item in top_level.body:
            if isinstance(class_item, ast.AnnAssign) and isinstance(class_item.target, ast.Name):
                fields.append(class_item.target.id)
        return tuple(fields)
    return ()


def _network_import_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        if node.module is None:
            return ()
        if node.module == "urllib":
            return tuple(f"urllib.{alias.name}" for alias in node.names)
        return (node.module,)
    return ()


def _is_forbidden_network_import(module_name: str) -> bool:
    return any(
        module_name == forbidden or module_name.startswith(f"{forbidden}.")
        for forbidden in FORBIDDEN_NETWORK_MODULES
    )


def _forbidden_runtime_imports(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted((root / "portia").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            violations.append(f"{relative}: cannot parse runtime source: {exc}")
            continue
        for ast_node in ast.walk(tree):
            for imported_name in _network_import_names(ast_node):
                if _is_forbidden_network_import(imported_name):
                    violations.append(
                        f"{relative}: imports network-capable module {imported_name!r}"
                    )
    return violations


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, PRIVACY_DOMAIN) != "pass":
        errors.append(f"{PRIVACY_DOMAIN} must be recorded as pass")
    if audit.get("synthetic_only_confirmation") is not True:
        errors.append("release audit must retain synthetic-only confirmation")
    if _obligation_status(audit, "PF-AUD-006") not in {
        "pending_reaudit",
        "reconciled",
    }:
        errors.append(
            "PF-AUD-006 must remain explicitly tracked across the privacy/usability handoff"
        )

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing privacy marker {marker!r}")

    try:
        attention_source = _read(root, "portia/attention/models.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read attention models: {exc}")
    else:
        item_fields = _dataclass_fields(attention_source, "PortiaAttentionItem")
        if item_fields != ATTENTION_ITEM_FIELDS:
            errors.append(f"PortiaAttentionItem must remain low-density; found fields {item_fields!r}")
        opaque_fields = _dataclass_fields(attention_source, "OpaqueAttentionSourceRef")
        if opaque_fields != OPAQUE_ATTENTION_FIELDS:
            errors.append(f"OpaqueAttentionSourceRef must remain opaque; found fields {opaque_fields!r}")

    errors.extend(_forbidden_runtime_imports(root))

    for path, markers in (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 4 — Sensitive-data minimization and privacy",
                "Domain result: **PASS**",
                "No `P54-AUD-*` defect was identified in this domain.",
                "PF-AUD-006 remains pending",
                "`urllib.parse` URI parsing remains permitted",
                "No production runtime code changed in Slice 4.",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 4 — Sensitive-data minimization and privacy",
                "Portia Issue #54 sensitive-data/privacy audit validation passed",
                "`urllib.parse` parsing is not classified as network I/O",
                "No production runtime code is changed by Slice 4.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 4 audit result",
                "No `P54-AUD-*` finding was opened for the sensitive-data-minimization / privacy domain.",
            ),
        ),
    ):
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 4 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        privacy_findings = [
            item for item in findings
            if isinstance(item, dict) and item.get("audit_domain") == PRIVACY_DOMAIN
        ]
        if privacy_findings:
            errors.append("privacy domain is recorded PASS but still has domain findings in audit JSON")
    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 sensitive-data/privacy audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 sensitive-data/privacy audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
