"""Guided class → paper form → verified preparation → PDF/preview menu.

Local-workspace authority is deliberately scoped to readable Core class/roster
metadata under the selected OS account. It is NOT school identity/authentication.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from portia.capture.form_catalog import list_supported_capture_forms
from portia.capture.teacher_flow import (
    TeacherCaptureRequest,
    TeacherCaptureService,
    _planned_specs,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.prompts import CancelMenuAction, confirm_write, prompt_text, select_one
from portia.menu.selectors import ClassOption, class_options
from portia.menu.ui import clear_screen, pause_for_user, print_menu_header
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaStorageError
from portia.storage.repository import PortiaRepository


class LocalWorkspaceCaptureAuthority:
    """OS-account local workspace gate; no claimed institutional user identity.

    Class membership is re-evaluated through Core's actual metadata and roster
    reader on EVERY operation, rather than from a caller-provided class label.
    A production multi-user/school rollout requires a stronger trusted adapter.
    """

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).absolute()

    def require_access(self, class_id: str, operation: str) -> None:
        if not operation.startswith(
            ("capture_", "page_", "capture_form.", "page_route.")
        ):
            raise PermissionError("unsupported capture operation")
        classes = {option.class_id for option in class_options(self.workspace)}
        if class_id not in classes:
            raise PermissionError("class is not present in this local Core workspace")

    def attribution(self) -> Mapping[str, object]:
        return {
            "type": "system_process",
            "process_id": "portia_local_capture_generation",
        }


@dataclass(frozen=True, slots=True)
class _ExistingWorkOption:
    work: ExactPortiaWorkRef
    label: str


def _existing_works(
    root: Path, class_id: str, kind: str
) -> tuple[_ExistingWorkOption, ...]:
    version = "2" if kind == "event" else "1"
    stored = PortiaRepository(root).list_works(
        class_id, work_kind=kind, version=version
    )
    options: list[_ExistingWorkOption] = []
    for item in stored:
        work_id = item.record.work_id
        if work_id is None:
            continue
        reference = ExactPortiaWorkRef(
            class_id=class_id,
            work_id=work_id,
            work_kind=kind,
            contract_version=version,
        )
        # Never expose an existing confidential Event narrative in the form menu.
        status = item.record.status or "status unavailable"
        options.append(
            _ExistingWorkOption(
                reference, f"{kind.replace('_', ' ').title()} — {status} — {work_id}"
            )
        )
    return tuple(options)


def _choose_class(root: Path) -> ClassOption:
    options = class_options(root)
    if not options:
        raise ValueError("No eligible Core class with metadata and roster exists")
    return select_one(
        "Paper Capture — Class",
        options,
        tuple(item.label for item in options),
        help_text="Only a class actually present in this Core workspace is selectable.",
    )


def _choose_form(root: Path, owner: ClassOption) -> TeacherCaptureRequest:
    catalog = list_supported_capture_forms()
    form_id = select_one(
        "Paper Capture — Form",
        tuple(item[0] for item in catalog),
        tuple(item[1] for item in catalog),
        help_text="Blank forms never establish a behavior record or observation.",
    )
    continuations = 0
    if form_id == "daily_classroom_observation":
        raw = prompt_text(
            "Paper Capture — Writing Space",
            "Continuation pages (0–8)",
            default="0",
            help_text=(
                "Each extra sheet has its own Page Target and PDS2 route. "
                "You can also choose zero for one normal Daily Observation page."
            ),
        )
        if raw is None or not raw.isascii() or not raw.isdecimal():
            raise ValueError("Continuation pages must be an integer from 0 to 8")
        continuations = int(raw)
    work: ExactPortiaWorkRef | None = None
    if form_id in {"event_evidence", "support_process_evidence"}:
        kind = "event" if form_id == "event_evidence" else "support_process"
        choices = _existing_works(root, owner.class_id, kind)
        if not choices:
            raise ValueError(f"No eligible existing {kind} found for this class")
        chosen = select_one(
            "Paper Capture — Existing Work",
            choices,
            tuple(item.label for item in choices),
            help_text="Select one exact existing work; no successor is substituted.",
        )
        work = chosen.work
    elif form_id in {
        "focused_monitoring",
        "communication_log",
        "support_implementation",
        "follow_up",
    }:
        link = select_one(
            "Paper Capture — Optional Context",
            (False, True),
            (
                "Create an unbound blank form",
                "Link an existing Event / Support Process",
            ),
            help_text="Optional context must refer to exact existing work in this class.",
        )
        if link:
            choices = (
                *_existing_works(root, owner.class_id, "event"),
                *_existing_works(root, owner.class_id, "support_process"),
            )
            if not choices:
                raise ValueError("No eligible existing work is available")
            selected = select_one(
                "Paper Capture — Optional Existing Work",
                choices,
                tuple(item.label for item in choices),
                help_text="Retains exact work kind and contract version; no inference.",
            )
            work = selected.work
    return TeacherCaptureRequest(owner.class_id, form_id, continuations, work)


def _show(lines: tuple[str, ...], *, title: str = "Paper Capture") -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _new_form(
    root: Path,
    state: MenuSessionContext,
    service: TeacherCaptureService,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> None:
    owner = _choose_class(root)
    state.remember_class(owner.class_id)
    request = _choose_form(root, owner)
    specs = _planned_specs(request)
    if not confirm_write(
        "Paper Capture — Review",
        "GENERATE",
        (
            f"Class: {owner.class_id}",
            f"Form: {dict(list_supported_capture_forms())[request.form_id]}",
            f"Pages: {len(specs)}",
            "Each page will receive a distinct registered PDS2 route.",
            "Blank forms contain no student facts or completed actions.",
        ),
        help_text="Confirm to prepare routes and save one verified PDF.",
    ):
        return
    plan = service.plan(
        request,
        batch_id=ids.new("cbat_"),
        page_ids=tuple(ids.new("ptgt_") for _ in specs),
        timestamp=clock.now().text,
    )
    outcome = service.generate(plan)
    if outcome.status != "pdf_ready":
        _show(("Needs attention — no PDF saved.", *outcome.diagnostics))
        return
    assert outcome.pdf is not None
    print(f"PDF ready: {outcome.pdf.page_count} page(s). Not yet printed.")
    if select_one(
        "Paper Capture — PDF Ready",
        (False, True),
        ("Return to menu", "Request PDF preview"),
        help_text="Preview requests a viewer launch; it cannot confirm display or print.",
    ):
        service.preview(owner.class_id, outcome.batch_id)
        _show(("Viewer launch requested. Printing was not confirmed.",))


def _saved_packet(root: Path, service: TeacherCaptureService) -> None:
    owner = _choose_class(root)
    batches = service.preparation.batches.list_batches(
        owner.class_id, authorization=service.authorization
    )
    if not batches:
        _show(("No saved Capture Batches are available for this class.",))
        return
    chosen = select_one(
        "Paper Capture — Saved Packets",
        batches,
        tuple(
            f"Capture packet {i} — {item.status}" for i, item in enumerate(batches, 1)
        ),
        help_text="A saved packet retains its original form identity and Core routes.",
    )
    batch_id = chosen.work_id
    if batch_id is None:
        raise ValueError("saved Capture Batch identity is missing")
    action = select_one(
        "Paper Capture — Existing Packet",
        ("preview", "reprint", "recover_pdf", "recover_routes"),
        (
            "Verify and request PDF preview",
            "Reuse exact PDF for printing another physical copy",
            "Explicitly recover interrupted PDF publication",
            "Inspect/recover incomplete Page Target routes",
        ),
        help_text="Reprints never change historical template or route identity.",
    )
    if action == "preview":
        service.preview(owner.class_id, batch_id)
        _show(("Viewer launch requested. No print completion was verified.",))
    elif action == "reprint":
        pdf = service.reprint(owner.class_id, batch_id)
        _show(
            (
                f"PDF ready: {pdf.page_count} page(s), state {pdf.state}.",
                "Second physical copies may return separately in later capture.",
            )
        )
    elif action == "recover_pdf":
        if confirm_write(
            "Recover Capture PDF",
            "RECOVER",
            ("Complete only an exactly verifiable interrupted PDF/receipt pair.",),
            help_text="Never overwrite a mismatched PDF or erase locks automatically.",
        ):
            result = service.recover_pdf(owner.class_id, batch_id)
            _show((f"PDF recovery: {result.state}.",))
    else:
        if confirm_write(
            "Recover PDS2 Routes",
            "RECOVER",
            ("Resume only unambiguous durable Page Targets missing routes.",),
            help_text="Never infer missing targets or alter conflicting registrations.",
        ):
            outcome = service.recover_routes(owner.class_id, batch_id)
            status = "Prepared" if outcome.ready_for_rendering else "Needs attention"
            _show((f"{status}: {len(outcome.pages)} Page Target(s).",))


def launch_capture_forms_menu(
    state: MenuSessionContext,
    *,
    service: TeacherCaptureService | None = None,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """One bounded task step; B returns normally, M/Q propagate through menu."""
    try:
        root = state.resolve_workspace()
        gateway = service or TeacherCaptureService(
            root, authorization=LocalWorkspaceCaptureAuthority(root)
        )
        choice = select_one(
            "Create Paper Capture Forms",
            ("new", "saved"),
            ("Create a new blank paper form", "Open / reprint / recover saved packet"),
            help_text=(
                "Register all PDS2 routes before PDF creation. "
                "Capture forms are not student observations until later reviewed."
            ),
        )
        if choice == "new":
            _new_form(
                root, state, gateway, clock or MenuClock(), ids or PortiaIdGenerator()
            )
        else:
            _saved_packet(root, gateway)
    except CancelMenuAction:
        return
    except (ValueError, PortiaStorageError, PermissionError) as exc:
        _show(("Needs attention. No successful print is recorded.", str(exc)))
