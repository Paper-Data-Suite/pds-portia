from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_DOMAIN = "record_distinction_identity"

MARKERS: dict[str, tuple[str, ...]] = {
    "docs/decisions/0004-define-portia-identity-ownership-and-storage.md": (
        "A Portia student reference is the pair `class_id + student_id`.",
        "The same textual `student_id` appearing in two rosters must not be assumed to represent the same person.",
        "The display snapshot is not identity",
        "Portia must not merge roster identities automatically",
        "Unresolved historical references must be reported rather than silently repaired.",
    ),
    "docs/decisions/0007-define-shared-reference-targeting-and-relationship-contracts.md": (
        "Equality is the exact `class_id + student_id` pair.",
        "Names are not identity and must not be used to locate, merge, repair, or authorize a reference.",
        "Equality is exact `actor_id`.",
        "A participant target identifies the Event Participant record, not the underlying person outside the Event context.",
        "Resolution never silently searches, repairs by name, normalizes identifiers, follows a successor, chooses a newest contract, or mutates the canonical referring record.",
    ),
    "docs/decisions/0010-define-actor-directory-domain-model-and-lifecycle.md": (
        "Names, contact values, imports, communication recurrence, and similarity results",
        "do not create active Actor identity automatically.",
        "Portia does not create Actors from roster selection and does not use Actors as a",
        "cross-class student identity shortcut.",
        "Historical snapshots are nonauthoritative and are not rewritten when current",
        "Exact historical references never silently follow successors.",
        "Similarity never proves identity.",
    ),
    "portia/identity/roster.py": (
        "Resolve only exact ``(class_id, student_id)`` Core identities.",
        "Display names, preferred names, local student IDs without a class, and Actor",
        "Core roster class_id does not match the explicitly requested class",
        "cannot build an exact student lookup",
    ),
    "portia/identity/actors.py": (
        "Exact Actor-family resolution without silently following successors.",
        "Resolve one supported exact Actor child without successor following.",
        "One explicit Actor relationship plus its exact current Core roster target.",
    ),
    "portia/workflows/participants.py": (
        "Manage Participants without merging Event-local or person identities.",
        "persisted Participant person identity cannot be retargeted in place",
        "Resolve exact historical identity without applying current-use policy.",
    ),
    "portia/models/references.py": (
        "Exact class-qualified Core roster identity.",
        "Identity-only reference to one Portia Actor Directory record.",
        "Reference to one exact historical/current local record representation.",
        "Reference to one exact Portia work representation.",
        "Reference to one exact child representation in one exact Portia work.",
    ),
}

EXPECTED_REFERENCE_FIELDS: dict[str, tuple[str, ...]] = {
    "RosterStudentRef": ("class_id", "student_id"),
    "ActorRef": ("actor_id",),
    "ExactLocalRecordRef": ("record_kind", "record_id", "contract_version"),
    "ExactPortiaWorkRef": (
        "class_id",
        "work_id",
        "work_kind",
        "contract_version",
        "module_id",
    ),
    "ExactPortiaWorkRecordRef": ("work_ref", "record_ref"),
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


def _missing_markers(root: Path, path: str, markers: tuple[str, ...]) -> list[str]:
    text = _read(root, path)
    return [marker for marker in markers if marker not in text]


def _class_fields(source: str, class_name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        fields: list[str] = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append(item.target.id)
        return tuple(fields)
    return ()


def _participant_subject_identity_branches(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tree = ast.parse(source)
    target: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_subject_identity":
            target = node
            break
    if target is None:
        return (), ()

    roster_tuple: tuple[str, ...] = ()
    actor_tuple: tuple[str, ...] = ()
    for node in ast.walk(target):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Tuple):
            continue
        values: list[str] = []
        for element in node.value.elts:
            if isinstance(element, ast.Name):
                values.append(element.id)
            elif isinstance(element, ast.Attribute):
                owner = element.value.id if isinstance(element.value, ast.Name) else "?"
                values.append(f"{owner}.{element.attr}")
            else:
                values.append("?")
        result = tuple(values)
        if result == ("kind", "reference.class_id", "reference.student_id"):
            roster_tuple = result
        if result == ("kind", "actor_id"):
            actor_tuple = result
    return roster_tuple, actor_tuple


def _participant_replace_has_retarget_guard(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if node.value == "persisted Participant person identity cannot be retargeted in place":
            return True
    return False


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, IDENTITY_DOMAIN) != "pass":
        errors.append(f"{IDENTITY_DOMAIN} must be recorded as pass")

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing identity marker {marker!r}")

    try:
        reference_source = _read(root, "portia/models/references.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read reference models: {exc}")
    else:
        for class_name, expected in EXPECTED_REFERENCE_FIELDS.items():
            actual = _class_fields(reference_source, class_name)
            if actual != expected:
                errors.append(
                    f"{class_name} identity shape drifted: expected {expected!r}; "
                    f"found {actual!r}"
                )

    try:
        participant_source = _read(root, "portia/workflows/participants.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read participant workflow: {exc}")
    else:
        roster_tuple, actor_tuple = _participant_subject_identity_branches(
            participant_source
        )
        if roster_tuple != ("kind", "reference.class_id", "reference.student_id"):
            errors.append(
                "Participant roster identity must remain kind + class_id + student_id"
            )
        if actor_tuple != ("kind", "actor_id"):
            errors.append("Participant Actor identity must remain kind + actor_id")
        if not _participant_replace_has_retarget_guard(participant_source):
            errors.append("Participant replacement must retain the in-place retarget guard")

    audit_markers = (
        "## Slice 5 — Record distinction and identity",
        "Domain result: **PASS**",
        "No `P54-AUD-*` defect was identified in this domain.",
        "No inherited foundation obligation is reconciled by Slice 5.",
        "No production runtime code changed in Slice 5.",
    )
    findings_markers = (
        "## Slice 5 audit result",
        "No `P54-AUD-*` finding was opened for the record-distinction / identity domain.",
    )
    validation_markers = (
        "## Slice 5 — Record distinction and identity",
        "Portia Issue #54 record-distinction/identity audit validation passed",
        "No production runtime code is changed by Slice 5.",
    )
    for path, markers in (
        ("docs/audits/portia-v0.2.0-release-audit.md", audit_markers),
        ("docs/audits/portia-v0.2.0-release-findings.md", findings_markers),
        ("docs/validation/issue-54-v0.2.0-release-audit-validation.md", validation_markers),
    ):
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 5 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        identity_findings = [
            finding
            for finding in findings
            if isinstance(finding, dict)
            and finding.get("audit_domain") == IDENTITY_DOMAIN
        ]
        if identity_findings:
            errors.append(
                "identity domain is recorded PASS but still has domain findings"
            )

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 record-distinction/identity audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 record-distinction/identity audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
