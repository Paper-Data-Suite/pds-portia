from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .schema_support import (
        REPO_ROOT,
        SchemaCatalogError,
        SchemaStore,
        load_json_object,
        validator_for,
    )
except ImportError:
    from schema_support import (
        REPO_ROOT,
        SchemaCatalogError,
        SchemaStore,
        load_json_object,
        validator_for,
    )


CORPUS_ROOT = REPO_ROOT / "tests" / "fixtures" / "issue_22"
CORPUS_PATH = CORPUS_ROOT / "corpus.json"

CORPUS_CONTRACT = "pds-portia.representative-contract-graph-corpus"
SCENARIO_CONTRACT = "pds-portia.representative-contract-graph-scenario"
FIXTURE_VERSION = "1"


@dataclass(frozen=True, order=True)
class GraphFinding:
    code: str
    scenario_id: str
    message: str


@dataclass(frozen=True)
class ScenarioRecord:
    descriptor: Mapping[str, Any]
    value: Mapping[str, Any]
    path: Path

    @property
    def contract(self) -> str:
        return str(self.descriptor["contract"])

    @property
    def version(self) -> str:
        return str(self.descriptor["version"])

    @property
    def logical_identity(self) -> str:
        return str(self.descriptor["logical_identity"])


def _safe_fixture_path(base: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValueError(f"absolute fixture path is not allowed: {relative!r}")

    root = CORPUS_ROOT.resolve()
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"fixture path escapes Issue #22 corpus: {relative!r}"
        ) from exc
    return resolved


def load_corpus() -> dict[str, Any]:
    return load_json_object(CORPUS_PATH)


def scenario_path_from_entry(entry: Mapping[str, Any]) -> Path:
    relative = entry.get("path")
    if not isinstance(relative, str) or not relative:
        raise ValueError("scenario entry must contain a nonempty path")
    return _safe_fixture_path(CORPUS_ROOT, relative)


def load_scenario(path: Path) -> dict[str, Any]:
    return load_json_object(path)


def scenario_by_id(
    corpus: Mapping[str, Any],
    scenario_id: str,
) -> tuple[Path, dict[str, Any]]:
    scenarios = corpus.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("corpus scenarios must be an array")

    for entry in scenarios:
        if (
            isinstance(entry, dict)
            and entry.get("scenario_id") == scenario_id
        ):
            path = scenario_path_from_entry(entry)
            return path, load_scenario(path)
    raise KeyError(scenario_id)


def load_scenario_records(
    scenario_path: Path,
    scenario: Mapping[str, Any],
) -> tuple[ScenarioRecord, ...]:
    descriptors = scenario.get("records")
    if not isinstance(descriptors, list):
        raise ValueError("scenario records must be an array")

    records: list[ScenarioRecord] = []
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError("record descriptor must be an object")
        relative = descriptor.get("fixture_path")
        if not isinstance(relative, str) or not relative:
            raise ValueError("record descriptor fixture_path must be nonempty")
        path = _safe_fixture_path(scenario_path.parent, relative)
        records.append(
            ScenarioRecord(
                descriptor=descriptor,
                value=load_json_object(path),
                path=path,
            )
        )
    return tuple(records)


def load_operational_contract_fixtures(
    scenario_path: Path,
    scenario: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], Mapping[str, Any], Path], ...]:
    descriptors = scenario.get("operational_contract_fixtures", [])
    if not isinstance(descriptors, list):
        raise ValueError("operational_contract_fixtures must be an array")

    fixtures: list[tuple[Mapping[str, Any], Mapping[str, Any], Path]] = []
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError("operational fixture descriptor must be an object")
        relative = descriptor.get("fixture_path")
        contract = descriptor.get("contract")
        version = descriptor.get("version")
        if not isinstance(relative, str) or not relative:
            raise ValueError("operational fixture_path must be nonempty")
        if not isinstance(contract, str) or not contract:
            raise ValueError("operational fixture contract must be nonempty")
        if not isinstance(version, str) or not version:
            raise ValueError("operational fixture version must be nonempty")
        path = _safe_fixture_path(scenario_path.parent, relative)
        fixtures.append((descriptor, load_json_object(path), path))
    return tuple(fixtures)


def load_derived_contract_fixtures(
    scenario_path: Path,
    scenario: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], Mapping[str, Any], Path], ...]:
    descriptors = scenario.get("derived_contract_fixtures", [])
    if not isinstance(descriptors, list):
        raise ValueError("derived_contract_fixtures must be an array")

    fixtures: list[tuple[Mapping[str, Any], Mapping[str, Any], Path]] = []
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError("derived fixture descriptor must be an object")
        relative = descriptor.get("fixture_path")
        contract = descriptor.get("contract")
        version = descriptor.get("version")
        if not isinstance(relative, str) or not relative:
            raise ValueError("derived fixture_path must be nonempty")
        if not isinstance(contract, str) or not contract:
            raise ValueError("derived fixture contract must be nonempty")
        if not isinstance(version, str) or not version:
            raise ValueError("derived fixture version must be nonempty")
        path = _safe_fixture_path(scenario_path.parent, relative)
        fixtures.append((descriptor, load_json_object(path), path))
    return tuple(fixtures)


def load_contexts(
    scenario_path: Path,
    scenario: Mapping[str, Any],
) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    descriptors = scenario.get("context", [])
    if not isinstance(descriptors, list):
        raise ValueError("scenario context must be an array")

    contexts: list[tuple[str, Mapping[str, Any]]] = []
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError("context descriptor must be an object")
        kind = descriptor.get("context_kind")
        relative = descriptor.get("fixture_path")
        if not isinstance(kind, str) or not kind:
            raise ValueError("context_kind must be a nonempty string")
        if not isinstance(relative, str) or not relative:
            raise ValueError("context fixture_path must be nonempty")
        path = _safe_fixture_path(scenario_path.parent, relative)
        contexts.append((kind, load_json_object(path)))
    return tuple(contexts)


def _first_structural_error_message(errors: Sequence[Any]) -> str:
    if not errors:
        return ""
    error = sorted(
        errors,
        key=lambda item: (
            tuple(str(piece) for piece in item.absolute_path),
            item.message,
        ),
    )[0]
    path = ".".join(str(piece) for piece in error.absolute_path)
    prefix = f"{path}: " if path else ""
    return f"{prefix}{error.message}"[:400]


def validate_structural_records(
    scenario_path: Path,
    scenario: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any],
    store: SchemaStore,
) -> tuple[GraphFinding, ...]:
    scenario_id = str(scenario.get("scenario_id", "<unknown>"))
    findings: list[GraphFinding] = []

    try:
        records = load_scenario_records(scenario_path, scenario)
    except (OSError, ValueError, SchemaCatalogError) as exc:
        return (
            GraphFinding(
                "G22.STRUCTURAL.FIXTURE_LOAD",
                scenario_id,
                str(exc)[:400],
            ),
        )

    for record in records:
        try:
            validator = validator_for(
                record.contract,
                record.version,
                catalog=catalog,
                store=store,
            )
        except SchemaCatalogError as exc:
            findings.append(
                GraphFinding(
                    "G22.STRUCTURAL.UNKNOWN_CONTRACT",
                    scenario_id,
                    (
                        f"{record.logical_identity}: "
                        f"{str(exc)[:300]}"
                    ),
                )
            )
            continue

        errors = tuple(validator.iter_errors(record.value))
        if errors:
            findings.append(
                GraphFinding(
                    "G22.STRUCTURAL.INVALID",
                    scenario_id,
                    (
                        f"{record.logical_identity}: "
                        f"{_first_structural_error_message(errors)}"
                    ),
                )
            )

    try:
        operational = load_operational_contract_fixtures(
            scenario_path,
            scenario,
        )
    except (OSError, ValueError, SchemaCatalogError) as exc:
        findings.append(
            GraphFinding(
                "G22.STRUCTURAL.FIXTURE_LOAD",
                scenario_id,
                str(exc)[:400],
            )
        )
        return tuple(sorted(findings))

    for descriptor, value, _path in operational:
        contract = str(descriptor["contract"])
        version = str(descriptor["version"])
        label = f"operational:{contract}:{descriptor.get('fixture_path')}"
        try:
            validator = validator_for(
                contract,
                version,
                catalog=catalog,
                store=store,
            )
        except SchemaCatalogError as exc:
            findings.append(
                GraphFinding(
                    "G22.STRUCTURAL.UNKNOWN_CONTRACT",
                    scenario_id,
                    f"{label}: {str(exc)[:300]}",
                )
            )
            continue
        errors = tuple(validator.iter_errors(value))
        if errors:
            findings.append(
                GraphFinding(
                    "G22.STRUCTURAL.INVALID",
                    scenario_id,
                    (
                        f"{label}: "
                        f"{_first_structural_error_message(errors)}"
                    ),
                )
            )

    try:
        derived = load_derived_contract_fixtures(
            scenario_path,
            scenario,
        )
    except (OSError, ValueError, SchemaCatalogError) as exc:
        findings.append(
            GraphFinding(
                "G22.STRUCTURAL.FIXTURE_LOAD",
                scenario_id,
                str(exc)[:400],
            )
        )
        return tuple(sorted(findings))

    for descriptor, value, _path in derived:
        contract = str(descriptor["contract"])
        version = str(descriptor["version"])
        label = f"derived:{contract}:{descriptor.get('fixture_path')}"
        try:
            validator = validator_for(
                contract,
                version,
                catalog=catalog,
                store=store,
            )
        except SchemaCatalogError as exc:
            findings.append(
                GraphFinding(
                    "G22.STRUCTURAL.UNKNOWN_CONTRACT",
                    scenario_id,
                    f"{label}: {str(exc)[:300]}",
                )
            )
            continue
        errors = tuple(validator.iter_errors(value))
        if errors:
            findings.append(
                GraphFinding(
                    "G22.STRUCTURAL.INVALID",
                    scenario_id,
                    f"{label}: {_first_structural_error_message(errors)}",
                )
            )

    return tuple(sorted(findings))


def _id_for_record(record: ScenarioRecord) -> str | None:
    value = record.value

    # Capture records carry several lineage identifiers simultaneously.
    # Resolve their own identity by contract before considering generic
    # domain-record identifiers so a contextual page_target_id cannot shadow
    # page_record_id / interpretation_id / proposal_id / review_id.
    capture_identity_keys = {
        "page_target": "page_target_id",
        "page_record": "page_record_id",
        "paper_interpretation": "interpretation_id",
        "capture_proposal": "proposal_id",
        "capture_review": "review_id",
    }
    support_identity_keys = {
        "support_process_participant": "participant_id",
        "support_need": "need_id",
        "support_goal": "goal_id",
        "support": "support_id",
        "intervention": "intervention_id",
        "implementation": "implementation_id",
        "fidelity": "fidelity_id",
        "follow_up": "follow_up_id",
        "outcome": "outcome_id",
        "reentry": "reentry_id",
        "repair": "repair_id",
    }
    support_key = support_identity_keys.get(record.contract)
    if support_key is not None:
        support_record_id = value.get(support_key)
        return (
            support_record_id
            if isinstance(support_record_id, str)
            else None
        )

    if record.contract == "deliberate_export":
        export_id = value.get("export_id")
        return export_id if isinstance(export_id, str) else None

    actor_identity_keys = {
        "actor": "actor_id",
        "actor_contact_point": "contact_point_id",
        "actor_student_relationship": "relationship_id",
    }
    actor_key = actor_identity_keys.get(record.contract)
    if actor_key is not None:
        actor_record_id = value.get(actor_key)
        return (
            actor_record_id
            if isinstance(actor_record_id, str)
            else None
        )

    import_identity_keys = {
        "import_batch": "import_batch_id",
        "import_source_record": "source_record_id",
        "import_proposal": "proposal_id",
        "import_review": "review_id",
    }
    import_key = import_identity_keys.get(record.contract)
    if import_key is not None:
        import_id = value.get(import_key)
        return import_id if isinstance(import_id, str) else None

    capture_key = capture_identity_keys.get(record.contract)
    if capture_key is not None:
        capture_id = value.get(capture_key)
        return capture_id if isinstance(capture_id, str) else None

    if record.contract == "capture_materialization":
        operation_ref = value.get("operation_journal_ref")
        review_ref = value.get("review_ref")
        if isinstance(operation_ref, dict) and isinstance(review_ref, dict):
            operation_id = operation_ref.get("operation_id")
            revision = operation_ref.get("journal_revision")
            review_id = review_ref.get("review_id")
            sequence = review_ref.get("review_sequence")
            if (
                isinstance(operation_id, str)
                and isinstance(revision, int)
                and isinstance(review_id, str)
                and isinstance(sequence, int)
            ):
                return (
                    f"{operation_id}--r{revision}--"
                    f"{review_id}--s{sequence}"
                )
        return None

    if record.contract == "import_materialization":
        operation_ref = value.get("operation_journal_ref")
        review_ref = value.get("review_ref")
        if isinstance(operation_ref, dict) and isinstance(review_ref, dict):
            operation_id = operation_ref.get("operation_id")
            revision = operation_ref.get("journal_revision")
            review_id = review_ref.get("review_id")
            sequence = review_ref.get("review_sequence")
            if (
                isinstance(operation_id, str)
                and isinstance(revision, int)
                and isinstance(review_id, str)
                and isinstance(sequence, int)
            ):
                return (
                    f"{operation_id}--r{revision}--"
                    f"{review_id}--s{sequence}"
                )
        return None

    for key in (
        "participant_id",
        "role_id",
        "observation_id",
        "account_id",
        "review_id",
        "disagreement_id",
        "transition_id",
        "classification_id",
        "hypothesis_id",
        "determination_id",
        "response_id",
        "communication_id",
        "support_process_id",
        "support_need_id",
        "support_goal_id",
        "support_id",
        "intervention_id",
        "implementation_id",
        "fidelity_id",
        "follow_up_id",
        "outcome_id",
        "reentry_id",
        "repair_id",
        "relationship_id",
        "dependency_id",
        "migration_id",
    ):
        value_id = value.get(key)
        if isinstance(value_id, str):
            return value_id

    return None


def _expected_work_root(owner: Mapping[str, Any]) -> str | None:
    class_id = owner.get("class_id")
    work_id = owner.get("work_id")
    if not isinstance(class_id, str) or not isinstance(work_id, str):
        return None
    return (
        f"classes/{class_id}/modules/portia/work/{work_id}"
    )


def _canonical_path_for_record(record: ScenarioRecord) -> str | None:
    owner = record.descriptor.get("owner")
    if not isinstance(owner, dict):
        return None

    if owner.get("owner_kind") == "deliberate_export":
        export_id = owner.get("export_id")
        if (
            record.contract == "deliberate_export"
            and isinstance(export_id, str)
            and record.value.get("export_id") == export_id
        ):
            return f"portia/exports/{export_id}/export.json"
        return None

    if owner.get("owner_kind") == "actor":
        actor_id = owner.get("actor_id")
        if not isinstance(actor_id, str):
            return None
        root = f"portia/actors/{actor_id}"
        record_id = _id_for_record(record)

        if record.contract == "actor":
            return f"{root}/actor.json"
        if (
            record.contract == "actor_contact_point"
            and record_id is not None
        ):
            return (
                f"{root}/records/actor_contact_point/"
                f"{record_id}.json"
            )
        if (
            record.contract == "actor_student_relationship"
            and record_id is not None
        ):
            return (
                f"{root}/records/actor_student_relationship/"
                f"{record_id}.json"
            )
        return None

    if owner.get("owner_kind") == "import_batch":
        class_id = owner.get("class_id")
        import_batch_id = owner.get("import_batch_id")
        if not isinstance(class_id, str) or not isinstance(import_batch_id, str):
            return None
        root = (
            f"classes/{class_id}/modules/portia/"
            f"imports/{import_batch_id}"
        )
        record_id = _id_for_record(record)

        if record.contract == "import_batch":
            return f"{root}/batch.json"
        if record.contract == "import_source_record" and record_id is not None:
            return f"{root}/source-records/{record_id}.json"
        if record.contract == "import_proposal" and record_id is not None:
            return f"{root}/proposals/{record_id}.json"
        if record.contract == "import_review" and record_id is not None:
            sequence = record.value.get("review_sequence")
            if isinstance(sequence, int):
                return f"{root}/reviews/{record_id}--s{sequence}.json"
            return None
        if record.contract == "import_materialization" and record_id is not None:
            return f"{root}/materializations/{record_id}.json"
        return None

    root = _expected_work_root(owner)
    if root is None:
        return None

    if record.value.get("record_type") == "portia_work":
        return f"{root}/work.json"

    record_id = _id_for_record(record)
    if record_id is None:
        return None

    record_kind = record.value.get("record_type")
    if not isinstance(record_kind, str):
        return None
    return f"{root}/records/{record_kind}/{record_id}.json"


def _active_records_by_type(
    records: Sequence[ScenarioRecord],
) -> dict[str, list[ScenarioRecord]]:
    result: dict[str, list[ScenarioRecord]] = {}
    for record in records:
        record_type = record.value.get("record_type")
        if (
            isinstance(record_type, str)
            and record.value.get("status") == "active"
        ):
            result.setdefault(record_type, []).append(record)
    return result



def durable_subject_key(
    subject: Mapping[str, Any],
) -> tuple[str, ...] | None:
    kind = subject.get("kind")

    if kind == "roster_student":
        ref = subject.get("roster_student_ref")
        if not isinstance(ref, dict):
            return None
        class_id = ref.get("class_id")
        student_id = ref.get("student_id")
        if isinstance(class_id, str) and isinstance(student_id, str):
            return ("roster_student", class_id, student_id)
        return None

    if kind == "actor":
        ref = subject.get("actor_ref")
        if not isinstance(ref, dict):
            return None
        actor_id = ref.get("actor_id")
        if isinstance(actor_id, str):
            return ("actor", actor_id)
        return None

    # Descriptive/unknown people intentionally have no durable identity key.
    return None


def _roster_contexts(
    contexts: Sequence[tuple[str, Mapping[str, Any]]],
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        value
        for kind, value in contexts
        if kind == "synthetic_core_roster"
    )


def _roster_subject_resolves(
    subject: Mapping[str, Any],
    rosters: Sequence[Mapping[str, Any]],
) -> bool:
    if subject.get("kind") != "roster_student":
        return True

    ref = subject.get("roster_student_ref")
    if not isinstance(ref, dict):
        return False

    class_id = ref.get("class_id")
    student_id = ref.get("student_id")
    for roster in rosters:
        if roster.get("class_id") != class_id:
            continue
        students = roster.get("students")
        if not isinstance(students, list):
            continue
        for student in students:
            if (
                isinstance(student, dict)
                and student.get("student_id") == student_id
            ):
                return True
    return False


def _participant_refs_from_target(
    target: Mapping[str, Any],
) -> tuple[tuple[str, str | None], ...]:
    kind = target.get("kind")
    if kind == "event_participant":
        refs = [target.get("record_ref")]
    elif kind == "event_participants":
        targets = target.get("targets")
        if not isinstance(targets, list):
            return ()
        refs = [
            item.get("record_ref")
            for item in targets
            if isinstance(item, dict)
        ]
    else:
        return ()

    result: list[tuple[str, str | None]] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        record_id = ref.get("record_id")
        version = ref.get("contract_version")
        if isinstance(record_id, str):
            result.append(
                (
                    record_id,
                    version if isinstance(version, str) else None,
                )
            )
    return tuple(result)



def _record_lookup_key(
    record: ScenarioRecord,
) -> tuple[str, str, str, str, str] | None:
    owner = record.descriptor.get("owner")
    if not isinstance(owner, dict):
        return None
    class_id = owner.get("class_id")
    work_id = owner.get("work_id")
    record_id = (
        record.value.get("work_id")
        if record.value.get("record_type") == "portia_work"
        else _id_for_record(record)
    )
    if not all(
        isinstance(value, str)
        for value in (class_id, work_id, record_id)
    ):
        return None
    return (
        str(class_id),
        str(work_id),
        record.contract,
        str(record_id),
        record.version,
    )


def _exact_portia_ref_key(
    work_record_ref: Mapping[str, Any],
) -> tuple[str, str, str, str, str] | None:
    work_ref = work_record_ref.get("work_ref")
    record_ref = work_record_ref.get("record_ref")
    if not isinstance(work_ref, dict) or not isinstance(record_ref, dict):
        return None
    class_id = work_ref.get("class_id")
    work_id = work_ref.get("work_id")
    record_kind = record_ref.get("record_kind")
    record_id = record_ref.get("record_id")
    version = record_ref.get("contract_version")
    if not all(
        isinstance(value, str)
        for value in (class_id, work_id, record_kind, record_id, version)
    ):
        return None
    return (
        str(class_id),
        str(work_id),
        str(record_kind),
        str(record_id),
        str(version),
    )


def _portia_evidence_refs(
    record: ScenarioRecord,
) -> tuple[Mapping[str, Any], ...]:
    refs: list[Mapping[str, Any]] = []

    if record.contract == "review":
        entries = record.value.get("evidence_considered", [])
        if isinstance(entries, list):
            for entry in entries:
                if (
                    isinstance(entry, dict)
                    and entry.get("kind") == "portia_record"
                    and isinstance(entry.get("work_record_ref"), dict)
                ):
                    refs.append(entry["work_record_ref"])

    if record.contract == "classification":
        entries = record.value.get("basis", [])
        if isinstance(entries, list):
            for entry in entries:
                if (
                    isinstance(entry, dict)
                    and entry.get("kind") == "portia_record"
                    and isinstance(entry.get("work_record_ref"), dict)
                ):
                    refs.append(entry["work_record_ref"])

    if record.contract in {"hypothesis", "determination"}:
        field = "evidence" if record.contract == "hypothesis" else "basis"
        entries = record.value.get(field, [])
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                evidence_ref = entry.get("evidence_ref")
                if (
                    isinstance(evidence_ref, dict)
                    and evidence_ref.get("kind") == "portia_record"
                    and isinstance(evidence_ref.get("work_record_ref"), dict)
                ):
                    refs.append(evidence_ref["work_record_ref"])

    return tuple(refs)


def _local_basis_refs(
    record: ScenarioRecord,
) -> tuple[tuple[str, str, str], ...]:
    if record.contract != "event_participant_role":
        return ()

    entries = record.value.get("basis", [])
    if not isinstance(entries, list):
        return ()

    result: list[tuple[str, str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        record_ref = entry.get("record_ref")
        if kind not in {"account_ref", "observation_ref"}:
            continue
        if not isinstance(record_ref, dict):
            continue
        record_kind = record_ref.get("record_kind")
        record_id = record_ref.get("record_id")
        version = record_ref.get("contract_version")
        if all(isinstance(value, str) for value in (record_kind, record_id, version)):
            result.append((str(record_kind), str(record_id), str(version)))
    return tuple(result)


def _account_source_subject(
    record: ScenarioRecord,
) -> Mapping[str, Any] | None:
    if record.contract != "account":
        return None
    source = record.value.get("source")
    return source if isinstance(source, dict) else None


def _work_ref_agrees_with_owner(
    record: ScenarioRecord,
    work_record_ref: Mapping[str, Any],
) -> bool:
    owner = record.descriptor.get("owner")
    work_ref = work_record_ref.get("work_ref")
    if not isinstance(owner, dict) or not isinstance(work_ref, dict):
        return False
    return (
        work_ref.get("module_id") == "portia"
        and work_ref.get("class_id") == owner.get("class_id")
        and work_ref.get("work_id") == owner.get("work_id")
        and work_ref.get("work_kind") == owner.get("work_kind")
    )


def _local_record_ref_key(
    *,
    class_id: str,
    work_id: str,
    record_ref: Mapping[str, Any],
) -> tuple[str, str, str, str, str] | None:
    record_kind = record_ref.get("record_kind")
    record_id = record_ref.get("record_id")
    version = record_ref.get("contract_version")
    if not all(
        isinstance(value, str)
        for value in (record_kind, record_id, version)
    ):
        return None
    return (
        class_id,
        work_id,
        str(record_kind),
        str(record_id),
        str(version),
    )


def replacement_frontier(
    records: Sequence[ScenarioRecord],
    contract: str,
) -> tuple[str, ...]:
    family = [
        record
        for record in records
        if record.contract == contract
    ]
    predecessor_ids: set[str] = set()

    for record in family:
        entries = record.value.get("supersedes", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            work_record_ref = entry.get("work_record_ref")
            if not isinstance(work_record_ref, dict):
                continue
            record_ref = work_record_ref.get("record_ref")
            if not isinstance(record_ref, dict):
                continue
            record_id = record_ref.get("record_id")
            if isinstance(record_id, str):
                predecessor_ids.add(record_id)

    result: list[str] = []
    for record in family:
        record_id = _id_for_record(record)
        if (
            isinstance(record_id, str)
            and record_id not in predecessor_ids
            and record.value.get("status") == "active"
        ):
            result.append(record_id)
    return tuple(sorted(result))


def lifecycle_heads(
    records: Sequence[ScenarioRecord],
) -> dict[tuple[str, str, str, str, str], ScenarioRecord]:
    transitions = [
        record
        for record in records
        if record.contract == "lifecycle_transition"
    ]
    referenced_previous: set[str] = set()

    for record in transitions:
        previous = record.value.get("previous_transition")
        if isinstance(previous, dict):
            previous_id = previous.get("record_id")
            if isinstance(previous_id, str):
                referenced_previous.add(previous_id)

    heads: dict[
        tuple[str, str, str, str, str],
        ScenarioRecord,
    ] = {}

    for record in transitions:
        transition_id = record.value.get("transition_id")
        if (
            not isinstance(transition_id, str)
            or transition_id in referenced_previous
        ):
            continue

        owner = record.descriptor.get("owner")
        target = record.value.get("target")
        if not isinstance(owner, dict) or not isinstance(target, dict):
            continue

        class_id = owner.get("class_id")
        work_id = owner.get("work_id")
        record_ref = target.get("record_ref")
        if (
            not isinstance(class_id, str)
            or not isinstance(work_id, str)
            or not isinstance(record_ref, dict)
        ):
            continue

        key = _local_record_ref_key(
            class_id=class_id,
            work_id=work_id,
            record_ref=record_ref,
        )
        if key is not None:
            heads[key] = record

    return heads


def _contexts_of_kind(
    contexts: Sequence[tuple[str, Mapping[str, Any]]],
    kind: str,
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        value
        for context_kind, value in contexts
        if context_kind == kind
    )


def _json_pointer_get(
    value: Mapping[str, Any],
    pointer: str,
) -> Any:
    if not pointer.startswith("/"):
        raise ValueError(f"not an absolute JSON Pointer: {pointer!r}")
    current: Any = value
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise KeyError(pointer)
        current = current[token]
    return current


def _capture_lineage_tuple(
    value: Mapping[str, Any],
) -> tuple[Any, Any, Any, Any]:
    return (
        value.get("class_id"),
        value.get("work_id"),
        value.get("page_target_id"),
        value.get("page_record_id"),
    )


ISSUE22_IMPORT_DIGEST_RECIPE = "issue22_fixture_canonical_json_v1"


def issue22_fixture_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def issue22_import_batch_identity_payload(
    batch: Mapping[str, Any],
) -> dict[str, Any]:
    snapshot = batch.get("source_snapshot")
    if not isinstance(snapshot, dict):
        return {}
    return {
        "class_id": batch.get("class_id"),
        "source_profile": batch.get("source_profile"),
        "source_snapshot": {
            "locator": snapshot.get("locator"),
            "fingerprint": snapshot.get("fingerprint"),
        },
        "mapping_profile": batch.get("mapping_profile"),
    }


def issue22_import_source_content_payload(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    fields = source.get("source_fields")
    sorted_fields = (
        sorted(
            fields,
            key=lambda item: str(item.get("field_key")),
        )
        if isinstance(fields, list)
        and all(isinstance(item, dict) for item in fields)
        else fields
    )
    return {
        "source_record_key_origin": source.get(
            "source_record_key_origin"
        ),
        "source_record_key": source.get("source_record_key"),
        "source_fields": sorted_fields,
    }


def issue22_import_source_identity_payload(
    batch: Mapping[str, Any],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "import_identity_digest": batch.get(
            "import_identity_digest"
        ),
        "source_record_key_origin": source.get(
            "source_record_key_origin"
        ),
        "source_record_key": source.get("source_record_key"),
        "source_record_digest": source.get("source_record_digest"),
    }


def issue22_import_proposal_identity_payload(
    batch: Mapping[str, Any],
    source: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    bindings = proposal.get("field_bindings")
    sorted_bindings = (
        sorted(
            bindings,
            key=lambda item: str(item.get("target_path")),
        )
        if isinstance(bindings, list)
        and all(isinstance(item, dict) for item in bindings)
        else bindings
    )
    return {
        "source_record_identity_digest": source.get(
            "source_record_identity_digest"
        ),
        "import_identity_digest": batch.get(
            "import_identity_digest"
        ),
        "mapping_profile": batch.get("mapping_profile"),
        "proposal_key": proposal.get("proposal_key"),
        "target": proposal.get("target"),
        "field_bindings": sorted_bindings,
    }


def _support_target_participant_id(
    value: Mapping[str, Any],
) -> tuple[str, str | None] | None:
    target = value.get("target")
    if (
        not isinstance(target, dict)
        or target.get("kind") != "support_process_participant"
    ):
        return None
    record_ref = target.get("record_ref")
    if not isinstance(record_ref, dict):
        return None
    record_id = record_ref.get("record_id")
    version = record_ref.get("contract_version")
    if isinstance(record_id, str):
        return (
            record_id,
            version if isinstance(version, str) else None,
        )
    return None


def _exact_work_record_tuple(
    value: Mapping[str, Any],
) -> tuple[str, str, str, str, str] | None:
    work_ref = value.get("work_ref")
    record_ref = value.get("record_ref")
    if not isinstance(work_ref, dict) or not isinstance(record_ref, dict):
        return None
    fields = (
        work_ref.get("class_id"),
        work_ref.get("work_id"),
        record_ref.get("record_kind"),
        record_ref.get("record_id"),
        record_ref.get("contract_version"),
    )
    if all(isinstance(item, str) for item in fields):
        return tuple(fields)  # type: ignore[return-value]
    return None

def _flat_exact_record_key(
    value: Mapping[str, Any],
) -> tuple[str, str, str, str, str] | None:
    fields = (
        value.get("class_id"),
        value.get("work_id"),
        value.get("record_kind"),
        value.get("record_id"),
        value.get("contract_version"),
    )
    if all(isinstance(item, str) for item in fields):
        return tuple(fields)  # type: ignore[return-value]
    return None


def _exact_work_ref_key(
    value: Mapping[str, Any],
) -> tuple[str, str, str, str, str] | None:
    fields = (
        value.get("class_id"),
        value.get("work_id"),
        value.get("work_kind"),
        value.get("work_id"),
        value.get("contract_version"),
    )
    if all(isinstance(item, str) for item in fields):
        return tuple(fields)  # type: ignore[return-value]
    return None


def _export_source_identity(entry: Mapping[str, Any]) -> str:
    if "artifact_identity_digest" in entry:
        payload = {
            "artifact_kind": entry.get("artifact_kind"),
            "artifact_identity_digest": entry.get("artifact_identity_digest"),
        }
        return json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    for key in ("work_ref", "work_record_ref", "module_work_record_ref"):
        if key in entry:
            return json.dumps(
                entry[key],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
    return ""


def _canonical_export_inventory_digest(value: Mapping[str, Any]) -> str:
    payload = {
        "inventory_algorithm": value.get("inventory_algorithm"),
        "entries": value.get("entries"),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _byte_fixtures_by_workspace_path(
    scenario_path: Path,
    scenario: Mapping[str, Any],
) -> dict[str, tuple[Path, bytes]]:
    descriptors = scenario.get("byte_fixtures", [])
    if not isinstance(descriptors, list):
        return {}
    result: dict[str, tuple[Path, bytes]] = {}
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            continue
        relative = descriptor.get("fixture_path")
        workspace_path = descriptor.get("workspace_relative_path")
        if not isinstance(relative, str) or not isinstance(workspace_path, str):
            continue
        path = _safe_fixture_path(scenario_path.parent, relative)
        try:
            payload = path.read_bytes()
        except OSError:
            continue
        result[workspace_path] = (path, payload)
    return result



def _fixture_resolution_findings(
    scenario_id: str,
    records: Sequence[ScenarioRecord],
    contexts: Sequence[tuple[str, Mapping[str, Any]]],
    exact_records: Mapping[
        tuple[str, str, str, str, str],
        ScenarioRecord,
    ],
) -> tuple[GraphFinding, ...]:
    """Validate noncanonical Issue #22 resolver expectations.

    These contexts are test-only semantic expectations used where an invalid
    resolver/derived result cannot be represented as a Portia public record
    without inventing a new production contract.  They never become authority.
    """

    findings: list[GraphFinding] = []
    rosters = _roster_contexts(contexts)
    actor_ids = {
        str(record.value.get("actor_id"))
        for record in records
        if (
            record.contract == "actor"
            and isinstance(record.value.get("actor_id"), str)
        )
    }

    for context_kind, value in contexts:
        if context_kind == "synthetic_identity_resolution":
            resolution_kind = value.get("resolution_kind")
            accepted_link = value.get("accepted_explicit_link")

            if (
                resolution_kind == "same_person"
                and accepted_link is False
            ):
                subjects = value.get("subjects")
                basis = value.get("basis")
                if (
                    isinstance(subjects, list)
                    and len(subjects) >= 2
                    and all(isinstance(item, dict) for item in subjects)
                ):
                    if basis == "repeated_local_student_id":
                        class_ids = {
                            str(item.get("class_id"))
                            for item in subjects
                            if isinstance(item.get("class_id"), str)
                        }
                        student_ids = {
                            str(item.get("student_id"))
                            for item in subjects
                            if isinstance(item.get("student_id"), str)
                        }
                        if len(class_ids) > 1 and len(student_ids) == 1:
                            findings.append(
                                GraphFinding(
                                    "G22.IDENTITY.CROSS_CLASS_LOCAL_ID_MERGE",
                                    scenario_id,
                                    (
                                        "synthetic identity resolver merges "
                                        "distinct class-qualified roster "
                                        "subjects solely by repeated local "
                                        "student_id"
                                    ),
                                )
                            )

                    if basis == "display_name":
                        durable_keys = {
                            (
                                str(item.get("class_id")),
                                str(item.get("student_id")),
                            )
                            for item in subjects
                            if (
                                isinstance(item.get("class_id"), str)
                                and isinstance(item.get("student_id"), str)
                            )
                        }
                        display_names = {
                            str(item.get("display_name"))
                            for item in subjects
                            if isinstance(item.get("display_name"), str)
                        }
                        if len(durable_keys) > 1 and len(display_names) == 1:
                            findings.append(
                                GraphFinding(
                                    "G22.IDENTITY.DISPLAY_NAME_MERGE",
                                    scenario_id,
                                    (
                                        "synthetic identity resolver merges "
                                        "distinct roster subjects solely by "
                                        "equal display name"
                                    ),
                                )
                            )

            if (
                resolution_kind == "actor_replaces_roster_identity"
                and accepted_link is False
            ):
                actor_id = value.get("actor_id")
                roster_ref = value.get("roster_student_ref")
                roster_subject = (
                    {
                        "kind": "roster_student",
                        "roster_student_ref": roster_ref,
                    }
                    if isinstance(roster_ref, dict)
                    else None
                )
                if (
                    isinstance(actor_id, str)
                    and actor_id in actor_ids
                    and isinstance(roster_subject, dict)
                    and _roster_subject_resolves(
                        roster_subject,
                        rosters,
                    )
                ):
                    findings.append(
                        GraphFinding(
                            "G22.IDENTITY.ACTOR_ROSTER_SUBSTITUTION",
                            scenario_id,
                            (
                                "synthetic identity resolver treats a "
                                "workspace Actor as a replacement for an "
                                "exact class-qualified roster identity"
                            ),
                        )
                    )

        if context_kind == "synthetic_reference_resolution":
            resolution_kind = value.get("resolution_kind")

            if resolution_kind == "foreign_substitution":
                requested = value.get("requested")
                resolved = value.get("resolved")
                if (
                    isinstance(requested, dict)
                    and requested.get("authority") == "core"
                    and requested.get("kind") == "roster_student"
                    and isinstance(resolved, dict)
                    and resolved.get("authority") == "portia"
                    and resolved.get("kind") == "actor"
                ):
                    roster_subject = {
                        "kind": "roster_student",
                        "roster_student_ref": {
                            "class_id": requested.get("class_id"),
                            "student_id": requested.get("student_id"),
                        },
                    }
                    actor_id = resolved.get("actor_id")
                    if (
                        isinstance(actor_id, str)
                        and actor_id in actor_ids
                        and _roster_subject_resolves(
                            roster_subject,
                            rosters,
                        )
                    ):
                        findings.append(
                            GraphFinding(
                                "G22.REFERENCE.FOREIGN_SUBSTITUTION",
                                scenario_id,
                                (
                                    "synthetic resolver substitutes a local "
                                    "Portia Actor for an exact Core-owned "
                                    "roster reference"
                                ),
                            )
                        )

            if resolution_kind == "historical_exact_follow":
                requested = value.get("requested")
                resolved = value.get("resolved")
                if isinstance(requested, dict) and isinstance(resolved, dict):
                    requested_key = (
                        requested.get("class_id"),
                        requested.get("work_id"),
                        requested.get("record_kind"),
                        requested.get("record_id"),
                        requested.get("contract_version"),
                    )
                    resolved_key = (
                        resolved.get("class_id"),
                        resolved.get("work_id"),
                        resolved.get("record_kind"),
                        resolved.get("record_id"),
                        resolved.get("contract_version"),
                    )
                    if (
                        all(isinstance(item, str) for item in requested_key)
                        and all(isinstance(item, str) for item in resolved_key)
                        and requested_key != resolved_key
                        and requested_key in exact_records
                        and resolved_key in exact_records
                    ):
                        findings.append(
                            GraphFinding(
                                "G22.REFERENCE.HISTORICAL_SUCCESSOR_FOLLOW",
                                scenario_id,
                                (
                                    "synthetic resolver silently follows an "
                                    "exact historical reference to a different "
                                    "current/successor representation"
                                ),
                            )
                        )


        if context_kind == "synthetic_derived_current_selection":
            record_contract = value.get("record_contract")
            selected = value.get("selected")
            expected_current = value.get("expected_current")
            if (
                isinstance(record_contract, str)
                and isinstance(selected, dict)
                and isinstance(expected_current, dict)
            ):
                selected_key = _flat_exact_record_key(selected)
                expected_key = _flat_exact_record_key(expected_current)
                selected_record = (
                    exact_records.get(selected_key)
                    if selected_key is not None
                    else None
                )
                expected_record = (
                    exact_records.get(expected_key)
                    if expected_key is not None
                    else None
                )
                if (
                    selected_record is not None
                    and expected_record is not None
                    and selected_key != expected_key
                ):
                    frontier = replacement_frontier(
                        records,
                        record_contract,
                    )
                    selected_id = _id_for_record(selected_record)
                    expected_id = _id_for_record(expected_record)
                    if (
                        selected_record.value.get("status")
                        in {"superseded", "invalidated"}
                        and isinstance(expected_id, str)
                        and expected_id in frontier
                        and selected_id not in frontier
                    ):
                        findings.append(
                            GraphFinding(
                                (
                                    "G22.DERIVED."
                                    "CURRENT_SELECTS_PREDECESSOR"
                                ),
                                scenario_id,
                                (
                                    "synthetic derived current selection "
                                    "chooses a superseded/invalidated "
                                    "predecessor instead of the exact active "
                                    "replacement frontier"
                                ),
                            )
                        )

        if context_kind == "synthetic_disagreement_resolution":
            disagreement_id = value.get("disagreement_id")
            intended = value.get("intended_target")
            actual = value.get("actual_target")
            disagreement = next(
                (
                    record
                    for record in records
                    if (
                        record.contract
                        == "statement_of_disagreement"
                        and record.value.get("disagreement_id")
                        == disagreement_id
                    )
                ),
                None,
            )
            if (
                disagreement is not None
                and isinstance(intended, dict)
                and isinstance(actual, dict)
            ):
                owner = disagreement.descriptor.get("owner")
                target = disagreement.value.get("target")
                record_ref = (
                    target.get("record_ref")
                    if isinstance(target, dict)
                    and target.get("kind") == "local_record"
                    else None
                )
                if (
                    isinstance(owner, dict)
                    and isinstance(record_ref, dict)
                    and isinstance(owner.get("class_id"), str)
                    and isinstance(owner.get("work_id"), str)
                ):
                    actual_key = _local_record_ref_key(
                        class_id=str(owner["class_id"]),
                        work_id=str(owner["work_id"]),
                        record_ref=record_ref,
                    )
                    intended_key = _local_record_ref_key(
                        class_id=str(owner["class_id"]),
                        work_id=str(owner["work_id"]),
                        record_ref=intended,
                    )
                    declared_actual_key = _local_record_ref_key(
                        class_id=str(owner["class_id"]),
                        work_id=str(owner["work_id"]),
                        record_ref=actual,
                    )
                    if (
                        actual_key is not None
                        and intended_key is not None
                        and declared_actual_key is not None
                        and actual_key == declared_actual_key
                        and actual_key != intended_key
                        and actual_key in exact_records
                        and intended_key in exact_records
                    ):
                        findings.append(
                            GraphFinding(
                                (
                                    "G22.CORRECTION."
                                    "DISAGREEMENT_WRONG_TARGET"
                                ),
                                scenario_id,
                                (
                                    "Statement of Disagreement resolves to "
                                    "a different exact record than the "
                                    "fixture-declared contested record"
                                ),
                            )
                        )

        if context_kind == "synthetic_migration_resolution":
            migration_id = value.get("migration_id")
            historical = value.get("historical_reference")
            resolved_after = value.get("resolved_after_migration")
            migration = next(
                (
                    record
                    for record in records
                    if (
                        record.contract == "record_migration"
                        and record.value.get("migration_id")
                        == migration_id
                    )
                ),
                None,
            )
            if (
                migration is not None
                and value.get("semantic_change") is True
                and value.get("rewrite_exact_reference") is True
                and isinstance(historical, dict)
                and isinstance(resolved_after, dict)
            ):
                source = migration.value.get("source")
                destination = migration.value.get("destination")
                source_ref = (
                    source.get("work_ref")
                    if isinstance(source, dict)
                    and source.get("kind") == "work"
                    else None
                )
                destination_ref = (
                    destination.get("work_ref")
                    if isinstance(destination, dict)
                    and destination.get("kind") == "work"
                    else None
                )
                historical_key = _flat_exact_record_key(historical)
                resolved_key = _flat_exact_record_key(resolved_after)
                source_key = (
                    _exact_work_ref_key(source_ref)
                    if isinstance(source_ref, dict)
                    else None
                )
                destination_key = (
                    _exact_work_ref_key(destination_ref)
                    if isinstance(destination_ref, dict)
                    else None
                )
                if (
                    historical_key is not None
                    and resolved_key is not None
                    and source_key == historical_key
                    and destination_key == resolved_key
                    and source_key in exact_records
                    and destination_key in exact_records
                    and source_key != destination_key
                ):
                    findings.append(
                        GraphFinding(
                            "G22.MIGRATION.HISTORICAL_RETARGET",
                            scenario_id,
                            (
                                "representation-only migration is used to "
                                "retarget an exact historical reference "
                                "across a substantive semantic correction"
                            ),
                        )
                    )

        if (
            context_kind
            == "synthetic_cross_year_continuation_resolution"
        ):
            migration_id = value.get("migration_id")
            predecessor = value.get("predecessor")
            successor = value.get("successor")
            migration = next(
                (
                    record
                    for record in records
                    if (
                        record.contract == "record_migration"
                        and record.value.get("migration_id")
                        == migration_id
                    )
                ),
                None,
            )
            if (
                migration is not None
                and value.get("intended_relationship")
                == "cross_year_continuation"
                and value.get("encoding") == "record_migration"
                and isinstance(predecessor, dict)
                and isinstance(successor, dict)
            ):
                predecessor_key = _flat_exact_record_key(predecessor)
                successor_key = _flat_exact_record_key(successor)
                predecessor_record = (
                    exact_records.get(predecessor_key)
                    if predecessor_key is not None
                    else None
                )
                successor_record = (
                    exact_records.get(successor_key)
                    if successor_key is not None
                    else None
                )
                source = migration.value.get("source")
                destination = migration.value.get("destination")
                source_ref = (
                    source.get("work_ref")
                    if isinstance(source, dict)
                    and source.get("kind") == "work"
                    else None
                )
                destination_ref = (
                    destination.get("work_ref")
                    if isinstance(destination, dict)
                    and destination.get("kind") == "work"
                    else None
                )
                source_key = (
                    _exact_work_ref_key(source_ref)
                    if isinstance(source_ref, dict)
                    else None
                )
                destination_key = (
                    _exact_work_ref_key(destination_ref)
                    if isinstance(destination_ref, dict)
                    else None
                )
                if (
                    predecessor_record is not None
                    and successor_record is not None
                    and predecessor_record.contract
                    == "support_process"
                    and successor_record.contract
                    == "support_process"
                    and source_key == predecessor_key
                    and destination_key == successor_key
                    and predecessor_key != successor_key
                    and successor_record.value.get("continues_from")
                    is None
                ):
                    findings.append(
                        GraphFinding(
                            (
                                "G22.SUPPORT."
                                "CONTINUATION_ENCODED_AS_MIGRATION"
                            ),
                            scenario_id,
                            (
                                "cross-year Support continuation is "
                                "encoded as Record Migration instead of "
                                "a new Support Process with exact "
                                "continues_from"
                            ),
                        )
                    )

        if context_kind == "synthetic_outcome_identity_write":
            existing = value.get("existing_outcome")
            attempted = value.get("attempted_later_evaluation")
            if (
                value.get("operation") == "overwrite_existing_identity"
                and isinstance(existing, dict)
                and isinstance(attempted, dict)
            ):
                existing_key = _flat_exact_record_key(existing)
                attempted_key = _flat_exact_record_key(attempted)
                existing_record = (
                    exact_records.get(existing_key)
                    if existing_key is not None
                    else None
                )
                if (
                    existing_record is not None
                    and existing_record.contract == "outcome"
                    and existing_key == attempted_key
                    and value.get("semantic_relationship")
                    == "distinct_later_timeframe_evaluation"
                    and value.get("timeframe_changed") is True
                ):
                    findings.append(
                        GraphFinding(
                            "G22.OUTCOME.IDENTITY_REUSED_FOR_LATER_EVALUATION",
                            scenario_id,
                            (
                                "a distinct later-timeframe Outcome write "
                                "attempts to overwrite/reuse the exact identity "
                                "of an earlier accepted Outcome"
                            ),
                        )
                    )

        if context_kind == "synthetic_import_replay_resolution":
            first = value.get("first_result")
            replayed = value.get("replayed_result")
            if (
                value.get("resolution_kind")
                == "accepted_proposal_replayed_as_new_domain_record"
                and value.get("unchanged_source_and_mapping") is True
                and isinstance(value.get("proposal_identity_digest"), str)
                and isinstance(first, dict)
                and isinstance(replayed, dict)
            ):
                first_key = _flat_exact_record_key(first)
                replayed_key = _flat_exact_record_key(replayed)
                if (
                    first_key is not None
                    and replayed_key is not None
                    and first_key != replayed_key
                    and first_key in exact_records
                    and replayed_key in exact_records
                ):
                    findings.append(
                        GraphFinding(
                            "G22.IMPORT.ACCEPTED_PROPOSAL_DUPLICATE_MATERIALIZATION",
                            scenario_id,
                            (
                                "unchanged retained-source replay creates a "
                                "second accepted domain record for one exact "
                                "accepted Import Proposal identity"
                            ),
                        )
                    )

        if context_kind == "synthetic_operation_restart_resolution":
            if (
                value.get("journal_state") in {"committed", "completed"}
                and value.get("prior_disposition") == "accepted"
                and value.get("semantic_write_already_durable") is True
                and value.get("restart_action") == "replay_semantic_write"
                and value.get("required_restart_action")
                == "reconcile_exact_readback"
            ):
                findings.append(
                    GraphFinding(
                        "G22.OPERATION.RESTART_REPLAYS_COMMITTED_WRITE",
                        scenario_id,
                        (
                            "restart replays an already accepted durable "
                            "semantic write instead of reconciling exact "
                            "canonical readback"
                        ),
                    )
                )

        if context_kind == "synthetic_support_process_reference_resolution":
            if value.get("resolution_kind") == "historical_exact_follow":
                requested = value.get("requested")
                resolved = value.get("resolved")
                if isinstance(requested, dict) and isinstance(resolved, dict):
                    requested_key = _flat_exact_record_key(requested)
                    resolved_key = _flat_exact_record_key(resolved)
                    requested_record = (
                        exact_records.get(requested_key)
                        if requested_key is not None
                        else None
                    )
                    resolved_record = (
                        exact_records.get(resolved_key)
                        if resolved_key is not None
                        else None
                    )
                    if (
                        requested_record is not None
                        and resolved_record is not None
                        and requested_record.contract == "support_process"
                        and resolved_record.contract == "support_process"
                        and requested_key != resolved_key
                        and resolved_record.value.get("continues_from")
                        is not None
                        and value.get("resolution_mode") == "follow_current"
                    ):
                        findings.append(
                            GraphFinding(
                                "G22.SUPPORT.HISTORICAL_PROCESS_SUCCESSOR_FOLLOW",
                                scenario_id,
                                (
                                    "an exact historical Support Process "
                                    "reference is silently resolved to the "
                                    "cross-year successor process"
                                ),
                            )
                        )

        if context_kind == "synthetic_participant_projection_result":
            focal = value.get("focal_subject")
            emitted = value.get("emitted_unrelated_refs", [])
            focal_key = _flat_exact_record_key(focal) if isinstance(focal, dict) else None
            emitted_keys = [
                _flat_exact_record_key(item)
                for item in emitted
                if isinstance(item, dict)
            ] if isinstance(emitted, list) else []
            if (
                value.get("projection_purpose") == "participant_specific"
                and focal_key in exact_records
                and any(key in exact_records and key != focal_key for key in emitted_keys)
                and (
                    isinstance(value.get("emitted_unrelated_stable_id"), str)
                    or value.get("unsafe_account_segment_included") is True
                )
            ):
                findings.append(
                    GraphFinding(
                        "G22.PRIVACY.PROJECTION_LEAKS_UNRELATED_DATA",
                        scenario_id,
                        "participant-specific projection emits unrelated participant identity/stable ID or unsafe Account content",
                    )
                )

        if context_kind == "synthetic_projection_state_serialization":
            items = value.get("items", [])
            collapsed = False
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    source = item.get("source_disposition")
                    outward = item.get("serialized_representation")
                    if source == "withheld" and outward in {"absent", False, "false", "no", 0, ""}:
                        collapsed = True
                    if source == "unavailable" and outward in {"absent", False, "false", "no"}:
                        collapsed = True
            if collapsed and value.get("accepted_output") is True:
                findings.append(
                    GraphFinding(
                        "G22.PRIVACY.PROJECTION_STATE_COLLAPSE",
                        scenario_id,
                        "projection collapses withheld/unavailable into absent or false/no semantics",
                    )
                )

        if context_kind == "synthetic_export_consumption_resolution":
            consumed = value.get("consumed_exact_source")
            bound = value.get("inventory_bound_source")
            consumed_key = _flat_exact_record_key(consumed) if isinstance(consumed, dict) else None
            bound_key = _flat_exact_record_key(bound) if isinstance(bound, dict) else None
            consumed_record = exact_records.get(consumed_key) if consumed_key is not None else None
            bound_record = exact_records.get(bound_key) if bound_key is not None else None
            export_id = value.get("export_id")
            export_record = next(
                (
                    record for record in records
                    if record.contract == "deliberate_export"
                    and record.value.get("export_id") == export_id
                ),
                None,
            )
            if consumed_record is not None and bound_record is not None and export_record is not None:
                inventory = export_record.value.get("source_inventory", {})
                entries = inventory.get("entries", []) if isinstance(inventory, dict) else []
                bound_present = False
                consumed_present = False
                if isinstance(entries, list):
                    for entry in entries:
                        if not isinstance(entry, dict) or entry.get("source_kind") != "portia_record":
                            continue
                        ref = entry.get("work_record_ref")
                        key = _exact_portia_ref_key(ref) if isinstance(ref, dict) else None
                        bound_present = bound_present or key == bound_key
                        consumed_present = consumed_present or key == consumed_key
                supersedes = bound_record.value.get("supersedes", [])
                supersedes_consumed = False
                if isinstance(supersedes, list):
                    for item in supersedes:
                        ref = item.get("work_record_ref") if isinstance(item, dict) else None
                        if isinstance(ref, dict) and _exact_portia_ref_key(ref) == consumed_key:
                            supersedes_consumed = True
                if (
                    bound_present
                    and not consumed_present
                    and supersedes_consumed
                    and value.get("inventory_fingerprint_truthful_for_bound_source") is True
                ):
                    findings.append(
                        GraphFinding(
                            "G22.PRIVACY.EXPORT_INVENTORY_WRONG_REPRESENTATION",
                            scenario_id,
                            "export source inventory binds a successor rather than the exact historical representation actually consumed",
                        )
                    )

        if context_kind == "synthetic_export_path_privacy_context":
            export_id = value.get("export_id")
            output_path = value.get("output_path")
            labels = value.get("synthetic_sensitive_labels", [])
            export_record = next(
                (
                    record for record in records
                    if record.contract == "deliberate_export"
                    and record.value.get("export_id") == export_id
                ),
                None,
            )
            if (
                export_record is not None
                and isinstance(output_path, str)
                and isinstance(labels, list)
                and value.get("path_is_export_id_scoped") is True
                and value.get("pii_minimized_path_required") is True
                and export_record.value.get("output", {}).get("workspace_relative_path") == output_path
                and any(isinstance(label, str) and label and label in output_path for label in labels)
            ):
                findings.append(
                    GraphFinding(
                        "G22.PRIVACY.EXPORT_OUTPUT_PATH_PII",
                        scenario_id,
                        "export output path is export-ID scoped but contains unnecessary person/class/behavior labels",
                    )
                )

        if context_kind == "synthetic_incoming_reference_index":
            relationship_id = value.get("relationship_id")
            relationship = next(
                (
                    record for record in records
                    if record.contract == "work_relationship"
                    and record.value.get("relationship_id") == relationship_id
                ),
                None,
            )
            canonical = value.get("canonical_target_work")
            indexed = value.get("indexed_target_work")
            if relationship is not None and isinstance(canonical, dict) and isinstance(indexed, dict):
                target = relationship.value.get("target")
                target_key = _exact_work_ref_key(target) if isinstance(target, dict) else None
                canonical_key = _exact_work_ref_key({"module_id":"portia", **canonical})
                indexed_key = _exact_work_ref_key({"module_id":"portia", **indexed})
                if (
                    target_key == canonical_key
                    and indexed_key != canonical_key
                    and value.get("accepted_as_authoritative") is True
                ):
                    findings.append(
                        GraphFinding(
                            "G22.DERIVED.INCOMING_INDEX_DISAGREES_FORWARD_REFS",
                            scenario_id,
                            "derived incoming-reference index disagrees with the canonical forward Work Relationship target",
                        )
                    )

        if context_kind == "synthetic_derived_current_view":
            contract = value.get("record_contract")
            current_ids = value.get("current_record_ids", [])
            if isinstance(contract, str) and isinstance(current_ids, list):
                frontier = set(replacement_frontier(records, contract))
                presented = {item for item in current_ids if isinstance(item, str)}
                family_ids = {
                    rid for record in records if record.contract == contract
                    for rid in [_id_for_record(record)] if isinstance(rid, str)
                }
                if (
                    value.get("accepted_as_current") is True
                    and frontier
                    and frontier <= presented
                    and bool((presented & family_ids) - frontier)
                ):
                    findings.append(
                        GraphFinding(
                            "G22.DERIVED.CURRENT_VIEW_INCLUDES_PREDECESSOR",
                            scenario_id,
                            "derived current/replacement view includes a historical predecessor alongside the active frontier",
                        )
                    )

        if context_kind == "synthetic_stale_source_snapshot_acceptance":
            source_ref = value.get("source_record")
            key = _flat_exact_record_key(source_ref) if isinstance(source_ref, dict) else None
            source = exact_records.get(key) if key is not None else None
            snapshot_digest = value.get("snapshot_representation_digest")
            if (
                source is not None
                and isinstance(snapshot_digest, str)
                and snapshot_digest != hashlib.sha256(source.path.read_bytes()).hexdigest()
                and value.get("source_changed_after_snapshot") is True
                and value.get("stale_derived_result_accepted") is True
            ):
                findings.append(
                    GraphFinding(
                        "G22.DERIVED.STALE_SOURCE_SNAPSHOT_ACCEPTED",
                        scenario_id,
                        "stale source snapshot is accepted after the exact canonical source representation changed",
                    )
                )

        if context_kind == "synthetic_disposition_custody_result":
            claims = value.get("foreign_destruction_claims", {})
            verification = value.get("owner_verification", {})
            if isinstance(claims, dict) and isinstance(verification, dict):
                unverified = [
                    owner for owner, claim in claims.items()
                    if claim == "destroyed" and verification.get(owner) is not True
                ]
                if (
                    value.get("portia_local_disposition") == "completed"
                    and value.get("global_completion_reported") is True
                    and unverified
                ):
                    findings.append(
                        GraphFinding(
                            "G22.CUSTODY.FOREIGN_DESTRUCTION_UNVERIFIED",
                            scenario_id,
                            "Portia reports foreign/external copies destroyed without authoritative owner verification",
                        )
                    )

    return tuple(sorted(findings))


def validate_graph(
    scenario_path: Path,
    scenario: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any],
    store: SchemaStore,
) -> tuple[GraphFinding, ...]:
    scenario_id = str(scenario.get("scenario_id", "<unknown>"))
    findings = list(
        validate_structural_records(
            scenario_path,
            scenario,
            catalog=catalog,
            store=store,
        )
    )
    if findings:
        return tuple(sorted(findings))

    records = load_scenario_records(scenario_path, scenario)
    contexts = load_contexts(scenario_path, scenario)
    operational_fixtures = load_operational_contract_fixtures(
        scenario_path,
        scenario,
    )

    seen_logical: set[str] = set()
    for record in records:
        logical = record.logical_identity
        if logical in seen_logical:
            findings.append(
                GraphFinding(
                    "G22.IDENTITY.DUPLICATE_LOGICAL_IDENTITY",
                    scenario_id,
                    f"duplicate logical fixture identity: {logical}",
                )
            )
        seen_logical.add(logical)

    event_roots: dict[tuple[str, str], ScenarioRecord] = {}
    capture_roots: dict[tuple[str, str], ScenarioRecord] = {}
    participants: dict[
        tuple[str, str, str],
        ScenarioRecord,
    ] = {}
    exact_records: dict[
        tuple[str, str, str, str, str],
        ScenarioRecord,
    ] = {}
    active_subjects: dict[
        tuple[str, str, tuple[str, ...]],
        ScenarioRecord,
    ] = {}

    for record in records:
        lookup_key = _record_lookup_key(record)
        if lookup_key is not None:
            exact_records[lookup_key] = record
        owner = record.descriptor.get("owner")
        if not isinstance(owner, dict):
            continue

        owner_class = owner.get("class_id")
        owner_scope_kind = owner.get("owner_kind")
        owner_work = owner.get("work_id")
        owner_kind = owner.get("work_kind")

        if record.value.get("class_id") != owner_class:
            findings.append(
                GraphFinding(
                    "G22.OWNERSHIP.CLASS_MISMATCH",
                    scenario_id,
                    f"{record.logical_identity}: class_id disagrees with owner",
                )
            )

        if owner_scope_kind == "actor":
            owner_actor = owner.get("actor_id")
            if record.value.get("actor_id") != owner_actor:
                findings.append(
                    GraphFinding(
                        "G22.OWNERSHIP.ACTOR_MISMATCH",
                        scenario_id,
                        (
                            f"{record.logical_identity}: Actor "
                            "scope disagrees with owner"
                        ),
                    )
                )
            if (
                "class_id" in record.value
                or "work_id" in record.value
            ):
                findings.append(
                    GraphFinding(
                        "G22.OWNERSHIP.ACTOR_IS_NOT_CLASS_WORK",
                        scenario_id,
                        (
                            f"{record.logical_identity}: workspace Actor "
                            "record must not claim class/work ownership"
                        ),
                    )
                )
        elif owner_scope_kind == "import_batch":
            owner_batch = owner.get("import_batch_id")
            if record.contract == "import_materialization":
                batch_ref = record.value.get("import_batch_ref")
                actual_batch = (
                    batch_ref.get("import_batch_id")
                    if isinstance(batch_ref, dict)
                    else None
                )
            else:
                actual_batch = record.value.get("import_batch_id")
            if actual_batch != owner_batch:
                findings.append(
                    GraphFinding(
                        "G22.OWNERSHIP.IMPORT_BATCH_MISMATCH",
                        scenario_id,
                        (
                            f"{record.logical_identity}: import batch "
                            "scope disagrees with owner"
                        ),
                    )
                )
            if "work_id" in record.value:
                findings.append(
                    GraphFinding(
                        "G22.OWNERSHIP.IMPORT_IS_NOT_WORK",
                        scenario_id,
                        (
                            f"{record.logical_identity}: class-local "
                            "import record must not claim work_id"
                        ),
                    )
                )
        else:
            if record.value.get("work_id") != owner_work:
                findings.append(
                    GraphFinding(
                        "G22.OWNERSHIP.WORK_MISMATCH",
                        scenario_id,
                        f"{record.logical_identity}: work_id disagrees with owner",
                    )
                )

            value_work_kind = record.value.get("work_kind")
            if (
                isinstance(value_work_kind, str)
                and value_work_kind != owner_kind
            ):
                findings.append(
                    GraphFinding(
                        "G22.OWNERSHIP.WORK_KIND_MISMATCH",
                        scenario_id,
                        f"{record.logical_identity}: work_kind disagrees with owner",
                    )
                )

        canonical_path = record.descriptor.get("canonical_path")
        expected_path = _canonical_path_for_record(record)
        if (
            not isinstance(canonical_path, str)
            or expected_path is None
            or canonical_path != expected_path
        ):
            findings.append(
                GraphFinding(
                    "G22.OWNERSHIP.CANONICAL_PATH_MISMATCH",
                    scenario_id,
                    (
                        f"{record.logical_identity}: canonical path "
                        "does not match persisted identity"
                    ),
                )
            )

        if (
            record.contract == "event"
            and isinstance(owner_class, str)
            and isinstance(owner_work, str)
        ):
            event_roots[(owner_class, owner_work)] = record

        if (
            record.contract == "capture_batch"
            and isinstance(owner_class, str)
            and isinstance(owner_work, str)
        ):
            capture_roots[(owner_class, owner_work)] = record

        if (
            record.contract == "event_participant"
            and isinstance(owner_class, str)
            and isinstance(owner_work, str)
        ):
            participant_id = record.value.get("participant_id")
            if isinstance(participant_id, str):
                participants[
                    (owner_class, owner_work, participant_id)
                ] = record

                subject = record.value.get("subject")
                subject_key = (
                    durable_subject_key(subject)
                    if isinstance(subject, dict)
                    else None
                )
                if (
                    record.value.get("status") == "active"
                    and subject_key is not None
                ):
                    active_key = (
                        owner_class,
                        owner_work,
                        subject_key,
                    )
                    if active_key in active_subjects:
                        findings.append(
                            GraphFinding(
                                "G22.IDENTITY.DUPLICATE_ACTIVE_SUBJECT",
                                scenario_id,
                                (
                                    f"{record.logical_identity}: durable "
                                    "subject duplicates another active "
                                    "participant in the same Event"
                                ),
                            )
                        )
                    else:
                        active_subjects[active_key] = record

    rosters = _roster_contexts(contexts)
    findings.extend(
        _fixture_resolution_findings(
            scenario_id,
            records,
            contexts,
            exact_records,
        )
    )

    for record in records:
        owner = record.descriptor.get("owner")
        if not isinstance(owner, dict):
            continue
        class_id = owner.get("class_id")
        work_id = owner.get("work_id")
        work_kind = owner.get("work_kind")

        if (
            work_kind == "event"
            and record.contract != "event"
            and isinstance(class_id, str)
            and isinstance(work_id, str)
            and (class_id, work_id) not in event_roots
        ):
            findings.append(
                GraphFinding(
                    "G22.REFERENCE.PARENT_EVENT_MISSING",
                    scenario_id,
                    f"{record.logical_identity}: owning Event does not resolve",
                )
            )

        if (
            work_kind == "capture_batch"
            and record.contract != "capture_batch"
            and isinstance(class_id, str)
            and isinstance(work_id, str)
            and (class_id, work_id) not in capture_roots
        ):
            findings.append(
                GraphFinding(
                    "G22.PAPER.CAPTURE_BATCH_UNRESOLVED",
                    scenario_id,
                    f"{record.logical_identity}: owning Capture Batch does not resolve",
                )
            )

        if record.contract == "event_participant":
            subject = record.value.get("subject")
            if (
                isinstance(subject, dict)
                and not _roster_subject_resolves(subject, rosters)
            ):
                findings.append(
                    GraphFinding(
                        "G22.IDENTITY.ROSTER_STUDENT_UNRESOLVED",
                        scenario_id,
                        (
                            f"{record.logical_identity}: exact roster "
                            "subject does not resolve in synthetic Core context"
                        ),
                    )
                )

        if record.contract in {
            "event_participant_role",
            "account",
            "observation",
            "review",
            "classification",
            "hypothesis",
            "determination",
            "response",
        }:
            target = record.value.get("target")
            if not isinstance(target, dict):
                continue
            for participant_id, contract_version in (
                _participant_refs_from_target(target)
            ):
                key = (str(class_id), str(work_id), participant_id)
                participant = participants.get(key)
                if participant is None:
                    findings.append(
                        GraphFinding(
                            "G22.REFERENCE.PARTICIPANT_TARGET_MISSING",
                            scenario_id,
                            (
                                f"{record.logical_identity}: target "
                                f"{participant_id} does not resolve in owner work"
                            ),
                        )
                    )
                    continue
                actual_version = participant.descriptor.get("version")
                if (
                    contract_version is not None
                    and contract_version != actual_version
                ):
                    findings.append(
                        GraphFinding(
                            "G22.REFERENCE.PARTICIPANT_VERSION_MISMATCH",
                            scenario_id,
                            (
                                f"{record.logical_identity}: target "
                                f"{participant_id} requests version "
                                f"{contract_version}, fixture is {actual_version}"
                            ),
                        )
                    )


        if record.contract == "account":
            source = _account_source_subject(record)
            if (
                isinstance(source, dict)
                and source.get("kind") == "roster_student"
                and not _roster_subject_resolves(source, rosters)
            ):
                findings.append(
                    GraphFinding(
                        "G22.IDENTITY.ACCOUNT_SOURCE_UNRESOLVED",
                        scenario_id,
                        (
                            f"{record.logical_identity}: exact roster Account "
                            "source does not resolve in synthetic Core context"
                        ),
                    )
                )

        for record_kind, record_id, version in _local_basis_refs(record):
            key = (
                str(class_id),
                str(work_id),
                record_kind,
                record_id,
                version,
            )
            if key not in exact_records:
                findings.append(
                    GraphFinding(
                        "G22.EVIDENCE.ROLE_BASIS_UNRESOLVED",
                        scenario_id,
                        (
                            f"{record.logical_identity}: local basis "
                            f"{record_kind}:{record_id}@{version} does not resolve"
                        ),
                    )
                )

        for work_record_ref in _portia_evidence_refs(record):
            if not _work_ref_agrees_with_owner(record, work_record_ref):
                findings.append(
                    GraphFinding(
                        "G22.EVIDENCE.WRONG_WORK",
                        scenario_id,
                        (
                            f"{record.logical_identity}: evidence reference "
                            "does not remain in the owning Event"
                        ),
                    )
                )
                continue
            key = _exact_portia_ref_key(work_record_ref)
            if key is None or key not in exact_records:
                findings.append(
                    GraphFinding(
                        "G22.EVIDENCE.UNRESOLVED",
                        scenario_id,
                        (
                            f"{record.logical_identity}: exact Portia evidence "
                            "reference does not resolve"
                        ),
                    )
                )

        if record.contract in {
            "classification",
            "hypothesis",
            "determination",
        }:
            review_ref = record.value.get("review_ref")
            review_record = None
            if isinstance(review_ref, dict):
                if not _work_ref_agrees_with_owner(record, review_ref):
                    findings.append(
                        GraphFinding(
                            "G22.JUDGMENT.REVIEW_WRONG_WORK",
                            scenario_id,
                            (
                                f"{record.logical_identity}: linked Review "
                                "does not remain in the owning Event"
                            ),
                        )
                    )
                else:
                    review_key = _exact_portia_ref_key(review_ref)
                    review_record = (
                        exact_records.get(review_key)
                        if review_key is not None
                        else None
                    )
                    if review_record is None:
                        findings.append(
                            GraphFinding(
                                "G22.JUDGMENT.REVIEW_UNRESOLVED",
                                scenario_id,
                                (
                                    f"{record.logical_identity}: linked Review "
                                    "does not resolve exactly"
                                ),
                            )
                        )

            requires_completed_review = (
                record.contract == "determination"
                and record.value.get("status") == "active"
            ) or (
                record.contract == "classification"
                and record.value.get("status") == "active"
                and record.value.get("stage")
                in {"reviewer_selected", "reviewer_confirmed"}
            )
            if (
                requires_completed_review
                and review_record is not None
                and review_record.value.get("review_state") != "completed"
            ):
                findings.append(
                    GraphFinding(
                        "G22.JUDGMENT.REVIEW_NOT_COMPLETED",
                        scenario_id,
                        (
                            f"{record.logical_identity}: active human "
                            "judgment requires completed Review"
                        ),
                    )
                )

            creation_source = record.value.get("creation_source")
            if (
                record.value.get("status") == "active"
                and isinstance(creation_source, dict)
                and creation_source.get("type") in {"import", "paper_capture"}
                and not isinstance(review_ref, dict)
            ):
                findings.append(
                    GraphFinding(
                        "G22.JUDGMENT.IMPORT_ACTIVE_WITHOUT_REVIEW",
                        scenario_id,
                        (
                            f"{record.logical_identity}: active "
                            "import/paper-origin judgment lacks "
                            "required review history"
                        ),
                    )
                )

    for context_kind, context in contexts:
        if context_kind != "synthetic_import_assertion_judgment_resolution":
            continue
        if (
            context.get("source_assertion_used_as_determination") is True
            and context.get("human_decision_occurred") is False
        ):
            findings.append(
                GraphFinding(
                    "G22.JUDGMENT.IMPORT_ASSERTION_AS_DETERMINATION",
                    scenario_id,
                    (
                        "imported/source assertion was promoted into "
                        "Determination semantics without an actual human "
                        "decision"
                    ),
                )
            )


    # Multi-Event Support Process chain.
    support_processes = {
        (
            str(record.value.get("class_id")),
            str(record.value.get("work_id")),
        ): record
        for record in records
        if record.contract == "support_process"
    }
    support_participants = {
        (
            str(record.value.get("class_id")),
            str(record.value.get("work_id")),
            str(record.value.get("participant_id")),
            record.version,
        ): record
        for record in records
        if (
            record.contract == "support_process_participant"
            and isinstance(record.value.get("participant_id"), str)
        )
    }
    support_local_records = {
        (
            str(record.value.get("class_id")),
            str(record.value.get("work_id")),
            str(record.value.get("record_type")),
            str(_id_for_record(record)),
            record.version,
        ): record
        for record in records
        if record.contract in {
            "support_process_participant",
            "support_need",
            "support_goal",
            "support",
            "intervention",
            "implementation",
            "fidelity",
            "follow_up",
            "outcome",
        }
        and _id_for_record(record) is not None
    }

    # Cross-year Support Process continuity is an exact work-to-work link.
    # It is deliberately separate from supersession, migration, ownership
    # correction, and child-record identity.
    for process in support_processes.values():
        continuation = process.value.get("continues_from")
        if not isinstance(continuation, dict):
            continue

        predecessor_key = (
            str(continuation.get("class_id")),
            str(continuation.get("work_id")),
        )
        predecessor = support_processes.get(predecessor_key)
        if predecessor is None:
            findings.append(
                GraphFinding(
                    "G22.SUPPORT.CONTINUATION_UNRESOLVED",
                    scenario_id,
                    (
                        f"{process.logical_identity}: exact predecessor "
                        "Support Process does not resolve"
                    ),
                )
            )
            continue

        if predecessor_key == (
            str(process.value.get("class_id")),
            str(process.value.get("work_id")),
        ):
            findings.append(
                GraphFinding(
                    "G22.SUPPORT.CONTINUATION_SELF_REFERENCE",
                    scenario_id,
                    (
                        f"{process.logical_identity}: continues_from "
                        "must identify a distinct Support Process"
                    ),
                )
            )

        if (
            continuation.get("module_id") != "portia"
            or continuation.get("work_kind") != "support_process"
            or continuation.get("contract_version") != predecessor.version
        ):
            findings.append(
                GraphFinding(
                    "G22.SUPPORT.CONTINUATION_EXACT_REF_MISMATCH",
                    scenario_id,
                    (
                        f"{process.logical_identity}: continues_from "
                        "does not match the exact predecessor contract"
                    ),
                )
            )

    for process in support_processes.values():
        initiation = process.value.get("initiation")
        if (
            isinstance(initiation, dict)
            and initiation.get("kind") == "event_context"
        ):
            event_ref_value = initiation.get("event_ref")
            if isinstance(event_ref_value, dict):
                key = (
                    str(event_ref_value.get("class_id")),
                    str(event_ref_value.get("work_id")),
                    str(event_ref_value.get("work_kind")),
                    str(event_ref_value.get("work_id")),
                    str(event_ref_value.get("contract_version")),
                )
                if exact_records.get(key) is None:
                    findings.append(
                        GraphFinding(
                            "G22.SUPPORT.INITIATING_EVENT_UNRESOLVED",
                            scenario_id,
                            (
                                f"{process.logical_identity}: exact "
                                "initiating Event does not resolve"
                            ),
                        )
                    )

    for record in records:
        if record.contract not in {
            "support_need",
            "support_goal",
            "support",
            "intervention",
            "implementation",
            "fidelity",
            "follow_up",
            "outcome",
        }:
            continue
        target_info = _support_target_participant_id(record.value)
        if target_info is None:
            continue
        participant_id, version = target_info
        key = (
            str(record.value.get("class_id")),
            str(record.value.get("work_id")),
            participant_id,
            version or "1",
        )
        if support_participants.get(key) is None:
            foreign_participant = next(
                (
                    candidate
                    for candidate_key, candidate in support_participants.items()
                    if (
                        candidate_key[2] == participant_id
                        and candidate_key[3] == (version or "1")
                        and candidate_key[:2] != key[:2]
                    )
                ),
                None,
            )
            if record.contract == "outcome" and foreign_participant is not None:
                code = "G22.OUTCOME.TARGET_WRONG_PROCESS"
                detail = (
                    "Outcome target resolves only in another Support Process"
                )
            else:
                code = "G22.SUPPORT.TARGET_PARTICIPANT_UNRESOLVED"
                detail = (
                    "exact Support Process participant target does not resolve"
                )
            findings.append(
                GraphFinding(
                    code,
                    scenario_id,
                    f"{record.logical_identity}: {detail}",
                )
            )

    for support in [
        record
        for record in records
        if record.contract in {"support", "intervention"}
    ]:
        for field_name, expected_kind in (
            ("need_refs", "support_need"),
            ("goal_refs", "support_goal"),
        ):
            refs = support.value.get(field_name, [])
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if not isinstance(ref, dict):
                    continue
                key = (
                    str(support.value.get("class_id")),
                    str(support.value.get("work_id")),
                    str(ref.get("record_kind")),
                    str(ref.get("record_id")),
                    str(ref.get("contract_version")),
                )
                resolved = support_local_records.get(key)
                if resolved is None or ref.get("record_kind") != expected_kind:
                    findings.append(
                        GraphFinding(
                            "G22.SUPPORT.PLAN_REFERENCE_UNRESOLVED",
                            scenario_id,
                            (
                                f"{support.logical_identity}: exact "
                                f"{field_name} reference does not resolve"
                            ),
                        )
                    )

        provider_plan = support.value.get("provider_plan")
        if (
            isinstance(provider_plan, dict)
            and provider_plan.get("kind") == "assigned"
        ):
            for ref in provider_plan.get("participant_refs", []):
                if not isinstance(ref, dict):
                    continue
                key = (
                    str(support.value.get("class_id")),
                    str(support.value.get("work_id")),
                    str(ref.get("record_id")),
                    str(ref.get("contract_version")),
                )
                provider = support_participants.get(key)
                participant_contexts = (
                    provider.value.get("contexts", [])
                    if provider is not None
                    else []
                )
                context_kinds = {
                    item.get("kind")
                    for item in participant_contexts
                    if isinstance(item, dict)
                }
                if (
                    provider is None
                    or "provider_or_collaborator" not in context_kinds
                ):
                    findings.append(
                        GraphFinding(
                            "G22.SUPPORT.PROVIDER_UNRESOLVED",
                            scenario_id,
                            (
                                f"{support.logical_identity}: assigned "
                                "provider participant does not resolve "
                                "with provider context"
                            ),
                        )
                    )

    implementations = {
        (
            str(record.value.get("class_id")),
            str(record.value.get("work_id")),
            str(record.value.get("implementation_id")),
            record.version,
        ): record
        for record in records
        if (
            record.contract == "implementation"
            and isinstance(record.value.get("implementation_id"), str)
        )
    }

    for implementation in implementations.values():
        plan_ref = implementation.value.get("plan_ref")
        if isinstance(plan_ref, dict):
            key = (
                str(implementation.value.get("class_id")),
                str(implementation.value.get("work_id")),
                str(plan_ref.get("record_kind")),
                str(plan_ref.get("record_id")),
                str(plan_ref.get("contract_version")),
            )
            if support_local_records.get(key) is None:
                foreign_plan = next(
                    (
                        candidate
                        for candidate in support_local_records.values()
                        if (
                            candidate.contract == plan_ref.get("record_kind")
                            and _id_for_record(candidate)
                            == plan_ref.get("record_id")
                            and candidate.version
                            == plan_ref.get("contract_version")
                            and (
                                candidate.value.get("class_id"),
                                candidate.value.get("work_id"),
                            )
                            != (
                                implementation.value.get("class_id"),
                                implementation.value.get("work_id"),
                            )
                        )
                    ),
                    None,
                )
                code = (
                    "G22.SUPPORT.IMPLEMENTATION_PLAN_WRONG_PROCESS"
                    if foreign_plan is not None
                    else "G22.SUPPORT.IMPLEMENTATION_PLAN_UNRESOLVED"
                )
                detail = (
                    "plan reference resolves only in another Support Process"
                    if foreign_plan is not None
                    else "plan reference does not resolve"
                )
                findings.append(
                    GraphFinding(
                        code,
                        scenario_id,
                        (
                            f"{implementation.logical_identity}: exact "
                            f"{detail}"
                        ),
                    )
                )

    for fidelity in [
        record for record in records if record.contract == "fidelity"
    ]:
        plan_ref = fidelity.value.get("plan_ref")
        if isinstance(plan_ref, dict):
            key = (
                str(fidelity.value.get("class_id")),
                str(fidelity.value.get("work_id")),
                str(plan_ref.get("record_kind")),
                str(plan_ref.get("record_id")),
                str(plan_ref.get("contract_version")),
            )
            if support_local_records.get(key) is None:
                findings.append(
                    GraphFinding(
                        "G22.SUPPORT.FIDELITY_PLAN_UNRESOLVED",
                        scenario_id,
                        (
                            f"{fidelity.logical_identity}: exact plan "
                            "reference does not resolve"
                        ),
                    )
                )

        scope = fidelity.value.get("scope")
        refs: list[dict[str, object]] = []
        if isinstance(scope, dict):
            if scope.get("kind") == "one_implementation":
                ref = scope.get("implementation_ref")
                if isinstance(ref, dict):
                    refs = [ref]
            elif scope.get("kind") == "implementation_set":
                candidate_refs = scope.get("implementation_refs", [])
                if isinstance(candidate_refs, list):
                    refs = [
                        ref for ref in candidate_refs if isinstance(ref, dict)
                    ]
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            key = (
                str(fidelity.value.get("class_id")),
                str(fidelity.value.get("work_id")),
                str(ref.get("record_id")),
                str(ref.get("contract_version")),
            )
            implementation = implementations.get(key)
            if implementation is None:
                foreign_implementation = next(
                    (
                        candidate
                        for candidate in implementations.values()
                        if (
                            candidate.value.get("implementation_id")
                            == ref.get("record_id")
                            and candidate.version
                            == ref.get("contract_version")
                            and (
                                candidate.value.get("class_id"),
                                candidate.value.get("work_id"),
                            )
                            != (
                                fidelity.value.get("class_id"),
                                fidelity.value.get("work_id"),
                            )
                        )
                    ),
                    None,
                )
                code = (
                    "G22.SUPPORT.FIDELITY_IMPLEMENTATION_WRONG_PROCESS"
                    if foreign_implementation is not None
                    else "G22.SUPPORT.FIDELITY_IMPLEMENTATION_UNRESOLVED"
                )
                detail = (
                    "resolves only in another Support Process"
                    if foreign_implementation is not None
                    else "does not resolve"
                )
                findings.append(
                    GraphFinding(
                        code,
                        scenario_id,
                        (
                            f"{fidelity.logical_identity}: scoped "
                            f"Implementation {detail}"
                        ),
                    )
                )
            elif (
                isinstance(plan_ref, dict)
                and implementation.value.get("plan_ref") != plan_ref
            ):
                findings.append(
                    GraphFinding(
                        "G22.SUPPORT.FIDELITY_PLAN_MISMATCH",
                        scenario_id,
                        (
                            f"{fidelity.logical_identity}: scoped "
                            "Implementation belongs to another plan"
                        ),
                    )
                )

    for follow_up in [
        record for record in records if record.contract == "follow_up"
    ]:
        owner_value = follow_up.value.get("owner")
        if (
            isinstance(owner_value, dict)
            and owner_value.get("kind")
            == "support_process_participant"
        ):
            ref = owner_value.get("participant_ref")
            if isinstance(ref, dict):
                key = (
                    str(follow_up.value.get("class_id")),
                    str(follow_up.value.get("work_id")),
                    str(ref.get("record_id")),
                    str(ref.get("contract_version")),
                )
                participant = support_participants.get(key)
                participant_contexts = (
                    participant.value.get("contexts", [])
                    if participant is not None
                    else []
                )
                context_kinds = {
                    item.get("kind")
                    for item in participant_contexts
                    if isinstance(item, dict)
                }
                if participant is None or not (
                    {"provider_or_collaborator", "coordinator"}
                    & context_kinds
                ):
                    findings.append(
                        GraphFinding(
                            "G22.SUPPORT.FOLLOW_UP_OWNER_UNRESOLVED",
                            scenario_id,
                            (
                                f"{follow_up.logical_identity}: owner "
                                "participant is not eligible"
                            ),
                        )
                    )

        for relation in follow_up.value.get("related_records", []):
            if not isinstance(relation, dict):
                continue
            record_ref = relation.get("record_ref")
            if not isinstance(record_ref, dict):
                continue
            key = _exact_work_record_tuple(record_ref)
            if key is None:
                continue
            lookup_key = (
                key[0],
                key[1],
                key[2],
                key[3],
                key[4],
            )
            if exact_records.get(lookup_key) is None:
                findings.append(
                    GraphFinding(
                        "G22.SUPPORT.FOLLOW_UP_RECORD_UNRESOLVED",
                        scenario_id,
                        (
                            f"{follow_up.logical_identity}: related "
                            "record does not resolve exactly"
                        ),
                    )
                )

    for outcome in [
        record for record in records if record.contract == "outcome"
    ]:
        evaluator = outcome.value.get("evaluator")
        if (
            isinstance(evaluator, dict)
            and evaluator.get("kind")
            == "support_process_participant"
        ):
            ref = evaluator.get("participant_ref")
            if isinstance(ref, dict):
                key = (
                    str(outcome.value.get("class_id")),
                    str(outcome.value.get("work_id")),
                    str(ref.get("record_id")),
                    str(ref.get("contract_version")),
                )
                participant = support_participants.get(key)
                participant_contexts = (
                    participant.value.get("contexts", [])
                    if participant is not None
                    else []
                )
                context_kinds = {
                    item.get("kind")
                    for item in participant_contexts
                    if isinstance(item, dict)
                }
                if participant is None or not (
                    {"provider_or_collaborator", "coordinator", "observer"}
                    & context_kinds
                ):
                    findings.append(
                        GraphFinding(
                            "G22.OUTCOME.EVALUATOR_UNRESOLVED",
                            scenario_id,
                            (
                                f"{outcome.logical_identity}: eligible "
                                "Outcome evaluator does not resolve"
                            ),
                        )
                    )

        for basis_entry in outcome.value.get("basis", []):
            if not isinstance(basis_entry, dict):
                continue
            locator = basis_entry.get("locator")
            if (
                not isinstance(locator, dict)
                or locator.get("kind") != "portia_record"
            ):
                continue
            record_ref = locator.get("record_ref")
            if not isinstance(record_ref, dict):
                continue
            key = _exact_work_record_tuple(record_ref)
            if key is None or exact_records.get(key) is None:
                findings.append(
                    GraphFinding(
                        "G22.OUTCOME.BASIS_UNRESOLVED",
                        scenario_id,
                        (
                            f"{outcome.logical_identity}: exact Outcome "
                            "basis record does not resolve"
                        ),
                    )
                )

    # Workspace Actor Directory + Response/Communication boundaries.
    actor_roots = {
        str(record.value["actor_id"]): record
        for record in records
        if (
            record.contract == "actor"
            and isinstance(record.value.get("actor_id"), str)
        )
    }
    actor_contacts = {
        (
            str(record.value["actor_id"]),
            str(record.value["contact_point_id"]),
            record.version,
        ): record
        for record in records
        if (
            record.contract == "actor_contact_point"
            and isinstance(record.value.get("actor_id"), str)
            and isinstance(
                record.value.get("contact_point_id"),
                str,
            )
        )
    }
    actor_relationships = {
        (
            str(record.value["actor_id"]),
            str(record.value["relationship_id"]),
            record.version,
        ): record
        for record in records
        if (
            record.contract == "actor_student_relationship"
            and isinstance(record.value.get("actor_id"), str)
            and isinstance(
                record.value.get("relationship_id"),
                str,
            )
        )
    }

    for contact in actor_contacts.values():
        actor_id = contact.value.get("actor_id")
        actor = (
            actor_roots.get(actor_id)
            if isinstance(actor_id, str)
            else None
        )
        if actor is None:
            findings.append(
                GraphFinding(
                    "G22.IDENTITY.CONTACT_ACTOR_UNRESOLVED",
                    scenario_id,
                    (
                        f"{contact.logical_identity}: owning Actor "
                        "does not resolve"
                    ),
                )
            )
        elif (
            contact.value.get("status") == "active"
            and actor.value.get("status") != "active"
        ):
            findings.append(
                GraphFinding(
                    "G22.IDENTITY.CONTACT_ACTOR_NOT_ACTIVE",
                    scenario_id,
                    (
                        f"{contact.logical_identity}: active Contact "
                        "Point requires active Actor"
                    ),
                )
            )

    for relationship in actor_relationships.values():
        actor_id = relationship.value.get("actor_id")
        actor = (
            actor_roots.get(actor_id)
            if isinstance(actor_id, str)
            else None
        )
        if actor is None:
            findings.append(
                GraphFinding(
                    "G22.IDENTITY.RELATIONSHIP_ACTOR_UNRESOLVED",
                    scenario_id,
                    (
                        f"{relationship.logical_identity}: owning Actor "
                        "does not resolve"
                    ),
                )
            )
        elif (
            relationship.value.get("status") == "active"
            and actor.value.get("status") != "active"
        ):
            findings.append(
                GraphFinding(
                    "G22.IDENTITY.RELATIONSHIP_ACTOR_NOT_ACTIVE",
                    scenario_id,
                    (
                        f"{relationship.logical_identity}: active "
                        "Relationship requires active Actor"
                    ),
                )
            )

        student_ref = relationship.value.get("student_ref")
        if (
            isinstance(student_ref, dict)
            and not _roster_subject_resolves(
                {
                    "kind": "roster_student",
                    "roster_student_ref": student_ref,
                },
                rosters,
            )
        ):
            findings.append(
                GraphFinding(
                    "G22.IDENTITY.RELATIONSHIP_STUDENT_UNRESOLVED",
                    scenario_id,
                    (
                        f"{relationship.logical_identity}: exact "
                        "roster-qualified student does not resolve"
                    ),
                )
            )

        if (
            relationship.value.get("status") == "active"
            and relationship.value.get("review", {}).get("kind")
            != "locally_reviewed"
        ):
            findings.append(
                GraphFinding(
                    "G22.IDENTITY.RELATIONSHIP_NOT_REVIEWED",
                    scenario_id,
                    (
                        f"{relationship.logical_identity}: active "
                        "Relationship requires local human review"
                    ),
                )
            )

    responses_by_work = {
        (
            str(record.value.get("class_id")),
            str(record.value.get("work_id")),
            str(record.value.get("response_id")),
            record.version,
        ): record
        for record in records
        if (
            record.contract == "response"
            and isinstance(record.value.get("response_id"), str)
        )
    }

    for communication in [
        record
        for record in records
        if record.contract == "communication"
    ]:
        recipients = communication.value.get("recipients", [])
        seen_recipients: set[tuple[str, str]] = set()

        if isinstance(recipients, list):
            for recipient in recipients:
                if not isinstance(recipient, dict):
                    continue
                person = recipient.get("person")
                if (
                    isinstance(person, dict)
                    and person.get("kind") == "actor"
                ):
                    actor_ref = person.get("actor_ref")
                    actor_id = (
                        actor_ref.get("actor_id")
                        if isinstance(actor_ref, dict)
                        else None
                    )
                    actor = (
                        actor_roots.get(actor_id)
                        if isinstance(actor_id, str)
                        else None
                    )
                    if actor is None:
                        findings.append(
                            GraphFinding(
                                "G22.COMMUNICATION.RECIPIENT_ACTOR_UNRESOLVED",
                                scenario_id,
                                (
                                    f"{communication.logical_identity}: "
                                    "recipient Actor does not resolve"
                                ),
                            )
                        )
                    elif actor.value.get("status") != "active":
                        findings.append(
                            GraphFinding(
                                "G22.COMMUNICATION.RECIPIENT_ACTOR_NOT_ACTIVE",
                                scenario_id,
                                (
                                    f"{communication.logical_identity}: "
                                    "recipient Actor is not active"
                                ),
                            )
                        )

                    endpoint_ref = recipient.get("endpoint_ref")
                    if isinstance(endpoint_ref, dict):
                        cp_key = (
                            str(endpoint_ref.get("actor_id")),
                            str(
                                endpoint_ref.get(
                                    "contact_point_id"
                                )
                            ),
                            str(
                                endpoint_ref.get(
                                    "contract_version"
                                )
                            ),
                        )
                        contact = actor_contacts.get(cp_key)
                        if contact is None:
                            findings.append(
                                GraphFinding(
                                    "G22.COMMUNICATION.ENDPOINT_UNRESOLVED",
                                    scenario_id,
                                    (
                                        f"{communication.logical_identity}: "
                                        "exact recipient Contact Point "
                                        "does not resolve"
                                    ),
                                )
                            )
                        else:
                            if contact.value.get("status") != "active":
                                findings.append(
                                    GraphFinding(
                                        "G22.COMMUNICATION.ENDPOINT_NOT_ACTIVE",
                                        scenario_id,
                                        (
                                            f"{communication.logical_identity}: "
                                            "recipient Contact Point is "
                                            "not active"
                                        ),
                                    )
                                )
                            if (
                                isinstance(actor_id, str)
                                and endpoint_ref.get("actor_id")
                                != actor_id
                            ):
                                findings.append(
                                    GraphFinding(
                                        "G22.COMMUNICATION.ENDPOINT_WRONG_ACTOR",
                                        scenario_id,
                                        (
                                            f"{communication.logical_identity}: "
                                            "endpoint belongs to another Actor"
                                        ),
                                    )
                                )

                    if isinstance(actor_id, str):
                        logical_recipient = ("actor", actor_id)
                        if logical_recipient in seen_recipients:
                            findings.append(
                                GraphFinding(
                                    "G22.COMMUNICATION.DUPLICATE_RECIPIENT",
                                    scenario_id,
                                    (
                                        f"{communication.logical_identity}: "
                                        "duplicate logical recipient"
                                    ),
                                )
                            )
                        seen_recipients.add(logical_recipient)

        relations = communication.value.get("relations", [])
        if isinstance(relations, list):
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                record_ref = relation.get("record_ref")
                if not isinstance(record_ref, dict):
                    continue
                work_ref = record_ref.get("work_ref")
                local_ref = record_ref.get("record_ref")
                if (
                    relation.get("relation")
                    == "relates_to_response"
                    and isinstance(work_ref, dict)
                    and isinstance(local_ref, dict)
                ):
                    key = (
                        str(work_ref.get("class_id")),
                        str(work_ref.get("work_id")),
                        str(local_ref.get("record_id")),
                        str(local_ref.get("contract_version")),
                    )
                    response = responses_by_work.get(key)
                    if (
                        response is None
                        or local_ref.get("record_kind")
                        != "response"
                    ):
                        findings.append(
                            GraphFinding(
                                "G22.COMMUNICATION.RESPONSE_UNRESOLVED",
                                scenario_id,
                                (
                                    f"{communication.logical_identity}: "
                                    "related Response does not resolve "
                                    "exactly"
                                ),
                            )
                        )
                    elif (
                        work_ref.get("class_id")
                        != communication.value.get("class_id")
                        or work_ref.get("work_id")
                        != communication.value.get("work_id")
                        or work_ref.get("work_kind")
                        != communication.value.get("work_kind")
                    ):
                        findings.append(
                            GraphFinding(
                                "G22.COMMUNICATION.RESPONSE_WRONG_WORK",
                                scenario_id,
                                (
                                    f"{communication.logical_identity}: "
                                    "related Response is outside the "
                                    "owning work"
                                ),
                            )
                        )

    # Paper/PDS2 capture lineage, review, and materialization.
    core_contexts = _contexts_of_kind(contexts, "synthetic_core_pds2")
    operation_contexts = _contexts_of_kind(
        contexts, "synthetic_operation_acceptance"
    )

    page_targets = {
        str(r.value["page_target_id"]): r
        for r in records
        if r.contract == "page_target"
        and isinstance(r.value.get("page_target_id"), str)
    }
    page_records = {
        str(r.value["page_record_id"]): r
        for r in records
        if r.contract == "page_record"
        and isinstance(r.value.get("page_record_id"), str)
    }
    interpretations = {
        (str(r.value["interpretation_id"]), int(r.value["generation"])): r
        for r in records
        if r.contract == "paper_interpretation"
        and isinstance(r.value.get("interpretation_id"), str)
        and isinstance(r.value.get("generation"), int)
    }
    proposals = {
        str(r.value["proposal_id"]): r
        for r in records
        if r.contract == "capture_proposal"
        and isinstance(r.value.get("proposal_id"), str)
    }
    capture_reviews = {
        (str(r.value["review_id"]), int(r.value["review_sequence"])): r
        for r in records
        if r.contract == "capture_review"
        and isinstance(r.value.get("review_id"), str)
        and isinstance(r.value.get("review_sequence"), int)
    }

    seen_ingestion: set[tuple[str, str, int]] = set()
    for page_record in page_records.values():
        route_id = page_record.value.get("route_id")
        source_ref = page_record.value.get("source_ref")
        if not isinstance(route_id, str) or not isinstance(source_ref, dict):
            continue

        scan_id = source_ref.get("source_scan_id")
        page_number = source_ref.get("source_page_number")
        if isinstance(scan_id, str) and isinstance(page_number, int):
            ingestion = (route_id, scan_id, page_number)
            if ingestion in seen_ingestion:
                findings.append(
                    GraphFinding(
                        "G22.PAPER.DUPLICATE_PHYSICAL_PAGE",
                        scenario_id,
                        f"{page_record.logical_identity}: duplicate physical-page ingestion tuple",
                    )
                )
            seen_ingestion.add(ingestion)

        target_id = page_record.value.get("page_target_id")
        if not isinstance(target_id, str) or target_id not in page_targets:
            findings.append(
                GraphFinding(
                    "G22.PAPER.PAGE_TARGET_UNRESOLVED",
                    scenario_id,
                    f"{page_record.logical_identity}: Page Target does not resolve",
                )
            )

        core = None
        for context in core_contexts:
            route = context.get("route")
            retained = context.get("retained_source")
            if (
                isinstance(route, dict)
                and route.get("route_id") == route_id
                and isinstance(retained, dict)
                and retained.get("source_scan_id") == scan_id
            ):
                core = context
                break
        if core is None:
            findings.append(
                GraphFinding(
                    "G22.PAPER.CORE_SOURCE_UNRESOLVED",
                    scenario_id,
                    f"{page_record.logical_identity}: Core route/source context does not resolve",
                )
            )
            continue

        route = core["route"]
        retained = core["retained_source"]
        route_target = route.get("target")
        if (
            route.get("module_id") != "portia"
            or route.get("class_id") != page_record.value.get("class_id")
            or route.get("work_id") != page_record.value.get("work_id")
            or not isinstance(route_target, dict)
            or route_target.get("record_kind") != "capture_page_target"
            or route_target.get("record_id") != target_id
            or route_target.get("contract_version") != "1"
        ):
            findings.append(
                GraphFinding(
                    "G22.PAPER.ROUTE_TARGET_MISMATCH",
                    scenario_id,
                    f"{page_record.logical_identity}: Core route target disagrees",
                )
            )
        if (
            retained.get("source_sha256") != source_ref.get("source_sha256")
            or retained.get("source_page_number") != page_number
        ):
            findings.append(
                GraphFinding(
                    "G22.PAPER.RETAINED_SOURCE_MISMATCH",
                    scenario_id,
                    f"{page_record.logical_identity}: retained source identity disagrees",
                )
            )

        fixture_path = retained.get("fixture_path")
        if isinstance(fixture_path, str):
            try:
                source_path = _safe_fixture_path(CORPUS_ROOT, fixture_path)
                source_bytes = source_path.read_bytes()
            except (OSError, ValueError):
                findings.append(
                    GraphFinding(
                        "G22.PAPER.SOURCE_BYTES_UNAVAILABLE",
                        scenario_id,
                        f"{page_record.logical_identity}: retained source bytes unavailable",
                    )
                )
            else:
                if hashlib.sha256(source_bytes).hexdigest() != retained.get("source_sha256"):
                    findings.append(
                        GraphFinding(
                            "G22.PAPER.SOURCE_DIGEST_MISMATCH",
                            scenario_id,
                            f"{page_record.logical_identity}: retained source digest disagrees",
                        )
                    )
                if len(source_bytes) != retained.get("byte_length"):
                    findings.append(
                        GraphFinding(
                            "G22.PAPER.SOURCE_LENGTH_MISMATCH",
                            scenario_id,
                            f"{page_record.logical_identity}: retained source length disagrees",
                        )
                    )

    for interpretation in interpretations.values():
        target = page_targets.get(interpretation.value.get("page_target_id"))
        page_record = page_records.get(interpretation.value.get("page_record_id"))
        if target is None or page_record is None:
            findings.append(
                GraphFinding(
                    "G22.PAPER.INTERPRETATION_LINEAGE_UNRESOLVED",
                    scenario_id,
                    f"{interpretation.logical_identity}: capture lineage does not resolve",
                )
            )
            continue
        if interpretation.value.get("layout_snapshot") != target.value.get("template_identity"):
            findings.append(
                GraphFinding(
                    "G22.PAPER.LAYOUT_SNAPSHOT_MISMATCH",
                    scenario_id,
                    f"{interpretation.logical_identity}: layout snapshot disagrees",
                )
            )

    for proposal in proposals.values():
        iref = proposal.value.get("interpretation_ref")
        ikey = (
            (iref.get("interpretation_id"), iref.get("generation"))
            if isinstance(iref, dict) else None
        )
        interpretation = interpretations.get(ikey) if ikey else None
        if interpretation is None:
            findings.append(
                GraphFinding(
                    "G22.PAPER.PROPOSAL_INTERPRETATION_UNRESOLVED",
                    scenario_id,
                    f"{proposal.logical_identity}: Interpretation does not resolve",
                )
            )
            continue
        if _capture_lineage_tuple(proposal.value) != _capture_lineage_tuple(interpretation.value):
            findings.append(
                GraphFinding(
                    "G22.PAPER.PROPOSAL_LINEAGE_MISMATCH",
                    scenario_id,
                    f"{proposal.logical_identity}: lineage differs from Interpretation",
                )
            )
        entry_key = proposal.value.get("entry_key")
        entries = interpretation.value.get("entries")
        entry = entries.get(entry_key) if isinstance(entries, dict) else None
        if not isinstance(entry, dict):
            findings.append(
                GraphFinding(
                    "G22.PAPER.PROPOSAL_ENTRY_UNRESOLVED",
                    scenario_id,
                    f"{proposal.logical_identity}: interpreted entry does not resolve",
                )
            )
            continue
        target = proposal.value.get("target")
        if isinstance(target, dict) and entry.get("mapped_record_kind") != target.get("record_kind"):
            findings.append(
                GraphFinding(
                    "G22.PAPER.PROPOSAL_MAPPING_MISMATCH",
                    scenario_id,
                    f"{proposal.logical_identity}: mapped kind differs from target",
                )
            )
        fields = entry.get("fields")
        for binding in proposal.value.get("field_bindings", []):
            source_field = binding.get("source_field") if isinstance(binding, dict) else None
            field_key = source_field.get("field_key") if isinstance(source_field, dict) else None
            if not isinstance(fields, dict) or field_key not in fields:
                findings.append(
                    GraphFinding(
                        "G22.PAPER.PROPOSAL_FIELD_UNRESOLVED",
                        scenario_id,
                        f"{proposal.logical_identity}: bound source field does not resolve",
                    )
                )

    for review in capture_reviews.values():
        pref = review.value.get("proposal_ref")
        iref = review.value.get("interpretation_ref")
        proposal = proposals.get(pref.get("proposal_id")) if isinstance(pref, dict) else None
        ikey = (
            (iref.get("interpretation_id"), iref.get("generation"))
            if isinstance(iref, dict) else None
        )
        interpretation = interpretations.get(ikey) if ikey else None
        if proposal is None or interpretation is None:
            findings.append(
                GraphFinding(
                    "G22.PAPER.REVIEW_LINEAGE_UNRESOLVED",
                    scenario_id,
                    f"{review.logical_identity}: Proposal/Interpretation does not resolve",
                )
            )
        elif (
            _capture_lineage_tuple(review.value) != _capture_lineage_tuple(proposal.value)
            or review.value.get("entry_key") != proposal.value.get("entry_key")
        ):
            findings.append(
                GraphFinding(
                    "G22.PAPER.REVIEW_LINEAGE_MISMATCH",
                    scenario_id,
                    f"{review.logical_identity}: review lineage disagrees",
                )
            )

    # G22-027 uses closed test-only resolution metadata to state that the
    # proposal itself resolves while the exact Capture Review does not.  This
    # prevents the negative fixture from conflating missing proposal lineage
    # with the intended review-gate defect.
    capture_resolution_contexts = _contexts_of_kind(
        contexts,
        "synthetic_capture_materialization_resolution",
    )
    capture_resolution_by_operation = {
        str(item.get("materialization_operation_id")): item
        for item in capture_resolution_contexts
        if isinstance(item.get("materialization_operation_id"), str)
    }

    for receipt in [r for r in records if r.contract == "capture_materialization"]:
        pref = receipt.value.get("proposal_ref")
        rref = receipt.value.get("review_ref")
        oref = receipt.value.get("operation_journal_ref")
        proposal = proposals.get(pref.get("proposal_id")) if isinstance(pref, dict) else None
        rkey = (
            (rref.get("review_id"), rref.get("review_sequence"))
            if isinstance(rref, dict) else None
        )
        review = capture_reviews.get(rkey) if rkey else None
        operation_id = oref.get("operation_id") if isinstance(oref, dict) else None
        synthetic_resolution = (
            capture_resolution_by_operation.get(operation_id)
            if isinstance(operation_id, str)
            else None
        )
        proposal_resolves = proposal is not None or (
            isinstance(synthetic_resolution, dict)
            and synthetic_resolution.get("proposal_resolves") is True
            and isinstance(pref, dict)
            and synthetic_resolution.get("proposal_ref") == pref
        )
        review_resolves = review is not None or (
            isinstance(synthetic_resolution, dict)
            and synthetic_resolution.get("review_resolves") is True
        )
        if not proposal_resolves or not review_resolves:
            findings.append(
                GraphFinding(
                    "G22.PAPER.MATERIALIZATION_REVIEW_UNRESOLVED",
                    scenario_id,
                    f"{receipt.logical_identity}: required exact Capture Review does not resolve",
                )
            )
            continue
        if _capture_lineage_tuple(receipt.value) != _capture_lineage_tuple(review.value):
            findings.append(
                GraphFinding(
                    "G22.PAPER.MATERIALIZATION_LINEAGE_MISMATCH",
                    scenario_id,
                    f"{receipt.logical_identity}: receipt lineage disagrees",
                )
            )
        if review.value.get("disposition") not in {"accepted", "corrected_and_accepted"}:
            findings.append(
                GraphFinding(
                    "G22.PAPER.REVIEW_NOT_ACCEPTED",
                    scenario_id,
                    f"{receipt.logical_identity}: review does not authorize next step",
                )
            )

        operation = None
        if isinstance(oref, dict):
            for context in operation_contexts:
                if (
                    context.get("operation_id") == oref.get("operation_id")
                    and context.get("journal_revision") == oref.get("journal_revision")
                    and context.get("contract_version") == oref.get("contract_version")
                ):
                    operation = context
                    break
        if operation is None or operation.get("state") != "committed":
            findings.append(
                GraphFinding(
                    "G22.OPERATION.MATERIALIZATION_NOT_COMMITTED",
                    scenario_id,
                    f"{receipt.logical_identity}: committed operation context does not resolve",
                )
            )

        for result in receipt.value.get("canonical_results", []):
            target = result.get("target") if isinstance(result, dict) else None
            work_ref = target.get("work_ref") if isinstance(target, dict) else None
            if not isinstance(work_ref, dict):
                continue
            result_key = (
                str(work_ref.get("class_id")),
                str(work_ref.get("work_id")),
                str(work_ref.get("work_kind")),
                str(work_ref.get("work_id")),
                str(work_ref.get("contract_version")),
            )
            produced = exact_records.get(result_key)
            if produced is None:
                findings.append(
                    GraphFinding(
                        "G22.PAPER.CANONICAL_RESULT_UNRESOLVED",
                        scenario_id,
                        f"{receipt.logical_identity}: canonical work result does not resolve",
                    )
                )
                continue

            source = produced.value.get("creation_source")
            page_record = page_records.get(receipt.value.get("page_record_id"))
            if (
                not isinstance(source, dict)
                or source.get("type") != "paper_capture"
                or source.get("stage") != "ingested"
                or page_record is None
                or source.get("route_id") != page_record.value.get("route_id")
                or source.get("page_record_id") != page_record.value.get("page_record_id")
            ):
                findings.append(
                    GraphFinding(
                        "G22.PAPER.CANONICAL_PROVENANCE_MISMATCH",
                        scenario_id,
                        f"{produced.logical_identity}: ingested paper provenance disagrees",
                    )
                )

            if review.value.get("disposition") == "accepted":
                iref = proposal.value.get("interpretation_ref")
                ikey = (
                    (iref.get("interpretation_id"), iref.get("generation"))
                    if isinstance(iref, dict) else None
                )
                interpretation = interpretations.get(ikey) if ikey else None
                if interpretation is not None:
                    entry = interpretation.value["entries"][proposal.value["entry_key"]]
                    fields = entry["fields"]
                    for binding in proposal.value.get("field_bindings", []):
                        source_field = binding["source_field"]
                        field = fields[source_field["field_key"]]
                        candidate = field.get("candidate_literal")
                        try:
                            actual = _json_pointer_get(produced.value, binding["target_path"])
                        except (KeyError, ValueError):
                            findings.append(
                                GraphFinding(
                                    "G22.PAPER.TARGET_PATH_UNRESOLVED",
                                    scenario_id,
                                    f"{proposal.logical_identity}: canonical target path does not resolve",
                                )
                            )
                        else:
                            if actual != candidate:
                                findings.append(
                                    GraphFinding(
                                        "G22.PAPER.ACCEPTED_VALUE_MISMATCH",
                                        scenario_id,
                                        f"{produced.logical_identity}: accepted candidate differs from canonical value",
                                    )
                                )

            if (
                isinstance(receipt.value.get("materialized_at"), str)
                and isinstance(produced.value.get("created_at"), str)
                and receipt.value["materialized_at"] < produced.value["created_at"]
            ):
                findings.append(
                    GraphFinding(
                        "G22.PAPER.RECEIPT_BEFORE_CANONICAL_ACCEPTANCE",
                        scenario_id,
                        f"{receipt.logical_identity}: receipt predates canonical creation",
                    )
                )

    # Durable operation evidence must reconcile accepted canonical write steps
    # against exact canonical readback.  Operation journals remain operational
    # evidence; they do not manufacture missing domain truth.
    for descriptor, journal, _journal_path in operational_fixtures:
        if (
            descriptor.get("contract") != "operation_journal"
            or journal.get("state") not in {"committed", "completed"}
            or not isinstance(journal.get("write_set"), list)
        ):
            continue
        missing_accepted = False
        for step in journal["write_set"]:
            if (
                not isinstance(step, dict)
                or step.get("disposition") != "accepted"
                or step.get("representation_role") != "canonical_domain"
            ):
                continue
            target = step.get("target")
            target_key = None
            if isinstance(target, dict):
                if (
                    target.get("kind") == "work_record"
                    and isinstance(target.get("work_record_ref"), dict)
                ):
                    target_key = _exact_portia_ref_key(
                        target["work_record_ref"]
                    )
                elif (
                    target.get("kind") == "work"
                    and isinstance(target.get("work_ref"), dict)
                ):
                    target_key = _exact_work_ref_key(target["work_ref"])
            if target_key is None or target_key not in exact_records:
                missing_accepted = True
                break
        if missing_accepted:
            findings.append(
                GraphFinding(
                    "G22.OPERATION.COMMITTED_RESULT_UNRESOLVED",
                    scenario_id,
                    (
                        f"operation:{journal.get('operation_id')}: "
                        "accepted committed write target does not resolve "
                        "from canonical readback"
                    ),
                )
            )

    # Structured import lineage, replay identity, review, and materialization.
    import_source_contexts = _contexts_of_kind(
        contexts,
        "synthetic_import_source",
    )
    import_mapping_contexts = _contexts_of_kind(
        contexts,
        "synthetic_import_mapping",
    )

    import_batches = {
        str(record.value["import_batch_id"]): record
        for record in records
        if (
            record.contract == "import_batch"
            and isinstance(record.value.get("import_batch_id"), str)
        )
    }
    import_sources = {
        str(record.value["source_record_id"]): record
        for record in records
        if (
            record.contract == "import_source_record"
            and isinstance(record.value.get("source_record_id"), str)
        )
    }
    import_proposals = {
        str(record.value["proposal_id"]): record
        for record in records
        if (
            record.contract == "import_proposal"
            and isinstance(record.value.get("proposal_id"), str)
        )
    }
    import_reviews = {
        (
            str(record.value["review_id"]),
            int(record.value["review_sequence"]),
        ): record
        for record in records
        if (
            record.contract == "import_review"
            and isinstance(record.value.get("review_id"), str)
            and isinstance(record.value.get("review_sequence"), int)
        )
    }

    # Resolve fixture-backed source snapshots and exact mapping bytes.
    source_context = (
        import_source_contexts[0]
        if len(import_source_contexts) == 1
        else None
    )
    mapping_context = (
        import_mapping_contexts[0]
        if len(import_mapping_contexts) == 1
        else None
    )

    source_fixture_by_locator: dict[str, str] = {}
    if isinstance(source_context, dict):
        snapshots = source_context.get("snapshots")
        if isinstance(snapshots, list):
            for item in snapshots:
                if not isinstance(item, dict):
                    continue
                workspace_path = item.get("workspace_path")
                fixture_path = item.get("fixture_path")
                if (
                    isinstance(workspace_path, str)
                    and isinstance(fixture_path, str)
                ):
                    source_fixture_by_locator[
                        workspace_path
                    ] = fixture_path

    if isinstance(mapping_context, dict):
        mapping_fixture_path = mapping_context.get(
            "mapping_fixture_path"
        )
        # When the context object itself is the mapping profile fixture, it
        # intentionally has no nested mapping_fixture_path.
        if mapping_fixture_path is None:
            mapping_fixture_path = (
                "shared/policy-context/"
                "p22-06-import-mapping.json"
            )
    else:
        mapping_fixture_path = None

    mapping_digest = None
    if isinstance(mapping_fixture_path, str):
        try:
            mapping_path = _safe_fixture_path(
                CORPUS_ROOT,
                mapping_fixture_path,
            )
            mapping_digest = hashlib.sha256(
                mapping_path.read_bytes()
            ).hexdigest()
        except (OSError, ValueError):
            findings.append(
                GraphFinding(
                    "G22.IMPORT.MAPPING_FIXTURE_UNAVAILABLE",
                    scenario_id,
                    "structured-import mapping fixture is unavailable",
                )
            )

    seen_import_identity: set[str] = set()
    for batch in import_batches.values():
        expected_identity = issue22_fixture_digest(
            issue22_import_batch_identity_payload(batch.value)
        )
        actual_identity = batch.value.get(
            "import_identity_digest"
        )
        if actual_identity != expected_identity:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.BATCH_IDENTITY_DIGEST_MISMATCH",
                    scenario_id,
                    (
                        f"{batch.logical_identity}: Import Batch "
                        "identity digest does not recompute"
                    ),
                )
            )
        elif isinstance(actual_identity, str):
            if actual_identity in seen_import_identity:
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.DUPLICATE_BATCH_IDENTITY",
                        scenario_id,
                        (
                            f"{batch.logical_identity}: duplicate "
                            "Import Batch logical identity digest"
                        ),
                    )
                )
            seen_import_identity.add(actual_identity)

        mapping_profile = batch.value.get("mapping_profile")
        if (
            isinstance(mapping_profile, dict)
            and mapping_digest is not None
            and mapping_profile.get("mapping_digest")
            != mapping_digest
        ):
            findings.append(
                GraphFinding(
                    "G22.IMPORT.MAPPING_DIGEST_MISMATCH",
                    scenario_id,
                    (
                        f"{batch.logical_identity}: exact mapping "
                        "profile digest does not match fixture"
                    ),
                )
            )

        snapshot = batch.value.get("source_snapshot")
        locator = (
            snapshot.get("locator")
            if isinstance(snapshot, dict)
            else None
        )
        fingerprint = (
            snapshot.get("fingerprint")
            if isinstance(snapshot, dict)
            else None
        )
        workspace_path = (
            locator.get("path")
            if isinstance(locator, dict)
            and locator.get("kind") == "workspace_file"
            else None
        )
        fixture_path = (
            source_fixture_by_locator.get(workspace_path)
            if isinstance(workspace_path, str)
            else None
        )
        if not isinstance(fixture_path, str):
            findings.append(
                GraphFinding(
                    "G22.IMPORT.SOURCE_SNAPSHOT_UNRESOLVED",
                    scenario_id,
                    (
                        f"{batch.logical_identity}: exact import "
                        "source byte fixture does not resolve"
                    ),
                )
            )
        else:
            try:
                source_path = _safe_fixture_path(
                    CORPUS_ROOT,
                    fixture_path,
                )
                source_bytes = source_path.read_bytes()
            except (OSError, ValueError):
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.SOURCE_BYTES_UNAVAILABLE",
                        scenario_id,
                        (
                            f"{batch.logical_identity}: source "
                            "snapshot bytes are unavailable"
                        ),
                    )
                )
            else:
                if (
                    not isinstance(fingerprint, dict)
                    or fingerprint.get("algorithm") != "sha256"
                    or fingerprint.get("digest")
                    != hashlib.sha256(source_bytes).hexdigest()
                    or fingerprint.get("byte_length")
                    != len(source_bytes)
                ):
                    findings.append(
                        GraphFinding(
                            "G22.IMPORT.SOURCE_FINGERPRINT_MISMATCH",
                            scenario_id,
                            (
                                f"{batch.logical_identity}: source "
                                "snapshot fingerprint does not match bytes"
                            ),
                        )
                    )

    seen_source_identity: set[str] = set()
    for source in import_sources.values():
        batch_id = source.value.get("import_batch_id")
        batch = (
            import_batches.get(batch_id)
            if isinstance(batch_id, str)
            else None
        )
        if batch is None:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.SOURCE_BATCH_UNRESOLVED",
                    scenario_id,
                    (
                        f"{source.logical_identity}: exact Import "
                        "Batch does not resolve"
                    ),
                )
            )
            continue

        fields = source.value.get("source_fields")
        if isinstance(fields, list):
            field_keys = [
                item.get("field_key")
                for item in fields
                if isinstance(item, dict)
            ]
            if len(field_keys) != len(set(field_keys)):
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.DUPLICATE_SOURCE_FIELD",
                        scenario_id,
                        (
                            f"{source.logical_identity}: source field "
                            "keys are not unique"
                        ),
                    )
                )

        expected_content_digest = issue22_fixture_digest(
            issue22_import_source_content_payload(source.value)
        )
        if (
            source.value.get("source_record_digest")
            != expected_content_digest
        ):
            findings.append(
                GraphFinding(
                    "G22.IMPORT.SOURCE_CONTENT_DIGEST_MISMATCH",
                    scenario_id,
                    (
                        f"{source.logical_identity}: source-record "
                        "content digest does not recompute"
                    ),
                )
            )

        expected_identity = issue22_fixture_digest(
            issue22_import_source_identity_payload(
                batch.value,
                source.value,
            )
        )
        actual_identity = source.value.get(
            "source_record_identity_digest"
        )
        if actual_identity != expected_identity:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.SOURCE_IDENTITY_DIGEST_MISMATCH",
                    scenario_id,
                    (
                        f"{source.logical_identity}: source-record "
                        "identity digest does not recompute"
                    ),
                )
            )
        elif isinstance(actual_identity, str):
            if actual_identity in seen_source_identity:
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.DUPLICATE_SOURCE_IDENTITY",
                        scenario_id,
                        (
                            f"{source.logical_identity}: duplicate "
                            "source-record logical identity"
                        ),
                    )
                )
            seen_source_identity.add(actual_identity)

    seen_proposal_identity: set[str] = set()
    for proposal in import_proposals.values():
        batch_id = proposal.value.get("import_batch_id")
        source_id = proposal.value.get("source_record_id")
        batch = (
            import_batches.get(batch_id)
            if isinstance(batch_id, str)
            else None
        )
        source = (
            import_sources.get(source_id)
            if isinstance(source_id, str)
            else None
        )
        if batch is None or source is None:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.PROPOSAL_LINEAGE_UNRESOLVED",
                    scenario_id,
                    (
                        f"{proposal.logical_identity}: exact Batch/"
                        "Source lineage does not resolve"
                    ),
                )
            )
            continue
        if source.value.get("import_batch_id") != batch_id:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.PROPOSAL_LINEAGE_MISMATCH",
                    scenario_id,
                    (
                        f"{proposal.logical_identity}: Source Record "
                        "belongs to a different Import Batch"
                    ),
                )
            )

        expected_identity = issue22_fixture_digest(
            issue22_import_proposal_identity_payload(
                batch.value,
                source.value,
                proposal.value,
            )
        )
        actual_identity = proposal.value.get(
            "proposal_identity_digest"
        )
        if actual_identity != expected_identity:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.PROPOSAL_IDENTITY_DIGEST_MISMATCH",
                    scenario_id,
                    (
                        f"{proposal.logical_identity}: proposal "
                        "identity digest does not recompute"
                    ),
                )
            )
        elif isinstance(actual_identity, str):
            if actual_identity in seen_proposal_identity:
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.DUPLICATE_PROPOSAL_IDENTITY",
                        scenario_id,
                        (
                            f"{proposal.logical_identity}: duplicate "
                            "logical Import Proposal identity"
                        ),
                    )
                )
            seen_proposal_identity.add(actual_identity)

        source_fields = source.value.get("source_fields")
        source_field_keys = {
            item.get("field_key")
            for item in source_fields
            if isinstance(item, dict)
        } if isinstance(source_fields, list) else set()

        for binding in proposal.value.get(
            "field_bindings",
            [],
        ):
            if not isinstance(binding, dict):
                continue
            field_key = binding.get("source_field_key")
            if field_key not in source_field_keys:
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.PROPOSAL_SOURCE_FIELD_UNRESOLVED",
                        scenario_id,
                        (
                            f"{proposal.logical_identity}: bound "
                            "source field does not resolve"
                        ),
                    )
                )

    for review in import_reviews.values():
        batch_id = review.value.get("import_batch_id")
        source_ref = review.value.get("source_record_ref")
        proposal_ref = review.value.get("proposal_ref")
        source_id = (
            source_ref.get("source_record_id")
            if isinstance(source_ref, dict)
            else None
        )
        proposal_id = (
            proposal_ref.get("proposal_id")
            if isinstance(proposal_ref, dict)
            else None
        )
        batch = (
            import_batches.get(batch_id)
            if isinstance(batch_id, str)
            else None
        )
        source = (
            import_sources.get(source_id)
            if isinstance(source_id, str)
            else None
        )
        proposal = (
            import_proposals.get(proposal_id)
            if isinstance(proposal_id, str)
            else None
        )
        if batch is None or source is None or proposal is None:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.REVIEW_LINEAGE_UNRESOLVED",
                    scenario_id,
                    (
                        f"{review.logical_identity}: exact Batch/"
                        "Source/Proposal lineage does not resolve"
                    ),
                )
            )
            continue
        if (
            source.value.get("import_batch_id") != batch_id
            or proposal.value.get("import_batch_id") != batch_id
            or proposal.value.get("source_record_id") != source_id
            or proposal_ref.get("proposal_identity_digest")
            != proposal.value.get("proposal_identity_digest")
        ):
            findings.append(
                GraphFinding(
                    "G22.IMPORT.REVIEW_LINEAGE_MISMATCH",
                    scenario_id,
                    (
                        f"{review.logical_identity}: Import Review "
                        "lineage does not agree"
                    ),
                )
            )

    operation_contexts_for_import = _contexts_of_kind(
        contexts,
        "synthetic_operation_acceptance",
    )
    for receipt in [
        record
        for record in records
        if record.contract == "import_materialization"
    ]:
        batch_ref = receipt.value.get("import_batch_ref")
        source_ref = receipt.value.get("source_record_ref")
        proposal_ref = receipt.value.get("proposal_ref")
        review_ref = receipt.value.get("review_ref")
        operation_ref = receipt.value.get(
            "operation_journal_ref"
        )

        batch = (
            import_batches.get(batch_ref.get("import_batch_id"))
            if isinstance(batch_ref, dict)
            else None
        )
        source = (
            import_sources.get(
                source_ref.get("source_record_id")
            )
            if isinstance(source_ref, dict)
            else None
        )
        proposal = (
            import_proposals.get(
                proposal_ref.get("proposal_id")
            )
            if isinstance(proposal_ref, dict)
            else None
        )
        review_key = (
            (
                review_ref.get("review_id"),
                review_ref.get("review_sequence"),
            )
            if isinstance(review_ref, dict)
            else None
        )
        review = (
            import_reviews.get(review_key)
            if review_key is not None
            else None
        )

        if (
            batch is None
            or source is None
            or proposal is None
            or review is None
        ):
            findings.append(
                GraphFinding(
                    "G22.IMPORT.MATERIALIZATION_LINEAGE_UNRESOLVED",
                    scenario_id,
                    (
                        f"{receipt.logical_identity}: exact import "
                        "materialization lineage does not resolve"
                    ),
                )
            )
            continue

        if (
            batch_ref.get("import_identity_digest")
            != batch.value.get("import_identity_digest")
            or source_ref.get(
                "source_record_identity_digest"
            )
            != source.value.get(
                "source_record_identity_digest"
            )
            or proposal_ref.get(
                "proposal_identity_digest"
            )
            != proposal.value.get(
                "proposal_identity_digest"
            )
            or review.value.get("import_batch_id")
            != batch.value.get("import_batch_id")
            or review.value.get(
                "source_record_ref", {}
            ).get("source_record_id")
            != source.value.get("source_record_id")
            or review.value.get(
                "proposal_ref", {}
            ).get("proposal_id")
            != proposal.value.get("proposal_id")
        ):
            findings.append(
                GraphFinding(
                    "G22.IMPORT.MATERIALIZATION_LINEAGE_MISMATCH",
                    scenario_id,
                    (
                        f"{receipt.logical_identity}: digest-bound "
                        "import lineage does not agree"
                    ),
                )
            )

        if review.value.get("disposition") not in {
            "accepted",
            "corrected_and_accepted",
        }:
            findings.append(
                GraphFinding(
                    "G22.IMPORT.REVIEW_NOT_ACCEPTED",
                    scenario_id,
                    (
                        f"{receipt.logical_identity}: Import Review "
                        "does not authorize materialization"
                    ),
                )
            )

        operation = None
        if isinstance(operation_ref, dict):
            for context in operation_contexts_for_import:
                if (
                    context.get("operation_id")
                    == operation_ref.get("operation_id")
                    and context.get("journal_revision")
                    == operation_ref.get("journal_revision")
                    and context.get("contract_version")
                    == operation_ref.get("contract_version")
                ):
                    operation = context
                    break
        if operation is None or operation.get("state") != "committed":
            findings.append(
                GraphFinding(
                    "G22.OPERATION.IMPORT_MATERIALIZATION_NOT_COMMITTED",
                    scenario_id,
                    (
                        f"{receipt.logical_identity}: committed "
                        "operation context does not resolve"
                    ),
                )
            )

        source_values = {
            item.get("field_key"): item.get("value")
            for item in source.value.get("source_fields", [])
            if isinstance(item, dict)
        }

        for result in receipt.value.get(
            "canonical_results",
            [],
        ):
            if not isinstance(result, dict):
                continue
            target = result.get("target")
            work_ref = (
                target.get("work_ref")
                if isinstance(target, dict)
                and target.get("kind") == "work"
                else None
            )
            if not isinstance(work_ref, dict):
                continue
            result_key = (
                str(work_ref.get("class_id")),
                str(work_ref.get("work_id")),
                str(work_ref.get("work_kind")),
                str(work_ref.get("work_id")),
                str(work_ref.get("contract_version")),
            )
            produced = exact_records.get(result_key)
            if produced is None:
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.CANONICAL_RESULT_UNRESOLVED",
                        scenario_id,
                        (
                            f"{receipt.logical_identity}: exact "
                            "canonical Event result does not resolve"
                        ),
                    )
                )
                continue

            creation_source = produced.value.get(
                "creation_source"
            )
            source_profile = batch.value.get(
                "source_profile"
            )
            if (
                not isinstance(creation_source, dict)
                or creation_source.get("type") != "import"
                or not isinstance(source_profile, dict)
                or creation_source.get("source_label")
                != source_profile.get("display_label")
                or creation_source.get("external_reference")
                != source.value.get("source_record_key")
            ):
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.CANONICAL_PROVENANCE_MISMATCH",
                        scenario_id,
                        (
                            f"{produced.logical_identity}: import "
                            "creation provenance does not align"
                        ),
                    )
                )

            if review.value.get("disposition") == "accepted":
                for binding in proposal.value.get(
                    "field_bindings",
                    [],
                ):
                    if not isinstance(binding, dict):
                        continue
                    target_path = binding.get("target_path")
                    source_field_key = binding.get(
                        "source_field_key"
                    )
                    value_source = binding.get("value_source")
                    if (
                        not isinstance(target_path, str)
                        or not isinstance(source_field_key, str)
                    ):
                        continue

                    if value_source == "source_value":
                        expected_value = source_values.get(
                            source_field_key
                        )
                    elif value_source == "transformed_candidate":
                        expected_value = binding.get(
                            "transformed_candidate"
                        )
                    else:
                        continue

                    try:
                        actual_value = _json_pointer_get(
                            produced.value,
                            target_path,
                        )
                    except (KeyError, ValueError):
                        findings.append(
                            GraphFinding(
                                "G22.IMPORT.TARGET_PATH_UNRESOLVED",
                                scenario_id,
                                (
                                    f"{proposal.logical_identity}: "
                                    "canonical target path does not resolve"
                                ),
                            )
                        )
                    else:
                        if actual_value != expected_value:
                            findings.append(
                                GraphFinding(
                                    "G22.IMPORT.ACCEPTED_VALUE_MISMATCH",
                                    scenario_id,
                                    (
                                        f"{produced.logical_identity}: "
                                        "accepted import value differs "
                                        "from canonical value"
                                    ),
                                )
                            )

            if (
                isinstance(
                    receipt.value.get("materialized_at"),
                    str,
                )
                and isinstance(
                    produced.value.get("created_at"),
                    str,
                )
                and receipt.value["materialized_at"]
                < produced.value["created_at"]
            ):
                findings.append(
                    GraphFinding(
                        "G22.IMPORT.RECEIPT_BEFORE_CANONICAL_ACCEPTANCE",
                        scenario_id,
                        (
                            f"{receipt.logical_identity}: receipt "
                            "predates canonical Event creation"
                        ),
                    )
                )

    # A later snapshot explicitly declared as changed-source/same-mapping may
    # omit the earlier source key without deleting or mutating the prior Event.
    for later in import_batches.values():
        comparison = later.value.get(
            "comparison_to_previous"
        )
        if (
            not isinstance(comparison, dict)
            or comparison.get("relationship")
            != "changed_source_same_mapping"
        ):
            continue
        prior_id = comparison.get(
            "previous_import_batch_id"
        )
        prior_sources = [
            source
            for source in import_sources.values()
            if source.value.get("import_batch_id") == prior_id
        ]
        later_sources = [
            source
            for source in import_sources.values()
            if source.value.get("import_batch_id")
            == later.value.get("import_batch_id")
        ]
        prior_keys = {
            source.value.get("source_record_key")
            for source in prior_sources
        }
        later_keys = {
            source.value.get("source_record_key")
            for source in later_sources
        }
        missing_keys = prior_keys - later_keys
        if missing_keys:
            for receipt in [
                record
                for record in records
                if record.contract == "import_materialization"
            ]:
                for result in receipt.value.get(
                    "canonical_results",
                    [],
                ):
                    target = (
                        result.get("target")
                        if isinstance(result, dict)
                        else None
                    )
                    work_ref = (
                        target.get("work_ref")
                        if isinstance(target, dict)
                        and target.get("kind") == "work"
                        else None
                    )
                    if not isinstance(work_ref, dict):
                        continue
                    result_key = (
                        str(work_ref.get("class_id")),
                        str(work_ref.get("work_id")),
                        str(work_ref.get("work_kind")),
                        str(work_ref.get("work_id")),
                        str(work_ref.get("contract_version")),
                    )
                    produced = exact_records.get(result_key)
                    if (
                        produced is not None
                        and produced.value.get("status")
                        != "active"
                    ):
                        findings.append(
                            GraphFinding(
                                "G22.IMPORT.LATER_ABSENCE_MUTATED_CANONICAL",
                                scenario_id,
                                (
                                    f"{produced.logical_identity}: "
                                    "later source absence must not "
                                    "deactivate prior canonical Event"
                                ),
                            )
                        )

    # Correction/disagreement exact-reference checks.
    for record in records:
        owner = record.descriptor.get("owner")
        if not isinstance(owner, dict):
            continue
        class_id = owner.get("class_id")
        work_id = owner.get("work_id")
        if not isinstance(class_id, str) or not isinstance(work_id, str):
            continue

        if record.contract == "statement_of_disagreement":
            target = record.value.get("target")
            if (
                isinstance(target, dict)
                and target.get("kind") == "local_record"
            ):
                record_ref = target.get("record_ref")
                if isinstance(record_ref, dict):
                    key = _local_record_ref_key(
                        class_id=class_id,
                        work_id=work_id,
                        record_ref=record_ref,
                    )
                    if key is None or key not in exact_records:
                        findings.append(
                            GraphFinding(
                                (
                                    "G22.CORRECTION."
                                    "DISAGREEMENT_TARGET_UNRESOLVED"
                                ),
                                scenario_id,
                                (
                                    f"{record.logical_identity}: exact "
                                    "disagreement target does not resolve"
                                ),
                            )
                        )

            source = record.value.get("source")
            if (
                isinstance(source, dict)
                and source.get("kind") == "roster_student"
                and not _roster_subject_resolves(source, rosters)
            ):
                findings.append(
                    GraphFinding(
                        (
                            "G22.IDENTITY."
                            "DISAGREEMENT_SOURCE_UNRESOLVED"
                        ),
                        scenario_id,
                        (
                            f"{record.logical_identity}: exact roster "
                            "disagreement source does not resolve"
                        ),
                    )
                )

        if record.contract == "account":
            supersedes = record.value.get("supersedes", [])
            if not isinstance(supersedes, list):
                continue

            for entry in supersedes:
                if not isinstance(entry, dict):
                    continue
                work_record_ref = entry.get("work_record_ref")
                if not isinstance(work_record_ref, dict):
                    continue

                if not _work_ref_agrees_with_owner(
                    record,
                    work_record_ref,
                ):
                    findings.append(
                        GraphFinding(
                            (
                                "G22.CORRECTION."
                                "PREDECESSOR_WRONG_WORK"
                            ),
                            scenario_id,
                            (
                                f"{record.logical_identity}: Account "
                                "predecessor is outside owning work"
                            ),
                        )
                    )
                    continue

                predecessor_key = _exact_portia_ref_key(
                    work_record_ref
                )
                predecessor = (
                    exact_records.get(predecessor_key)
                    if predecessor_key is not None
                    else None
                )

                if predecessor is None:
                    findings.append(
                        GraphFinding(
                            (
                                "G22.CORRECTION."
                                "PREDECESSOR_UNRESOLVED"
                            ),
                            scenario_id,
                            (
                                f"{record.logical_identity}: Account "
                                "predecessor does not resolve exactly"
                            ),
                        )
                    )
                    continue

                if (
                    predecessor.logical_identity
                    == record.logical_identity
                ):
                    findings.append(
                        GraphFinding(
                            "G22.CORRECTION.SELF_SUPERSESSION",
                            scenario_id,
                            (
                                f"{record.logical_identity}: Account "
                                "cannot supersede itself"
                            ),
                        )
                    )

                if predecessor.value.get("status") != "superseded":
                    findings.append(
                        GraphFinding(
                            (
                                "G22.CORRECTION."
                                "PREDECESSOR_STATUS"
                            ),
                            scenario_id,
                            (
                                f"{record.logical_identity}: replaced "
                                "Account predecessor must be superseded"
                            ),
                        )
                    )


    # Material replacement topology must remain acyclic.  The focused
    # graph-invalid corpus currently exercises this with Account@2, whose
    # forward supersedes links are exact work-record references.
    account_edges: dict[
        tuple[str, str, str, str, str],
        set[tuple[str, str, str, str, str]],
    ] = {}
    for record in records:
        if record.contract != "account":
            continue
        source_key = _record_lookup_key(record)
        if source_key is None:
            continue
        for entry in record.value.get("supersedes", []):
            if not isinstance(entry, dict):
                continue
            ref = entry.get("work_record_ref")
            if not isinstance(ref, dict):
                continue
            target_key = _exact_portia_ref_key(ref)
            if (
                target_key is not None
                and target_key in exact_records
                and exact_records[target_key].contract == "account"
            ):
                account_edges.setdefault(source_key, set()).add(
                    target_key
                )

    visited: set[tuple[str, str, str, str, str]] = set()
    active_stack: set[
        tuple[str, str, str, str, str]
    ] = set()

    def account_cycle_from(
        node: tuple[str, str, str, str, str],
    ) -> bool:
        if node in active_stack:
            return True
        if node in visited:
            return False
        active_stack.add(node)
        for target in account_edges.get(node, set()):
            if account_cycle_from(target):
                return True
        active_stack.remove(node)
        visited.add(node)
        return False

    if any(
        account_cycle_from(node)
        for node in sorted(account_edges)
        if node not in visited
    ):
        findings.append(
            GraphFinding(
                "G22.CORRECTION.SUPERSESSION_CYCLE",
                scenario_id,
                "material Account supersession graph contains a cycle",
            )
        )

    # Required Portia-record dependencies must resolve under the exact
    # work scope named by the dependency reference.  A same-looking record
    # in another work cannot satisfy the dependency.
    for record in records:
        if (
            record.contract != "dependency"
            or record.value.get("strength") != "required"
        ):
            continue
        dependency = record.value.get("dependency")
        if (
            not isinstance(dependency, dict)
            or dependency.get("kind") != "portia_record"
        ):
            continue
        work_record_ref = dependency.get("work_record_ref")
        key = (
            _exact_portia_ref_key(work_record_ref)
            if isinstance(work_record_ref, dict)
            else None
        )
        if key is None or key not in exact_records:
            findings.append(
                GraphFinding(
                    (
                        "G22.DEPENDENCY."
                        "REQUIRED_TARGET_UNRESOLVED"
                    ),
                    scenario_id,
                    (
                        f"{record.logical_identity}: required exact "
                        "Portia-record dependency does not resolve in "
                        "the declared work"
                    ),
                )
            )

    # Deliberate-export privacy/provenance reconciliation.
    byte_fixtures = _byte_fixtures_by_workspace_path(
        scenario_path, scenario
    )
    for export_record in [
        record for record in records if record.contract == "deliberate_export"
    ]:
        value = export_record.value
        scope = value.get("export_scope")
        if isinstance(scope, dict) and scope.get("scope") == "work":
            work = scope.get("work_ref")
            key = _exact_work_ref_key(work) if isinstance(work, dict) else None
            if key is None or key not in exact_records:
                findings.append(
                    GraphFinding(
                        "G22.PRIVACY.EXPORT_SCOPE_UNRESOLVED",
                        scenario_id,
                        f"{export_record.logical_identity}: exact work scope does not resolve",
                    )
                )

        focal = value.get("focal_subject_ref")
        if isinstance(focal, dict):
            key = _exact_portia_ref_key(focal)
            if key is None or key not in exact_records:
                findings.append(
                    GraphFinding(
                        "G22.PRIVACY.FOCAL_SUBJECT_UNRESOLVED",
                        scenario_id,
                        f"{export_record.logical_identity}: focal subject does not resolve exactly",
                    )
                )

        inventory = value.get("source_inventory")
        if isinstance(inventory, dict):
            entries = inventory.get("entries", [])
            if isinstance(entries, list):
                expected_order = sorted(
                    entries,
                    key=lambda item: (
                        str(item.get("source_role")),
                        str(item.get("source_kind")),
                        _export_source_identity(item),
                    ),
                )
                if entries != expected_order:
                    findings.append(
                        GraphFinding(
                            "G22.PRIVACY.EXPORT_INVENTORY_ORDER",
                            scenario_id,
                            f"{export_record.logical_identity}: source inventory is not deterministically sorted",
                        )
                    )
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    source_kind = entry.get("source_kind")
                    if source_kind == "portia_work":
                        ref = entry.get("work_ref")
                        key = _exact_work_ref_key(ref) if isinstance(ref, dict) else None
                    elif source_kind == "portia_record":
                        ref = entry.get("work_record_ref")
                        key = _exact_portia_ref_key(ref) if isinstance(ref, dict) else None
                    else:
                        key = None
                    source = exact_records.get(key) if key is not None else None
                    if source_kind in {"portia_work", "portia_record"}:
                        if source is None:
                            findings.append(
                                GraphFinding(
                                    "G22.PRIVACY.EXPORT_SOURCE_UNRESOLVED",
                                    scenario_id,
                                    f"{export_record.logical_identity}: exact contributing source does not resolve",
                                )
                            )
                            continue
                        payload = source.path.read_bytes()
                        if (
                            entry.get("representation_digest")
                            != hashlib.sha256(payload).hexdigest()
                            or entry.get("byte_length") != len(payload)
                        ):
                            findings.append(
                                GraphFinding(
                                    "G22.PRIVACY.EXPORT_SOURCE_FINGERPRINT",
                                    scenario_id,
                                    f"{export_record.logical_identity}: contributing source digest/length is not truthful",
                                )
                            )
            if inventory.get("inventory_digest") != _canonical_export_inventory_digest(inventory):
                findings.append(
                    GraphFinding(
                        "G22.PRIVACY.EXPORT_INVENTORY_DIGEST",
                        scenario_id,
                        f"{export_record.logical_identity}: source inventory digest does not recompute",
                    )
                )

        output = value.get("output")
        if isinstance(output, dict):
            workspace_path = output.get("workspace_relative_path")
            fixture = (
                byte_fixtures.get(workspace_path)
                if isinstance(workspace_path, str)
                else None
            )
            if fixture is None:
                findings.append(
                    GraphFinding(
                        "G22.PRIVACY.EXPORT_OUTPUT_UNRESOLVED",
                        scenario_id,
                        f"{export_record.logical_identity}: exported artifact bytes do not resolve in fixture map",
                    )
                )
            else:
                _, payload = fixture
                if (
                    output.get("sha256_digest")
                    != hashlib.sha256(payload).hexdigest()
                    or output.get("byte_length") != len(payload)
                ):
                    findings.append(
                        GraphFinding(
                            "G22.PRIVACY.EXPORT_OUTPUT_FINGERPRINT",
                            scenario_id,
                            f"{export_record.logical_identity}: output digest/length is not truthful",
                        )
                    )

    # Append-only lifecycle predecessor-chain reconciliation.
    transition_records = [
        record
        for record in records
        if record.contract == "lifecycle_transition"
    ]
    transition_by_id = {
        str(record.value["transition_id"]): record
        for record in transition_records
        if isinstance(record.value.get("transition_id"), str)
    }

    for transition in transition_records:
        owner = transition.descriptor.get("owner")
        target = transition.value.get("target")
        if not isinstance(owner, dict) or not isinstance(target, dict):
            continue

        class_id = owner.get("class_id")
        work_id = owner.get("work_id")
        record_ref = target.get("record_ref")
        if (
            not isinstance(class_id, str)
            or not isinstance(work_id, str)
            or not isinstance(record_ref, dict)
        ):
            continue

        target_key = _local_record_ref_key(
            class_id=class_id,
            work_id=work_id,
            record_ref=record_ref,
        )
        if target_key is None or target_key not in exact_records:
            findings.append(
                GraphFinding(
                    "G22.LIFECYCLE.TARGET_UNRESOLVED",
                    scenario_id,
                    (
                        f"{transition.logical_identity}: lifecycle "
                        "target does not resolve exactly"
                    ),
                )
            )

        previous = transition.value.get("previous_transition")
        if isinstance(previous, dict):
            previous_id = previous.get("record_id")
            predecessor = (
                transition_by_id.get(previous_id)
                if isinstance(previous_id, str)
                else None
            )

            if predecessor is None:
                findings.append(
                    GraphFinding(
                        "G22.LIFECYCLE.PREVIOUS_UNRESOLVED",
                        scenario_id,
                        (
                            f"{transition.logical_identity}: previous "
                            "transition does not resolve"
                        ),
                    )
                )
            else:
                predecessor_target = predecessor.value.get("target")
                predecessor_ref = (
                    predecessor_target.get("record_ref")
                    if isinstance(predecessor_target, dict)
                    else None
                )

                if predecessor_ref != record_ref:
                    findings.append(
                        GraphFinding(
                            (
                                "G22.LIFECYCLE."
                                "PREVIOUS_TARGET_MISMATCH"
                            ),
                            scenario_id,
                            (
                                f"{transition.logical_identity}: previous "
                                "transition targets a different record"
                            ),
                        )
                    )

                if (
                    predecessor.value.get("to_status")
                    != transition.value.get("from_status")
                ):
                    findings.append(
                        GraphFinding(
                            (
                                "G22.LIFECYCLE."
                                "STATUS_CHAIN_MISMATCH"
                            ),
                            scenario_id,
                            (
                                f"{transition.logical_identity}: previous "
                                "to_status differs from current from_status"
                            ),
                        )
                    )

    heads = lifecycle_heads(records)
    for target_key, head in heads.items():
        target_record = exact_records.get(target_key)
        if target_record is None:
            continue
        if (
            target_record.value.get("status")
            != head.value.get("to_status")
        ):
            findings.append(
                GraphFinding(
                    "G22.LIFECYCLE.FINAL_STATUS_MISMATCH",
                    scenario_id,
                    (
                        f"{head.logical_identity}: selected lifecycle "
                        "head does not reconcile target final status"
                    ),
                )
            )

    return tuple(sorted(findings))


def build_teacher_current_summary(
    scenario_path: Path,
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    records = load_scenario_records(scenario_path, scenario)
    active = _active_records_by_type(records)

    events = [
        record
        for record in records
        if (
            record.contract == "event"
            and record.value.get("status") == "active"
        )
    ]
    if len(events) != 1:
        raise ValueError(
            "teacher-current Slice 1 summary requires exactly one active Event"
        )

    work_id = events[0].value.get("work_id")
    if not isinstance(work_id, str):
        raise ValueError("active Event has no string work_id")

    def ids(record_type: str, key: str) -> list[str]:
        values: list[str] = []
        for record in active.get(record_type, []):
            value = record.value.get(key)
            if isinstance(value, str):
                values.append(value)
        return sorted(values)

    return {
        "work_id": work_id,
        "participant_ids": ids("event_participant", "participant_id"),
        "role_ids": ids("event_participant_role", "role_id"),
        "observation_ids": ids("observation", "observation_id"),
    }
