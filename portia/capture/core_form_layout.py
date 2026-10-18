"""Exact, pure drawing plans for bounded non-Daily v0.3 Portia capture forms.

All marks start unselected. Nothing in a plan is a scanned page, verified
Core route, canonical domain fact, or authorized printable PDF. The renderer
must reload active Batch/Page Target/Core registration before drawing a QR.
"""

from __future__ import annotations

from dataclasses import dataclass

from portia.capture.form_catalog import (
    CaptureCatalogError,
    CaptureField,
    CapturePageSpec,
    CaptureRectangle,
    capture_pages_for_form,
    resolve_capture_page_spec,
)
from portia.capture.observation_layout import (
    PAGE_HEIGHT_POINTS,
    PAGE_WIDTH_POINTS,
    MarkOption,
    TextRun,
    WritingRule,
)
from portia.models import PageTargetV2

CORE_FORM_DRAW_PLAN_VERSION = "core_capture_form_draw_plan_v1"


class CoreFormLayoutError(CaptureCatalogError):
    """A non-Daily form's layout or historical meaning cannot be safely drawn."""


@dataclass(frozen=True, slots=True)
class CoreFieldDrawing:
    entry_key: str
    field_key: str
    region_key: str
    rectangle: CaptureRectangle
    label: TextRun
    writing_rules: tuple[WritingRule, ...]
    mark_options: tuple[MarkOption, ...]


@dataclass(frozen=True, slots=True)
class CoreEntryDrawing:
    entry_key: str
    heading: TextRun | None
    fields: tuple[CoreFieldDrawing, ...]


@dataclass(frozen=True, slots=True)
class CoreFormDrawing:
    """One deterministic form page, without any route, content, or output path."""

    spec: CapturePageSpec
    title: TextRun
    instructions: tuple[TextRun, ...]
    footer: TextRun
    entries: tuple[CoreEntryDrawing, ...]
    route_text_area: CaptureRectangle
    version: str = CORE_FORM_DRAW_PLAN_VERSION

    @property
    def qr_area(self) -> CaptureRectangle:
        return self.spec.qr_rectangle

    @property
    def field_drawings(self) -> tuple[CoreFieldDrawing, ...]:
        return tuple(field for entry in self.entries for field in entry.fields)

    def assert_target_exact(self, target: PageTargetV2) -> None:
        """Check semantics/page index only; never substitute for render authority."""
        self.spec.assert_page_target_exact(target)
        # Page index belongs to the later batch/page-generation plan, not to
        # this frozen template-local ordinal. Every actual page still needs
        # its own verified Page Target and Core registration.


def _fits(run: TextRun) -> bool:
    return len(run.text) * run.font_size * 0.68 <= run.max_width


def _wrap(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        next_line = f"{current} {word}" if current else word
        if _fits(TextRun(next_line, 0, 0, 8.0, "regular", 404)):
            current = next_line
            continue
        if not current or len(lines) >= 2:
            raise CoreFormLayoutError("instructions exceed print header")
        lines.append(current)
        current = word
        if not _fits(TextRun(current, 0, 0, 8.0, "regular", 404)):
            raise CoreFormLayoutError("instruction word does not fit")
    if current:
        lines.append(current)
    if not 1 <= len(lines) <= 2:
        raise CoreFormLayoutError("instructions must fit on one or two lines")
    return tuple(lines)


def _entry_label(key: str) -> str:
    return key.replace("_", " ").title()


def _field_drawing(entry_key: str, source: CaptureField) -> CoreFieldDrawing:
    if not isinstance(source, CaptureField):
        raise CoreFormLayoutError("expected frozen CaptureField")
    box = source.rectangle
    label = TextRun(source.label, box.x + 4, box.y + 9, 6.6, "regular", box.width - 8)
    if not _fits(label):
        raise CoreFormLayoutError("field label exceeds exact region")
    if source.field_type == "text":
        rules = tuple(
            WritingRule(box.x + 6, y, box.right - 6)
            for y in range(box.y + 20, box.bottom - 3, 13)
        )
        if not rules:
            raise CoreFormLayoutError("text field is not writable")
        marks: tuple[MarkOption, ...] = ()
    else:
        rules = ()
        unit = (box.width - 12) // len(source.choices)
        marks = tuple(
            MarkOption(
                value=value,
                checkbox=CaptureRectangle(box.x + 6 + i * unit, box.y + 13, 8, 8),
                label=TextRun(
                    value.replace("_", " ").capitalize(),
                    box.x + 18 + i * unit,
                    box.y + 21,
                    6.7,
                    "regular",
                    unit - 15,
                ),
            )
            for i, value in enumerate(source.choices)
        )
        if any(
            not _fits(mark.label)
            or mark.checkbox.right > box.right - 3
            or mark.checkbox.bottom > box.bottom - 3
            for mark in marks
        ):
            raise CoreFormLayoutError("choice will not fit its exact field")
    return CoreFieldDrawing(
        entry_key=entry_key,
        field_key=source.field_key,
        region_key=source.region_key,
        rectangle=box,
        label=label,
        writing_rules=rules,
        mark_options=marks,
    )


def _drawing_from_spec(spec: CapturePageSpec) -> CoreFormDrawing:
    title = TextRun(
        spec.title, 40, 65, 13.5, "bold", 408
    )
    instructions = tuple(
        TextRun(line, 40, 86 + index * 12, 8.0, "regular", 404)
        for index, line in enumerate(_wrap(spec.instructions))
    )
    entries = tuple(
        CoreEntryDrawing(
            entry_key=entry.entry_key,
            heading=(
                None if index == 0 else TextRun(
                    _entry_label(entry.entry_key),
                    36,
                    min(field.rectangle.y for field in entry.fields) - 9,
                    8.5,
                    "bold",
                    360,
                )
            ),
            fields=tuple(_field_drawing(entry.entry_key, field) for field in entry.fields),
        )
        for index, entry in enumerate(spec.entries)
    )
    drawing = CoreFormDrawing(
        spec=spec,
        title=title,
        instructions=instructions,
        footer=TextRun("Portia capture form", 40, 753, 7.2, "regular", 532),
        entries=entries,
        route_text_area=CaptureRectangle(40, 115, 400, 20),
    )
    _validate_core_form_drawing(drawing)
    return drawing


def _validate_core_form_drawing(drawing: CoreFormDrawing) -> None:
    """Reject speculative, outdated or partially drawn layouts before rendering."""
    if drawing.version != CORE_FORM_DRAW_PLAN_VERSION:
        raise CoreFormLayoutError("unknown drawing version")
    spec = resolve_capture_page_spec(drawing.spec.template_identity())
    if spec != drawing.spec:
        raise CoreFormLayoutError("specification differs from frozen installed history")
    if spec.form_id == "daily_classroom_observation":
        raise CoreFormLayoutError("Daily Observation uses its own frozen drawing plan")
    if (PAGE_WIDTH_POINTS, PAGE_HEIGHT_POINTS) != (612, 792):
        raise CoreFormLayoutError("unexpected paper geometry")
    if drawing.route_text_area != CaptureRectangle(40, 115, 400, 20):
        raise CoreFormLayoutError("future fallback reservation changed")
    if drawing.qr_area != CaptureRectangle(468, 40, 108, 108):
        raise CoreFormLayoutError("QR reservation changed")
    expected_title = TextRun(spec.title, 40, 65, 13.5, "bold", 408)
    if drawing.title != expected_title or not _fits(drawing.title):
        raise CoreFormLayoutError("invalid exact form heading")
    expected_instructions = tuple(
        TextRun(line, 40, 86 + index * 12, 8.0, "regular", 404)
        for index, line in enumerate(_wrap(spec.instructions))
    )
    if drawing.instructions != expected_instructions:
        raise CoreFormLayoutError("instructions no longer match capture spec")
    if drawing.footer != TextRun("Portia capture form", 40, 753, 7.2, "regular", 532):
        raise CoreFormLayoutError("fixed footer changed")
    if not all(_fits(line) for line in drawing.instructions):
        raise CoreFormLayoutError("instructions exceed header")
    if len(drawing.entries) != len(spec.entries):
        raise CoreFormLayoutError("entry count disagrees with spec")
    for index, (actual, source) in enumerate(
        zip(drawing.entries, spec.entries, strict=True)
    ):
        if actual.entry_key != source.entry_key:
            raise CoreFormLayoutError("entry identity changed")
        expected_heading = None if index == 0 else TextRun(
            _entry_label(source.entry_key), 36,
            min(field.rectangle.y for field in source.fields) - 9,
            8.5, "bold", 360,
        )
        if actual.heading != expected_heading:
            raise CoreFormLayoutError("entry heading changed")
        if len(actual.fields) != len(source.fields):
            raise CoreFormLayoutError("capture field is missing")
        for rendered, field in zip(actual.fields, source.fields, strict=True):
            if rendered != _field_drawing(source.entry_key, field):
                raise CoreFormLayoutError("capture field drawing changed")
            rectangle = rendered.rectangle
            if not (
                36 <= rectangle.x < rectangle.right <= 576
                and 154 <= rectangle.y < rectangle.bottom <= 742
            ):
                raise CoreFormLayoutError("field outside printable region")
            if any(
                not (rectangle.right <= b.x or rectangle.x >= b.right
                or rectangle.bottom <= b.y or rectangle.y >= b.bottom)
                for b in (spec.header_rectangle, spec.footer_rectangle, spec.qr_rectangle)
            ):
                raise CoreFormLayoutError("field collides with reserved region")


def plan_core_capture_form(form_id: str) -> CoreFormDrawing:
    """Plan one blank non-Daily sheet by *exact* catalog form identifier."""
    specs = capture_pages_for_form(form_id)
    if len(specs) != 1:
        raise CoreFormLayoutError("multi-role form needs its specific drawing planner")
    return _drawing_from_spec(specs[0])
