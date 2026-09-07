"""Issue #46 runtime acceptance against representative Issue #22 scenarios."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from portia.identity.roster import ResolvedRosterStudent
from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.validation import KnownValidationContext
from portia.workflows import (
    FidelityWorkflowService,
    FollowUpWorkflowService,
    ImplementationWorkflowService,
    OutcomeWorkflowService,
    ReentryWorkflowService,
    RepairWorkflowService,
    SupportProcessWorkflowService,
)
from portia.workflows.context import (
    AuthoritativeWorkflowContext,
    roster_references,
)

SCENARIO_ROOT = Path("tests/fixtures/issue_22/positive")


class _RepresentativeRosters:
    """Resolve synthetic fixture roster refs without introducing name matching."""

    def resolve_reference(self, reference: object) -> ResolvedRosterStudent:
        del reference
        return cast(ResolvedRosterStudent, object())


class _RepresentativeActors:
    def load_actor(
        self,
        reference: object,
        *,
        require_current_use: bool = False,
    ) -> StoredRecord:
        del reference, require_current_use
        return cast(StoredRecord, object())


class _RepresentativeContext:
    """Known closed roster context for the already-validated synthetic corpus."""

    def __init__(self) -> None:
        self.rosters = _RepresentativeRosters()
        self.actors = _RepresentativeActors()

    def assemble(
        self,
        records: Sequence[PortiaRecord],
        *,
        require_actor_current_use: bool = False,
    ) -> AuthoritativeWorkflowContext:
        del require_actor_current_use
        references = roster_references(records)
        return AuthoritativeWorkflowContext(
            validation=KnownValidationContext.from_values(
                roster_students=references,
                core_works=None,
            ),
            roster_students=(),
            actors=(),
        )


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _scenario(name: str) -> tuple[Path, dict[str, object]]:
    root = SCENARIO_ROOT / name
    return root, _json(root / "scenario.json")


def _entries(scenario: Mapping[str, object]) -> tuple[dict[str, object], ...]:
    records = scenario["records"]
    assert isinstance(records, list)
    assert all(isinstance(item, dict) for item in records)
    return tuple(cast(dict[str, object], item) for item in records)


def _entry(
    scenario: Mapping[str, object],
    *,
    filename: str | None = None,
    contract: str | None = None,
) -> dict[str, object]:
    matches = tuple(
        item
        for item in _entries(scenario)
        if (filename is None or item["fixture_path"] == filename)
        and (contract is None or item["contract"] == contract)
    )
    assert len(matches) == 1
    return matches[0]


def _contract_entries(
    scenario: Mapping[str, object], contract: str
) -> tuple[dict[str, object], ...]:
    return tuple(item for item in _entries(scenario) if item["contract"] == contract)


def _owner_work(entry: Mapping[str, object]) -> ExactPortiaWorkRef:
    owner = entry["owner"]
    assert isinstance(owner, Mapping)
    work_kind = owner["work_kind"]
    assert work_kind in {"event", "support_process"}
    return ExactPortiaWorkRef(
        class_id=str(owner["class_id"]),
        work_id=str(owner["work_id"]),
        work_kind=str(work_kind),
        contract_version="2" if work_kind == "event" else "1",
    )


def _record_ref(
    entry: Mapping[str, object], record: PortiaRecord
) -> ExactPortiaWorkRecordRef:
    logical_id = record.logical_id
    assert logical_id is not None
    return ExactPortiaWorkRecordRef(
        work_ref=_owner_work(entry),
        record_ref=ExactLocalRecordRef(
            record_kind=str(entry["contract"]),
            record_id=logical_id,
            contract_version=str(entry["version"]),
        ),
    )


def _seed_scenario(
    tmp_path: Path,
    name: str,
) -> tuple[
    PortiaRepository,
    _RepresentativeContext,
    dict[str, object],
    dict[str, PortiaRecord],
]:
    fixture_root, scenario = _scenario(name)
    repository = PortiaRepository(tmp_path)
    records: dict[str, PortiaRecord] = {}
    for entry in _entries(scenario):
        if entry.get("authority") != "portia":
            continue
        filename = str(entry["fixture_path"])
        wire = _json(fixture_root / filename)
        contract = str(entry["contract"])
        version = str(entry["version"])
        record = parse_portia_record(contract, version, wire)
        work = _owner_work(entry)
        if wire.get("record_type") == "portia_work":
            repository.create_work(work, record)
        else:
            repository.create_work_record(work, record)
        records[filename] = record
    return repository, _RepresentativeContext(), scenario, records


def _service_kwargs(
    repository: PortiaRepository,
    context: _RepresentativeContext,
) -> dict[str, object]:
    return {
        "repository": repository,
        "context_assembler": context,
    }


def _work_refs(value: object) -> tuple[dict[str, object], ...]:
    found: list[dict[str, object]] = []
    if isinstance(value, Mapping):
        required = {
            "module_id",
            "class_id",
            "work_id",
            "work_kind",
            "contract_version",
        }
        if required.issubset(value):
            found.append(dict(value))
        for child in value.values():
            found.extend(_work_refs(child))
    elif isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        for child in value:
            found.extend(_work_refs(child))
    return tuple(found)


def _all_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                found.add(key)
            found.update(_all_keys(child))
    elif isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        for child in value:
            found.update(_all_keys(child))
    return found


def test_p22_08_runs_real_support_implementation_fidelity_followup_outcome(
    tmp_path: Path,
) -> None:
    repository, context, scenario, records = _seed_scenario(
        tmp_path,
        "p22_08_support_positive_outcome",
    )
    kwargs = _service_kwargs(repository, context)
    support_entry = _entry(scenario, filename="support-process.json")
    work = _owner_work(support_entry)
    root_before = repository.load_work(work).record.to_dict()

    support_service = SupportProcessWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    support_service.require_current_use(work)
    implementation_service = ImplementationWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    for entry in _contract_entries(scenario, "implementation"):
        record = records[str(entry["fixture_path"])]
        implementation_service.require_current_use(_record_ref(entry, record))

    fidelity_entry = _entry(scenario, contract="fidelity")
    fidelity_service = FidelityWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    fidelity_service.require_current_use(
        _record_ref(fidelity_entry, records[str(fidelity_entry["fixture_path"])])
    )
    follow_up_entry = _entry(scenario, contract="follow_up")
    follow_up_service = FollowUpWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    follow_up_service.require_current_use(
        _record_ref(follow_up_entry, records[str(follow_up_entry["fixture_path"])])
    )
    outcome_entry = _entry(scenario, contract="outcome")
    outcome_service = OutcomeWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    outcome_service.require_current_use(
        _record_ref(outcome_entry, records[str(outcome_entry["fixture_path"])])
    )

    root_after = repository.load_work(work).record.to_dict()
    assert root_after == root_before
    assert root_after["workflow_state"] == "active"


def test_p22_09_preserves_inconclusive_and_later_adverse_outcomes(
    tmp_path: Path,
) -> None:
    repository, context, scenario, records = _seed_scenario(
        tmp_path,
        "p22_09_inconclusive_adverse_outcomes",
    )
    kwargs = _service_kwargs(repository, context)
    work = _owner_work(_entry(scenario, filename="support-process.json"))
    root_before = repository.load_work(work).record.to_dict()
    support_service = SupportProcessWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    support_service.require_current_use(work)

    service = OutcomeWorkflowService(tmp_path, **kwargs)  # type: ignore[arg-type]
    inconclusive_entry = _entry(scenario, filename="outcome-inconclusive.json")
    adverse_entry = _entry(scenario, filename="outcome-adverse.json")
    inconclusive = service.require_current_use(
        _record_ref(
            inconclusive_entry,
            records[str(inconclusive_entry["fixture_path"])],
        )
    ).record
    adverse = service.require_current_use(
        _record_ref(adverse_entry, records[str(adverse_entry["fixture_path"])])
    ).record

    assert inconclusive.logical_id != adverse.logical_id
    assert inconclusive.field("result") == "unable_to_determine"
    assert inconclusive.field("limitations") == (
        {"kind": "insufficient_observation_opportunity"},
    )
    adverse_scope = adverse.field("scope")
    assert isinstance(adverse_scope, Mapping)
    assert adverse_scope["kind"] == "unintended_or_adverse_effect_review"
    assert adverse_scope.get("coverage") is not None
    assert inconclusive.field("supersedes") is None
    assert adverse.field("supersedes") is None
    assert repository.load_work(work).record.to_dict() == root_before


def test_p22_10_preserves_reentry_repair_and_followup_nonfabrication(
    tmp_path: Path,
) -> None:
    repository, context, scenario, records = _seed_scenario(
        tmp_path,
        "p22_10_reentry_repair_without_overclaiming",
    )
    kwargs = _service_kwargs(repository, context)
    reentry_entry = _entry(scenario, contract="reentry")
    repair_entry = _entry(scenario, contract="repair")
    follow_up_entry = _entry(scenario, contract="follow_up")

    reentry_ref = _record_ref(reentry_entry, records["reentry.json"])
    repair_ref = _record_ref(repair_entry, records["repair.json"])
    follow_up_ref = _record_ref(follow_up_entry, records["follow-up.json"])
    before = {
        "reentry": repository.load_work_record(
            reentry_ref.work_ref,
            "reentry",
            "1",
            reentry_ref.record_ref.record_id,
        ).record.to_dict(),
        "repair": repository.load_work_record(
            repair_ref.work_ref,
            "repair",
            "1",
            repair_ref.record_ref.record_id,
        ).record.to_dict(),
        "follow_up": repository.load_work_record(
            follow_up_ref.work_ref,
            "follow_up",
            "1",
            follow_up_ref.record_ref.record_id,
        ).record.to_dict(),
    }

    reentry_service = ReentryWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    reentry = reentry_service.require_current_use(reentry_ref).record
    repair_service = RepairWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    repair = repair_service.require_current_use(repair_ref).record
    follow_up_service = FollowUpWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    follow_up = follow_up_service.require_current_use(follow_up_ref).record

    assert reentry.field("workflow_state") == "completed"
    assert repair.field("workflow_state") == "completed"
    assert follow_up.field("workflow_state") == "completed"
    participant_states = {
        participant["participation_state"]
        for participant in repair.to_dict()["participants"]
    }
    assert participant_states == {"participated", "declined"}
    assert _contract_entries(scenario, "outcome") == ()
    assert _all_keys(reentry.to_dict()).isdisjoint(
        {"clearance", "cleared", "readiness_score", "rehabilitated"}
    )
    assert _all_keys(repair.to_dict()).isdisjoint(
        {
            "admission_required",
            "apology_required",
            "remorse_score",
            "forgiveness",
            "relationship_restored",
        }
    )
    assert repository.load_work_record(
        reentry_ref.work_ref, "reentry", "1", reentry_ref.record_ref.record_id
    ).record.to_dict() == before["reentry"]
    assert repository.load_work_record(
        repair_ref.work_ref, "repair", "1", repair_ref.record_ref.record_id
    ).record.to_dict() == before["repair"]
    assert repository.load_work_record(
        follow_up_ref.work_ref,
        "follow_up",
        "1",
        follow_up_ref.record_ref.record_id,
    ).record.to_dict() == before["follow_up"]


def test_p22_11_preserves_exact_cross_year_downstream_history(
    tmp_path: Path,
) -> None:
    repository, context, scenario, records = _seed_scenario(
        tmp_path,
        "p22_11_cross_year_support_continuation",
    )
    kwargs = _service_kwargs(repository, context)
    root_2026_entry = _entry(scenario, filename="process-2026.json")
    root_2027_entry = _entry(scenario, filename="process-2027.json")
    work_2026 = _owner_work(root_2026_entry)
    work_2027 = _owner_work(root_2027_entry)
    assert work_2026 != work_2027
    assert work_2026.class_id == "eng10_p2_2026"
    assert work_2027.class_id == "eng11_p3_2027"

    root_service = SupportProcessWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    root_service.require_current_use(work_2026)
    root_service.require_current_use(work_2027)

    implementation_service = ImplementationWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    for entry in _contract_entries(scenario, "implementation"):
        record = records[str(entry["fixture_path"])]
        implementation_service.require_current_use(_record_ref(entry, record))

    outcome_service = OutcomeWorkflowService(
        tmp_path, **kwargs  # type: ignore[arg-type]
    )
    outcome_2026_entry = _entry(scenario, filename="outcome-2026.json")
    outcome_2027_entry = _entry(scenario, filename="outcome-2027.json")
    outcome_2026 = outcome_service.require_current_use(
        _record_ref(outcome_2026_entry, records["outcome-2026.json"])
    ).record
    outcome_2027 = outcome_service.require_current_use(
        _record_ref(outcome_2027_entry, records["outcome-2027.json"])
    ).record

    refs_2026 = _work_refs(outcome_2026.to_dict())
    refs_2027 = _work_refs(outcome_2027.to_dict())
    assert refs_2026
    assert refs_2027
    assert {ref["class_id"] for ref in refs_2026} == {"eng10_p2_2026"}
    assert {ref["class_id"] for ref in refs_2027} == {"eng11_p3_2027"}
    root_2027 = records["process-2027.json"].to_dict()
    assert root_2027.get("supersedes") is None
    continuation_refs = _work_refs(root_2027.get("continues_from"))
    assert any(
        ref["class_id"] == "eng10_p2_2026"
        and ref["work_id"] == "sup_p22_crossyear_2026"
        for ref in continuation_refs
    )


def test_issue46_representatives_do_not_encode_forbidden_automatic_state() -> None:
    scenarios = (
        "p22_08_support_positive_outcome",
        "p22_09_inconclusive_adverse_outcomes",
        "p22_10_reentry_repair_without_overclaiming",
        "p22_11_cross_year_support_continuation",
    )
    forbidden = {
        "effectiveness_score",
        "causal_effect",
        "readiness_score",
        "compliance_score",
        "remorse_score",
        "forgiveness",
        "relationship_restored",
        "recurrence_risk_score",
    }
    for scenario_name in scenarios:
        fixture_root, scenario = _scenario(scenario_name)
        for entry in _entries(scenario):
            if entry.get("authority") != "portia":
                continue
            wire = _json(fixture_root / str(entry["fixture_path"]))
            assert _all_keys(wire).isdisjoint(forbidden)
