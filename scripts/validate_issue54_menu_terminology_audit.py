from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "menu_terminology"

MARKERS: dict[str, tuple[str, ...]] = {
    "portia/menu/main.py": (
        '"Record Event"',
        '"Add Information"',
        '"Record Response / Communication"',
        '"Manage Support"',
        '"Complete Follow-Up"',
        '"View Timeline"',
        '"Correct / Retract"',
        '"Attention Needed"',
        "without inferring its effect.",
        "without adding ranking or risk scoring.",
    ),
    "portia/menu/navigation.py": (
        '"H. Help"',
        "Core-owned B/M/Q navigation semantics.",
    ),
    "portia/menu/information.py": (
        'print("3. Review recorded Accounts / Observations")',
        'print("4. Start a Review")',
        'print("5. Record a Classification")',
        'print("6. Record a Hypothesis")',
        'print("7. Record a Determination")',
        "Review, Classification, Hypothesis, and Determination remain distinct.",
        "Do not convert certainty into truth.",
        "it does not establish blame, truth, or a finding.",
    ),
    "portia/menu/judgment.py": (
        "This does not create a Classification, Hypothesis, or Determination.",
        "A Classification records a category selection. It does not establish a ",
        "Hypothesis, Determination, policy violation, severity, or discipline.",
        "A Hypothesis remains provisional",
        "Authority: Teacher-local review",
        "This does not create a Response, Support, Follow-Up, or Outcome record.",
    ),
    "portia/menu/response_communication.py": (
        "This records what was done or attempted. It does not record effectiveness or Outcome.",
        "Merely listing a recipient does not establish ",
        "delivery, reading, understanding, or agreement.",
        "Response records a bounded action; it does not establish effectiveness.",
        "Communication records a communication act or attempt; it does not establish reading, understanding, or agreement.",
    ),
    "portia/menu/support.py": (
        "Activation does not establish a need, goal, service delivery, fidelity, or Outcome.",
        "Canonical activation does not prove implementation, fidelity, effectiveness, or Outcome.",
        "A target identifies scope only; it does not ",
        "assign a role, establish delivery, or assert an Outcome.",
    ),
    "portia/menu/attention.py": (
        "Attention is workflow state, not a behavior score, risk score, ",
        "urgency ranking, or recommendation.",
        "It is not student risk, severity, or priority.",
    ),
    "portia/menu/teacher_reference_export.py": (
        "Export Teacher Reference",
        "This is a local teacher reference.",
        "not an official record, disclosure ",
        "does not by itself authorize disclosure",
    ),
    "docs/task-oriented-teacher-menu.md": (
        "Review, Classification,",
        "Hypothesis, or Determination information without collapsing their epistemic",
        "Support, Intervention, Implementation, and Fidelity while keeping planning,",
        "delivery, fidelity, and Outcome separate.",
        "complete one exact Follow-Up without automatically creating Outcome,",
        "No behavior/risk/urgency/priority scoring is introduced.",
        "Portia remains teacher-local support/response tooling.",
    ),
    "tests/test_teacher_menu_foundation.py": (
        '"H. Help"',
        '"Q. Quit"',
        '"B. Back"',
        '"M. Main Menu"',
    ),
    "tests/test_teacher_menu_judgment.py": (
        "test_add_information_routes_each_judgment_as_an_independent_action",
        "test_prepare_hypothesis_is_under_consideration_not_determination",
        "test_prepare_determination_is_teacher_local_and_bounded",
    ),
    "tests/test_teacher_menu_response_communication.py": (
        "test_prepare_response_is_bounded_and_does_not_encode_outcome",
        'assert "effectiveness" not in data',
        'assert "agreement" not in data',
    ),
    "tests/test_teacher_menu_support_delivery.py": (
        "test_prepare_fidelity_is_plan_adherence_not_outcome",
    ),
    "tests/test_teacher_menu_follow_up.py": (
        "test_support_review_completion_may_add_disposition_without_outcome",
    ),
    "tests/test_teacher_menu_attention.py": (
        "test_partial_and_unavailable_labels_remain_distinct",
        '"Attention Needed"',
    ),
}


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
        if not isinstance(raw_domain, dict):
            continue
        domain = cast(dict[str, Any], raw_domain)
        if domain.get("domain_id") == domain_id:
            status = domain.get("status")
            return status if isinstance(status, str) else None
    return None


def _obligation_statuses(audit: dict[str, Any]) -> dict[str, str]:
    raw_items = audit.get("inherited_foundation_obligations")
    if not isinstance(raw_items, list):
        return {}
    result: dict[str, str] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, Any], raw_item)
        finding_id = item.get("finding_id")
        status = item.get("status")
        if isinstance(finding_id, str) and isinstance(status, str):
            result[finding_id] = status
    return result


def _missing_markers(root: Path, path: str, markers: tuple[str, ...]) -> list[str]:
    source = _read(root, path)
    return [marker for marker in markers if marker not in source]


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, DOMAIN) != "pass":
        errors.append(f"{DOMAIN} must be recorded as pass")

    statuses = _obligation_statuses(audit)
    if not statuses or set(statuses.values()) != {"reconciled"}:
        errors.append(
            "Slice 10 must preserve the fully reconciled inherited-foundation state"
        )

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing menu-terminology marker {marker!r}")

    docs_checks = (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 10 — Menu terminology",
                "Domain result: **PASS**",
                "No inherited foundation disposition changes in Slice 10.",
                "No `P54-AUD-*` defect was identified in this domain.",
                "No production runtime code changed in Slice 10.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 10 audit result",
                "No `P54-AUD-*` finding was opened for the menu-terminology domain.",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 10 — Menu terminology",
                "Portia Issue #54 menu terminology audit validation passed",
                "No production runtime code is changed by Slice 10.",
            ),
        ),
    )
    for path, markers in docs_checks:
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 10 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        domain_findings = [
            item
            for item in findings
            if isinstance(item, dict) and item.get("audit_domain") == DOMAIN
        ]
        if domain_findings:
            errors.append(
                "menu-terminology domain is PASS but still has domain findings"
            )

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 10 must not advance the final release verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        errors.append("Slice 10 must not advance release publication state")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 menu terminology audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 menu terminology audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
