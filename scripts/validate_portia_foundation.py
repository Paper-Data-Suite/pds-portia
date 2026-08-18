#!/usr/bin/env python3
"""Offline validator for the Portia Issue #23 foundation audit."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ALLOWED_CLASSIFICATIONS = {
    "milestone_blocker",
    "implementation_concern",
    "future_enhancement",
    "institutional_policy_dependency",
    "deliberately_out_of_scope",
}

ALLOWED_DISPOSITIONS = {
    "fixed_in_audit",
    "deferred_with_issue",
    "accepted_policy_dependency",
    "accepted_out_of_scope",
    "not_a_defect",
    "superseded",
}

ALLOWED_ADR_DISPOSITIONS = {
    "accepted",
    "accepted_with_nonblocking_implementation_concern",
    "superseded",
    "deprecated",
    "rejected",
    "requires_new_decision",
}

REQUIRED_AUDIT_FILES = (
    "docs/audits/README.md",
    "docs/audits/portia-foundation-audit.md",
    "docs/audits/portia-foundation-findings.md",
    "docs/audits/portia-foundation-traceability.md",
    "docs/audits/portia-foundation-audit.json",
    "docs/decisions/README.md",
    "docs/validation/issue-23-portia-foundation-validation.md",
    "scripts/validate_portia_foundation.py",
    "tests/schema_validation/test_issue_23_foundation_audit.py",
)

REQUIRED_AUDIT_HEADINGS = {
    "docs/audits/portia-foundation-audit.md": (
        "# Portia Foundation Architecture Audit",
        "## Scope",
        "## Audit method",
        "## Evidence hierarchy",
        "## ADR dispositions",
        "## Domain conclusions",
        "## Findings summary",
        "## Institutional-policy dependencies",
        "## Deliberately out of scope",
        "## Downstream implementation constraints",
        "## Exit-condition evaluation",
        "## Validation status",
        "## Final verdict",
    ),
    "docs/audits/portia-foundation-findings.md": (
        "# Portia Foundation Audit Findings",
        "## Summary",
    ),
    "docs/audits/portia-foundation-traceability.md": (
        "# Portia Foundation Traceability",
        "## Foundation issue traceability",
        "## ADR-to-evidence traceability",
        "## Foundation exit-condition traceability",
        "## Findings-to-exit traceability",
    ),
}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FINDING_RE = re.compile(r"^PF-AUD-\d{3}$")
ADR_RE = re.compile(r"^(\d{4})-.*\.md$")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)

ISSUE_22_TEXT_SUFFIXES = {
    ".json",
    ".txt",
    ".csv",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
}

REQUIRED_LF_ATTRIBUTE = "* text=auto eol=lf"


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_safe_repo_relative(value: str) -> bool:
    p = Path(value)
    if p.is_absolute():
        return False
    if ".." in p.parts:
        return False
    if value.startswith(("/", "\\")):
        return False
    return True


def _check_markdown_links(root: Path, relpath: str, errors: list[str]) -> None:
    path = root / relpath
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if len(FENCE_RE.findall(text)) % 2:
        errors.append(f"{relpath}: unbalanced triple-backtick fences")
    for target in MARKDOWN_LINK_RE.findall(text):
        target = target.strip()
        if (
            not target
            or target.startswith("#")
            or target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("mailto:")
        ):
            continue
        target_path = target.split("#", 1)[0]
        if not target_path:
            continue
        if not is_safe_repo_relative(target_path):
            errors.append(f"{relpath}: unsafe Markdown link target {target!r}")
            continue
        resolved = (path.parent / target_path).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{relpath}: Markdown link escapes repository: {target!r}")
            continue
        if not resolved.exists():
            errors.append(f"{relpath}: broken repository-relative Markdown link {target!r}")


def _catalog_contracts(catalog: Any) -> dict[str, Any]:
    if not isinstance(catalog, dict):
        return {}
    contracts = catalog.get("contracts")
    return contracts if isinstance(contracts, dict) else {}



def _check_exact_byte_checkout_policy(root: Path, errors: list[str]) -> None:
    attributes_path = root / ".gitattributes"
    if not attributes_path.is_file():
        errors.append("missing repository line-ending policy: .gitattributes")
    else:
        try:
            attributes_text = attributes_path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"cannot read .gitattributes: {exc}")
        else:
            policy_lines = {
                line.strip()
                for line in attributes_text.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
            if REQUIRED_LF_ATTRIBUTE not in policy_lines:
                errors.append(
                    "repository line-ending policy must include "
                    f"{REQUIRED_LF_ATTRIBUTE!r} for exact-byte fixtures"
                )

    issue22_root = root / "tests" / "fixtures" / "issue_22"
    if not issue22_root.is_dir():
        return

    crlf_paths: list[str] = []
    for path in sorted(issue22_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ISSUE_22_TEXT_SUFFIXES:
            continue
        try:
            payload = path.read_bytes()
        except OSError as exc:
            errors.append(f"cannot read Issue #22 fixture {path}: {exc}")
            continue
        if b"\r\n" in payload:
            crlf_paths.append(path.relative_to(root).as_posix())

    if crlf_paths:
        preview = ", ".join(crlf_paths[:8])
        suffix = "" if len(crlf_paths) <= 8 else f" (+{len(crlf_paths) - 8} more)"
        errors.append(
            "Issue #22 exact-byte text fixtures contain CRLF working-tree bytes; "
            f"normalize to LF: {preview}{suffix}"
        )

def validate_repo(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    _check_exact_byte_checkout_policy(root, errors)

    for relpath in REQUIRED_AUDIT_FILES:
        if not (root / relpath).is_file():
            errors.append(f"missing required audit file: {relpath}")

    audit_path = root / "docs/audits/portia-foundation-audit.json"
    if not audit_path.is_file():
        return errors

    try:
        audit = load_json(audit_path)
    except Exception as exc:  # noqa: BLE001 - validator reports parse failure
        errors.append(f"cannot parse audit JSON: {exc}")
        return errors

    required_fields = (
        "audit_record_kind",
        "audit_record_version",
        "audit_issue",
        "umbrella_issue",
        "audit_date",
        "starting_portia_commit",
        "final_audited_portia_commit",
        "reviewed_repository_baselines",
        "adr_dispositions",
        "finding_counts",
        "findings",
        "unresolved_finding_ids",
        "exit_condition_results",
        "schema_catalog_coverage",
        "representative_corpus_result",
        "complete_validation_result",
        "final_verdict",
        "synthetic_data_confirmation",
        "sibling_repository_modification_confirmation",
    )
    for field in required_fields:
        if field not in audit:
            errors.append(f"audit JSON missing required field: {field}")

    if audit.get("audit_record_kind") != "pds-portia.foundation-architecture-audit":
        errors.append("audit_record_kind must be pds-portia.foundation-architecture-audit")
    if audit.get("audit_record_version") != "1":
        errors.append("audit_record_version must be '1'")
    if audit.get("audit_issue") != 23:
        errors.append("audit_issue must be 23")
    if audit.get("umbrella_issue") != 10:
        errors.append("umbrella_issue must be 10")

    start_sha = audit.get("starting_portia_commit")
    if not isinstance(start_sha, str) or not SHA_RE.fullmatch(start_sha):
        errors.append("starting_portia_commit must be a 40-character lowercase hex SHA")

    final_sha = audit.get("final_audited_portia_commit")
    verdict = audit.get("final_verdict")
    if verdict not in {"ready_for_implementation", "not_ready"}:
        errors.append("final_verdict must be ready_for_implementation or not_ready")
    if final_sha is not None and (not isinstance(final_sha, str) or not SHA_RE.fullmatch(final_sha)):
        errors.append("final_audited_portia_commit must be null or a 40-character lowercase hex SHA")
    if verdict == "ready_for_implementation" and not isinstance(final_sha, str):
        errors.append("ready_for_implementation requires final_audited_portia_commit")

    baselines = audit.get("reviewed_repository_baselines")
    if not isinstance(baselines, list) or not baselines:
        errors.append("reviewed_repository_baselines must be a non-empty list")
    else:
        seen_repos: set[str] = set()
        for item in baselines:
            if not isinstance(item, dict):
                errors.append("reviewed_repository_baselines entries must be objects")
                continue
            repo = item.get("repository")
            sha = item.get("commit")
            if not isinstance(repo, str) or not repo:
                errors.append("reviewed repository baseline missing repository")
            elif repo in seen_repos:
                errors.append(f"duplicate reviewed repository baseline: {repo}")
            else:
                seen_repos.add(repo)
            if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
                errors.append(f"reviewed repository {repo!r} has malformed commit SHA")
        if "pds-portia" not in seen_repos or "pds-core" not in seen_repos:
            errors.append("reviewed baselines must include pds-portia and pds-core")

    historical = audit.get("historical_issue_22_baseline")
    if not isinstance(historical, dict):
        errors.append("historical_issue_22_baseline must be a separate object")
    elif historical.get("portia_commit") != start_sha:
        errors.append("historical Issue #22 baseline must bind the starting Portia commit")

    findings = audit.get("findings")
    finding_ids: list[str] = []
    unresolved_actual: list[str] = []
    if not isinstance(findings, list):
        errors.append("findings must be a list")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            errors.append("finding entries must be objects")
            continue
        for field in (
            "finding_id",
            "audit_domain",
            "classification",
            "summary",
            "exact_evidence",
            "affected_files_or_contracts",
            "expected_architecture",
            "observed_problem",
            "risk_or_consequence",
            "required_disposition",
            "resolution",
            "validation_evidence",
            "follow_up_issue_if_any",
            "status",
            "disposition",
        ):
            if field not in finding:
                errors.append(f"finding missing required field {field!r}: {finding.get('finding_id')!r}")
        finding_id = finding.get("finding_id")
        if not isinstance(finding_id, str) or not FINDING_RE.fullmatch(finding_id):
            errors.append(f"invalid finding_id: {finding_id!r}")
        else:
            finding_ids.append(finding_id)
        classification = finding.get("classification")
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"{finding_id}: invalid classification {classification!r}")
        disposition = finding.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            errors.append(f"{finding_id}: invalid disposition {disposition!r}")
        status = finding.get("status")
        if status not in {"open", "resolved", "accepted"}:
            errors.append(f"{finding_id}: invalid status {status!r}")
        if status == "open" and isinstance(finding_id, str):
            unresolved_actual.append(finding_id)
        affected = finding.get("affected_files_or_contracts")
        if isinstance(affected, list):
            for value in affected:
                if isinstance(value, str) and ("/" in value or value.endswith((".md", ".json", ".py"))):
                    if value.startswith("#"):
                        continue
                    if not is_safe_repo_relative(value):
                        errors.append(f"{finding_id}: unsafe affected path {value!r}")

    if len(finding_ids) != len(set(finding_ids)):
        errors.append("duplicate finding IDs")

    declared_counts = audit.get("finding_counts")
    if not isinstance(declared_counts, dict):
        errors.append("finding_counts must be an object")
    else:
        actual_counts = {classification: 0 for classification in ALLOWED_CLASSIFICATIONS}
        for finding in findings:
            if isinstance(finding, dict) and finding.get("classification") in actual_counts:
                actual_counts[finding["classification"]] += 1
        if declared_counts != actual_counts:
            errors.append(
                "finding_counts does not match findings; "
                f"declared={declared_counts}, actual={actual_counts}"
            )

    unresolved_declared = audit.get("unresolved_finding_ids")
    if not isinstance(unresolved_declared, list):
        errors.append("unresolved_finding_ids must be a list")
    else:
        if sorted(unresolved_declared) != sorted(unresolved_actual):
            errors.append("unresolved_finding_ids does not match finding status=open entries")

    unresolved_blockers = [
        f.get("finding_id")
        for f in findings
        if isinstance(f, dict)
        and f.get("classification") == "milestone_blocker"
        and f.get("status") == "open"
    ]

    approval_path = root / "docs/audits/portia-foundation-approval.json"
    approval_exists = approval_path.is_file()
    if verdict == "ready_for_implementation":
        if unresolved_blockers:
            errors.append(
                "ready_for_implementation cannot have unresolved milestone blockers: "
                + ", ".join(str(x) for x in unresolved_blockers)
            )
        if not approval_exists:
            errors.append("ready_for_implementation requires docs/audits/portia-foundation-approval.json")
    elif verdict == "not_ready" and approval_exists:
        try:
            approval = load_json(approval_path)
        except Exception:
            approval = {}
        if approval.get("verdict") == "ready_for_implementation":
            errors.append("not_ready audit cannot coexist with a ready foundation approval record")

    adr_entries = audit.get("adr_dispositions")
    adr_ids: set[str] = set()
    if not isinstance(adr_entries, list):
        errors.append("adr_dispositions must be a list")
        adr_entries = []
    for item in adr_entries:
        if not isinstance(item, dict):
            errors.append("adr disposition entry must be an object")
            continue
        adr = item.get("adr")
        path = item.get("path")
        disposition = item.get("audit_disposition")
        if not isinstance(adr, str) or not re.fullmatch(r"\d{4}", adr):
            errors.append(f"invalid ADR id in audit disposition: {adr!r}")
        else:
            adr_ids.add(adr)
        if disposition not in ALLOWED_ADR_DISPOSITIONS:
            errors.append(f"ADR {adr}: invalid audit disposition {disposition!r}")
        if not isinstance(path, str) or not is_safe_repo_relative(path):
            errors.append(f"ADR {adr}: invalid path {path!r}")
        elif not (root / path).is_file():
            errors.append(f"ADR {adr}: path does not exist: {path}")

    actual_adr_files = sorted(
        p for p in (root / "docs/decisions").glob("[0-9][0-9][0-9][0-9]-*.md")
        if p.is_file()
    )
    actual_adr_ids = {p.name[:4] for p in actual_adr_files}
    required_adr_ids = {f"{n:04d}" for n in range(1, 18)}
    missing_required_adr_ids = required_adr_ids - actual_adr_ids
    if missing_required_adr_ids:
        errors.append(
            "repository is missing foundation ADRs required by Issue #23: "
            f"{sorted(missing_required_adr_ids)}"
        )
    if adr_ids != required_adr_ids:
        errors.append(f"audit ADR dispositions incomplete; found {sorted(adr_ids)}")

    adr_index = root / "docs/decisions/README.md"
    if adr_index.is_file():
        index_text = adr_index.read_text(encoding="utf-8")
        for adr_file in actual_adr_files:
            if adr_file.name[:4] in required_adr_ids and adr_file.name not in index_text:
                errors.append(f"ADR index does not reference {adr_file.name}")

    for relpath, headings in REQUIRED_AUDIT_HEADINGS.items():
        path = root / relpath
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for heading in headings:
            if heading not in text:
                errors.append(f"{relpath}: missing required heading {heading!r}")

    trace_path = root / "docs/audits/portia-foundation-traceability.md"
    if trace_path.is_file():
        trace_text = trace_path.read_text(encoding="utf-8")
        for issue in range(10, 23):
            if f"| #{issue} |" not in trace_text:
                errors.append(f"traceability missing issue #{issue}")
        exit_results = audit.get("exit_condition_results")
        if not isinstance(exit_results, list) or not exit_results:
            errors.append("exit_condition_results must be a non-empty list")
        else:
            exit_ids: list[str] = []
            for entry in exit_results:
                if not isinstance(entry, dict):
                    errors.append("exit condition entry must be an object")
                    continue
                exit_id = entry.get("id")
                if not isinstance(exit_id, str) or not re.fullmatch(r"EC-\d{2}", exit_id):
                    errors.append(f"invalid exit condition id: {exit_id!r}")
                    continue
                exit_ids.append(exit_id)
                if f"| {exit_id} |" not in trace_text:
                    errors.append(f"traceability missing exit condition {exit_id}")
            if len(exit_ids) != len(set(exit_ids)):
                errors.append("duplicate exit condition IDs")

    corpus_path = root / "tests/fixtures/issue_22/corpus.json"
    if not corpus_path.is_file():
        errors.append("missing Issue #22 corpus descriptor")
    else:
        try:
            corpus = load_json(corpus_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"cannot parse Issue #22 corpus descriptor: {exc}")
        else:
            scenarios = corpus.get("scenarios")
            if not isinstance(scenarios, list):
                errors.append("Issue #22 corpus scenarios must be a list")
            else:
                positive = [x for x in scenarios if isinstance(x, dict) and x.get("scenario_kind") == "positive"]
                invalid = [x for x in scenarios if isinstance(x, dict) and x.get("scenario_kind") == "graph_invalid"]
                ids = [x.get("scenario_id") for x in scenarios if isinstance(x, dict)]
                if len(ids) != len(set(ids)):
                    errors.append("Issue #22 corpus has duplicate scenario IDs")
                if len(positive) != 15:
                    errors.append(f"Issue #22 corpus must contain 15 positive scenarios, found {len(positive)}")
                if len(invalid) != 37:
                    errors.append(f"Issue #22 corpus must contain 37 graph-invalid scenarios, found {len(invalid)}")
                if corpus.get("planned_positive_scenarios") != []:
                    errors.append("Issue #22 corpus still has planned positive scenarios")
                if corpus.get("planned_graph_invalid_scenarios") != []:
                    errors.append("Issue #22 corpus still has planned graph-invalid scenarios")
                if corpus.get("synthetic") is not True:
                    errors.append("Issue #22 corpus must declare synthetic=true")

    catalog_path = root / "schemas/schema-catalog.json"
    coverage_path = root / "tests/fixtures/issue_22/contract-coverage.json"
    if not catalog_path.is_file():
        errors.append("missing schemas/schema-catalog.json")
    if not coverage_path.is_file():
        errors.append("missing tests/fixtures/issue_22/contract-coverage.json")
    if catalog_path.is_file() and coverage_path.is_file():
        try:
            catalog = load_json(catalog_path)
            coverage = load_json(coverage_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"cannot parse catalog/coverage JSON: {exc}")
        else:
            contracts = _catalog_contracts(catalog)
            coverage_entries = coverage.get("contracts")
            if not isinstance(coverage_entries, list):
                errors.append("Issue #22 contract coverage must contain a contracts list")
                coverage_entries = []
            coverage_names = [
                entry.get("contract")
                for entry in coverage_entries
                if isinstance(entry, dict) and isinstance(entry.get("contract"), str)
            ]
            if len(coverage_names) != len(set(coverage_names)):
                errors.append("Issue #22 contract coverage has duplicate contract names")
            if set(contracts) != set(coverage_names):
                missing = sorted(set(contracts) - set(coverage_names))
                extra = sorted(set(coverage_names) - set(contracts))
                errors.append(
                    "schema catalog and Issue #22 contract coverage differ; "
                    f"missing={missing}, extra={extra}"
                )
            allowed_coverage = set(coverage.get("allowed_dispositions") or [])
            if "planned" in allowed_coverage:
                errors.append("Issue #22 coverage must not allow a planned disposition")
            for entry in coverage_entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("disposition") == "planned":
                    errors.append(f"contract coverage still planned: {entry.get('contract')}")
            for contract_name, versions in contracts.items():
                if not isinstance(versions, dict):
                    errors.append(f"catalog contract {contract_name!r} versions must be an object")
                    continue
                for version, meta in versions.items():
                    if not isinstance(meta, dict):
                        errors.append(f"catalog contract {contract_name}@{version} metadata must be an object")
                        continue
                    rel = meta.get("path")
                    if not isinstance(rel, str) or not is_safe_repo_relative(rel):
                        errors.append(f"catalog contract {contract_name}@{version} has invalid path {rel!r}")
                    elif not (root / rel).is_file():
                        errors.append(f"catalog schema path does not exist: {contract_name}@{version} -> {rel}")

    audit_surfaces = [
        "docs/audits/README.md",
        "docs/audits/portia-foundation-audit.md",
        "docs/audits/portia-foundation-findings.md",
        "docs/audits/portia-foundation-traceability.md",
        "docs/decisions/README.md",
        "docs/validation/issue-23-portia-foundation-validation.md",
    ]
    for relpath in audit_surfaces:
        _check_markdown_links(root, relpath, errors)

    if audit.get("synthetic_data_confirmation") is not True:
        errors.append("synthetic_data_confirmation must be true")
    if audit.get("sibling_repository_modification_confirmation") is not True:
        errors.append("sibling_repository_modification_confirmation must be true")

    if approval_exists:
        try:
            approval = load_json(approval_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"cannot parse foundation approval JSON: {exc}")
        else:
            if approval.get("approval_record_kind") != "pds-portia.foundation-approval":
                errors.append("approval_record_kind must be pds-portia.foundation-approval")
            if approval.get("approval_record_version") != "1":
                errors.append("approval_record_version must be '1'")
            if approval.get("milestone_issue") != 10 or approval.get("audit_issue") != 23:
                errors.append("approval must bind milestone #10 and audit #23")
            if approval.get("verdict") != "ready_for_implementation":
                errors.append("foundation approval verdict must be ready_for_implementation")
            approved_sha = approval.get("approved_portia_commit")
            if not isinstance(approved_sha, str) or not SHA_RE.fullmatch(approved_sha):
                errors.append("approved_portia_commit must be a 40-character lowercase hex SHA")
            if verdict == "ready_for_implementation" and approved_sha != final_sha:
                errors.append("approval commit must equal audit final_audited_portia_commit")
            for key in ("audit_record_reference", "findings_record_reference", "traceability_reference"):
                ref = approval.get(key)
                if not isinstance(ref, str) or not is_safe_repo_relative(ref):
                    errors.append(f"approval {key} must be a safe repository-relative path")
                elif not (root / ref).is_file():
                    errors.append(f"approval {key} does not resolve: {ref}")
            serialized = json.dumps(approval, sort_keys=True).lower()
            for token in ("tbd", "todo", '"planned"'):
                if token in serialized:
                    errors.append(f"approval contains forbidden placeholder token: {token}")

    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else repo_root_from_script()
    errors = validate_repo(root)
    if errors:
        print(f"Portia foundation audit validation: FAIL ({len(errors)} issue(s))")
        for error in errors:
            print(f"- {error}")
        return 1
    audit = load_json(root / "docs/audits/portia-foundation-audit.json")
    print("Portia foundation audit validation: OK")
    print(f"verdict: {audit['final_verdict']}")
    print(f"findings: {len(audit['findings'])}")
    print(f"unresolved: {len(audit['unresolved_finding_ids'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
