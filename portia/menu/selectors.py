"""Exact Core- and Portia-backed selectors for teacher-menu workflows."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pds_core.class_metadata import load_class_metadata_for_class
from pds_core.classes import list_class_folders
from pds_core.rosters import student_display_name, student_sort_name

from portia.identity import CoreRosterResolver
from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import EventWorkflowService, ParticipantWorkflowService


@dataclass(frozen=True, slots=True)
class ClassOption:
    """One exact selectable Core class with bounded presentation metadata."""

    class_id: str
    school_year: str
    student_count: int

    @property
    def label(self) -> str:
        noun = "student" if self.student_count == 1 else "students"
        return f"{self.class_id} — {self.school_year} — {self.student_count} {noun}"


@dataclass(frozen=True, slots=True)
class StudentOption:
    """One exact class-qualified Core roster student."""

    class_id: str
    student_id: str
    display_name: str
    period: str
    label: str


@dataclass(frozen=True, slots=True)
class EventOption:
    """One exact selectable Event with teacher-facing context."""

    work: ExactPortiaWorkRef
    status: str
    summary: str
    occurrence_label: str
    label: str


@dataclass(frozen=True, slots=True)
class EventParticipantOption:
    """One exact active Event Participant with bounded display context."""

    participant_id: str
    display_name: str
    label: str
    record: PortiaRecord


def class_options(workspace_root: str | Path) -> tuple[ClassOption, ...]:
    """Return valid Core classes that have both metadata and a roster."""

    folders = list_class_folders(
        workspace_root,
        require_roster=True,
        require_metadata=True,
    )
    resolver = CoreRosterResolver(workspace_root)
    options: list[ClassOption] = []
    for folder in folders:
        metadata = load_class_metadata_for_class(workspace_root, folder.class_id)
        roster = resolver.load_roster(folder.class_id)
        options.append(
            ClassOption(
                class_id=folder.class_id,
                school_year=metadata.school_year,
                student_count=len(roster.students),
            )
        )
    return tuple(sorted(options, key=lambda item: item.class_id.casefold()))


def student_options(
    workspace_root: str | Path,
    class_id: str,
) -> tuple[StudentOption, ...]:
    """Return exact roster choices without using names as identity."""

    roster = CoreRosterResolver(workspace_root).load_roster(class_id)
    ordered = sorted(roster.students, key=student_sort_name)
    display_names = [student_display_name(student) for student in ordered]
    name_counts = Counter(name.casefold() for name in display_names)
    duplicate_names = {name for name, count in name_counts.items() if count > 1}
    options: list[StudentOption] = []
    for student, display_name in zip(ordered, display_names, strict=True):
        label = f"{display_name} — Period {student.period}"
        if display_name.casefold() in duplicate_names:
            label += f" — {student.student_id}"
        options.append(
            StudentOption(
                class_id=student.class_id,
                student_id=student.student_id,
                display_name=display_name,
                period=student.period,
                label=label,
            )
        )
    return tuple(options)


def _event_occurrence_label(record: PortiaRecord) -> str:
    occurrence = record.field("occurrence")
    if not isinstance(occurrence, Mapping):
        return "time not recorded"
    precision = occurrence.get("precision")
    if precision in {"exact", "range", "approximate"}:
        started = occurrence.get("started_at")
        if isinstance(started, str):
            return started
    if precision == "date_only":
        date = occurrence.get("date")
        if isinstance(date, str):
            return date
    if precision == "unknown":
        return "time unknown"
    return "time not recorded"


def event_options(
    workspace_root: str | Path,
    class_id: str,
) -> tuple[EventOption, ...]:
    """Return evidence-write-eligible event@2 choices for one exact Core class."""

    stored = EventWorkflowService(workspace_root).list(class_id)
    preliminary: list[tuple[ExactPortiaWorkRef, str, str, str, str]] = []
    for item in stored:
        record = item.record
        if record.status not in {"draft", "active", "closed"}:
            continue
        if record.work_id is None:
            continue
        work = ExactPortiaWorkRef(
            class_id=class_id,
            work_id=record.work_id,
            work_kind="event",
            contract_version="2",
        )
        raw_summary = record.field("summary")
        summary = raw_summary if isinstance(raw_summary, str) else "Event without summary"
        occurrence = _event_occurrence_label(record)
        status = record.status or "unknown"
        label = f"{summary} — {occurrence} — {status.title()}"
        preliminary.append((work, status, summary, occurrence, label))

    counts = Counter(item[4].casefold() for item in preliminary)
    options: list[EventOption] = []
    for work, status, summary, occurrence, label in preliminary:
        if counts[label.casefold()] > 1:
            label += f" — exact Event {work.work_id}"
        options.append(
            EventOption(
                work=work,
                status=status,
                summary=summary,
                occurrence_label=occurrence,
                label=label,
            )
        )
    return tuple(options)


def _participant_display(record: PortiaRecord) -> tuple[str, str]:
    subject = record.field("subject")
    if not isinstance(subject, Mapping):
        return "Participant", "Participant"
    kind = subject.get("kind")
    if kind == "roster_student":
        snapshot = subject.get("display_snapshot")
        reference = subject.get("roster_student_ref")
        display = (
            snapshot.get("display_name")
            if isinstance(snapshot, Mapping)
            else None
        )
        class_id = reference.get("class_id") if isinstance(reference, Mapping) else None
        name = display if isinstance(display, str) else "Roster student"
        context = class_id if isinstance(class_id, str) else "roster student"
        return name, f"{name} — {context}"
    if kind == "actor":
        snapshot = subject.get("display_snapshot")
        display = (
            snapshot.get("display_name")
            if isinstance(snapshot, Mapping)
            else None
        )
        name = display if isinstance(display, str) else "Actor"
        return name, f"{name} — Actor"
    if kind == "descriptive_person":
        display = subject.get("display_label")
        description_type = subject.get("description_type")
        name = display if isinstance(display, str) else "Described person"
        context = (
            str(description_type).replace("_", " ")
            if isinstance(description_type, str)
            else "described person"
        )
        return name, f"{name} — {context}"
    if kind == "unknown_person":
        description = subject.get("description")
        name = description if isinstance(description, str) else "Unidentified person"
        return name, name
    return "Participant", "Participant"


def event_participant_options(
    workspace_root: str | Path,
    work: ExactPortiaWorkRef,
) -> tuple[EventParticipantOption, ...]:
    """Return exact active Participant choices for one Event."""

    stored = ParticipantWorkflowService(workspace_root).list(work)
    preliminary: list[tuple[str, str, str, PortiaRecord]] = []
    for item in stored:
        record = item.record
        if record.status != "active" or record.logical_id is None:
            continue
        display_name, label = _participant_display(record)
        preliminary.append((record.logical_id, display_name, label, record))

    counts = Counter(item[2].casefold() for item in preliminary)
    options: list[EventParticipantOption] = []
    for participant_id, display_name, label, record in preliminary:
        if counts[label.casefold()] > 1:
            label += f" — exact participant {participant_id}"
        options.append(
            EventParticipantOption(
                participant_id=participant_id,
                display_name=display_name,
                label=label,
                record=record,
            )
        )
    return tuple(options)
