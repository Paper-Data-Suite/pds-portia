"""Validate Issue #54 Slice 15 cumulative repository qualification wiring."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "cumulative_repository_qualification"

ISSUE54_SOURCE_VALIDATORS = (
    "scripts/validate_issue54_release_audit.py",
    "scripts/validate_issue54_ethics_audit.py",
    "scripts/validate_issue54_authority_audit.py",
    "scripts/validate_issue54_privacy_audit.py",
    "scripts/validate_issue54_identity_audit.py",
    "scripts/validate_issue54_architecture_audit.py",
    "scripts/validate_issue54_storage_compat_audit.py",
    "scripts/validate_issue54_recovery_integrity_audit.py",
    "scripts/validate_issue54_usability_audit.py",
    "scripts/validate_issue54_menu_terminology_audit.py",
    "scripts/validate_issue54_read_only_audit.py",
    "scripts/validate_issue54_packaging_audit.py",
    "scripts/validate_issue54_documentation_audit.py",
    "scripts/validate_issue54_release_mechanics.py",
    "scripts/validate_issue54_cumulative_qualification.py",
)

EARLIER_DOMAINS = (
    "ethical_neutrality_epistemic_distinctions",
    "teacher_local_authority",
    "sensitive_data_minimization_privacy",
    "record_distinction_identity",
    "architecture_ownership",
    "storage_path_history_compatibility",
    "recovery_error_integrity",
    "teacher_usability_workload",
    "menu_terminology",
    "read_only_surfaces",
    "packaging_public_surface",
    "documentation_reconciliation",
    "release_contract_mechanical",
)

CORE_065 = {
    "version": "0.6.5",
    "filename": "pds_core-0.6.5-py3-none-any.whl",
    "sha256": "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18",
    "source_commit": "64da9d2e4884ffe78a020aed87b1d5b9500927ad",
}
CORE_064 = {
    "version": "0.6.4",
    "filename": "pds_core-0.6.4-py3-none-any.whl",
    "sha256": "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b",
    "source_commit": "152d1c65064c4f8fe55249ff2ca3379d7c4d6ccb",
}
CORE_063 = {
    "version": "0.6.3",
    "filename": "pds_core-0.6.3-py3-none-any.whl",
    "sha256": "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _audit(root: Path) -> dict[str, Any]:
    raw: object = json.loads(
        _read(root, "docs/audits/portia-v0.2.0-release-audit.json")
    )
    if not isinstance(raw, dict):
        raise ValueError("release audit JSON must be one object")
    return cast(dict[str, Any], raw)


def _statuses(audit: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    domains = audit.get("audit_domains")
    if not isinstance(domains, list):
        return result
    for raw in domains:
        if not isinstance(raw, dict):
            continue
        domain_id = raw.get("domain_id")
        status = raw.get("status")
        if isinstance(domain_id, str) and isinstance(status, str):
            result[domain_id] = status
    return result


def validate_repo(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    try:
        audit = _audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit: {exc}"]

    statuses = _statuses(audit)
    for domain_id in EARLIER_DOMAINS:
        if statuses.get(domain_id) != "pass":
            errors.append(f"earlier audit domain regressed: {domain_id}")
    if statuses.get(DOMAIN) != "pass":
        errors.append(f"{DOMAIN} must be recorded as pass")
    if statuses.get("python_platform_qualification") != "pending":
        errors.append("Slice 15 must leave Python/platform qualification pending")

    core = audit.get("core_qualification")
    if not isinstance(core, dict):
        errors.append("core_qualification is unavailable")
    else:
        if core.get("current") != CORE_065:
            errors.append("current Core qualification authority must be exact 0.6.5")
        if core.get("prior_release_compatibility") != CORE_064:
            errors.append("prior-release Core compatibility authority must be exact 0.6.4")
        if core.get("historical") != CORE_063:
            errors.append("historical Core compatibility authority must remain exact 0.6.3")

    if audit.get("unresolved_finding_ids") != []:
        errors.append("Slice 15 requires zero unresolved Issue #54 findings")
    counts = audit.get("finding_counts")
    if not isinstance(counts, dict):
        errors.append("finding_counts are unavailable")
    elif counts.get("BLOCKER") != 0 or counts.get("MAJOR") != 0:
        errors.append("Slice 15 cannot pass with BLOCKER or MAJOR findings")

    obligations = audit.get("inherited_foundation_obligations")
    if not isinstance(obligations, list) or any(
        not isinstance(item, dict) or item.get("status") != "reconciled"
        for item in obligations
    ):
        errors.append("all inherited foundation obligations must remain reconciled")

    publication = audit.get("release_publication")
    if not isinstance(publication, dict):
        errors.append("release publication state is unavailable")
    else:
        if publication.get("status") != "not_started":
            errors.append("Slice 15 must not advance publication state")
        for field in (
            "release_commit",
            "release_tree",
            "tag",
            "github_release_url",
            "wheel_filename",
            "wheel_sha256",
            "sdist_filename",
            "sdist_sha256",
            "sha256sums_sha256",
        ):
            if publication.get(field) is not None:
                errors.append(f"Slice 15 must not freeze publication field {field}")
    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 15 must retain PENDING final verdict")

    try:
        repository = _read(root, "scripts/validate_repository.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read authoritative repository validator: {exc}")
        repository = ""

    for marker in (
        '"""Run the complete Portia repository qualification through Issue #54 cumulative qualification."""',
        "Issue #54 cumulative qualification requires the authenticated Core 0.6.5 wheel",
        "Portia Issue #54 cumulative repository qualification passed",
        "_ISSUE53_CLOSEOUT_COMPATIBILITY_MARKERS",
        'parser.add_argument(\n        "--prior-core-wheel",',
        'if expected_core_version != "0.6.5":',
        'if expected_prior_core_version != "0.6.4":',
        'if expected_historical_core_version != "0.6.3":',
    ):
        if marker not in repository:
            errors.append(f"repository validator missing cumulative marker {marker!r}")

    positions: list[int] = []
    for marker in ISSUE54_SOURCE_VALIDATORS:
        position = repository.find(marker)
        if position < 0:
            errors.append(f"repository validator does not invoke {marker}")
        else:
            positions.append(position)
    if positions and positions != sorted(positions):
        errors.append("Issue #54 source validators are not invoked in cumulative order")

    if repository.count('[sys.executable, "-m", "pytest"]') != 1:
        errors.append("authoritative cumulative gate must run exactly one full pytest stage")
    for marker in (
        '[sys.executable, "-m", "ruff", "check", "."]',
        '[sys.executable, "-m", "mypy"]',
        '[sys.executable, "-m", "pip", "check"]',
        '[sys.executable, "-m", "build"]',
        '[sys.executable, "-m", "twine", "check"',
        '"scripts/check_issue53_package.py"',
        '"scripts/check_issue54_release_package.py"',
        '"scripts/smoke_test_issue52_module_operations_wheel.py"',
        '"scripts/smoke_test_issue92_deep_workspace_wheel.py"',
        '"scripts/smoke_test_issue53_end_to_end_wheel.py"',
        '"scripts/smoke_test_issue54_core065_wheel.py"',
        '["git", "diff", "--check"]',
    ):
        if marker not in repository:
            errors.append(f"repository validator missing cumulative gate marker {marker!r}")

    package_53 = repository.find('"scripts/check_issue53_package.py"')
    package_54 = repository.find('"scripts/check_issue54_release_package.py"')
    smoke_52 = repository.find('"scripts/smoke_test_issue52_module_operations_wheel.py"')
    smoke_92 = repository.find('"scripts/smoke_test_issue92_deep_workspace_wheel.py"')
    smoke_53 = repository.find('"scripts/smoke_test_issue53_end_to_end_wheel.py"')
    smoke_54 = repository.find('"scripts/smoke_test_issue54_core065_wheel.py"')
    diff_check = repository.find('["git", "diff", "--check"]')
    if not (
        0 <= package_53 < package_54 < smoke_52 < smoke_92 < smoke_53 < smoke_54 < diff_check
    ):
        errors.append("package/smoke/diff cumulative order drifted")

    try:
        workflow = _read(root, ".github/workflows/ci.yml")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read CI workflow: {exc}")
    else:
        for marker in (
            "os: ubuntu-latest",
            "os: windows-latest",
            'python: "3.11"',
            'current_core: "0.6.5"',
            'prior_core: "0.6.4"',
            'core: "0.6.3"',
            "python scripts/validate_repository.py",
            '--core-wheel "$env:PDS_CORE_WHEEL"',
            '--prior-core-wheel "$env:PDS_PRIOR_CORE_WHEEL"',
            '--historical-core-wheel "$env:PDS_HISTORICAL_CORE_WHEEL"',
        ):
            if marker not in workflow:
                errors.append(f"CI cumulative gate missing marker {marker!r}")
        if "check_issue54_release_package.py" in workflow:
            errors.append("CI must delegate package sequencing to validate_repository.py")

    try:
        verifier = _read(root, "scripts/verify_core_wheel.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot inspect Core wheel verifier: {exc}")
    else:
        for marker in (
            '"pds_core-0.6.5-py3-none-any.whl"',
            CORE_065["sha256"],
        ):
            if marker not in verifier:
                errors.append(f"Core wheel verifier missing 0.6.5 authority {marker!r}")

    try:
        package_checker = _read(root, "scripts/check_issue54_release_package.py")
        generic_checker = _read(root, "scripts/check_package.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot inspect package evidence wiring: {exc}")
    else:
        for marker in (
            '"scripts/validate_issue54_cumulative_qualification.py"',
            '"scripts/smoke_test_issue54_core065_wheel.py"',
            '"tests/test_issue54_cumulative_qualification.py"',
        ):
            if marker not in package_checker:
                errors.append(f"Issue #54 package checker missing {marker}")
            if marker not in generic_checker:
                errors.append(f"generic package checker missing {marker}")
        if (
            'statuses.get("cumulative_repository_qualification") != "pass"'
            not in package_checker
        ):
            errors.append("sdist package gate must require cumulative qualification pass")

    try:
        mechanics = _read(root, "scripts/validate_issue54_release_mechanics.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot inspect release-mechanics validator: {exc}")
    else:
        if '{"pending", "pass"}' not in mechanics:
            errors.append(
                "release-mechanics validator must allow monotonic cumulative advancement"
            )
        if "Slice 14 must leave cumulative qualification pending" in mechanics:
            errors.append("release-mechanics validator still freezes cumulative status")

    try:
        with (root / "pyproject.toml").open("rb") as handle:
            data = tomllib.load(handle)
        mypy_files = set(data["tool"]["mypy"]["files"])
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"cannot inspect strict mypy scope: {exc}")
    else:
        for required in (
            "scripts/validate_issue54_cumulative_qualification.py",
            "scripts/smoke_test_issue54_core065_wheel.py",
        ):
            if required not in mypy_files:
                errors.append(f"strict mypy scope missing {required}")

    docs = {
        "docs/audits/portia-v0.2.0-release-audit.md": (
            "## Slice 15 — Cumulative repository qualification",
            "Domain result: **PASS**",
            "Core 0.6.5",
            "No `P54-AUD-*` finding was opened in Slice 15.",
            "Final verdict remains **PENDING**",
        ),
        "docs/audits/portia-v0.2.0-release-findings.md": (
            "## Slice 15 audit result",
            "No `P54-AUD-*` finding was opened for the cumulative repository qualification domain.",
        ),
        "docs/validation/issue-54-v0.2.0-release-audit-validation.md": (
            "## Slice 15 — Cumulative repository qualification",
            "Portia Issue #54 cumulative repository qualification passed",
            "Core 0.6.5",
            "Python/platform qualification remains pending",
        ),
    }
    for relative, markers in docs.items():
        try:
            source = _read(root, relative)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {relative}: {exc}")
            continue
        for marker in markers:
            if marker not in source:
                errors.append(f"{relative}: missing Slice 15 marker {marker!r}")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 cumulative qualification validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 cumulative qualification validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
