"""Exact resolution for the shared judgment-evidence reference family."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from portia.models import PortiaRecord
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    ModuleWorkRecordRef,
)
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)


class ModuleJudgmentEvidenceAuthority(Protocol):
    """Explicit public authority for exact sibling-module judgment evidence."""

    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        """Resolve and authorize one exact sibling-module record reference."""
        ...


@dataclass(frozen=True, slots=True)
class JudgmentEvidenceResolution:
    """Typed result that preserves which judgment-evidence branch was resolved."""

    kind: str
    stored: StoredRecord | None = None
    module_reference: ModuleWorkRecordRef | None = None
    module_value: object | None = None


def _module_reference(value: Mapping[str, object]) -> ModuleWorkRecordRef:
    reference = ModuleWorkRecordRef.from_dict(value.get("module_work_record_ref"))
    if reference.work_ref.module_id != reference.record_ref.module_id:
        raise WorkflowOwnershipError(
            "module judgment evidence work and record identities disagree"
        )
    if reference.work_ref.module_id == "portia":
        raise WorkflowOwnershipError(
            "Portia records must use the portia_record judgment-evidence branch"
        )
    return reference


def resolve_judgment_evidence(
    repository: PortiaRepository,
    value: object,
    *,
    module_authority: ModuleJudgmentEvidenceAuthority | None = None,
) -> JudgmentEvidenceResolution:
    """Resolve one exact judgment-evidence reference without successor following.

    Portia branches resolve through Portia's canonical repository. A sibling-module
    branch requires an explicitly supplied public resolution/authorization authority;
    Portia never guesses a sibling's private storage layout.
    """
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("judgment evidence reference is malformed")
    kind = value.get("kind")

    if kind == "portia_work":
        work_reference = ExactPortiaWorkRef.from_dict(value.get("work_ref"))
        return JudgmentEvidenceResolution(
            kind=kind,
            stored=repository.load_work(work_reference),
        )

    if kind == "portia_record":
        record_reference = ExactPortiaWorkRecordRef.from_dict(
            value.get("work_record_ref")
        )
        stored = repository.load_work_record(
            record_reference.work_ref,
            record_reference.record_ref.record_kind,
            record_reference.record_ref.contract_version,
            record_reference.record_ref.record_id,
        )
        return JudgmentEvidenceResolution(kind=kind, stored=stored)

    if kind == "module_record":
        module_reference = _module_reference(value)
        if module_authority is None:
            raise WorkflowPrerequisiteError(
                "module_record judgment evidence requires an explicit public "
                "resolution authority"
            )
        resolved = module_authority.resolve_exact(module_reference)
        if resolved is None:
            raise WorkflowPrerequisiteError(
                "module_record judgment evidence did not resolve through the "
                "supplied authority"
            )
        return JudgmentEvidenceResolution(
            kind=kind,
            module_reference=module_reference,
            module_value=resolved,
        )

    raise WorkflowOwnershipError(
        f"unsupported judgment evidence reference kind {kind!r}"
    )


def resolve_judgment_evidence_set(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
    *,
    module_authority: ModuleJudgmentEvidenceAuthority | None = None,
    require_module_authority: bool,
    field_name: str = "evidence_considered",
) -> tuple[JudgmentEvidenceResolution, ...]:
    """Resolve one judgment record's exact evidence within its Event boundary.

    Proposed records may preserve a structurally valid sibling-module reference
    without pretending Portia can authorize it. Active/current use requires the
    explicit adapter and therefore fails closed by default.
    """
    evidence = record.field(field_name)
    if evidence is None:
        return ()
    if not isinstance(evidence, tuple):
        raise WorkflowOwnershipError(f"judgment {field_name} is malformed")

    resolved: list[JudgmentEvidenceResolution] = []
    for value in evidence:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError("judgment evidence reference is malformed")
        kind = value.get("kind")
        if kind == "portia_work":
            work_reference = ExactPortiaWorkRef.from_dict(value.get("work_ref"))
            if work_reference != work:
                raise WorkflowOwnershipError(
                    "Event-local judgment evidence cannot resolve another Portia work"
                )
            resolved.append(resolve_judgment_evidence(repository, value))
            continue
        if kind == "portia_record":
            record_reference = ExactPortiaWorkRecordRef.from_dict(
                value.get("work_record_ref")
            )
            if record_reference.work_ref != work:
                raise WorkflowOwnershipError(
                    "Event-local judgment evidence cannot resolve another Portia work"
                )
            resolved.append(resolve_judgment_evidence(repository, value))
            continue
        if kind == "module_record" and not require_module_authority:
            module_reference = _module_reference(value)
            resolved.append(
                JudgmentEvidenceResolution(
                    kind="module_record",
                    module_reference=module_reference,
                )
            )
            continue
        resolved.append(
            resolve_judgment_evidence(
                repository,
                value,
                module_authority=module_authority,
            )
        )
    return tuple(resolved)
