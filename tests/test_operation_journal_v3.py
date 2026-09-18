from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.integrity import (
    observe_operation_durable_state,
    validate_operation_durable_state,
)
from portia.storage.operation_journal import absence_steps
from portia.storage.orchestration import (
    commit_journaled_candidates,
    planned_writes,
    requires_specialized_persistence,
)
from portia.storage.paths import operation_current_path, operation_revision_path
from portia.storage.recovery import OperationRecovery
from portia.storage.series import OperationJournalStore

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-47"
    / "operation-journal-v3"
)
CERTIFICATE_FIXTURE = (
    ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-12"
    / "migration-ownership-removal"
    / "valid"
    / "removal-accepted-test-data.json"
)


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / "valid" / name).read_text(encoding="utf-8"))


def _pointer(operation_id: str, revision: int = 1):
    return parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": operation_id,
            "journal_revision": revision,
        },
    )


def _materialize_evidence(
    root: Path,
    data: dict[str, object],
    *,
    certificate: bool,
    payload: bytes | None,
    certificate_target_matches: bool = True,
    certificate_content_matches: bool = True,
) -> None:
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    certificate_step = write_set[0]
    removal_step = write_set[1]
    assert isinstance(certificate_step, dict)
    assert isinstance(removal_step, dict)
    target_path = root / str(removal_step["destination_path"])
    if payload is not None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(payload)
        prior = fingerprint_bytes(payload).to_dict()
        precondition = removal_step["precondition"]
        intended = removal_step["intended_result"]
        assert isinstance(precondition, dict)
        assert isinstance(intended, dict)
        precondition["fingerprint"] = prior
        intended["prior_fingerprint"] = prior

    if not certificate:
        return
    certificate_value = json.loads(CERTIFICATE_FIXTURE.read_text(encoding="utf-8"))
    intended = removal_step["intended_result"]
    assert isinstance(intended, dict)
    prior = intended["prior_fingerprint"]
    assert isinstance(prior, dict)
    target = removal_step["target"]
    certificate_value["class_id"] = "class_english10_p2"
    certificate_value["removal_id"] = "rmv_issue47_v3"
    certificate_value["target"] = (
        copy.deepcopy(target)
        if certificate_target_matches
        else copy.deepcopy(certificate_value["target"])
    )
    certificate_value["content_evidence"]["byte_length"] = (
        prior["byte_length"]
        if certificate_content_matches
        else int(prior["byte_length"]) + 1
    )
    certificate_record = parse_portia_record(
        "exceptional_removal", "1", certificate_value
    )
    content = canonical_json_bytes(certificate_record.to_dict())
    certificate_fp = fingerprint_bytes(content).to_dict()
    certificate_path = root / str(certificate_step["destination_path"])
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    certificate_path.write_bytes(content)
    certificate_intended = certificate_step["intended_result"]
    assert isinstance(certificate_intended, dict)
    certificate_intended["fingerprint"] = certificate_fp
    observed = certificate_step.get("observed_result")
    if isinstance(observed, dict):
        observed["fingerprint"] = certificate_fp
    link = intended["removal_certificate"]
    assert isinstance(link, dict)
    link["fingerprint"] = certificate_fp


def _record(data: dict[str, object]):
    return parse_portia_record("operation_journal", "3", data)


def test_v3_runtime_round_trip_preserves_absence_evidence() -> None:
    record = _record(_load_fixture("v3-removal-pending.json"))
    reparsed = _record(record.to_dict())
    view = absence_steps(reparsed)[0]
    assert view.prior_contract_version == "3"
    assert view.removal_ref["removal_id"] == "rmv_issue47_v3"
    assert view.observed_absent is False


@pytest.mark.parametrize(
    "action",
    [
        "exclusive_create",
        "revision_aware_replace",
        "atomic_pointer_replace",
        "install_derived_replacement",
    ],
)
def test_v3_present_write_uses_existing_byte_plan_semantics(action: str) -> None:
    data = _load_fixture("v3-present-write.json")
    write_set = data["write_set"]
    assert isinstance(write_set, list) and isinstance(write_set[0], dict)
    write_set[0]["action"] = action
    v3_writes = planned_writes(_record(data))

    v2_data = copy.deepcopy(data)
    v2_data["schema_version"] = "2"
    v2_write_set = v2_data["write_set"]
    assert isinstance(v2_write_set, list) and isinstance(v2_write_set[0], dict)
    intended = v2_write_set[0]["intended_result"]
    assert isinstance(intended, dict)
    intended.pop("kind")
    v2_writes = planned_writes(parse_portia_record("operation_journal", "2", v2_data))

    assert v3_writes == v2_writes
    assert [item.action for item in v3_writes] == (
        [] if action == "install_derived_replacement" else [action]
    )
    if v3_writes:
        assert v3_writes[0].intended_fingerprint.digest == "3" * 64


def test_v3_accepted_present_step_preserves_missing_result_semantics(
    tmp_path: Path,
) -> None:
    data = _load_fixture("v3-present-write.json")
    step = data["write_set"][0]
    assert isinstance(step, dict)
    intended = step["intended_result"]
    assert isinstance(intended, dict)
    step["disposition"] = "accepted"
    step["observed_result"] = {
        "kind": "present",
        "workspace_relative_path": step["destination_path"],
        "fingerprint": copy.deepcopy(intended["fingerprint"]),
        "observed_at": "2026-08-05T20:00:03-04:00",
    }
    data["state"] = "completed"
    data["commit_point"] = {
        "reached": True,
        "reached_at": "2026-08-05T20:00:04-04:00",
    }
    partial = data["partial_state"]
    assert isinstance(partial, dict)
    partial["durability_assessment"] = "confirmed"
    partial["accepted_steps"] = [step["step_id"]]
    partial["remaining_canonical_steps"] = []
    partial["recommended_disposition"] = None
    findings = validate_operation_durable_state(tmp_path, _record(data))
    assert {item.code for item in findings} == {
        "PORTIA.STORAGE.DURABLE_RESULT_MISSING"
    }


def test_operation_series_selects_v3_explicitly_and_rejects_mixed_versions(
    tmp_path: Path,
) -> None:
    data = _load_fixture("v3-present-write.json")
    journal = _record(data)
    store = OperationJournalStore(tmp_path)
    current = store.create(journal, _pointer("op_v3_present"))
    assert store.load_current("op_v3_present").revision.contract_version == "3"

    successor = copy.deepcopy(data)
    successor["schema_version"] = "2"
    successor["journal_revision"] = 2
    successor["previous_journal_revision"] = 1
    write_set = successor["write_set"]
    assert isinstance(write_set, list) and isinstance(write_set[0], dict)
    intended = write_set[0]["intended_result"]
    assert isinstance(intended, dict)
    intended.pop("kind")
    v2 = parse_portia_record("operation_journal", "2", successor)
    with pytest.raises(PortiaConflictError, match="cannot mix"):
        store.append(
            v2,
            _pointer("op_v3_present", 2),
            expected_pointer=current.pointer_fingerprint,
        )


def test_new_v2_exceptional_removal_series_fails_closed(tmp_path: Path) -> None:
    data = _load_fixture("v3-present-write.json")
    data["schema_version"] = "2"
    data["operation_kind"] = "exceptionally_remove"
    step = data["write_set"][0]
    assert isinstance(step, dict) and isinstance(step["intended_result"], dict)
    step["intended_result"].pop("kind")
    journal = parse_portia_record("operation_journal", "2", data)
    with pytest.raises(PortiaConflictError, match="require operation_journal@3"):
        OperationJournalStore(tmp_path).create(journal, _pointer("op_v3_present"))


def test_unknown_journal_version_fails_closed(tmp_path: Path) -> None:
    data = _load_fixture("v3-present-write.json")
    data["schema_version"] = "99"
    revision_path = operation_revision_path(tmp_path, "op_v3_present", 1)
    revision_path.parent.mkdir(parents=True, exist_ok=True)
    revision_path.write_bytes(canonical_json_bytes(data))
    pointer_path = operation_current_path(tmp_path, "op_v3_present")
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_bytes(canonical_json_bytes(_pointer("op_v3_present").to_dict()))
    with pytest.raises(PortiaCorruptionError, match="unsupported explicit"):
        OperationJournalStore(tmp_path).load_current("op_v3_present")


def test_v2_and_v3_completed_and_in_progress_series_coexist(tmp_path: Path) -> None:
    store = OperationJournalStore(tmp_path)
    expected = {
        "op_mix_v2_pending": ("2", "prepared"),
        "op_mix_v2_done": ("2", "completed"),
        "op_mix_v3_pending": ("3", "prepared"),
        "op_mix_v3_done": ("3", "completed"),
    }
    for operation_id, (version, state) in expected.items():
        data = _load_fixture("v3-present-write.json")
        data["operation_id"] = operation_id
        for lock in data["lock_set"]:
            if isinstance(lock, dict) and lock.get("lock_scope") == "operation":
                lock["protected_target"]["operation_ref"]["operation_id"] = operation_id
        if version == "2":
            data["schema_version"] = "2"
            step = data["write_set"][0]
            assert isinstance(step, dict) and isinstance(step["intended_result"], dict)
            step["intended_result"].pop("kind")
        if state == "completed":
            data["state"] = "completed"
            data["write_set"] = []
            data["compensation_plan"] = []
            data["commit_point"] = {
                "reached": True,
                "reached_at": "2026-08-05T20:00:04-04:00",
            }
            partial = data["partial_state"]
            assert isinstance(partial, dict)
            partial["durability_assessment"] = "confirmed"
            partial["remaining_canonical_steps"] = []
            partial["recommended_disposition"] = None
        journal = parse_portia_record("operation_journal", version, data)
        store.create(journal, _pointer(operation_id))

    for operation_id, (version, state) in expected.items():
        selected = store.load_current(operation_id)
        assert selected.revision.contract_version == version
        assert selected.revision.field("state") == state
        assert selected.pointer.field("journal_revision") == 1


def test_coordinator_recognizes_but_does_not_dispatch_canonical_removal(
    tmp_path: Path,
) -> None:
    record = _record(_load_fixture("v3-removal-certificate-present-payload-pending.json"))
    assert requires_specialized_persistence("exceptional_remove")
    assert not requires_specialized_persistence("remove_transient")
    with pytest.raises(PortiaConflictError, match="specialized canonical-removal"):
        commit_journaled_candidates(tmp_path, record, (), {})


def test_accepted_absence_with_matching_certificate_is_consistent(tmp_path: Path) -> None:
    data = _load_fixture("v3-removal-accepted.json")
    _materialize_evidence(tmp_path, data, certificate=True, payload=None)
    record = _record(data)
    assert validate_operation_durable_state(tmp_path, record) == ()
    evidence = observe_operation_durable_state(tmp_path, record)
    removal = next(item for item in evidence if item.step_id == "step_remove_canonical_payload")
    assert removal.disposition == "accepted"

    OperationJournalStore(tmp_path).create(record, _pointer("op_v3_absence"))
    assessment = OperationRecovery(tmp_path).assess("op_v3_absence")
    assert assessment.disposition == "terminal_consistent"


def test_accepted_absence_with_retained_or_changed_payload_fails_closed(
    tmp_path: Path,
) -> None:
    retained = _load_fixture("v3-removal-accepted.json")
    _materialize_evidence(tmp_path, retained, certificate=True, payload=b"prior-payload")
    findings = validate_operation_durable_state(tmp_path, _record(retained))
    assert "PORTIA.STORAGE.REMOVAL_TARGET_RETAINED" in {item.code for item in findings}

    changed = _load_fixture("v3-removal-accepted.json")
    _materialize_evidence(tmp_path, changed, certificate=True, payload=b"prior-payload")
    removal_step = changed["write_set"][1]
    assert isinstance(removal_step, dict)
    path = tmp_path / str(removal_step["destination_path"])
    path.write_bytes(b"foreign-change")
    findings = validate_operation_durable_state(tmp_path, _record(changed))
    assert "PORTIA.STORAGE.REMOVAL_TARGET_CHANGED" in {item.code for item in findings}


def test_absence_certificate_missing_or_mismatched_is_deterministic(
    tmp_path: Path,
) -> None:
    missing = _record(_load_fixture("v3-removal-accepted.json"))
    findings = validate_operation_durable_state(tmp_path, missing)
    assert "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISSING" in {
        item.code for item in findings
    }

    mismatch_data = _load_fixture("v3-removal-accepted.json")
    _materialize_evidence(
        tmp_path,
        mismatch_data,
        certificate=True,
        payload=None,
        certificate_target_matches=False,
    )
    findings = validate_operation_durable_state(tmp_path, _record(mismatch_data))
    assert "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH" in {
        item.code for item in findings
    }

    content_mismatch = _load_fixture("v3-removal-accepted.json")
    _materialize_evidence(
        tmp_path,
        content_mismatch,
        certificate=True,
        payload=None,
        certificate_content_matches=False,
    )
    findings = validate_operation_durable_state(tmp_path, _record(content_mismatch))
    assert "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH" in {
        item.code for item in findings
    }


def test_pending_absence_classifies_certificate_payload_partial_states(
    tmp_path: Path,
) -> None:
    unexplained = _load_fixture("v3-removal-pending.json")
    evidence = observe_operation_durable_state(tmp_path, _record(unexplained))
    removal = next(item for item in evidence if item.step_id == "step_remove_canonical_payload")
    assert removal.disposition == "indeterminate"

    retained = _load_fixture("v3-removal-certificate-present-payload-pending.json")
    _materialize_evidence(tmp_path, retained, certificate=True, payload=b"prior-payload")
    evidence = observe_operation_durable_state(tmp_path, _record(retained))
    removal = next(item for item in evidence if item.step_id == "step_remove_canonical_payload")
    assert removal.disposition == "not_written"

    path = tmp_path / removal.relative_path
    path.unlink()
    evidence = observe_operation_durable_state(tmp_path, _record(retained))
    removal = next(item for item in evidence if item.step_id == "step_remove_canonical_payload")
    assert removal.disposition == "durable_unverified"
