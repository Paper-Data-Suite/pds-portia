"""Exact Core-backed selectors for Portia teacher-menu workflows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pds_core.class_metadata import load_class_metadata_for_class
from pds_core.classes import list_class_folders
from pds_core.rosters import student_display_name, student_sort_name

from portia.identity import CoreRosterResolver


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
