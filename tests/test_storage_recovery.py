from __future__ import annotations

import json
from pathlib import Path

from portia.models import parse_portia_record
from portia.storage.integrity import validate_operation_durable_state
from portia.storage.recovery import OperationRecovery
from portia.storage.series import OperationJournalStore

ROOT = Path(__file__).resolve().parents[1]
CREATE_ACTOR_FIXTURE = (
    ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-14"
    / "actor-aware-operations"
    / "operation-journal"
    / "valid"
    / "create-actor.json"
)


def _create_actor_journal() -> object:
    return json.loads(CREATE_ACTOR_FIXTURE.read_text(encoding="utf-8"))


def test_prepared_operation_series_is_resumable(tmp_path: Path) -> None:
    journal = parse_portia_record("operation_journal", "2", _create_actor_journal())
    pointer = parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": "op_create_actor",
            "journal_revision": 1,
        },
    )
    OperationJournalStore(tmp_path).create(journal, pointer)

    assessment = OperationRecovery(tmp_path).assess("op_create_actor")

    assert assessment.state == "prepared"
    assert assessment.disposition == "resume"
    assert assessment.findings == ()


def test_operation_target_path_mismatch_is_persistence_finding(
    tmp_path: Path,
) -> None:
    data = _create_actor_journal()
    assert isinstance(data, dict)
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    step["destination_path"] = "portia/actors/actr_other/actor.json"
    journal = parse_portia_record("operation_journal", "2", data)

    findings = validate_operation_durable_state(tmp_path, journal)

    assert {finding.code for finding in findings} == {
        "PORTIA.STORAGE.CANONICAL_PATH_OWNER_MISMATCH"
    }
