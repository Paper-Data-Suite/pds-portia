from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "documentation_reconciliation"
FINDING_ID = "P54-AUD-001"

REQUIRED_RELEASE_NOTE_MARKERS = (
    "# Portia v0.2.0 Release Notes",
    "Status: **release candidate; publication pending Issue #54 Phase 2 verification**",
    "Python >=3.11",
    "pds-core>=0.6.3,<0.7",
    "Core 0.6.4",
    "Core 0.6.3",
    "No sibling PDS runtime dependency",
    "No publication-producer capability",
    "teacher-local",
    "not an official institutional record",
    "does not define legal retention periods",
    "RELEASED — VERIFIED",
)

STALE_README_MARKERS = (
    "Portia is in its executable v0.2.0 implementation phase.",
    "accepted Architecture Decision Records ADR 0001 through ADR 0019",
    "ADRs 0001–0019",
    "Likely next work includes:",
    "implementing the accepted ADR 0009, ADR 0010, and ADR 0011 persistence",
    "Licensing information will be documented before an initial software release.",
)

REQUIRED_README_MARKERS = (
    "Portia is in v0.2.0 release-candidate audit and release preparation.",
    "It is not yet `RELEASED — VERIFIED`.",
    "accepted Architecture Decision Records ADR 0001 through ADR 0020",
    "ADRs 0001–0020",
    "## Deferred Beyond v0.2.0",
    "future privacy-minimized Core intervention publication",
    "future Suite-wide retention/disposition orchestration",
    "paper/import operationalization beyond the v0.2.0 digital/local runtime",
    "Portia is licensed under the MIT License.",
)

REQUIRED_DOC_INDEX_MARKERS = (
    "../RELEASE_NOTES_v0.2.0.md",
    "audits/portia-v0.2.0-release-audit.md",
    "validation/issue-54-v0.2.0-release-audit-validation.md",
    "Slice 1 through Slice 13",
)

REQUIRED_CHANGELOG_MARKERS = (
    "## Unreleased",
    "No changes yet.",
    "## 0.2.0",
    "Issue #54 release-audit evidence through documentation reconciliation",
)

REQUIRED_SECURITY_MARKERS = (
    "# Security Policy",
    "## Identity and Cross-Module Boundaries",
    "## Compliance Disclaimer",
    "not a hosted service, identity provider, compliance certification",
)

REQUIRED_AUDIT_MARKERS = (
    "## Slice 13 — Documentation reconciliation",
    "Domain result: **PASS**",
    "P54-AUD-001",
    "Classification: **MINOR**",
    "Status: **RESOLVED**",
    "Final verdict remains **PENDING**",
)

REQUIRED_FINDINGS_MARKERS = (
    "## P54-AUD-001 — Stale release-facing documentation",
    "Classification: **MINOR**",
    "Audit domain: `documentation_reconciliation`",
    "Status: **RESOLVED**",
)

REQUIRED_VALIDATION_MARKERS = (
    "## Slice 13 — Documentation reconciliation",
    "Portia Issue #54 documentation reconciliation audit validation passed",
    "P54-AUD-001 is resolved",
    "No production runtime code is changed by Slice 13.",
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
    for raw_domain in domains:
        if isinstance(raw_domain, dict) and raw_domain.get("domain_id") == domain_id:
            status = raw_domain.get("status")
            return status if isinstance(status, str) else None
    return None


def _finding(audit: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    findings = audit.get("findings")
    if not isinstance(findings, list):
        return None
    for raw in findings:
        if isinstance(raw, dict) and raw.get("finding_id") == finding_id:
            return cast(dict[str, Any], raw)
    return None


def _require_markers(
    root: Path,
    relative: str,
    markers: tuple[str, ...],
    errors: list[str],
) -> None:
    try:
        source = _read(root, relative)
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {relative}: {exc}")
        return
    for marker in markers:
        if marker not in source:
            errors.append(f"{relative}: missing documentation marker {marker!r}")


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, DOMAIN) != "pass":
        errors.append(f"{DOMAIN} must be recorded as pass")

    finding = _finding(audit, FINDING_ID)
    if finding is None:
        errors.append(f"{FINDING_ID} must be recorded")
    else:
        expected = {
            "audit_domain": DOMAIN,
            "classification": "MINOR",
            "status": "resolved",
        }
        for key, value in expected.items():
            if finding.get(key) != value:
                errors.append(
                    f"{FINDING_ID}.{key} must be {value!r}, got {finding.get(key)!r}"
                )

    counts = audit.get("finding_counts")
    if not isinstance(counts, dict) or counts.get("MINOR") != 1:
        errors.append("finding_counts must record exactly one MINOR finding")
    if audit.get("unresolved_finding_ids") != []:
        errors.append("Slice 13 must leave no unresolved Issue #54 finding IDs")

    obligations = audit.get("inherited_foundation_obligations")
    if not isinstance(obligations, list) or not obligations:
        errors.append("inherited foundation obligations are unavailable")
    else:
        if any(
            not isinstance(item, dict) or item.get("status") != "reconciled"
            for item in obligations
        ):
            errors.append("all inherited foundation obligations must remain reconciled")

    _require_markers(root, "RELEASE_NOTES_v0.2.0.md", REQUIRED_RELEASE_NOTE_MARKERS, errors)
    _require_markers(root, "README.md", REQUIRED_README_MARKERS, errors)
    _require_markers(root, "docs/README.md", REQUIRED_DOC_INDEX_MARKERS, errors)
    _require_markers(root, "CHANGELOG.md", REQUIRED_CHANGELOG_MARKERS, errors)
    _require_markers(root, "SECURITY.md", REQUIRED_SECURITY_MARKERS, errors)
    _require_markers(
        root,
        "docs/audits/portia-v0.2.0-release-audit.md",
        REQUIRED_AUDIT_MARKERS,
        errors,
    )
    _require_markers(
        root,
        "docs/audits/portia-v0.2.0-release-findings.md",
        REQUIRED_FINDINGS_MARKERS,
        errors,
    )
    _require_markers(
        root,
        "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
        REQUIRED_VALIDATION_MARKERS,
        errors,
    )

    try:
        readme = _read(root, "README.md")
    except (OSError, UnicodeError):
        readme = ""
    for marker in STALE_README_MARKERS:
        if marker in readme:
            errors.append(f"README.md retains stale release-facing marker {marker!r}")

    try:
        security = _read(root, "SECURITY.md")
    except (OSError, UnicodeError):
        security = ""
    if security.count("## Identity and Cross-Module Boundaries") != 1:
        errors.append(
            "SECURITY.md must contain exactly one Identity and Cross-Module Boundaries heading"
        )

    try:
        docs_index = _read(root, "docs/README.md")
    except (OSError, UnicodeError):
        docs_index = ""
    if "â€”" in docs_index:
        errors.append("docs/README.md retains mojibake em-dash text")

    try:
        manifest = _read(root, "MANIFEST.in")
        checker = _read(root, "scripts/check_package.py")
        release_validator = _read(root, "scripts/validate_issue54_release_audit.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot inspect release-note packaging wiring: {exc}")
    else:
        if "include RELEASE_NOTES_v0.2.0.md" not in manifest:
            errors.append("MANIFEST.in must include RELEASE_NOTES_v0.2.0.md")
        if '"RELEASE_NOTES_v0.2.0.md"' not in checker:
            errors.append("generic package checker must require release notes in sdist")
        if '"RELEASE_NOTES_v0.2.0.md"' not in release_validator:
            errors.append("Issue #54 foundation validator must require release notes")

    try:
        with (root / "pyproject.toml").open("rb") as handle:
            data = tomllib.load(handle)
        files = set(data["tool"]["mypy"]["files"])
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"cannot inspect strict mypy scope: {exc}")
    else:
        if "scripts/validate_issue54_documentation_audit.py" not in files:
            errors.append("documentation validator must be in strict mypy scope")

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 13 must not advance final release verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        errors.append("Slice 13 must not advance release publication state")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 documentation reconciliation audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 documentation reconciliation audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
