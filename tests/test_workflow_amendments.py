from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaOperationPartialCommitError,
)
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    AmendmentResolution,
    AmendmentWorkflowService,
    amendable_paths,
    amendment_path_policies,
    supported_amendment_contracts,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import AGENT

T0 = "2026-09-07T16:00:00-04:00"
T1 = "2026-09-07T16:05:00-04:00"
T2 = "2026-09-07T16:10:00-04:00"
T3 = "2026-09-07T16:15:00-04:00"


@dataclass
class _SyntheticRecord:
    contract: str
    contract_version: str
    logical_id: str
    class_id: str
    work_id: str
    status: str
    data: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return dict(self.data)

    def field(self, name: str) -> object:
        return self.data.get(name)


class _AmendmentRepository:
    def __init__(
        self,
        target: PortiaRecord,
        amendments: tuple[StoredRecord, ...] = (),
    ) -> None:
        self.target = target
        self.amendments = amendments

    def load_work(self, work: ExactPortiaWorkRef) -> StoredRecord:
        if work != _event_work():
            raise AssertionError("unexpected exact test work lookup")
        return _stored(self.target)

    def load_work_record(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        version: str,
        record_id: str,
    ) -> StoredRecord:
        if (
            work != _event_work()
            or contract != self.target.contract
            or version != self.target.contract_version
            or record_id != self.target.logical_id
        ):
            raise AssertionError("unexpected exact child lookup")
        return _stored(self.target)

    def list_work_records(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        *,
        version: str,
    ) -> tuple[StoredRecord, ...]:
        if work != _event_work():
            raise AssertionError("unexpected exact Amendment work lookup")
        if contract == "amendment" and version == "1":
            return self.amendments
        return ()


def _event_work() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def _record_reference(
    contract: str,
    version: str,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=_event_work(),
        record_ref=ExactLocalRecordRef(
            record_kind=contract,
            record_id=record_id,
            contract_version=version,
        ),
    )


def _synthetic_target(
    contract: str,
    version: str,
    record_id: str,
    *,
    updated_at: str,
    **extra: object,
) -> PortiaRecord:
    data: dict[str, object] = {
        "schema_version": version,
        "record_type": "portia_work" if contract == "event" else contract,
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "status": "active",
        "created_at": T0,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
        **extra,
    }
    if contract == "event":
        data["work_kind"] = "event"
    return cast(
        PortiaRecord,
        _SyntheticRecord(
            contract=contract,
            contract_version=version,
            logical_id=record_id,
            class_id="class_a",
            work_id="evt_alpha",
            status="active",
            data=data,
        ),
    )


def _stored(record: PortiaRecord) -> StoredRecord:
    content = canonical_json_bytes(record.to_dict())
    return StoredRecord(
        record=record,
        path=Path(f"synthetic/{record.contract}/{record.logical_id}.json"),
        fingerprint=fingerprint_bytes(content),
    )


def _target_dict(
    reference: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
) -> dict[str, object]:
    if isinstance(reference, ExactPortiaWorkRef):
        return {
            "kind": "work",
            "work_kind": reference.work_kind,
            "contract_version": reference.contract_version,
        }
    return {"kind": "local_record", "record_ref": reference.record_ref.to_dict()}


def _replace(path: str, before: object, after: object) -> dict[str, object]:
    return {
        "path": path,
        "operation": "replace",
        "before": {"present": True, "value": before},
        "after": {"present": True, "value": after},
    }


def _amendment(
    amendment_id: str,
    reference: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    *,
    before_updated_at: str,
    created_at: str,
    changes: list[dict[str, object]],
    previous_id: str | None = None,
) -> PortiaRecord:
    previous = None
    if previous_id is not None:
        previous = {
            "record_kind": "amendment",
            "record_id": previous_id,
            "contract_version": "1",
        }
    return parse_portia_record(
        "amendment",
        "1",
        {
            "schema_version": "1",
            "record_type": "amendment",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "amendment_id": amendment_id,
            "target": _target_dict(reference),
            "previous_amendment": previous,
            "target_updated_at_before": before_updated_at,
            "changes": changes,
            "reason": {"code": "spelling_corrected"},
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": AGENT,
        },
    )


def _service(
    tmp_path: Path,
    target: PortiaRecord,
    amendments: tuple[StoredRecord, ...] = (),
) -> AmendmentWorkflowService:
    repository = _AmendmentRepository(target, amendments)
    return AmendmentWorkflowService(
        tmp_path,
        repository=cast(PortiaRepository, repository),
    )


def test_amendment_policy_registry_is_closed_and_exact() -> None:
    assert supported_amendment_contracts() == (
        ("event", "2"),
        ("event_participant", "3"),
        ("event_participant_role", "3"),
        ("statement_of_disagreement", "1"),
        ("work_relationship", "2"),
    )
    assert amendable_paths("event", "2") == (
        "/summary",
        "/location/detail",
        "/instructional_context/detail",
    )
    assert amendable_paths("event_participant", "3") == (
        "/subject/display_snapshot/display_name",
    )
    assert amendable_paths("event_participant_role", "3") == ("/detail",)
    assert amendable_paths("statement_of_disagreement", "1") == (
        "/statement/text",
    )
    assert amendable_paths("work_relationship", "2") == ("/detail",)
    assert all(policy.validator for policy in amendment_path_policies("event", "2"))


def test_later_families_without_amendment_authority_fail_closed(
    tmp_path: Path,
) -> None:
    protected = (
        ("account", "2"),
        ("observation", "2"),
        ("review", "1"),
        ("classification", "1"),
        ("hypothesis", "1"),
        ("determination", "1"),
        ("response", "1"),
        ("communication", "1"),
        ("support_process", "1"),
        ("support_process_participant", "1"),
        ("support_need", "1"),
        ("support_goal", "1"),
        ("support", "1"),
        ("intervention", "1"),
        ("implementation", "1"),
        ("fidelity", "1"),
        ("follow_up", "1"),
        ("outcome", "1"),
        ("reentry", "1"),
        ("repair", "1"),
    )
    for contract, version in protected:
        assert amendable_paths(contract, version) == ()
        assert amendment_path_policies(contract, version) == ()

    target = _synthetic_target(
        "account", "2", "acct_alpha", updated_at=T0, content=[]
    )
    service = _service(tmp_path, target)
    with pytest.raises(WorkflowOwnershipError, match="no registered Amendment policy"):
        service.load_history(_record_reference("account", "2", "acct_alpha"))


def test_empty_event_amendment_history_is_reconciled(tmp_path: Path) -> None:
    target = _synthetic_target(
        "event",
        "2",
        "evt_alpha",
        updated_at=T0,
        summary="Student received the handout.",
    )
    resolution = _service(tmp_path, target).load_history(_event_work())

    assert isinstance(resolution, AmendmentResolution)
    assert resolution.amendments == ()
    assert resolution.selected_amendment is None
    assert resolution.selected_amendment_id is None
    assert resolution.reconciled is True
    assert resolution.reconciliation_error is None


def test_amendment_chain_uses_predecessors_and_reconciles_current_values(
    tmp_path: Path,
) -> None:
    target = _synthetic_target(
        "event",
        "2",
        "evt_alpha",
        updated_at=T3,
        summary="Student received the handout.",
    )
    first = _amendment(
        "amd_first",
        _event_work(),
        before_updated_at=T0,
        created_at=T1,
        changes=[
            _replace(
                "/summary",
                "Student recieveed the handout",
                "Student received the handout",
            )
        ],
    )
    second = _amendment(
        "amd_second",
        _event_work(),
        before_updated_at=T1,
        created_at=T2,
        previous_id="amd_first",
        changes=[
            _replace(
                "/summary",
                "Student received the handout",
                "Student received the handout.",
            )
        ],
    )
    service = _service(tmp_path, target, (_stored(second), _stored(first)))

    resolution = service.require_reconciled(_event_work())

    assert tuple(item.record.logical_id for item in resolution.amendments) == (
        "amd_first",
        "amd_second",
    )
    assert resolution.selected_amendment_id == "amd_second"
    assert resolution.reconciled is True


def test_later_unrelated_target_revision_does_not_erase_amendment_reconciliation(
    tmp_path: Path,
) -> None:
    target = _synthetic_target(
        "event",
        "2",
        "evt_alpha",
        updated_at=T3,
        summary="Student received the handout.",
    )
    amendment = _amendment(
        "amd_summary",
        _event_work(),
        before_updated_at=T0,
        created_at=T1,
        changes=[
            _replace(
                "/summary",
                "Student recieveed the handout.",
                "Student received the handout.",
            )
        ],
    )

    resolution = _service(tmp_path, target, (_stored(amendment),)).load_history(
        _event_work()
    )

    assert resolution.reconciled is True
    assert resolution.target.record.field("updated_at") == T3


def test_stale_current_amended_value_is_reported_as_unreconciled(
    tmp_path: Path,
) -> None:
    target = _synthetic_target(
        "event",
        "2",
        "evt_alpha",
        updated_at=T2,
        summary="Different current summary.",
    )
    amendment = _amendment(
        "amd_summary",
        _event_work(),
        before_updated_at=T0,
        created_at=T1,
        changes=[
            _replace(
                "/summary",
                "Student recieveed the handout.",
                "Student received the handout.",
            )
        ],
    )
    service = _service(tmp_path, target, (_stored(amendment),))

    resolution = service.load_history(_event_work())

    assert resolution.reconciled is False
    assert "after state does not match" in cast(str, resolution.reconciliation_error)
    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.require_reconciled(_event_work())


def test_amendment_history_rejects_missing_predecessor(tmp_path: Path) -> None:
    target = _synthetic_target(
        "event", "2", "evt_alpha", updated_at=T2, summary="Corrected."
    )
    amendment = _amendment(
        "amd_orphan",
        _event_work(),
        before_updated_at=T1,
        created_at=T2,
        previous_id="amd_missing",
        changes=[_replace("/summary", "Wrong.", "Corrected.")],
    )

    with pytest.raises(WorkflowPrerequisiteError, match="missing predecessor"):
        _service(tmp_path, target, (_stored(amendment),)).load_history(_event_work())


def test_amendment_history_rejects_fork(tmp_path: Path) -> None:
    target = _synthetic_target(
        "event", "2", "evt_alpha", updated_at=T3, summary="Corrected."
    )
    root = _amendment(
        "amd_root",
        _event_work(),
        before_updated_at=T0,
        created_at=T1,
        changes=[_replace("/summary", "Wrogn.", "Wrong.")],
    )
    left = _amendment(
        "amd_left",
        _event_work(),
        before_updated_at=T1,
        created_at=T2,
        previous_id="amd_root",
        changes=[_replace("/summary", "Wrong.", "Corrected.")],
    )
    right = _amendment(
        "amd_right",
        _event_work(),
        before_updated_at=T1,
        created_at=T3,
        previous_id="amd_root",
        changes=[_replace("/summary", "Wrong.", "Corrected.")],
    )

    with pytest.raises(WorkflowPrerequisiteError, match="fork"):
        _service(
            tmp_path,
            target,
            (_stored(root), _stored(left), _stored(right)),
        ).load_history(_event_work())


def test_amendment_change_paths_must_not_overlap(tmp_path: Path) -> None:
    target = _synthetic_target(
        "event",
        "2",
        "evt_alpha",
        updated_at=T1,
        location={"type": "classroom", "detail": "Room 201"},
    )
    amendment = _amendment(
        "amd_overlap",
        _event_work(),
        before_updated_at=T0,
        created_at=T1,
        changes=[
            _replace(
                "/location",
                {"type": "classroom", "detail": "Room 210"},
                {"type": "classroom", "detail": "Room 201"},
            ),
            _replace("/location/detail", "Room 210", "Room 201"),
        ],
    )

    with pytest.raises(WorkflowPrerequisiteError, match="must not overlap"):
        _service(tmp_path, target, (_stored(amendment),)).load_history(_event_work())


def test_amendment_change_path_must_not_traverse_array(tmp_path: Path) -> None:
    target = _synthetic_target(
        "event",
        "2",
        "evt_alpha",
        updated_at=T1,
        items=["corrected"],
    )
    amendment = _amendment(
        "amd_array",
        _event_work(),
        before_updated_at=T0,
        created_at=T1,
        changes=[_replace("/items/0", "wrogn", "corrected")],
    )

    with pytest.raises(WorkflowPrerequisiteError, match="must not traverse an array"):
        _service(tmp_path, target, (_stored(amendment),)).load_history(_event_work())


def test_participant_display_amendment_requires_stable_identity_variant(
    tmp_path: Path,
) -> None:
    reference = _record_reference("event_participant", "3", "ep_alpha")
    allowed = _synthetic_target(
        "event_participant",
        "3",
        "ep_alpha",
        updated_at=T1,
        subject={
            "kind": "actor",
            "actor_ref": {"actor_id": "actr_alpha"},
            "display_snapshot": {"display_name": "Ms. Jones"},
        },
    )
    amendment = _amendment(
        "amd_display",
        reference,
        before_updated_at=T0,
        created_at=T1,
        changes=[
            _replace(
                "/subject/display_snapshot/display_name",
                "Ms Jnoes",
                "Ms. Jones",
            )
        ],
    )
    assert _service(
        tmp_path, allowed, (_stored(amendment),)
    ).require_reconciled(reference).reconciled

    disallowed = _synthetic_target(
        "event_participant",
        "3",
        "ep_alpha",
        updated_at=T1,
        subject={
            "kind": "descriptive_person",
            "display_snapshot": {"display_name": "Ms. Jones"},
        },
    )
    with pytest.raises(
        WorkflowPrerequisiteError, match="stable roster-student or Actor"
    ):
        _service(tmp_path, disallowed, (_stored(amendment),)).load_history(reference)


def test_disagreement_text_amendment_requires_recorded_summary(tmp_path: Path) -> None:
    reference = _record_reference(
        "statement_of_disagreement", "1", "dsg_alpha"
    )
    target = _synthetic_target(
        "statement_of_disagreement",
        "1",
        "dsg_alpha",
        updated_at=T1,
        statement={
            "representation": "verbatim_quote",
            "text": "I disagree.",
        },
    )
    amendment = _amendment(
        "amd_disagreement",
        reference,
        before_updated_at=T0,
        created_at=T1,
        changes=[_replace("/statement/text", "I disagee.", "I disagree.")],
    )

    with pytest.raises(WorkflowPrerequisiteError, match="recorded_summary"):
        _service(tmp_path, target, (_stored(amendment),)).load_history(reference)


def test_amendment_service_exposes_only_named_mutation_surface() -> None:
    allowed = {
        "load_history",
        "resolve_selected_head",
        "require_reconciled",
        "supported_contracts",
        "apply_amendment",
    }
    assert allowed.issubset(vars(AmendmentWorkflowService))
    forbidden = {
        "amend",
        "apply",
        "replace",
        "revise",
        "save",
        "patch",
        "delete",
        "update_any_field",
    }
    assert forbidden.isdisjoint(vars(AmendmentWorkflowService))



def _canonical_event(*, summary: str, updated_at: str = T0) -> PortiaRecord:
    return parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "school_year": "2026-2027",
            "status": "active",
            "occurrence": {"precision": "exact", "started_at": T0},
            "summary": summary,
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _canonical_participant(*, display_name: str, updated_at: str = T0) -> PortiaRecord:
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "participant_id": "ep_alpha",
            "status": "active",
            "subject": {
                "kind": "actor",
                "actor_ref": {"actor_id": "actr_alpha"},
                "display_snapshot": {"display_name": display_name},
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _real_event_service(
    tmp_path: Path,
    *,
    summary: str = "Student recieveed the handout.",
) -> tuple[AmendmentWorkflowService, PortiaRepository, StoredRecord]:
    repository = PortiaRepository(tmp_path)
    stored = repository.create_work(_event_work(), _canonical_event(summary=summary))
    service = AmendmentWorkflowService(tmp_path, repository=repository)
    return service, repository, stored


def test_apply_amendment_commits_evidence_before_target_and_replays(
    tmp_path: Path,
) -> None:
    service, repository, prior = _real_event_service(tmp_path)
    changes = [
        _replace(
            "/summary",
            "Student recieveed the handout.",
            "Student received the handout.",
        )
    ]

    result = service.apply_amendment(
        _event_work(),
        expected=prior.fingerprint,
        amendment_id="amd_summary",
        changes=changes,
        reason_code="spelling_corrected",
        created_at=T1,
        created_by=AGENT,
        semantic_equivalence_confirmed=True,
    )

    assert result.accepted_steps == (
        "step_history",
        "step_amendment",
        "step_target",
    )
    amended = repository.load_work(_event_work())
    assert amended.record.field("summary") == "Student received the handout."
    assert amended.record.field("updated_at") == T1
    assert amended.record.field("updated_by") == AGENT
    evidence = repository.load_work_record(
        _event_work(), "amendment", "1", "amd_summary"
    )
    assert evidence.record.field("target_updated_at_before") == T0
    assert evidence.record.field("previous_amendment") is None

    journal = OperationJournalStore(tmp_path).load_current(result.operation_id)
    journal_data = journal.revision.to_dict()
    assert journal_data["operation_kind"] == "apply_amendment"
    assert journal_data["state"] == "completed"
    write_set = cast(list[object], journal_data["write_set"])
    step_ids = [cast(dict[str, object], step)["step_id"] for step in write_set]
    assert step_ids.index("step_amendment") < step_ids.index("step_target")

    replay = service.apply_amendment(
        _event_work(),
        expected=prior.fingerprint,
        amendment_id="amd_summary",
        changes=changes,
        reason_code="spelling_corrected",
        created_at=T1,
        created_by=AGENT,
        semantic_equivalence_confirmed=True,
    )
    assert replay.operation_id == result.operation_id
    assert replay.accepted_steps == result.accepted_steps


def test_apply_amendment_appends_exact_previous_head(tmp_path: Path) -> None:
    service, repository, prior = _real_event_service(
        tmp_path, summary="Student recieveed the handout"
    )
    service.apply_amendment(
        _event_work(),
        expected=prior.fingerprint,
        amendment_id="amd_first",
        changes=[
            _replace(
                "/summary",
                "Student recieveed the handout",
                "Student received the handout",
            )
        ],
        reason_code="spelling_corrected",
        created_at=T1,
        created_by=AGENT,
        semantic_equivalence_confirmed=True,
    )
    current = repository.load_work(_event_work())
    service.apply_amendment(
        _event_work(),
        expected=current.fingerprint,
        amendment_id="amd_second",
        changes=[
            _replace(
                "/summary",
                "Student received the handout",
                "Student received the handout.",
            )
        ],
        reason_code="punctuation_corrected",
        created_at=T2,
        created_by=AGENT,
        semantic_equivalence_confirmed=True,
    )

    second = repository.load_work_record(
        _event_work(), "amendment", "1", "amd_second"
    )
    assert second.record.field("previous_amendment") == {
        "record_kind": "amendment",
        "record_id": "amd_first",
        "contract_version": "1",
    }
    resolution = service.require_reconciled(_event_work())
    assert tuple(item.record.logical_id for item in resolution.amendments) == (
        "amd_first",
        "amd_second",
    )


def test_apply_amendment_supports_exact_child_target(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(_event_work(), _canonical_event(summary="Event summary."))
    participant = repository.create_work_record(
        _event_work(), _canonical_participant(display_name="Ms Jnoes")
    )
    reference = _record_reference("event_participant", "3", "ep_alpha")
    service = AmendmentWorkflowService(tmp_path, repository=repository)

    service.apply_amendment(
        reference,
        expected=participant.fingerprint,
        amendment_id="amd_display",
        changes=[
            _replace(
                "/subject/display_snapshot/display_name",
                "Ms Jnoes",
                "Ms Jones",
            )
        ],
        reason_code="display_value_corrected",
        created_at=T1,
        created_by=AGENT,
        semantic_equivalence_confirmed=True,
    )

    current = repository.load_work_record(
        _event_work(), "event_participant", "3", "ep_alpha"
    )
    subject = cast(dict[str, object], current.record.to_dict()["subject"])
    snapshot = cast(dict[str, object], subject["display_snapshot"])
    assert snapshot["display_name"] == "Ms Jones"
    assert service.require_reconciled(reference).selected_amendment_id == "amd_display"


def test_apply_amendment_requires_explicit_semantic_equivalence(
    tmp_path: Path,
) -> None:
    service, repository, prior = _real_event_service(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="successor correction"):
        service.apply_amendment(
            _event_work(),
            expected=prior.fingerprint,
            amendment_id="amd_unconfirmed",
            changes=[
                _replace(
                    "/summary",
                    "Student recieveed the handout.",
                    "Student received the handout.",
                )
            ],
            reason_code="spelling_corrected",
            created_at=T1,
            created_by=AGENT,
            semantic_equivalence_confirmed=False,
        )
    assert repository.list_work_records(
        _event_work(), "amendment", version="1"
    ) == ()


def test_apply_amendment_rejects_presence_change_as_correction_required(
    tmp_path: Path,
) -> None:
    service, _repository, prior = _real_event_service(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="add/remove"):
        service.apply_amendment(
            _event_work(),
            expected=prior.fingerprint,
            amendment_id="amd_add",
            changes=[
                {
                    "path": "/location/detail",
                    "operation": "add",
                    "before": {"present": False},
                    "after": {"present": True, "value": "Room 201"},
                }
            ],
            reason_code="other",
            reason_detail="clerical detail",
            created_at=T1,
            created_by=AGENT,
            semantic_equivalence_confirmed=True,
        )


def test_apply_amendment_rejects_reason_incompatible_with_path(
    tmp_path: Path,
) -> None:
    service, _repository, prior = _real_event_service(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="incompatible"):
        service.apply_amendment(
            _event_work(),
            expected=prior.fingerprint,
            amendment_id="amd_reason",
            changes=[
                _replace(
                    "/summary",
                    "Student recieveed the handout.",
                    "Student received the handout.",
                )
            ],
            reason_code="display_value_corrected",
            created_at=T1,
            created_by=AGENT,
            semantic_equivalence_confirmed=True,
        )


def test_apply_amendment_rejects_stale_expected_target_revision(
    tmp_path: Path,
) -> None:
    service, _repository, _prior = _real_event_service(tmp_path)
    stale = fingerprint_bytes(b"stale Amendment target")
    with pytest.raises(PortiaConflictError, match="expected Amendment target state"):
        service.apply_amendment(
            _event_work(),
            expected=stale,
            amendment_id="amd_stale",
            changes=[
                _replace(
                    "/summary",
                    "Student recieveed the handout.",
                    "Student received the handout.",
                )
            ],
            reason_code="spelling_corrected",
            created_at=T1,
            created_by=AGENT,
            semantic_equivalence_confirmed=True,
        )


def test_apply_amendment_rejects_reused_amendment_identity(tmp_path: Path) -> None:
    service, repository, prior = _real_event_service(
        tmp_path, summary="Student recieveed the handout"
    )
    service.apply_amendment(
        _event_work(),
        expected=prior.fingerprint,
        amendment_id="amd_same",
        changes=[
            _replace(
                "/summary",
                "Student recieveed the handout",
                "Student received the handout",
            )
        ],
        reason_code="spelling_corrected",
        created_at=T1,
        created_by=AGENT,
        semantic_equivalence_confirmed=True,
    )
    current = repository.load_work(_event_work())
    with pytest.raises(PortiaConflictError, match="identity already exists"):
        service.apply_amendment(
            _event_work(),
            expected=current.fingerprint,
            amendment_id="amd_same",
            changes=[
                _replace(
                    "/summary",
                    "Student received the handout",
                    "Student received the handout.",
                )
            ],
            reason_code="punctuation_corrected",
            created_at=T2,
            created_by=AGENT,
            semantic_equivalence_confirmed=True,
        )


def test_apply_amendment_partial_commit_preserves_durable_evidence(
    tmp_path: Path,
) -> None:
    service, repository, prior = _real_event_service(tmp_path)

    def fault(event: str, identifier: str | None) -> None:
        if event == "after_publish" and identifier == "step_amendment":
            raise RuntimeError("synthetic interruption after Amendment evidence")

    with pytest.raises(PortiaOperationPartialCommitError) as exc_info:
        service.apply_amendment(
            _event_work(),
            expected=prior.fingerprint,
            amendment_id="amd_partial",
            changes=[
                _replace(
                    "/summary",
                    "Student recieveed the handout.",
                    "Student received the handout.",
                )
            ],
            reason_code="spelling_corrected",
            created_at=T1,
            created_by=AGENT,
            semantic_equivalence_confirmed=True,
            operation_id="op_amend_partial",
            fault_hook=fault,
        )

    assert "step_amendment" in exc_info.value.accepted_steps
    evidence = repository.load_work_record(
        _event_work(), "amendment", "1", "amd_partial"
    )
    assert evidence.record.logical_id == "amd_partial"
    unchanged = repository.load_work(_event_work())
    assert unchanged.fingerprint == prior.fingerprint
    resolution = service.load_history(_event_work())
    assert resolution.reconciled is False
    journal = OperationJournalStore(tmp_path).load_current("op_amend_partial")
    assert journal.revision.to_dict()["state"] == "failed"
