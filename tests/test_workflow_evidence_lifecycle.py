from __future__ import annotations

from copy import deepcopy

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.evidence import (
    require_coordinated_evidence_transition,
    require_evidence_revision_invariants,
)
from tests.workflow_helpers import AGENT, TIMESTAMP

LATER = "2026-08-26T12:05:00-04:00"


def _account(*, status: str = "active", updated_at: str = TIMESTAMP) -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "account_id": "acct_alpha",
            "status": status,
            "target": {"kind": "event"},
            "source": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic source contribution.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _observation(
    *, status: str = "active", updated_at: str = TIMESTAMP
) -> PortiaRecord:
    return parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "observation_id": "obs_alpha",
            "status": status,
            "target": {"kind": "event"},
            "observer": {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "method": "live_direct",
            "content": {"narrative": "Synthetic observable information."},
            "observation_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


@pytest.mark.parametrize(
    ("prior", "candidate"),
    [
        (_account(status="proposed"), _account(status="active", updated_at=LATER)),
        (_account(status="active"), _account(status="retracted", updated_at=LATER)),
        (
            _account(status="invalidated"),
            _account(status="superseded", updated_at=LATER),
        ),
        (
            _observation(status="proposed"),
            _observation(status="active", updated_at=LATER),
        ),
        (
            _observation(status="invalidated"),
            _observation(status="superseded", updated_at=LATER),
        ),
    ],
)
def test_accepted_evidence_lifecycle_edges_are_modeled(
    prior: PortiaRecord, candidate: PortiaRecord
) -> None:
    require_coordinated_evidence_transition(prior, candidate)


def test_terminal_evidence_state_cannot_resurrect() -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="illegal ordinary lifecycle"):
        require_coordinated_evidence_transition(
            _account(status="superseded"),
            _account(status="active", updated_at=LATER),
        )

    with pytest.raises(WorkflowPrerequisiteError, match="illegal ordinary lifecycle"):
        require_coordinated_evidence_transition(
            _observation(status="superseded"),
            _observation(status="active", updated_at=LATER),
        )


def test_account_material_content_change_is_not_an_in_place_revision() -> None:
    prior = _account()
    changed = deepcopy(prior.to_dict())
    changed["content"][0]["text"] = "Changed synthetic wording."
    changed["updated_at"] = LATER
    candidate = parse_portia_record("account", "2", changed)

    with pytest.raises(WorkflowPrerequisiteError, match="evidence field content"):
        require_evidence_revision_invariants(prior, candidate)


def test_observation_material_method_change_is_not_an_in_place_revision() -> None:
    prior = _observation()
    changed = deepcopy(prior.to_dict())
    changed["method"] = "other"
    changed["method_detail"] = "Synthetic alternate method"
    changed["updated_at"] = LATER
    candidate = parse_portia_record("observation", "2", changed)

    with pytest.raises(WorkflowPrerequisiteError, match="evidence field method"):
        require_evidence_revision_invariants(prior, candidate)


def test_creation_provenance_and_update_chronology_remain_immutable() -> None:
    prior = _account()
    changed_creation = deepcopy(prior.to_dict())
    changed_creation["created_at"] = "2026-08-26T12:00:01-04:00"
    changed_creation["updated_at"] = LATER
    with pytest.raises(WorkflowPrerequisiteError, match="immutable created_at"):
        require_evidence_revision_invariants(
            prior, parse_portia_record("account", "2", changed_creation)
        )

    later_prior = _account(updated_at=LATER)
    with pytest.raises(WorkflowPrerequisiteError, match="updated_at cannot precede"):
        require_evidence_revision_invariants(later_prior, _account(updated_at=TIMESTAMP))


def test_transition_helper_rejects_metadata_only_touch_without_status_change() -> None:
    prior = _observation()
    candidate = _observation(updated_at=LATER)
    require_evidence_revision_invariants(prior, candidate)
    with pytest.raises(WorkflowPrerequisiteError, match="requires a status change"):
        require_coordinated_evidence_transition(prior, candidate)
