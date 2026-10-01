from __future__ import annotations

from pathlib import Path

import pytest

from portia.exports import (
    TeacherReferenceExportScope,
    TeacherReferenceScopeDiscoveryService,
    TeacherReferenceSourceObservation,
)
from portia.models import PortiaRecord, parse_portia_record
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage import PortiaRepository, StoredRecord
from portia.storage.fingerprint import fingerprint_bytes
from portia.views import CurrentnessDecision
from portia.workflows import AmendmentResolution, WorkflowPrerequisiteError
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
    relationship_record,
    role_record,
)

LATER = "2026-08-26T12:05:00-04:00"


def child(
    work: ExactPortiaWorkRef,
    kind: str,
    identifier: str,
    version: str,
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=kind,
            record_id=identifier,
            contract_version=version,
        ),
    )


class _Currentness:
    def __init__(
        self,
        *,
        noncurrent_ids: frozenset[str] = frozenset(),
        unavailable_ids: frozenset[str] = frozenset(),
        root_state: str = "current",
    ) -> None:
        self.noncurrent_ids = noncurrent_ids
        self.unavailable_ids = unavailable_ids
        self.root_state = root_state
        self.seen: list[ExactPortiaWorkRef | ExactPortiaWorkRecordRef] = []

    def evaluate(
        self,
        source_ref: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    ) -> CurrentnessDecision:
        self.seen.append(source_ref)
        if isinstance(source_ref, ExactPortiaWorkRef):
            return CurrentnessDecision(
                source_ref,
                self.root_state,  # type: ignore[arg-type]
                f"synthetic_{self.root_state}",
            )
        identifier = source_ref.record_ref.record_id
        if identifier in self.noncurrent_ids:
            return CurrentnessDecision(
                source_ref,
                "noncurrent",
                "synthetic_noncurrent",
            )
        if identifier in self.unavailable_ids:
            return CurrentnessDecision(
                source_ref,
                "unavailable",
                "synthetic_unavailable",
            )
        return CurrentnessDecision(source_ref, "current", "synthetic_current")


class _Disagreements:
    def __init__(
        self,
        records: tuple[StoredRecord, ...],
        *,
        unavailable_ids: frozenset[str] = frozenset(),
    ) -> None:
        self.records = records
        self.unavailable_ids = unavailable_ids

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        assert all(record.record.work_id == work.work_id for record in self.records)
        return self.records

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        if reference.record_ref.record_id in self.unavailable_ids:
            raise WorkflowPrerequisiteError("synthetic unavailable disagreement")
        return next(
            record
            for record in self.records
            if record.record.logical_id == reference.record_ref.record_id
        )


class _Amendments:
    def __init__(
        self,
        repository: PortiaRepository,
        selected: dict[
            ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
            StoredRecord,
        ],
    ) -> None:
        self.repository = repository
        self.selected = selected

    def require_reconciled(
        self,
        reference: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    ) -> AmendmentResolution:
        if isinstance(reference, ExactPortiaWorkRef):
            target = self.repository.load_work(reference)
        else:
            target = self.repository.load_work_record(
                reference.work_ref,
                reference.record_ref.record_kind,
                reference.record_ref.contract_version,
                reference.record_ref.record_id,
            )
        selected = self.selected.get(reference)
        amendments = () if selected is None else (selected,)
        return AmendmentResolution(
            reference=reference,
            target=target,
            amendments=amendments,
            selected_amendment=selected,
            policies=(),
            reconciliation_error=None,
        )


def _seed_event(tmp_path: Path) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), participant_record())
    return repository


def _account(
    *,
    account_id: str,
    participant_id: str,
    source: dict[str, object],
) -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "work_kind": "event",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "account_id": account_id,
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": participant_id,
                    "contract_version": "3",
                },
            },
            "source": source,
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic bounded account.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _disagreement(
    *,
    disagreement_id: str,
    participant_id: str,
    status: str = "active",
) -> PortiaRecord:
    return parse_portia_record(
        "statement_of_disagreement",
        "1",
        {
            "schema_version": "1",
            "record_type": "statement_of_disagreement",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "disagreement_id": disagreement_id,
            "status": status,
            "target": {
                "kind": "local_record",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": participant_id,
                    "contract_version": "3",
                },
            },
            "source": {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            "positions": ["qualifies_record"],
            "statement": {
                "representation": "recorded_summary",
                "text": "Synthetic bounded disagreement context.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _amendment(
    *,
    amendment_id: str,
    target: dict[str, object],
    path: str,
) -> PortiaRecord:
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
            "target": target,
            "previous_amendment": None,
            "target_updated_at_before": TIMESTAMP,
            "changes": [
                {
                    "path": path,
                    "operation": "replace",
                    "before": {"present": True, "value": "before"},
                    "after": {"present": True, "value": "after"},
                }
            ],
            "reason": {"code": "spelling_corrected"},
            "creation_source": {"type": "digital_entry"},
            "created_at": LATER,
            "created_by": AGENT,
        },
    )


def _support_process_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def _support_process() -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "school_year": "2026-2027",
            "status": "active",
            "workflow_state": "active",
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic bounded need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _support_participant() -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "participant_id": "spp_alpha",
            "status": "active",
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic learner",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def test_scope_is_exact_work_only_and_focal_only_for_participant_specific() -> None:
    work = event_ref()
    focal = child(work, "event_participant", "ep_alpha", "3")

    assert TeacherReferenceExportScope("teacher_current", work).focal_subject_ref is None
    assert TeacherReferenceExportScope(
        "participant_specific",
        work,
        focal,
    ).focal_subject_ref == focal

    with pytest.raises(PortiaLocalValidationError, match="requires one exact focal"):
        TeacherReferenceExportScope("participant_specific", work)
    with pytest.raises(PortiaLocalValidationError, match="cannot carry a focal"):
        TeacherReferenceExportScope("teacher_current", work, focal)


def test_scope_rejects_legacy_root_and_wrong_or_cross_work_focal() -> None:
    legacy = event_ref(version="1")
    with pytest.raises(PortiaLocalValidationError, match="unsupported teacher-reference"):
        TeacherReferenceExportScope("teacher_current", legacy)

    work = event_ref()
    foreign = event_ref(event_id="evt_other")
    with pytest.raises(PortiaLocalValidationError, match="exact selected work"):
        TeacherReferenceExportScope(
            "participant_specific",
            work,
            child(foreign, "event_participant", "ep_other", "3"),
        )
    with pytest.raises(PortiaLocalValidationError, match="exact current participant family"):
        TeacherReferenceExportScope(
            "participant_specific",
            work,
            child(work, "event_participant", "ep_alpha", "2"),
        )


def test_teacher_current_discovers_root_and_current_domain_with_exact_bytes(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(event_ref(), role_record())
    scope = TeacherReferenceExportScope("teacher_current", event_ref())

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    ).discover(scope)

    root = result.observation_for(event_ref())
    assert root.source_role == "projection_context"
    assert root.source_kind == "portia_work"
    assert root.focal_applicability == "whole_work"
    persisted = repository.load_work(event_ref())
    assert root.fingerprint == persisted.fingerprint
    assert root.fingerprint == fingerprint_bytes(persisted.path.read_bytes())

    participant = result.observation_for(
        child(event_ref(), "event_participant", "ep_alpha", "3")
    )
    assert participant.source_role == "projected_domain"
    assert participant.focal_applicability == "whole_work"
    assert participant.fingerprint == fingerprint_bytes(
        repository.load_work_record(
            event_ref(), "event_participant", "3", "ep_alpha"
        ).path.read_bytes()
    )


def test_noncurrent_domain_is_not_selected_but_unavailable_remains_distinct(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        participant_record(
            participant_id="ep_old",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    repository.create_work_record(
        event_ref(),
        _account(
            account_id="acct_unavailable",
            participant_id="ep_alpha",
            source={"kind": "local_operator", "display_label": "Teacher"},
        ),
    )

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(
            noncurrent_ids=frozenset({"ep_old"}),
            unavailable_ids=frozenset({"acct_unavailable"}),
        ),
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))

    refs = {item.source_ref for item in result.observations}
    assert child(event_ref(), "event_participant", "ep_old", "3") not in refs
    unavailable = result.observation_for(
        child(event_ref(), "account", "acct_unavailable", "2")
    )
    assert unavailable.state == "unavailable"
    assert unavailable.state_reason == "synthetic_unavailable"


def test_noncurrent_or_unavailable_root_fails_closed(tmp_path: Path) -> None:
    repository = _seed_event(tmp_path)
    for state in ("noncurrent", "unavailable"):
        with pytest.raises(PortiaLocalValidationError, match="exact current work root"):
            TeacherReferenceScopeDiscoveryService(
                tmp_path,
                repository=repository,
                currentness=_Currentness(root_state=state),
            ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))


def test_participant_specific_uses_exact_participant_targets_not_other_people(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        participant_record(
            participant_id="ep_other",
            subject={
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_2",
                },
                "display_snapshot": {"display_name": "Other Student"},
            },
        ),
    )
    repository.create_work_record(event_ref(), role_record(role_id="epr_focal"))
    repository.create_work_record(
        event_ref(),
        role_record(role_id="epr_other", participant_id="ep_other"),
    )
    focal = child(event_ref(), "event_participant", "ep_alpha", "3")

    currentness = _Currentness()
    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=currentness,
    ).discover(TeacherReferenceExportScope("participant_specific", event_ref(), focal))

    refs = {item.source_ref for item in result.observations}
    assert result.observation_for(focal).focal_applicability == "direct"
    assert child(event_ref(), "event_participant", "ep_other", "3") not in refs
    assert result.observation_for(
        child(event_ref(), "event_participant_role", "epr_focal", "3")
    ).focal_applicability == "direct"
    assert child(event_ref(), "event_participant_role", "epr_other", "3") not in refs
    assert child(event_ref(), "event_participant", "ep_other", "3") not in currentness.seen
    assert child(event_ref(), "event_participant_role", "epr_other", "3") not in currentness.seen


def test_class_qualified_roster_identity_prevents_bare_student_id_match(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        participant_record(
            participant_id="ep_other",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    repository.create_work_record(
        event_ref(),
        _account(
            account_id="acct_same_class",
            participant_id="ep_other",
            source={
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Same Display"},
            },
        ),
    )
    repository.create_work_record(
        event_ref(),
        _account(
            account_id="acct_other_class",
            participant_id="ep_other",
            source={
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_b",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Same Display"},
            },
        ),
    )
    focal = child(event_ref(), "event_participant", "ep_alpha", "3")

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    ).discover(TeacherReferenceExportScope("participant_specific", event_ref(), focal))

    same_class = result.observation_for(
        child(event_ref(), "account", "acct_same_class", "2")
    )
    refs = {item.source_ref for item in result.observations}
    assert same_class.focal_applicability == "direct"
    assert same_class.focal_relation == "source"
    assert child(event_ref(), "account", "acct_other_class", "2") not in refs


def test_display_labels_are_never_used_as_cross_record_identity(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(
        event_ref(),
        participant_record(
            subject={
                "kind": "descriptive_person",
                "description_type": "visitor",
                "display_label": "Repeated Label",
            }
        ),
    )
    repository.create_work_record(
        event_ref(),
        participant_record(
            participant_id="ep_other",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    repository.create_work_record(
        event_ref(),
        _account(
            account_id="acct_label",
            participant_id="ep_other",
            source={
                "kind": "descriptive_person",
                "description_type": "visitor",
                "display_label": "Repeated Label",
            },
        ),
    )
    focal = child(event_ref(), "event_participant", "ep_alpha", "3")

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    ).discover(TeacherReferenceExportScope("participant_specific", event_ref(), focal))

    assert child(event_ref(), "account", "acct_label", "2") not in {
        item.source_ref for item in result.observations
    }


def test_related_work_is_observed_only_as_owned_context_and_never_traversed(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    foreign = event_ref(event_id="evt_beta")
    repository.create_work(foreign, event_record(event_id="evt_beta"))
    repository.create_work_record(
        foreign,
        participant_record(event_id="evt_beta", participant_id="ep_foreign"),
    )
    repository.create_work_record(event_ref(), relationship_record())

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))

    relationship = result.observation_for(
        child(event_ref(), "work_relationship", "rel_alpha", "2")
    )
    assert relationship.focal_applicability == "whole_work"
    assert relationship.native_scope == "work"
    assert all(item.work_ref == event_ref() for item in result.observations)
    assert all(item.source_ref != foreign for item in result.observations)


def test_disagreement_and_selected_amendment_heads_get_truthful_context_roles(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    disagreement_stored = repository.create_work_record(
        event_ref(),
        _disagreement(disagreement_id="sod_alpha", participant_id="ep_alpha"),
    )
    root_amendment = repository.create_work_record(
        event_ref(),
        _amendment(
            amendment_id="amd_root",
            target={
                "kind": "work",
                "work_kind": "event",
                "contract_version": "2",
            },
            path="/summary",
        ),
    )
    disagreement_amendment = repository.create_work_record(
        event_ref(),
        _amendment(
            amendment_id="amd_sod",
            target={
                "kind": "local_record",
                "record_ref": {
                    "record_kind": "statement_of_disagreement",
                    "record_id": "sod_alpha",
                    "contract_version": "1",
                },
            },
            path="/statement/text",
        ),
    )
    disagreement_ref = child(
        event_ref(), "statement_of_disagreement", "sod_alpha", "1"
    )
    amendments = _Amendments(
        repository,
        {
            event_ref(): root_amendment,
            disagreement_ref: disagreement_amendment,
        },
    )

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
        disagreements=_Disagreements((disagreement_stored,)),
        amendments=amendments,
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))

    disagreement = result.observation_for(disagreement_ref)
    assert disagreement.source_role == "disagreement_context"
    assert disagreement.context_target_ref == child(
        event_ref(), "event_participant", "ep_alpha", "3"
    )
    root_context = result.observation_for(child(event_ref(), "amendment", "amd_root", "1"))
    assert root_context.source_role == "correction_context"
    assert root_context.context_target_ref == event_ref()
    sod_context = result.observation_for(child(event_ref(), "amendment", "amd_sod", "1"))
    assert sod_context.source_role == "correction_context"
    assert sod_context.context_target_ref == disagreement_ref


def test_participant_specific_does_not_discover_context_for_unrelated_participant(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        participant_record(
            participant_id="ep_other",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    focal_sod = repository.create_work_record(
        event_ref(),
        _disagreement(disagreement_id="sod_focal", participant_id="ep_alpha"),
    )
    other_sod = repository.create_work_record(
        event_ref(),
        _disagreement(disagreement_id="sod_other", participant_id="ep_other"),
    )
    focal = child(event_ref(), "event_participant", "ep_alpha", "3")

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
        disagreements=_Disagreements((focal_sod, other_sod)),
        amendments=_Amendments(repository, {}),
    ).discover(TeacherReferenceExportScope("participant_specific", event_ref(), focal))

    assert child(event_ref(), "statement_of_disagreement", "sod_focal", "1") in {
        item.source_ref for item in result.observations
    }
    assert child(event_ref(), "statement_of_disagreement", "sod_other", "1") not in {
        item.source_ref for item in result.observations
    }


def test_unavailable_disagreement_remains_unavailable_context(tmp_path: Path) -> None:
    repository = _seed_event(tmp_path)
    stored = repository.create_work_record(
        event_ref(),
        _disagreement(disagreement_id="sod_blocked", participant_id="ep_alpha"),
    )
    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
        disagreements=_Disagreements(
            (stored,), unavailable_ids=frozenset({"sod_blocked"})
        ),
        amendments=_Amendments(repository, {}),
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))

    observation = result.observation_for(
        child(event_ref(), "statement_of_disagreement", "sod_blocked", "1")
    )
    assert observation.state == "unavailable"
    assert observation.state_reason == "current_authority_unavailable"


def test_support_process_is_supported_as_exact_current_work_scope(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = _support_process_ref()
    repository.create_work(work, _support_process())
    repository.create_work_record(work, _support_participant())
    focal = child(work, "support_process_participant", "spp_alpha", "1")

    result = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    ).discover(TeacherReferenceExportScope("participant_specific", work, focal))

    assert result.observation_for(work).source_role == "projection_context"
    assert result.observation_for(focal).focal_applicability == "direct"


def test_discovery_is_read_only_and_deterministically_ordered(tmp_path: Path) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(event_ref(), role_record())
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    service = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    )
    first = service.discover(TeacherReferenceExportScope("teacher_current", event_ref()))
    second = service.discover(TeacherReferenceExportScope("teacher_current", event_ref()))

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after
    assert first == second
    assert first.observations[0].source_ref == event_ref()


def test_observation_rejects_role_surface_mismatch() -> None:
    work = event_ref()
    stored_fingerprint = fingerprint_bytes(b"synthetic\n")
    with pytest.raises(PortiaLocalValidationError, match="role disagrees"):
        TeacherReferenceSourceObservation(
            source_ref=child(work, "amendment", "amd_alpha", "1"),
            source_role="projected_domain",
            fingerprint=stored_fingerprint,
            state="current",
            state_reason="synthetic_current",
            focal_applicability="whole_work",
            native_scope="record",
        )
