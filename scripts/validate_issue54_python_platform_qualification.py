"""Validate Issue #54 Slice 16 Python/platform qualification statement."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "python_platform_qualification"

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
    "cumulative_repository_qualification",
)

EXPECTED_PYTHON = "3.11"
EXPECTED_CURRENT_CORE = "0.6.5"
EXPECTED_PRIOR_CORE = "0.6.4"
EXPECTED_HISTORICAL_CORE = "0.6.3"


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

    release_contract = audit.get("release_contract")
    if not isinstance(release_contract, dict):
        errors.append("release_contract is unavailable")
    elif release_contract.get("requires_python") != ">=3.11":
        errors.append("machine audit must preserve Requires-Python >=3.11")

    if audit.get("unresolved_finding_ids") != []:
        errors.append("Slice 16 requires zero unresolved Issue #54 findings")
    counts = audit.get("finding_counts")
    if not isinstance(counts, dict):
        errors.append("finding_counts are unavailable")
    elif counts.get("BLOCKER") != 0 or counts.get("MAJOR") != 0:
        errors.append("Slice 16 cannot pass with BLOCKER or MAJOR findings")

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 16 must retain PENDING final verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict):
        errors.append("release publication state is unavailable")
    else:
        if publication.get("status") != "not_started":
            errors.append("Slice 16 must not advance publication state")
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
                errors.append(f"Slice 16 must not freeze publication field {field}")

    try:
        with (root / "pyproject.toml").open("rb") as handle:
            project_data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"cannot load pyproject.toml: {exc}")
        project_data = {}

    project = project_data.get("project")
    if not isinstance(project, dict):
        errors.append("pyproject project table is unavailable")
    else:
        if project.get("requires-python") != ">=3.11":
            errors.append("package Requires-Python must remain >=3.11")
        classifiers = project.get("classifiers")
        if not isinstance(classifiers, list):
            errors.append("project classifiers are unavailable")
        else:
            if "Programming Language :: Python :: 3.11" not in classifiers:
                errors.append("package classifiers must retain Python 3.11")
            for unsupported_claim in (
                "Programming Language :: Python :: 3.12",
                "Programming Language :: Python :: 3.13",
                "Programming Language :: Python :: 3.14",
            ):
                if unsupported_claim in classifiers:
                    errors.append(
                        f"Slice 16 must not add unqualified classifier {unsupported_claim!r}"
                    )

    try:
        ci = _read(root, ".github/workflows/ci.yml")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read CI workflow: {exc}")
        ci = ""

    python_versions = re.findall(
        r'^\s+python:\s*"([^"]+)"\s*$',
        ci,
        flags=re.MULTILINE,
    )
    if python_versions != [EXPECTED_PYTHON, EXPECTED_PYTHON]:
        errors.append(
            "release qualification matrix must contain exactly two Python 3.11 lanes"
        )

    matrix_counts = {
        'os: ubuntu-latest': 1,
        'os: windows-latest': 1,
        f'current_core: "{EXPECTED_CURRENT_CORE}"': 2,
        f'prior_core: "{EXPECTED_PRIOR_CORE}"': 2,
        f'core: "{EXPECTED_HISTORICAL_CORE}"': 2,
    }
    for marker, expected_count in matrix_counts.items():
        actual = ci.count(marker)
        if actual != expected_count:
            errors.append(
                f"CI matrix marker {marker!r} count is {actual}; expected {expected_count}"
            )

    for marker in (
        "actions/setup-python@v5",
        "python scripts/validate_repository.py",
        '--core-wheel "$env:PDS_CORE_WHEEL"',
        '--prior-core-wheel "$env:PDS_PRIOR_CORE_WHEEL"',
        '--historical-core-wheel "$env:PDS_HISTORICAL_CORE_WHEEL"',
    ):
        if marker not in ci:
            errors.append(f"CI platform qualification missing marker {marker!r}")

    if "  push:\n" not in ci:
        errors.append("CI must retain push qualification, including tag pushes")
    if "tags-ignore:" in ci:
        errors.append("CI must not exclude immutable release-tag pushes")

    try:
        repository = _read(root, "scripts/validate_repository.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read repository validator: {exc}")
        repository = ""
    cumulative_marker = '"scripts/validate_issue54_cumulative_qualification.py"'
    platform_marker = '"scripts/validate_issue54_python_platform_qualification.py"'
    pytest_marker = '[sys.executable, "-m", "pytest"]'
    cumulative_pos = repository.find(cumulative_marker)
    platform_pos = repository.find(platform_marker)
    pytest_pos = repository.find(pytest_marker)
    if not (0 <= cumulative_pos < platform_pos < pytest_pos):
        errors.append(
            "repository validator must run Slice 16 after cumulative qualification and before full pytest"
        )

    try:
        mechanics = _read(root, "scripts/validate_issue54_release_mechanics.py")
        cumulative = _read(root, "scripts/validate_issue54_cumulative_qualification.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot inspect monotonic Issue #54 validators: {exc}")
    else:
        expected_guard = (
            'statuses.get("python_platform_qualification") '
            'not in {"pending", "pass"}'
        )
        if expected_guard not in mechanics:
            errors.append("release-mechanics validator must allow later platform PASS")
        if expected_guard not in cumulative:
            errors.append("cumulative validator must allow later platform PASS")
        if "scripts/validate_issue54_python_platform_qualification.py" not in cumulative:
            errors.append(
                "cumulative wiring audit must know the Slice 16 platform validator"
            )

    try:
        package_checker = _read(root, "scripts/check_issue54_release_package.py")
        generic_checker = _read(root, "scripts/check_package.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot inspect package evidence wiring: {exc}")
    else:
        for marker in (
            "scripts/validate_issue54_python_platform_qualification.py",
            "tests/test_issue54_python_platform_qualification.py",
        ):
            if marker not in package_checker:
                errors.append(f"Issue #54 package checker missing {marker}")
            if marker not in generic_checker:
                errors.append(f"generic package checker missing {marker}")
        if (
            'statuses.get("python_platform_qualification") != "pass"'
            not in package_checker
        ):
            errors.append("Issue #54 sdist gate must require platform qualification PASS")

    try:
        release_notes = _read(root, "RELEASE_NOTES_v0.2.0.md")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read release notes: {exc}")
    else:
        for marker in (
            "Release qualification matrix: Python 3.11 on Windows and Ubuntu.",
            "`Requires-Python >=3.11` is package compatibility syntax",
            "Python minors other than 3.11 are not claimed as release-tested",
        ):
            if marker not in release_notes:
                errors.append(f"release notes missing platform boundary {marker!r}")

    try:
        docs_index = _read(root, "docs/README.md")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read docs index: {exc}")
    else:
        if "Slice 1 through Slice 16 audit qualification evidence" not in docs_index:
            errors.append("docs index must advance Issue #54 evidence through Slice 16")

    docs = {
        "docs/audits/portia-v0.2.0-release-audit.md": (
            "## Slice 16 — Python and platform qualification statement",
            "Domain result: **PASS**",
            "Python 3.11 on Windows",
            "Python 3.11 on Ubuntu",
            "Requires-Python >=3.11",
            "Hosted release-preparation PR CI remains a later release-phase gate.",
            "Final verdict remains **PENDING**",
        ),
        "docs/audits/portia-v0.2.0-release-findings.md": (
            "## Slice 16 audit result",
            "No `P54-AUD-*` finding was opened for the Python/platform qualification domain.",
        ),
        "docs/validation/issue-54-v0.2.0-release-audit-validation.md": (
            "## Slice 16 — Python and platform qualification statement",
            "Portia Issue #54 Python/platform qualification validation passed",
            "Windows / Python 3.11",
            "Ubuntu / Python 3.11",
            "Hosted release-preparation PR CI remains pending",
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
                errors.append(f"{relative}: missing Slice 16 marker {marker!r}")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 Python/platform qualification validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 Python/platform qualification validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
