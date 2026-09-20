from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.migration_representations import (
    version_qualified_representation_path,
)
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    MigrationPlan,
    MigrationTransformContext,
    RecordMigrationWorkflowService,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_ref,
    event_wire,
    participant_wire,
)

EFFECTIVE_AT = "2026-08-26T12:05:00-04:00"


def _event_v1(*, status: str = "active") -> PortiaRecord:
    value = event_wire(status=status)
    value["schema_version"] = "1"
    return parse_portia_record("event", "1", value)


def _participant_v2(*, status: str = "active") -> PortiaRecord:
    value = participant_wire(status=status)
    value["schema_version"] = "2"
    return parse_portia_record("event_participant", "2", value)


def _participant_ref(
    work: ExactPortiaWorkRef,
    version: str = "2",
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="event_participant",
            record_id="ep_alpha",
            contract_version=version,
        ),
    )


def _event_transform(
    source: PortiaRecord,
    context: MigrationTransformContext,
) -> PortiaRecord:
    assert isinstance(context.source_reference, ExactPortiaWorkRef)
    value = source.to_dict()
    value["schema_version"] = context.destination_version
    value["supersedes"] = [context.source_reference.to_dict()]
    value["creation_source"] = {"type": "digital_entry"}
    value["created_at"] = context.effective_at
    value["created_by"] = dict(context.created_by)
    value["updated_at"] = context.effective_at
    value["updated_by"] = dict(context.created_by)
    return parse_portia_record("event", context.destination_version, value)


def _event_equivalent(source: PortiaRecord, destination: PortiaRecord) -> bool:
    source_data = source.to_dict()
    destination_data = destination.to_dict()
    semantic_fields = (
        "class_id",
        "instructional_context",
        "location",
        "module_id",
        "occurrence",
        "school_year",
        "status",
        "summary",
        "work_id",
        "work_kind",
    )
    return all(source_data.get(field) == destination_data.get(field) for field in semantic_fields)


def _participant_transform(
    source: PortiaRecord,
    context: MigrationTransformContext,
) -> PortiaRecord:
    assert isinstance(context.source_reference, ExactPortiaWorkRecordRef)
    value = source.to_dict()
    value["schema_version"] = context.destination_version
    value["supersedes"] = [
        {
            "work_record_ref": context.source_reference.to_dict(),
            "reason": "contract_migrated",
        }
    ]
    value["creation_source"] = {"type": "digital_entry"}
    value["created_at"] = context.effective_at
    value["created_by"] = dict(context.created_by)
    value["updated_at"] = context.effective_at
    value["updated_by"] = dict(context.created_by)
    return parse_portia_record(
        "event_participant",
        context.destination_version,
        value,
    )


def _participant_equivalent(
    source: PortiaRecord,
    destination: PortiaRecord,
) -> bool:
    source_data = source.to_dict()
    destination_data = destination.to_dict()
    semantic_fields = (
        "class_id",
        "module_id",
        "participant_id",
        "status",
        "subject",
        "work_id",
    )
    return all(source_data.get(field) == destination_data.get(field) for field in semantic_fields)


def _register_event(
    service: RecordMigrationWorkflowService,
    *,
    transform=_event_transform,
    semantic_equivalence=_event_equivalent,
    reason_category: str = "contract_upgrade",
    reason_code: str = "event_v1_to_v2",
) -> None:
    service.register_transformer(
        "event",
        "1",
        "2",
        transformer_id="event_v1_to_v2",
        transformer_version="1",
        reason_category=reason_category,
        reason_code=reason_code,
        transform=transform,
        semantic_equivalence=semantic_equivalence,
    )


def _register_participant(
    service: RecordMigrationWorkflowService,
    *,
    transformer_id: str = "event_participant_v2_to_v3",
) -> None:
    service.register_transformer(
        "event_participant",
        "2",
        "3",
        transformer_id=transformer_id,
        transformer_version="1",
        reason_category="contract_upgrade",
        reason_code="event_participant_v2_to_v3",
        transform=_participant_transform,
        semantic_equivalence=_participant_equivalent,
    )


def _create_event_v1(tmp_path: Path, *, status: str = "active") -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(version="1"), _event_v1(status=status))
    return repository


def test_registry_starts_empty(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)

    assert service.registered_transformers() == ()


def test_register_transformer_exposes_exact_metadata(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)

    spec = service.register_transformer(
        "event",
        "1",
        "2",
        transformer_id="event_v1_to_v2",
        transformer_version="1",
        reason_category="contract_upgrade",
        reason_code="event_v1_to_v2",
        transform=_event_transform,
        semantic_equivalence=_event_equivalent,
    )

    assert spec.contract == "event"
    assert spec.source_version == "1"
    assert spec.destination_version == "2"
    assert service.registered_transformers() == (spec,)


def test_register_rejects_same_version_pair(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="must differ"):
        service.register_transformer(
            "event",
            "2",
            "2",
            transformer_id="event_v2_rewrite",
            transformer_version="1",
            reason_category="canonical_representation_change",
            reason_code="event_v2_rewrite",
            transform=_event_transform,
            semantic_equivalence=_event_equivalent,
        )


def test_register_rejects_unmodeled_destination(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="not modeled"):
        service.register_transformer(
            "event",
            "1",
            "99",
            transformer_id="event_v1_to_v99",
            transformer_version="1",
            reason_category="contract_upgrade",
            reason_code="event_v1_to_v99",
            transform=_event_transform,
            semantic_equivalence=_event_equivalent,
        )


def test_register_rejects_duplicate_exact_pair(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)
    _register_event(service)

    with pytest.raises(WorkflowPrerequisiteError, match="already registered"):
        _register_event(service)


def test_transformer_identity_cannot_name_two_version_pairs(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)
    _register_event(service)

    with pytest.raises(WorkflowPrerequisiteError, match="cannot name multiple"):
        _register_participant(service, transformer_id="event_v1_to_v2")


def test_registration_rejects_non_lowercase_transformer_id(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="lowercase migration token"):
        service.register_transformer(
            "event",
            "1",
            "2",
            transformer_id="EventV1ToV2",
            transformer_version="1",
            reason_category="contract_upgrade",
            reason_code="event_v1_to_v2",
            transform=_event_transform,
            semantic_equivalence=_event_equivalent,
        )


def test_can_migrate_is_false_for_unregistered_pair(tmp_path: Path) -> None:
    _create_event_v1(tmp_path)
    service = RecordMigrationWorkflowService(tmp_path)

    assert service.can_migrate(event_ref(version="1"), "2") is False


def test_can_migrate_does_not_run_transformer(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)
    calls = 0

    def transform(
        source: PortiaRecord,
        context: MigrationTransformContext,
    ) -> PortiaRecord:
        nonlocal calls
        calls += 1
        return _event_transform(source, context)

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=transform)

    assert service.can_migrate(event_ref(version="1"), "2") is True
    assert calls == 0


def test_can_migrate_fails_closed_for_already_superseded_source(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path, status="superseded")
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service)

    with pytest.raises(WorkflowPrerequisiteError, match="current frontier"):
        service.can_migrate(event_ref(version="1"), "2")


def test_plan_event_migration_is_side_effect_free_and_exact(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)
    source_ref = event_ref(version="1")
    source_before = repository.load_work(source_ref)
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service)

    plan = service.plan_migration(
        source_ref,
        "2",
        effective_at=EFFECTIVE_AT,
        created_by=AGENT,
    )

    assert isinstance(plan, MigrationPlan)
    assert plan.source_reference == source_ref
    assert plan.destination_reference == event_ref(version="2")
    assert plan.source.fingerprint == source_before.fingerprint
    assert plan.source_observed_updated_at == TIMESTAMP
    assert plan.destination_observed_updated_at == EFFECTIVE_AT
    assert plan.transformation == {
        "transformer_id": "event_v1_to_v2",
        "transformer_version": "1",
    }
    assert plan.reason == {
        "category": "contract_upgrade",
        "code": "event_v1_to_v2",
    }
    assert repository.load_work(source_ref).fingerprint == source_before.fingerprint
    destination_path = version_qualified_representation_path(
        tmp_path,
        source_ref,
        "event",
        "evt_alpha",
        "2",
    )
    assert not destination_path.exists()


def test_plan_child_migration_builds_exact_same_work_destination(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, parse_portia_record("event", "2", event_wire()))
    repository.create_work_record(work, _participant_v2())
    source_ref = _participant_ref(work)
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_participant(service)

    plan = service.plan_migration(
        source_ref,
        "3",
        effective_at=EFFECTIVE_AT,
        created_by=AGENT,
    )

    assert plan.destination_reference == _participant_ref(work, "3")
    assert plan.destination.contract == "event_participant"
    assert plan.destination.contract_version == "3"
    assert plan.destination.logical_id == "ep_alpha"
    assert plan.destination.status == "active"


def test_plan_rejects_unregistered_pair_as_unsupported(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)

    with pytest.raises(WorkflowPrerequisiteError, match="unsupported migration"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_plan_rejects_effective_time_before_observed_source_revision(
    tmp_path: Path,
) -> None:
    repository = _create_event_v1(tmp_path)
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service)

    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at="2026-08-26T11:59:00-04:00",
            created_by=AGENT,
        )


def test_plan_rejects_changed_logical_identity(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)

    def changed_identity(
        source: PortiaRecord,
        context: MigrationTransformContext,
    ) -> PortiaRecord:
        value = _event_transform(source, context).to_dict()
        value["work_id"] = "evt_changed"
        value["supersedes"] = [event_ref(version="1").to_dict()]
        return parse_portia_record("event", "2", value)

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=changed_identity)

    with pytest.raises(WorkflowOwnershipError, match="work-root identity|logical identity"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_plan_rejects_wrong_destination_version(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)

    def wrong_version(
        source: PortiaRecord,
        _context: MigrationTransformContext,
    ) -> PortiaRecord:
        return source

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=wrong_version)

    with pytest.raises(WorkflowOwnershipError, match="wrong destination"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_plan_rejects_lifecycle_change_hidden_in_migration(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)

    def changes_status(
        source: PortiaRecord,
        context: MigrationTransformContext,
    ) -> PortiaRecord:
        value = _event_transform(source, context).to_dict()
        value["status"] = "closed"
        return parse_portia_record("event", "2", value)

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=changes_status)

    with pytest.raises(WorkflowPrerequisiteError, match="preserve semantic lifecycle"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_plan_rejects_non_migration_creation_provenance(tmp_path: Path) -> None:
    source_value = event_wire(status="active")
    source_value["schema_version"] = "1"
    source_value["creation_source"] = {
        "type": "import",
        "source_label": "Synthetic legacy Event",
    }
    repository = PortiaRepository(tmp_path)
    repository.create_work(
        event_ref(version="1"),
        parse_portia_record("event", "1", source_value),
    )

    def copies_source_provenance(
        source: PortiaRecord,
        context: MigrationTransformContext,
    ) -> PortiaRecord:
        value = _event_transform(source, context).to_dict()
        value["creation_source"] = source.to_dict()["creation_source"]
        return parse_portia_record("event", "2", value)

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=copies_source_provenance)

    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_plan_rejects_destination_timestamp_not_at_effective_time(
    tmp_path: Path,
) -> None:
    repository = _create_event_v1(tmp_path)

    def wrong_timestamp(
        source: PortiaRecord,
        context: MigrationTransformContext,
    ) -> PortiaRecord:
        value = _event_transform(source, context).to_dict()
        value["updated_at"] = "2026-08-26T12:06:00-04:00"
        return parse_portia_record("event", "2", value)

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=wrong_timestamp)

    with pytest.raises(WorkflowPrerequisiteError, match="must equal effective_at"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_plan_rejects_semantic_equivalence_failure(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, semantic_equivalence=lambda _source, _destination: False)

    with pytest.raises(WorkflowPrerequisiteError, match="semantic-equivalence"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_plan_wraps_transformer_failure_without_writing(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)

    def fails(
        _source: PortiaRecord,
        _context: MigrationTransformContext,
    ) -> PortiaRecord:
        raise ValueError("synthetic transformer failure")

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=fails)

    with pytest.raises(WorkflowPrerequisiteError, match="transformer failed"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_other_reason_requires_detail_at_plan_time(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(
        service,
        reason_category="other",
        reason_code="manual_event_v1_to_v2",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="requires nonempty detail"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by=AGENT,
        )


def test_reason_code_cannot_name_two_version_pairs(tmp_path: Path) -> None:
    service = RecordMigrationWorkflowService(tmp_path)
    _register_event(service)

    with pytest.raises(WorkflowPrerequisiteError, match="reason code cannot name multiple"):
        service.register_transformer(
            "event_participant",
            "2",
            "3",
            transformer_id="participant_upgrade_alt",
            transformer_version="1",
            reason_category="contract_upgrade",
            reason_code="event_v1_to_v2",
            transform=_participant_transform,
            semantic_equivalence=_participant_equivalent,
        )


def test_plan_rejects_invalid_created_by_before_transform(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)
    calls = 0

    def transform(
        source: PortiaRecord,
        context: MigrationTransformContext,
    ) -> PortiaRecord:
        nonlocal calls
        calls += 1
        return _event_transform(source, context)

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(service, transform=transform)

    with pytest.raises(WorkflowPrerequisiteError, match="valid attribution agent"):
        service.plan_migration(
            event_ref(version="1"),
            "2",
            effective_at=EFFECTIVE_AT,
            created_by={"type": "made_up"},
        )
    assert calls == 0


def test_other_reason_detail_is_preserved_in_plan(tmp_path: Path) -> None:
    repository = _create_event_v1(tmp_path)
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    _register_event(
        service,
        reason_category="other",
        reason_code="manual_event_v1_to_v2",
    )

    plan = service.plan_migration(
        event_ref(version="1"),
        "2",
        effective_at=EFFECTIVE_AT,
        created_by=AGENT,
        reason_detail="Reviewed representation-only manual procedure.",
    )

    assert plan.reason == {
        "category": "other",
        "code": "manual_event_v1_to_v2",
        "detail": "Reviewed representation-only manual procedure.",
    }
