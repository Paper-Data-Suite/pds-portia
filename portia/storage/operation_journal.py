"""Version-aware accessors for durable Operation Journal evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from portia.models import PortiaRecord
from portia.storage.errors import PortiaCorruptionError
from portia.storage.fingerprint import ContentFingerprint


@dataclass(frozen=True, slots=True)
class AbsenceStepView:
    """Validated privacy-minimized view of one v3 canonical absence step."""

    step_id: str
    destination_path: str
    disposition: str
    prior_contract_version: str
    prior_fingerprint: ContentFingerprint
    removal_ref: Mapping[str, Any]
    certificate_path: str
    certificate_fingerprint: ContentFingerprint
    observed_absent: bool


def journal_version(journal: PortiaRecord | Mapping[str, Any]) -> str:
    """Return the explicit journal contract version; never infer from storage."""
    if isinstance(journal, PortiaRecord):
        if journal.contract != "operation_journal":
            raise PortiaCorruptionError("record is not an Operation Journal")
        return journal.contract_version
    version = journal.get("schema_version")
    if not isinstance(version, str):
        raise PortiaCorruptionError("operation journal lacks explicit schema_version")
    return version


def _data(journal: PortiaRecord | Mapping[str, Any]) -> Mapping[str, Any]:
    return journal.to_dict() if isinstance(journal, PortiaRecord) else journal


def is_absence_step(step: object) -> bool:
    return isinstance(step, Mapping) and step.get("action") == "exceptional_remove"


def _target_contract_version(target: object) -> object:
    if not isinstance(target, Mapping):
        return None
    kind = target.get("kind")
    if kind == "work":
        work_ref = target.get("work_ref")
        return work_ref.get("contract_version") if isinstance(work_ref, Mapping) else None
    if kind == "work_record":
        work_record_ref = target.get("work_record_ref")
        if not isinstance(work_record_ref, Mapping):
            return None
        record_ref = work_record_ref.get("record_ref")
        return record_ref.get("contract_version") if isinstance(record_ref, Mapping) else None
    if kind == "actor_directory_record":
        actor_record_ref = target.get("actor_directory_record_ref")
        if not isinstance(actor_record_ref, Mapping):
            return None
        actor_kind = actor_record_ref.get("kind")
        field = {
            "actor": "actor_ref",
            "actor_contact_point": "contact_point_ref",
            "actor_student_relationship": "relationship_ref",
            "actor_roster_student_collision": "collision_ref",
        }.get(str(actor_kind))
        nested = actor_record_ref.get(field) if field is not None else None
        return nested.get("contract_version") if isinstance(nested, Mapping) else None
    return None


def absence_step_view(step: object) -> AbsenceStepView:
    """Return a strict typed view without resolving external certificate state."""
    if not isinstance(step, Mapping) or step.get("action") != "exceptional_remove":
        raise PortiaCorruptionError("write step is not exceptional_remove")
    intended = step.get("intended_result")
    precondition = step.get("precondition")
    if not isinstance(intended, Mapping) or intended.get("kind") != "absent":
        raise PortiaCorruptionError("exceptional_remove requires absent intended_result")
    if not isinstance(precondition, Mapping) or precondition.get("presence") != "must_match":
        raise PortiaCorruptionError("exceptional_remove requires exact must_match precondition")
    try:
        prior = ContentFingerprint.from_dict(intended.get("prior_fingerprint"))
        preflight = ContentFingerprint.from_dict(precondition.get("fingerprint"))
    except ValueError as exc:
        raise PortiaCorruptionError("exceptional_remove lacks an exact prior fingerprint") from exc
    prior_version = intended.get("prior_contract_version")
    if prior != preflight or prior_version != precondition.get("contract_version"):
        raise PortiaCorruptionError(
            "absence intent does not agree with the exact precondition"
        )
    link = intended.get("removal_certificate")
    if not isinstance(link, Mapping):
        raise PortiaCorruptionError("absence intent lacks removal certificate linkage")
    removal_ref = link.get("ref")
    certificate_path = link.get("workspace_relative_path")
    if not isinstance(removal_ref, Mapping) or not isinstance(certificate_path, str):
        raise PortiaCorruptionError("removal certificate linkage is incomplete")
    try:
        certificate_fp = ContentFingerprint.from_dict(link.get("fingerprint"))
    except ValueError as exc:
        raise PortiaCorruptionError("removal certificate link lacks an exact fingerprint") from exc
    step_id = step.get("step_id")
    destination = step.get("destination_path")
    disposition = step.get("disposition")
    if (
        not isinstance(step_id, str)
        or not isinstance(destination, str)
        or not isinstance(disposition, str)
        or not isinstance(prior_version, str)
    ):
        raise PortiaCorruptionError("exceptional_remove step identity is incomplete")
    observed = step.get("observed_result")
    observed_absent = isinstance(observed, Mapping) and observed.get("kind") == "absent"
    if isinstance(observed, Mapping) and observed.get("workspace_relative_path") != destination:
        raise PortiaCorruptionError("absence observation path differs from its destination")
    return AbsenceStepView(
        step_id=step_id,
        destination_path=destination,
        disposition=disposition,
        prior_contract_version=prior_version,
        prior_fingerprint=prior,
        removal_ref=removal_ref,
        certificate_path=certificate_path,
        certificate_fingerprint=certificate_fp,
        observed_absent=observed_absent,
    )


def validate_operation_journal_application(
    journal: PortiaRecord | Mapping[str, Any],
) -> None:
    """Enforce cross-field version/action rules not expressible as simple types."""
    version = journal_version(journal)
    if version not in {"2", "3"}:
        raise PortiaCorruptionError(f"unsupported current journal version: {version}")
    data = _data(journal)
    raw_steps = data.get("write_set")
    if not isinstance(raw_steps, list):
        raise PortiaCorruptionError("operation journal write_set is not an array")
    absence_steps = [step for step in raw_steps if is_absence_step(step)]
    if version == "2":
        if absence_steps:
            raise PortiaCorruptionError(
                "exceptionally_remove operations with canonical absence require operation_journal@3"
            )
        return
    if absence_steps and data.get("operation_kind") != "exceptionally_remove":
        raise PortiaCorruptionError(
            "exceptional_remove action requires exceptionally_remove operation kind"
        )
    for step in absence_steps:
        view = absence_step_view(step)
        if _target_contract_version(step.get("target")) != view.prior_contract_version:
            raise PortiaCorruptionError(
                f"exceptional_remove prior version differs from its exact target: {view.step_id}"
            )
        if step.get("phase") != "canonical_gate" or step.get("representation_role") != "canonical_domain":
            raise PortiaCorruptionError(
                f"exceptional_remove must be a canonical-domain gate: {view.step_id}"
            )
        if view.disposition in {"durable", "verified", "accepted"} and not view.observed_absent:
            raise PortiaCorruptionError(
                f"durable exceptional_remove lacks observed absence: {view.step_id}"
            )
        sequence = step.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise PortiaCorruptionError(
                f"exceptional_remove lacks an exact sequence: {view.step_id}"
            )

        def is_certificate_step(candidate: object) -> bool:
            if not isinstance(candidate, Mapping):
                return False
            candidate_sequence = candidate.get("sequence")
            return (
                candidate.get("destination_path") == view.certificate_path
                and candidate.get("action") == "exclusive_create"
                and candidate.get("representation_role") == "canonical_domain"
                and isinstance(candidate_sequence, int)
                and not isinstance(candidate_sequence, bool)
                and candidate_sequence < sequence
            )

        certificate_steps = [
            candidate
            for candidate in raw_steps
            if is_certificate_step(candidate)
        ]
        if len(certificate_steps) != 1:
            raise PortiaCorruptionError(
                f"exceptional_remove must follow one exact certificate write: {view.step_id}"
            )
        certificate_intent = certificate_steps[0].get("intended_result")
        certificate_target = certificate_steps[0].get("target")
        expected_certificate_kind = (
            "exceptional_removal"
            if "class_id" in view.removal_ref
            else "actor_directory_removal"
        )
        if (
            not isinstance(certificate_target, Mapping)
            or certificate_target.get("kind") != expected_certificate_kind
            or certificate_target.get("removal_ref") != view.removal_ref
        ):
            raise PortiaCorruptionError(
                "absence certificate link differs from its certificate write target"
            )
        if not isinstance(certificate_intent, Mapping):
            raise PortiaCorruptionError("certificate write lacks intended bytes")
        try:
            planned_certificate = ContentFingerprint.from_dict(
                certificate_intent.get("fingerprint")
            )
        except ValueError as exc:
            raise PortiaCorruptionError("certificate write lacks exact fingerprint") from exc
        if certificate_intent.get("kind") != "present" or planned_certificate != view.certificate_fingerprint:
            raise PortiaCorruptionError(
                "absence certificate link differs from its preceding certificate write"
            )
        certificate_disposition = certificate_steps[0].get("disposition")
        if (
            view.disposition == "durable"
            and certificate_disposition not in {"durable", "verified", "accepted"}
        ) or (
            view.disposition in {"verified", "accepted"}
            and certificate_disposition != "accepted"
        ):
            raise PortiaCorruptionError(
                "durable absence cannot outrun its exact certificate evidence"
            )


def absence_steps(
    journal: PortiaRecord | Mapping[str, Any],
) -> tuple[AbsenceStepView, ...]:
    """Return all validated canonical absence steps in deterministic write-set order."""
    validate_operation_journal_application(journal)
    if journal_version(journal) != "3":
        return ()
    raw_steps = _data(journal).get("write_set")
    assert isinstance(raw_steps, list)
    return tuple(absence_step_view(step) for step in raw_steps if is_absence_step(step))
