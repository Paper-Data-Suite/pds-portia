"""Bounded expert inspection and exact administration routing for Portia."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from portia.identity.actors import ActorDirectoryService
from portia.menu.context import MenuSessionContext
from portia.menu.correction import launch_correct_retract_menu
from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    navigation_hint_with_help,
    parse_menu_navigation,
)
from portia.menu.prompts import CancelMenuAction, prompt_text, select_one
from portia.menu.selectors import ClassOption, class_options
from portia.menu.ui import (
    clear_screen,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models.references import ExactActorRef, ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    IntegrityWorkflowService,
    RecoveryWorkflowService,
    supported_amendment_contracts,
    supported_ownership_correction_families,
)

RecordSpec = tuple[str, frozenset[str]]

_EVENT_RECORDS: Final[tuple[RecordSpec, ...]] = (
    ("event_participant", frozenset({"3"})),
    ("event_participant_role", frozenset({"3"})),
    ("work_relationship", frozenset({"2"})),
)
_EVIDENCE_JUDGMENT_RECORDS: Final[tuple[RecordSpec, ...]] = (
    ("account", frozenset({"1", "2"})),
    ("observation", frozenset({"1", "2"})),
    ("review", frozenset({"1"})),
    ("classification", frozenset({"1"})),
    ("hypothesis", frozenset({"1"})),
    ("determination", frozenset({"1"})),
)
_RESPONSE_RECORDS: Final[tuple[RecordSpec, ...]] = (
    ("response", frozenset({"1"})),
    ("communication", frozenset({"1"})),
)
_SUPPORT_RECORDS: Final[tuple[RecordSpec, ...]] = (
    ("support_process_participant", frozenset({"1"})),
    ("support_need", frozenset({"1"})),
    ("support_goal", frozenset({"1"})),
    ("support", frozenset({"1"})),
    ("intervention", frozenset({"1"})),
    ("implementation", frozenset({"1"})),
    ("fidelity", frozenset({"1"})),
    ("follow_up", frozenset({"1"})),
    ("outcome", frozenset({"1"})),
    ("reentry", frozenset({"1"})),
    ("repair", frozenset({"1"})),
)
_HISTORY_RECORDS: Final[tuple[RecordSpec, ...]] = (
    ("lifecycle_transition", frozenset({"1"})),
    ("amendment", frozenset({"1"})),
    ("statement_of_disagreement", frozenset({"1"})),
    ("dependency", frozenset({"1"})),
)


@dataclass(frozen=True, slots=True)
class AdvancedWorkOption:
    work: ExactPortiaWorkRef
    label: str


@dataclass(frozen=True, slots=True)
class TechnicalRecord:
    stored: StoredRecord
    label: str


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _bounded(value: object, *, limit: int = 96) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _show(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _remember_work(state: MenuSessionContext, work: ExactPortiaWorkRef) -> None:
    if work.work_kind == "event":
        state.remember_work(
            class_id=work.class_id,
            work_kind="event",
            work_id=work.work_id,
        )
    elif work.work_kind == "support_process":
        state.remember_work(
            class_id=work.class_id,
            work_kind="support_process",
            work_id=work.work_id,
        )
    else:
        raise ValueError("advanced work scope must be Event or Support Process")


def _work_options(root: Path, class_id: str) -> tuple[AdvancedWorkOption, ...]:
    repository = PortiaRepository(root)
    options: list[AdvancedWorkOption] = []
    for kind, version, label in (
        ("event", "2", "Event"),
        ("support_process", "1", "Support Process"),
    ):
        for stored in repository.list_works(
            class_id,
            work_kind=kind,
            version=version,
        ):
            work_id = stored.record.work_id
            if work_id is None:
                raise PortiaCorruptionError(
                    "Portia work root has incomplete exact identity"
                )
            work = ExactPortiaWorkRef(
                class_id=class_id,
                work_id=work_id,
                work_kind=kind,
                contract_version=version,
            )
            status = stored.record.status or "unknown"
            options.append(
                AdvancedWorkOption(
                    work,
                    f"{label} — {_humanize(status)} — exact {work_id}",
                )
            )
    return tuple(options)


def _choose_work(
    state: MenuSessionContext,
    root: Path,
    *,
    title: str,
) -> ExactPortiaWorkRef:
    classes = class_options(root)
    if not classes:
        raise ValueError(
            "No Core classes with both metadata and rosters are available."
        )
    owner: ClassOption = select_one(
        f"{title} — Class",
        classes,
        tuple(item.label for item in classes),
        help_text=(
            "Choose the exact Core class that owns the Portia work. "
            "Display names are never identity authority."
        ),
    )
    state.remember_class(owner.class_id)
    works = _work_options(root, owner.class_id)
    if not works:
        raise ValueError("No Event or Support Process work exists in that class.")
    selected = select_one(
        f"{title} — Work",
        works,
        tuple(item.label for item in works),
        help_text=(
            "The numbered choice retains the exact class/work/contract reference."
        ),
    )
    _remember_work(state, selected.work)
    return selected.work


def _records_for_specs(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    specs: tuple[RecordSpec, ...],
) -> tuple[TechnicalRecord, ...]:
    values: list[TechnicalRecord] = []
    for contract, versions in specs:
        stored_values = repository.list_work_records_mixed_versions(
            work,
            contract,
            supported_versions=versions,
        )
        for stored in stored_values:
            identifier = stored.record.logical_id or "identity unavailable"
            status = stored.record.status or "no lifecycle status"
            label = (
                f"{_humanize(contract)}@{stored.record.contract_version} — "
                f"{_humanize(status)} — exact {identifier}"
            )
            values.append(TechnicalRecord(stored, label))
    return tuple(values)


def _record_details(
    work: ExactPortiaWorkRef,
    stored: StoredRecord,
) -> tuple[str, ...]:
    record = stored.record
    return (
        f"Family: {record.contract}@{record.contract_version}",
        f"Exact record ID: {record.logical_id or 'not applicable'}",
        f"Exact class: {work.class_id}",
        f"Exact work: {work.work_kind}@{work.contract_version} / {work.work_id}",
        f"Canonical status: {record.status or 'not applicable'}",
        f"Fingerprint SHA-256: {stored.fingerprint.digest}",
        "Raw record JSON and filesystem paths are intentionally not displayed.",
    )


def _browse_record_group(
    state: MenuSessionContext,
    root: Path,
    *,
    title: str,
    specs: tuple[RecordSpec, ...],
) -> None:
    work = _choose_work(state, root, title=title)
    repository = PortiaRepository(root)
    records = _records_for_specs(repository, work, specs)
    if not records:
        _show(title, ("No records from this exact family group are present.",))
        return
    while True:
        try:
            selected = select_one(
                title,
                records,
                tuple(item.label for item in records),
                help_text=(
                    "This is an exact technical inventory. Selection is by canonical "
                    "record identity, not by free-text matching."
                ),
            )
        except CancelMenuAction:
            return
        _show(title, _record_details(work, selected.stored))


def _actor_lookup(root: Path) -> None:
    actor_id = prompt_text(
        "Advanced — Actor Directory",
        "Exact Actor ID",
        help_text=(
            "Enter the complete canonical actr_ identifier. "
            "Advanced mode does not provide a broad identity browser."
        ),
    )
    assert actor_id is not None
    version = prompt_text(
        "Advanced — Actor Directory",
        "Actor contract version",
        default="1",
        help_text="Exact Actor root contract version; ordinary current records use 1.",
    )
    assert version is not None
    resolution = ActorDirectoryService(root).resolve_actor(
        ExactActorRef(actor_id=actor_id, contract_version=version)
    )
    lines: tuple[str, ...]
    if resolution.stored is None:
        lines = (
            f"Exact Actor: {actor_id}",
            f"Contract: actor@{version}",
            "Disposition: exceptionally removed",
            "Removed payload is not reproduced.",
        )
    else:
        lines = (
            f"Exact Actor: {actor_id}",
            f"Contract: actor@{version}",
            f"Disposition: {resolution.disposition}",
            f"Canonical status: {resolution.stored.record.status or 'not applicable'}",
            f"Fingerprint SHA-256: {resolution.stored.fingerprint.digest}",
            "Contact Point values and raw Actor payload are not displayed here.",
        )
    _show("Advanced — Actor Directory", lines)


def _history_inventory(
    state: MenuSessionContext,
    root: Path,
) -> None:
    _browse_record_group(
        state,
        root,
        title="Advanced — Lifecycle / Amendment / Disagreement / Dependency",
        specs=_HISTORY_RECORDS,
    )


def _authority_registry(root: Path, state: MenuSessionContext) -> None:
    while True:
        clear_screen()
        print_menu_header("Advanced — Correction / Migration / Ownership")
        print("1. Open family-specific Correct / Retract")
        print("2. Show registered Amendment contracts")
        print("3. Show supported Ownership Correction families")
        print("4. Migration / Ownership authority boundary")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show(
                "Advanced — Correction / Migration / Ownership Help",
                (
                    "Expert correction still uses production family services.",
                    "No generic JSON editor, forced current pointer, or cross-work move is provided.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        elif raw == "1":
            launch_correct_retract_menu(state)
        elif raw == "2":
            values = tuple(
                f"- {contract}@{version}"
                for contract, version in supported_amendment_contracts()
            )
            _show(
                "Advanced — Amendment Registry",
                (
                    "Registered nonmaterial Amendment contracts:",
                    *(values or ("- None",)),
                ),
            )
        elif raw == "3":
            values = tuple(
                f"- {registration.contract}@{registration.contract_version}"
                for registration in supported_ownership_correction_families().values()
            )
            _show(
                "Advanced — Ownership Correction Registry",
                (
                    "Production Ownership Correction families:",
                    *(values or ("- None",)),
                    "Execution requires an exact predecessor, destination work, candidate, "
                    "incoming-reference review, and Dependency review.",
                ),
            )
        elif raw == "4":
            _show(
                "Advanced — Migration / Ownership Boundary",
                (
                    "Record migration and Ownership Correction remain production workflow services.",
                    "This menu does not synthesize successor records or accept arbitrary JSON.",
                    "Use the exact service with explicit candidate authoring and guarded expected state.",
                ),
            )
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def _quarantine_lines(root: Path) -> tuple[str, ...]:
    records = QuarantineGuard(root).active_records()
    if not records:
        return ("No active Quarantine records.",)
    lines: list[str] = []
    for record in records:
        data = record.to_dict()
        identifier = data.get("quarantine_id", "identity unavailable")
        reason = data.get("reason", "reason unavailable")
        target = data.get("target")
        target_kind = (
            target.get("kind")
            if isinstance(target, dict)
            else "target unavailable"
        )
        effects = data.get("effects")
        effect_text = (
            ", ".join(str(value) for value in effects)
            if isinstance(effects, list)
            else "effects unavailable"
        )
        lines.append(
            f"- {identifier}: {_humanize(str(reason))}; "
            f"target {_humanize(str(target_kind))}; effects {effect_text}"
        )
    return tuple(lines)


def _recovery_lines(root: Path) -> tuple[str, ...]:
    ids = OperationJournalStore(root).series_ids()
    if not ids:
        return ("No Operation Journal series.",)
    service = RecoveryWorkflowService(root)
    lines: list[str] = []
    for operation_id in ids:
        assessment = service.assess(operation_id)
        state = assessment.state or "no selected state"
        lines.append(
            f"- {operation_id}: state {_humanize(state)}; "
            f"recovery {_humanize(assessment.disposition)}; "
            f"findings {len(assessment.findings)}"
        )
    return tuple(lines)


def _integrity_lines(root: Path) -> tuple[str, ...]:
    operation_ids = OperationJournalStore(root).series_ids()
    if not operation_ids:
        return ("No operation-scoped Integrity projections.",)
    service = IntegrityWorkflowService(root)
    lines: list[str] = []
    for operation_id in operation_ids:
        scope = service.operation_scope(operation_id)
        if not service.has_current_finding_projection(scope):
            continue
        try:
            findings = service.current_findings(scope)
        except PortiaQuarantinedError:
            lines.append(
                f"- {operation_id}: current Integrity projection is Quarantine-blocked"
            )
            continue
        for finding in findings:
            data = finding.to_dict()
            key = data.get("finding_key", "finding key unavailable")
            code = data.get("code", "finding code unavailable")
            status = data.get("status", "status unavailable")
            lines.append(
                f"- {operation_id}: {key}; code {_humanize(str(code))}; "
                f"status {_humanize(str(status))}"
            )
    return tuple(lines) or ("No current Integrity findings.",)


def _technical_inspection(root: Path) -> None:
    while True:
        clear_screen()
        print_menu_header("Advanced — Integrity / Quarantine / Recovery")
        print("1. Active Quarantine inspection")
        print("2. Operation recovery assessment")
        print("3. Current Integrity finding inspection")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show(
                "Advanced — Technical Inspection Help",
                (
                    "These screens are read-only inspection.",
                    "Viewing does not acknowledge or suppress Integrity findings.",
                    "Viewing does not release Quarantine or resume/reconcile recovery.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        elif raw == "1":
            _show("Advanced — Active Quarantine", _quarantine_lines(root))
        elif raw == "2":
            _show("Advanced — Recovery Assessment", _recovery_lines(root))
        elif raw == "3":
            _show("Advanced — Integrity Findings", _integrity_lines(root))
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def _exceptional_certificate_lines(root: Path) -> tuple[str, ...]:
    repository = PortiaRepository(root)
    lines: list[str] = []
    for class_option in class_options(root):
        for stored in repository.list_exceptional_removals(class_option.class_id):
            identifier = stored.record.logical_id or "certificate identity unavailable"
            lines.append(
                f"- Portia work certificate {identifier} — class {class_option.class_id}"
            )
    actors = ActorDirectoryService(root)
    for stored in actors.list_exceptional_removals():
        identifier = stored.record.logical_id or "certificate identity unavailable"
        lines.append(f"- Actor Directory certificate {identifier}")
    return tuple(lines) or ("No Exceptional Removal certificates.",)


def _exceptional_operations(root: Path) -> None:
    _show(
        "Advanced — Exceptional Operations",
        (
            "Exceptional Removal is not ordinary correction or deletion.",
            "Production execution requires configured local authority, an external "
            "decision reference, complete reference/dependency review, Integrity "
            "clearance, Quarantine, certificate-first ordering, and explicit confirmation.",
            "",
            "Existing removal certificates:",
            *_exceptional_certificate_lines(root),
            "",
            "This Issue #50 menu intentionally provides inspection only; it does not "
            "add a generic delete or bypass the ExceptionalRemovalWorkflowService.",
        ),
    )


def launch_advanced_menu(state: MenuSessionContext) -> None:
    """Launch bounded exact administration without bypassing production authority."""

    while True:
        clear_screen()
        print_menu_header("Advanced Portia tools")
        print("Exact record-family and diagnostic access for expert use.")
        print()
        print("1. Event / Participant / Role / Relationship records")
        print("2. Evidence and judgment records")
        print("3. Response / Communication records")
        print("4. Support and downstream record families")
        print("5. Actor Directory exact lookup")
        print("6. Lifecycle / Amendment / Disagreement / Dependency history")
        print("7. Correction / Migration / Ownership Correction")
        print("8. Integrity / Quarantine / Recovery inspection")
        print("9. Exceptional operations")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show(
                "Advanced Portia tools Help",
                (
                    "Advanced mode preserves exact contracts, identities, provenance, "
                    "and operational diagnostics.",
                    "It does not authorize raw filesystem mutation, arbitrary JSON editing, "
                    "generic pointer rewriting, lock clearing, Quarantine release, or delete.",
                ),
            )
            continue
        if navigation is NavigationChoice.BACK:
            return
        try:
            root = state.resolve_workspace()
            if raw == "1":
                _browse_record_group(
                    state,
                    root,
                    title="Advanced — Event / Participant / Role / Relationship",
                    specs=_EVENT_RECORDS,
                )
            elif raw == "2":
                _browse_record_group(
                    state,
                    root,
                    title="Advanced — Evidence and Judgment",
                    specs=_EVIDENCE_JUDGMENT_RECORDS,
                )
            elif raw == "3":
                _browse_record_group(
                    state,
                    root,
                    title="Advanced — Response / Communication",
                    specs=_RESPONSE_RECORDS,
                )
            elif raw == "4":
                _browse_record_group(
                    state,
                    root,
                    title="Advanced — Support and Downstream",
                    specs=_SUPPORT_RECORDS,
                )
            elif raw == "5":
                _actor_lookup(root)
            elif raw == "6":
                _history_inventory(state, root)
            elif raw == "7":
                _authority_registry(root, state)
            elif raw == "8":
                _technical_inspection(root)
            elif raw == "9":
                _exceptional_operations(root)
            else:
                print(navigation_hint_with_help())
                pause_for_user()
        except CancelMenuAction:
            continue
        except (
            PortiaCorruptionError,
            PortiaNotFoundError,
            PortiaQuarantinedError,
            PortiaRecoveryRequiredError,
            PortiaStorageError,
            ValueError,
        ):
            _show(
                "Advanced Portia tools — Unable to Inspect",
                (
                    "The exact requested expert view could not be inspected safely.",
                    "No canonical state was changed and no automatic repair was attempted.",
                ),
            )
