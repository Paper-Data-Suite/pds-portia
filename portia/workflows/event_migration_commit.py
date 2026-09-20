"""Journaled representation migration for canonical Event work roots.

Slice 27 composes the version-explicit Event lifecycle authority established by
Slice 24 with the corrected-history selector qualified in Slice 26.  Exact
``event@1`` -> ``event@2`` representation migration extends the selected Event
lifecycle head, whether selection comes from an ordinary linear history or an
append-only lifecycle-history correction chain.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import cast

from portia.models import PortiaRecord, parse_portia_record
from portia.models.common import AttributionAgent
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.io import read_bytes
from portia.storage.locks import derive_lock_id
from portia.storage.migration_representations import (
    version_qualified_representation_path,
)
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.paths import (
    work_manifest_path,
    work_record_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.repository import StoredRecord
from portia.workflows.action_transition import _journal_plan, _lock_plan, _state_fact
from portia.workflows.common import record_target, work_target
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from portia.workflows.event_lifecycle import (
    build_event_migration_supersession_transition_from_selected_head,
)
from portia.workflows.event_lifecycle_history import (
    require_event_lifecycle_history_reconciled,
)
from portia.workflows.migration_commit import (
    PlanValidator,
    RecordMigrationCommitCoordinator,
    _parsed_timestamp,
)
from portia.workflows.migrations import MigrationPlan

HistorySnapshot = tuple[tuple[str, ContentFingerprint], ...]


def _event_lifecycle_target(work: ExactPortiaWorkRef) -> dict[str, object]:
    return {
        "kind": "work",
        "work_kind": "event",
        "contract_version": work.contract_version,
    }


def _history_snapshot(records: tuple[StoredRecord, ...]) -> HistorySnapshot:
    values: list[tuple[str, ContentFingerprint]] = []
    for stored in records:
        identifier = stored.record.logical_id
        if not isinstance(identifier, str):
            raise WorkflowOwnershipError(
                "Event migration lifecycle artifact has no exact identity"
            )
        values.append((identifier, stored.fingerprint))
    return tuple(sorted(values, key=lambda item: item[0]))


def _work_migration_certificate(
    plan: MigrationPlan,
    *,
    migration_id: str,
    created_at: str,
) -> PortiaRecord:
    if not isinstance(plan.source_reference, ExactPortiaWorkRef) or not isinstance(
        plan.destination_reference,
        ExactPortiaWorkRef,
    ):
        raise WorkflowOwnershipError(
            "Event work-root migration certificate requires exact work endpoints"
        )
    source = plan.source_reference
    destination = plan.destination_reference
    try:
        return parse_portia_record(
            "record_migration",
            "1",
            {
                "schema_version": "1",
                "record_type": "record_migration",
                "module_id": "portia",
                "class_id": source.class_id,
                "work_id": source.work_id,
                "migration_id": migration_id,
                "source": {
                    "kind": "work",
                    "work_ref": source.to_dict(),
                    "observed_updated_at": plan.source_observed_updated_at,
                },
                "destination": {
                    "kind": "work",
                    "work_ref": destination.to_dict(),
                    "observed_updated_at": plan.destination_observed_updated_at,
                },
                "reason": plan.reason,
                "transformation": plan.transformation,
                "effective_at": plan.effective_at,
                "creation_source": {"type": "digital_entry"},
                "created_at": created_at,
                "created_by": dict(plan.created_by),
            },
        )
    except Exception as exc:
        raise WorkflowPrerequisiteError(
            "Event work-root migration certificate is not structurally valid"
        ) from exc


def _superseded_event_source(
    source: PortiaRecord,
    *,
    updated_at: str,
    updated_by: Mapping[str, object],
) -> PortiaRecord:
    if source.contract != "event" or source.contract_version != "1":
        raise WorkflowOwnershipError(
            "Event work-root migration retirement requires event@1 source"
        )
    value = source.to_dict()
    value["status"] = "superseded"
    value["updated_at"] = updated_at
    try:
        value["updated_by"] = AttributionAgent.from_dict(updated_by).to_dict()
        return parse_portia_record("event", "1", value)
    except Exception as exc:
        raise WorkflowPrerequisiteError(
            "event@1 cannot represent the final migration-retired source"
        ) from exc


def _intent_digest(
    plan: MigrationPlan,
    *,
    certificate: PortiaRecord,
    transition: PortiaRecord,
    superseded_source: PortiaRecord,
) -> str:
    source = cast(ExactPortiaWorkRef, plan.source_reference)
    destination = cast(ExactPortiaWorkRef, plan.destination_reference)
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "source_reference": source.to_dict(),
                "destination_reference": destination.to_dict(),
                "source": plan.source.record.to_dict(),
                "destination": plan.destination.to_dict(),
                "certificate": certificate.to_dict(),
                "transition": transition.to_dict(),
                "superseded_source": superseded_source.to_dict(),
            }
        )
    ).hexdigest()


class EventMigrationCommitCoordinator(RecordMigrationCommitCoordinator):
    """Commit one exact ``event@1`` -> ``event@2`` representation migration."""

    @staticmethod
    def _require_exact_pair(
        plan: MigrationPlan,
    ) -> tuple[ExactPortiaWorkRef, ExactPortiaWorkRef]:
        if not isinstance(plan.source_reference, ExactPortiaWorkRef) or not isinstance(
            plan.destination_reference,
            ExactPortiaWorkRef,
        ):
            raise WorkflowOwnershipError(
                "Event work-root migration requires exact work endpoints"
            )
        source = plan.source_reference
        destination = plan.destination_reference
        if (
            source.work_kind != "event"
            or source.contract_version != "1"
            or destination.work_kind != "event"
            or destination.contract_version != "2"
        ):
            raise WorkflowOwnershipError(
                "journaled work-root migration currently supports exact "
                "event@1 -> event@2 only"
            )
        if (
            source.module_id != destination.module_id
            or source.class_id != destination.class_id
            or source.work_id != destination.work_id
        ):
            raise WorkflowOwnershipError(
                "Event work-root migration must preserve exact logical ownership"
            )
        return source, destination

    def _event_target_history_records(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
    ) -> tuple[StoredRecord, ...]:
        target = _event_lifecycle_target(work)
        return tuple(
            stored
            for stored in self.repository.list_work_records(
                work,
                contract,
                version="1",
            )
            if stored.record.field("target") == target
        )

    def _event_selected_source_history(
        self,
        work: ExactPortiaWorkRef,
        root: PortiaRecord,
    ) -> tuple[StoredRecord | None, HistorySnapshot, HistorySnapshot]:
        resolution = require_event_lifecycle_history_reconciled(
            self.repository,
            work,
            root,
        )
        return (
            resolution.selected_head,
            _history_snapshot(resolution.transitions),
            _history_snapshot(resolution.corrections),
        )

    @staticmethod
    def _transition_previous_id(transition: PortiaRecord) -> str | None:
        previous = transition.field("previous_transition")
        if previous is None:
            return None
        if (
            not isinstance(previous, Mapping)
            or previous.get("record_kind") != "lifecycle_transition"
            or previous.get("contract_version") != "1"
            or not isinstance(previous.get("record_id"), str)
        ):
            raise PortiaCorruptionError(
                "Event migration transition has malformed previous_transition"
            )
        return str(previous["record_id"])

    def _intent_transition(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        superseded_source: PortiaRecord,
        *,
        transition_id: str,
        reason_detail: str | None,
        effective_at: str,
    ) -> PortiaRecord:
        try:
            stored = self.repository.load_work_record(
                work,
                "lifecycle_transition",
                "1",
                transition_id,
            )
        except PortiaNotFoundError:
            selected_head, _, _ = self._event_selected_source_history(work, prior)
            return build_event_migration_supersession_transition_from_selected_head(
                work,
                prior,
                superseded_source,
                selected_head=selected_head,
                transition_id=transition_id,
                reason_detail=reason_detail,
                effective_at=effective_at,
            )
        if stored.record.field("target") != _event_lifecycle_target(work):
            raise PortiaConflictError(
                "Event migration lifecycle transition identity already targets "
                "another record"
            )
        return stored.record

    def _require_locked_event_history_state(
        self,
        work: ExactPortiaWorkRef,
        *,
        expected_transitions: HistorySnapshot,
        expected_corrections: HistorySnapshot,
    ) -> None:
        transitions = _history_snapshot(
            self._event_target_history_records(work, "lifecycle_transition")
        )
        if transitions != expected_transitions:
            raise PortiaConflictError(
                "Event migration source lifecycle transition history changed "
                "after preflight"
            )
        corrections = _history_snapshot(
            self._event_target_history_records(
                work,
                "lifecycle_history_correction",
            )
        )
        if corrections != expected_corrections:
            raise PortiaConflictError(
                "Event migration source lifecycle-history correction chain changed "
                "after preflight"
            )

    def _require_event_plan_current(
        self,
        plan: MigrationPlan,
        source: ExactPortiaWorkRef,
    ) -> StoredRecord:
        current = self.repository.load_work(source)
        if (
            current.fingerprint != plan.source.fingerprint
            or current.record.to_dict() != plan.source.record.to_dict()
        ):
            raise PortiaConflictError("Event migration source changed after planning")
        return current

    def _require_event_quarantine_allowed(
        self,
        source: ExactPortiaWorkRef,
        destination: ExactPortiaWorkRef,
        *,
        certificate: PortiaRecord,
        transition: PortiaRecord,
    ) -> None:
        for target in (
            work_target(source),
            work_target(destination),
            record_target(source, certificate),
            record_target(source, transition),
        ):
            self.quarantine.require_allowed(target, "block_work_writes")

    def commit(
        self,
        plan: MigrationPlan,
        *,
        migration_id: str,
        transition_id: str,
        created_at: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        plan_validator: PlanValidator,
    ) -> OperationCommitResult:
        """Commit one exact Event work-root migration through the #38 journal gate."""
        source, destination = self._require_exact_pair(plan)
        created = _parsed_timestamp(created_at, description="migration created_at")
        effective = _parsed_timestamp(
            plan.effective_at,
            description="migration effective_at",
        )
        if created < effective:
            raise WorkflowPrerequisiteError(
                "migration created_at cannot precede effective_at"
            )

        certificate = _work_migration_certificate(
            plan,
            migration_id=migration_id,
            created_at=created_at,
        )
        superseded_source = _superseded_event_source(
            plan.source.record,
            updated_at=created_at,
            updated_by=plan.created_by,
        )
        transition = self._intent_transition(
            source,
            plan.source.record,
            superseded_source,
            transition_id=transition_id,
            reason_detail=plan.reason_detail,
            effective_at=plan.effective_at,
        )
        intent_previous_transition_id = self._transition_previous_id(transition)
        expected_previous = (
            None
            if intent_previous_transition_id is None
            else {
                "record_kind": "lifecycle_transition",
                "record_id": intent_previous_transition_id,
                "contract_version": "1",
            }
        )

        digest = _intent_digest(
            plan,
            certificate=certificate,
            transition=transition,
            superseded_source=superseded_source,
        )
        op_id = operation_id or f"op_{digest}"
        replay = self._completed_replay(op_id, digest=digest)
        if replay is not None:
            return replay

        validated = plan_validator(plan)
        self._require_same_plan(plan, validated)
        current = self._require_event_plan_current(validated, source)
        selected_head, transition_snapshot, correction_snapshot = (
            self._event_selected_source_history(source, current.record)
        )
        selected_previous_transition_id: str | None = None
        if selected_head is not None:
            selected_identifier = selected_head.record.logical_id
            if not isinstance(selected_identifier, str):
                raise WorkflowOwnershipError(
                    "selected Event migration lifecycle head has no exact identity"
                )
            selected_previous_transition_id = selected_identifier
        if selected_previous_transition_id != intent_previous_transition_id:
            raise PortiaConflictError(
                "Event migration source lifecycle selection changed during "
                "commit preflight"
            )
        if selected_head is not None:
            head_effective = selected_head.record.field("effective_at")
            if not isinstance(head_effective, str):
                raise WorkflowOwnershipError(
                    "selected Event migration lifecycle head has no effective_at"
                )
            if effective < _parsed_timestamp(
                head_effective,
                description="selected Event lifecycle head effective_at",
            ):
                raise WorkflowPrerequisiteError(
                    "migration effective_at cannot precede the selected Event "
                    "lifecycle head"
                )

        self._require_event_quarantine_allowed(
            source,
            destination,
            certificate=certificate,
            transition=transition,
        )

        source_status = current.record.status
        destination_status = validated.destination.status
        if not isinstance(source_status, str) or not isinstance(
            destination_status, str
        ):
            raise WorkflowPrerequisiteError(
                "Event migration source and destination require lifecycle status"
            )
        if source_status != destination_status:
            raise WorkflowPrerequisiteError(
                "Event migration destination lifecycle changed after planning"
            )

        current_path = work_manifest_path(self.workspace_root, source)
        current_bytes = read_bytes(current.path)
        if fingerprint_bytes(current_bytes) != current.fingerprint:
            raise PortiaConflictError(
                "selected Event migration source changed during commit preflight"
            )

        history_path = work_storage_history_path(
            self.workspace_root,
            source,
            "event",
            source.work_id,
            current.fingerprint.digest,
        )
        destination_path = version_qualified_representation_path(
            self.workspace_root,
            source,
            "event",
            source.work_id,
            destination.contract_version,
        )
        source_version_path = version_qualified_representation_path(
            self.workspace_root,
            source,
            "event",
            source.work_id,
            source.contract_version,
        )
        certificate_path = work_record_path(
            self.workspace_root,
            source,
            "record_migration",
            migration_id,
        )
        transition_path = work_record_path(
            self.workspace_root,
            source,
            "lifecycle_transition",
            transition_id,
        )

        for description, path in (
            ("destination Event representation", destination_path),
            ("Event migration certificate", certificate_path),
            ("Event migration transition", transition_path),
            ("final source Event representation", source_version_path),
        ):
            if path.exists():
                raise PortiaConflictError(
                    f"{description} already exists before journaled migration commit"
                )

        destination_bytes = canonical_json_bytes(validated.destination.to_dict())
        certificate_bytes = canonical_json_bytes(certificate.to_dict())
        transition_bytes = canonical_json_bytes(transition.to_dict())
        superseded_bytes = canonical_json_bytes(superseded_source.to_dict())
        superseded_fp = fingerprint_bytes(superseded_bytes)

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}

        if history_path.exists():
            history_bytes = read_bytes(history_path)
            if (
                history_bytes != current_bytes
                or fingerprint_bytes(history_bytes) != current.fingerprint
            ):
                raise PortiaCorruptionError(
                    "Event migration technical storage-history collision"
                )
        else:
            candidates["step_source_history"] = current_bytes
            steps.append(
                self._step(
                    step_id="step_source_history",
                    sequence=len(steps) + 1,
                    action="exclusive_create",
                    target={"kind": "workspace"},
                    role="operational_revision",
                    destination_path=workspace_relative(
                        self.workspace_root,
                        history_path,
                    ),
                    precondition={"presence": "must_be_absent"},
                    contract_version=source.contract_version,
                    content=current_bytes,
                    selected_state=[_state_fact("status", source_status)],
                    reason_code="preserve_prior_revision",
                )
            )

        candidates["step_destination"] = destination_bytes
        steps.append(
            self._step(
                step_id="step_destination",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target={"kind": "workspace"},
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    destination_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version=destination.contract_version,
                content=destination_bytes,
                selected_state=[_state_fact("status", destination_status)],
                reason_code="prepare_migration_destination",
            )
        )

        certificate_target = record_target(source, certificate)
        candidates["step_certificate"] = certificate_bytes
        steps.append(
            self._step(
                step_id="step_certificate",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target=certificate_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    certificate_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version="1",
                content=certificate_bytes,
                selected_state=[_state_fact("migration", "accepted")],
                reason_code=validated.reason_code,
            )
        )

        transition_target = record_target(source, transition)
        candidates["step_transition"] = transition_bytes
        steps.append(
            self._step(
                step_id="step_transition",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target=transition_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    transition_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version="1",
                content=transition_bytes,
                selected_state=[
                    _state_fact("from_status", source_status),
                    _state_fact("to_status", "superseded"),
                ],
                reason_code="contract_migrated",
            )
        )

        source_target = work_target(source)
        candidates["step_source_superseded"] = superseded_bytes
        steps.append(
            self._step(
                step_id="step_source_superseded",
                sequence=len(steps) + 1,
                action="revision_aware_replace",
                target=source_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    current_path,
                ),
                precondition={
                    "presence": "must_match",
                    "fingerprint": current.fingerprint.to_dict(),
                    "contract_version": source.contract_version,
                    "semantic_checks": [_state_fact("status", source_status)],
                },
                contract_version=source.contract_version,
                content=superseded_bytes,
                selected_state=[_state_fact("status", "superseded")],
                reason_code="contract_migrated",
            )
        )

        candidates["step_source_version"] = superseded_bytes
        steps.append(
            self._step(
                step_id="step_source_version",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target={"kind": "workspace"},
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    source_version_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version=source.contract_version,
                content=superseded_bytes,
                selected_state=[_state_fact("status", "superseded")],
                reason_code="preserve_migrated_source",
            )
        )

        destination_target = work_target(destination)
        candidates["step_current_switch"] = destination_bytes
        steps.append(
            self._step(
                step_id="step_current_switch",
                sequence=len(steps) + 1,
                action="revision_aware_replace",
                target=destination_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    current_path,
                ),
                precondition={
                    "presence": "must_match",
                    "fingerprint": superseded_fp.to_dict(),
                    "contract_version": source.contract_version,
                    "semantic_checks": [_state_fact("status", "superseded")],
                },
                contract_version=destination.contract_version,
                content=destination_bytes,
                selected_state=[_state_fact("status", destination_status)],
                reason_code="select_migration_destination",
            )
        )

        lock_entries, lock_records = _lock_plan(op_id, source, created_at)
        plan_wire = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=created_at,
            initiated_by=validated.created_by,
            primary_target=source_target,
            affected_targets=[
                destination_target,
                certificate_target,
                transition_target,
            ],
            lock_entries=lock_entries,
            steps=steps,
            prior_status=source_status,
            candidate_status=destination_status,
            contract="event",
            operation_kind="migrate_representation",
        )

        work_lock_id = derive_lock_id("work", work_target(source))

        def history_guarded_fault_hook(
            event: str,
            identifier: str | None,
        ) -> None:
            if event == "after_lock_acquire" and identifier == work_lock_id:
                self._require_locked_event_history_state(
                    source,
                    expected_transitions=transition_snapshot,
                    expected_corrections=correction_snapshot,
                )
            if fault_hook is not None:
                fault_hook(event, identifier)

        result = self._writer()._write_plan(
            plan=plan_wire,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=history_guarded_fault_hook,
        )

        accepted_current = self.repository.load_work(destination)
        accepted_source = self.representations.load_preserved_work_representation(
            source
        )
        accepted_destination = self.representations.load_preserved_work_representation(
            destination
        )
        accepted_certificate = self.repository.load_work_record(
            destination,
            "record_migration",
            "1",
            migration_id,
        )
        accepted_transition = self.repository.load_work_record(
            destination,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if accepted_current.record.to_dict() != validated.destination.to_dict():
            raise PortiaCorruptionError(
                "Event migration current-representation readback disagrees "
                "with destination"
            )
        if accepted_destination.record.to_dict() != validated.destination.to_dict():
            raise PortiaCorruptionError(
                "Event migration destination exact-version readback disagrees"
            )
        if accepted_source.record.to_dict() != superseded_source.to_dict():
            raise PortiaCorruptionError(
                "Event migration source exact-version readback is not final "
                "superseded source"
            )
        if accepted_certificate.record.to_dict() != certificate.to_dict():
            raise PortiaCorruptionError(
                "Event migration certificate readback disagrees with committed "
                "certificate"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "Event migration lifecycle-transition readback disagrees with "
                "committed transition"
            )
        if accepted_transition.record.field("previous_transition") != expected_previous:
            raise PortiaCorruptionError(
                "Event migration lifecycle-transition readback selected the wrong "
                "predecessor"
            )
        return result
