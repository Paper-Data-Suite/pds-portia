"""Evidence-first inspection for interrupted Portia operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from portia.models import parse_portia_record
from portia.storage.errors import (
    PortiaAmbiguousRecoveryError,
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import ContentFingerprint, canonical_json_bytes
from portia.storage.integrity import (
    PersistenceFinding,
    validate_operation_durable_state,
)
from portia.storage.io import guarded_replace, read_json
from portia.storage.paths import operation_current_path, operation_revision_path
from portia.storage.series import (
    OperationJournalStore,
    RecoveryObservation,
    SeriesState,
)


@dataclass(frozen=True, slots=True)
class OperationRecoveryAssessment:
    """Non-mutating recovery classification for one exact operation series."""

    operation_id: str
    state: str | None
    disposition: str
    series: RecoveryObservation
    findings: tuple[PersistenceFinding, ...]


class OperationRecovery:
    """Conservative recovery facade; inspection is separate from explicit repair."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self.store = OperationJournalStore(self.root)

    def assess(self, operation_id: str) -> OperationRecoveryAssessment:
        series = self.store.inspect_recovery(operation_id)
        if series.disposition == "absent":
            return OperationRecoveryAssessment(operation_id, None, "absent", series, ())
        if series.disposition == "pointer_missing_manual_recovery":
            return OperationRecoveryAssessment(
                operation_id,
                None,
                "manual_review",
                series,
                (),
            )
        if series.disposition == "orphan_linear_successor":
            current = self.store.load_current(operation_id)
            state = current.revision.to_dict().get("state")
            return OperationRecoveryAssessment(
                operation_id,
                state if isinstance(state, str) else None,
                "restore_pointer_candidate",
                series,
                (),
            )

        current = self.store.load_current(operation_id)
        state_value = current.revision.to_dict().get("state")
        state = state_value if isinstance(state_value, str) else None
        findings = validate_operation_durable_state(self.root, current.revision)
        if findings:
            return OperationRecoveryAssessment(
                operation_id,
                state,
                "quarantine_or_manual_review",
                series,
                findings,
            )
        if state in {"completed", "compensated", "aborted"}:
            disposition = "terminal_consistent"
        elif state == "committed":
            disposition = "finalize_post_commit"
        elif state in {"prepared", "staged", "committing", "recovering"}:
            disposition = "resume"
        elif state in {"quarantined", "failed", "compensating"}:
            disposition = "manual_review"
        else:
            disposition = "manual_review"
        return OperationRecoveryAssessment(
            operation_id,
            state,
            disposition,
            series,
            (),
        )

    def select_exact_orphan_successor(
        self,
        operation_id: str,
        *,
        expected_pointer: ContentFingerprint,
    ) -> SeriesState:
        """Advance only one exact, valid, linear orphan successor after inspection."""
        observation = self.store.inspect_recovery(operation_id)
        if (
            observation.disposition != "orphan_linear_successor"
            or len(observation.orphan_successors) != 1
        ):
            raise PortiaAmbiguousRecoveryError(
                "recovery does not expose exactly one safe orphan successor"
            )
        current = self.store.load_current(operation_id)
        if current.pointer_fingerprint != expected_pointer:
            raise PortiaConflictError(
                "operation current pointer changed before recovery"
            )
        successor_number = observation.orphan_successors[0]
        successor_path = operation_revision_path(
            self.root, operation_id, successor_number
        )
        successor_value, _successor_bytes, _successor_fp = read_json(successor_path)
        try:
            successor = parse_portia_record("operation_journal", "2", successor_value)
        except Exception as exc:
            raise PortiaCorruptionError(
                "orphan successor is not a valid current journal"
            ) from exc
        successor_data = successor.to_dict()
        selected = current.revision.to_dict().get("journal_revision")
        if successor_data.get("previous_journal_revision") != selected:
            raise PortiaAmbiguousRecoveryError(
                "orphan successor does not name the selected revision as predecessor"
            )
        if successor_data.get("intent_digest") != current.revision.to_dict().get(
            "intent_digest"
        ):
            raise PortiaAmbiguousRecoveryError(
                "orphan successor changes immutable operation intent"
            )

        pointer_data = current.pointer.to_dict()
        pointer_data["journal_revision"] = successor_number
        try:
            replacement_pointer = parse_portia_record(
                "operation_current_pointer",
                "1",
                pointer_data,
            )
        except Exception as exc:
            raise PortiaCorruptionError(
                "recovery pointer candidate is invalid"
            ) from exc
        pointer_path = operation_current_path(self.root, operation_id)
        try:
            guarded_replace(
                pointer_path,
                canonical_json_bytes(replacement_pointer.to_dict()),
                expected=expected_pointer,
            )
        except Exception as exc:
            raise PortiaRecoveryRequiredError(
                "orphan successor remains durable but pointer recovery did not complete"
            ) from exc
        return self.store.load_current(operation_id)
