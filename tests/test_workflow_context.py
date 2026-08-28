from __future__ import annotations

from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.workflows import WorkflowContextAssembler
from tests.workflow_helpers import participant_record


def test_context_resolves_every_roster_reference_before_closing_known_set(
    tmp_path: Path,
) -> None:
    for class_id in ("class_a", "class_b"):
        write_class_roster(
            tmp_path,
            create_roster(
                class_id,
                [
                    {
                        "student_id": "student_1",
                        "last_name": "Same",
                        "first_name": "Display",
                        "period": "2",
                    }
                ],
            ),
        )
    records = (
        participant_record(),
        participant_record(
            participant_id="ep_beta",
            subject={
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_b",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Same Display"},
            },
        ),
    )
    assembled = WorkflowContextAssembler(tmp_path).assemble(records)
    assert len(assembled.roster_students) == 2
    assert assembled.validation.roster_student_exists(
        assembled.roster_students[0].reference
    ) is True
    assert assembled.validation.roster_student_exists(
        assembled.roster_students[1].reference
    ) is True
    assert assembled.validation.core_works is None
