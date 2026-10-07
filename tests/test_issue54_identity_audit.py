from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

from portia.models.references import (
    ActorRef,
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_identity_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_identity_audit", path)
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


def test_issue54_slice5_validator_accepts_identity_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_identity_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("record_distinction_identity") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_roster_identity_remains_class_qualified() -> None:
    first = RosterStudentRef(class_id="class_a", student_id="student_1")
    second = RosterStudentRef(class_id="class_b", student_id="student_1")
    assert first != second
    assert first.to_dict() == {"class_id": "class_a", "student_id": "student_1"}


def test_issue54_actor_identity_does_not_embed_roster_or_display_data() -> None:
    actor = ActorRef(actor_id="actr_example")
    assert actor.to_dict() == {"actor_id": "actr_example"}


def test_issue54_exact_record_identity_remains_version_aware() -> None:
    first = ExactLocalRecordRef(
        record_kind="event_participant",
        record_id="ep_example",
        contract_version="2",
    )
    second = ExactLocalRecordRef(
        record_kind="event_participant",
        record_id="ep_example",
        contract_version="3",
    )
    assert first != second


def test_issue54_exact_work_record_ref_carries_work_and_child_identity() -> None:
    work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_example",
        work_kind="event",
        contract_version="2",
    )
    child = ExactLocalRecordRef(
        record_kind="event_participant",
        record_id="ep_example",
        contract_version="3",
    )
    reference = ExactPortiaWorkRecordRef(work_ref=work, record_ref=child)
    assert reference.work_ref == work
    assert reference.record_ref == child


def test_issue54_participant_subject_identity_uses_explicit_authority_keys() -> None:
    validator = _load_validator()
    source = (ROOT / "portia" / "workflows" / "participants.py").read_text(
        encoding="utf-8"
    )
    roster_tuple, actor_tuple = validator._participant_subject_identity_branches(source)
    assert roster_tuple == ("kind", "reference.class_id", "reference.student_id")
    assert actor_tuple == ("kind", "actor_id")


def test_issue54_participant_in_place_retarget_remains_forbidden() -> None:
    source = (ROOT / "portia" / "workflows" / "participants.py").read_text(
        encoding="utf-8"
    )
    assert "persisted Participant person identity cannot be retargeted in place" in source


def test_issue54_slice5_opens_no_identity_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    identity_findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "record_distinction_identity"
    ]
    assert identity_findings == []
