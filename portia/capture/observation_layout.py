"""Pure, historically pinned page drawing plans for Daily Classroom Observation.

No output file, QR symbol, fallback locator, batch, route, student or domain
record is created here. A later renderer must separately authorize and verify
persisted Portia/Core routing immediately before rendering each actual page.

Coordinates are integer PDF points, measured from the upper-left of US Letter.
The plan cannot reinterpret a catalog version or invent field/entry semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from portia.capture.form_catalog import (
    CaptureCatalogError,
    CaptureField,
    CapturePageSpec,
    CaptureRectangle,
    capture_pages_for_form,
    resolve_capture_page_spec,
)
from portia.models import PageTargetV2

DRAW_PLAN_VERSION = "daily_observation_draw_plan_v1"
PAGE_WIDTH_POINTS = 612
PAGE_HEIGHT_POINTS = 792
MAX_CONTINUATION_PAGES = 8


class ObservationLayoutError(CaptureCatalogError):
    """A layout cannot be described safely by the frozen drawing contract."""


@dataclass(frozen=True, slots=True)
class TextRun:
    """Baseline coordinate, top-origin, with a bounded Helvetica text region."""

    text: str
    x: int
    baseline_y: int
    font_size: float
    weight: Literal["regular", "bold"]
    max_width: int


@dataclass(frozen=True, slots=True)
class WritingRule:
    """Light gray handwriting line, inside an exact capture field region."""

    x_start: int
    y: int
    x_end: int


@dataclass(frozen=True, slots=True)
class MarkOption:
    """One unmarked, explicitly descriptive source cue within a choice field."""

    value: str
    checkbox: CaptureRectangle
    label: TextRun


@dataclass(frozen=True, slots=True)
class FieldDrawing:
    """Exactly one historical field and its display-only drawing instructions."""

    entry_key: str
    field_key: str
    region_key: str
    source_role: Literal["session_context", "observation"]
    field_type: Literal["text", "choice"]
    rectangle: CaptureRectangle
    label: TextRun
    writing_rules: tuple[WritingRule, ...]
    mark_options: tuple[MarkOption, ...]


@dataclass(frozen=True, slots=True)
class EntryDrawing:
    entry_key: str
    source_role: Literal["session_context", "observation"]
    heading: TextRun | None
    fields: tuple[FieldDrawing, ...]


@dataclass(frozen=True, slots=True)
class ObservationPageDrawing:
    """Immutable instructions to draw one unregistered *layout*, not a form.

    This intentionally holds no QR payload or human fallback. A caller MUST
    verify an open durable Capture Batch, current Page Target, Core route and
    canonical PDS2 locator before a print-ready PDF can be produced.
    """

    spec: CapturePageSpec
    page_index: int
    total_pages: int
    title: TextRun
    instructions: tuple[TextRun, ...]
    footer: TextRun
    entries: tuple[EntryDrawing, ...]
    route_text_area: CaptureRectangle
    drawing_version: str = DRAW_PLAN_VERSION

    @property
    def qr_area(self) -> CaptureRectangle:
        return self.spec.qr_rectangle

    @property
    def field_drawings(self) -> tuple[FieldDrawing, ...]:
        return tuple(field for entry in self.entries for field in entry.fields)

    def assert_target_exact(self, target: PageTargetV2) -> None:
        """Pure layout/target check, never a substitution for render authority."""
        try:
            self.spec.assert_page_target_exact(target)
        except CaptureCatalogError as exc:
            raise ObservationLayoutError(str(exc)) from exc
        if target.field("page_index") != self.page_index:
            raise ObservationLayoutError("Page Target page_index does not match drawing")


@dataclass(frozen=True, slots=True)
class DailyObservationPacketDrawing:
    """Main sheet plus zero or more separately routable continuation layouts."""

    pages: tuple[ObservationPageDrawing, ...]

    def __post_init__(self) -> None:
        if not self.pages or len(self.pages) > MAX_CONTINUATION_PAGES + 1:
            raise ObservationLayoutError("packet page count is invalid")
        if tuple(page.page_index for page in self.pages) != tuple(
            range(1, len(self.pages) + 1)
        ):
            raise ObservationLayoutError("packet page indices must be contiguous")
        if any(page.total_pages != len(self.pages) for page in self.pages):
            raise ObservationLayoutError("packet has inconsistent page counts")
        roles = tuple(page.spec.page_role for page in self.pages)
        if roles != ("classroom_observation",) + (
            "observation_continuation",
        ) * (len(self.pages) - 1):
            raise ObservationLayoutError("packet must start with the daily main page")

    @property
    def page_count(self) -> int:
        return len(self.pages)


def _fits(run: TextRun) -> bool:
    """Conservative width limit; exact glyph fitting remains renderer-owned."""
    return (len(run.text) * run.font_size * 0.68) <= run.max_width


def _wrap_words(text: str, max_width: int, font_size: float) -> tuple[str, ...]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if _fits(TextRun(candidate, 0, 0, font_size, "regular", max_width)):
            current = candidate
        else:
            if not current or len(lines) >= 2:
                raise ObservationLayoutError("instructions exceed reserved header space")
            lines.append(current)
            current = word
            if not _fits(TextRun(current, 0, 0, font_size, "regular", max_width)):
                raise ObservationLayoutError("unbreakable header text is too long")
    if current:
        lines.append(current)
    if not 1 <= len(lines) <= 2:
        raise ObservationLayoutError("instructions need one or two lines")
    return tuple(lines)


def _field_drawing(
    entry_key: str,
    source_role: Literal["session_context", "observation"],
    field: CaptureField,
) -> FieldDrawing:
    box = field.rectangle
    label = TextRun(field.label, box.x + 4, box.y + 9, 6.6, "regular", box.width - 8)
    if not _fits(label):
        raise ObservationLayoutError(f"field label will not fit: {field.region_key}")
    if field.field_type == "text":
        rules = tuple(
            WritingRule(box.x + 6, y, box.right - 6)
            for y in range(box.y + 20, box.bottom - 3, 13)
        )
        if not rules or any(rule.x_start >= rule.x_end for rule in rules):
            raise ObservationLayoutError("text capture field has no writable rule")
        options: tuple[MarkOption, ...] = ()
    else:
        rules = ()
        if field.choices != ("positive", "general", "concern"):
            raise ObservationLayoutError("unknown Daily Observation source cues")
        unit = (box.width - 12) // len(field.choices)
        options = tuple(
            MarkOption(
                value=value,
                checkbox=CaptureRectangle(box.x + 6 + n * unit, box.y + 13, 8, 8),
                label=TextRun(
                    value.capitalize(),
                    box.x + 18 + n * unit,
                    box.y + 21,
                    6.7,
                    "regular",
                    unit - 15,
                ),
            )
            for n, value in enumerate(field.choices)
        )
        for option in options:
            if (
                not _fits(option.label)
                or option.checkbox.right > box.right - 3
                or option.checkbox.bottom > box.bottom - 3
                or option.label.x + option.label.max_width > box.right
            ):
                raise ObservationLayoutError("choice geometry exceeds capture field")
    return FieldDrawing(
        entry_key=entry_key,
        field_key=field.field_key,
        region_key=field.region_key,
        source_role=source_role,
        field_type=field.field_type,
        rectangle=box,
        label=label,
        writing_rules=rules,
        mark_options=options,
    )


def _entry_drawing(spec: CapturePageSpec, entry_index: int) -> EntryDrawing:
    entry = spec.entries[entry_index]
    source_role: Literal["session_context", "observation"]
    if entry.source_role == "session_context":
        source_role = "session_context"
    elif entry.source_role == "observation":
        source_role = "observation"
    else:
        raise ObservationLayoutError("not a Daily Observation source role")
    fields = tuple(
        _field_drawing(entry.entry_key, source_role, field)
        for field in entry.fields
    )
    heading = None
    if entry.source_role == "observation":
        ordinal = int(entry.entry_key.rsplit("_", 1)[1])
        first_y = min(field.rectangle.y for field in fields)
        heading = TextRun(
            f"Observation {ordinal}", 36, first_y - 6, 8.5, "bold", 200
        )
    return EntryDrawing(entry.entry_key, source_role, heading, fields)


def _validate_page_drawing(page: ObservationPageDrawing) -> None:
    """Check geometry/identity against the actual frozen resource."""
    spec = resolve_capture_page_spec(page.spec.template_identity())
    if spec != page.spec:
        raise ObservationLayoutError("uninstalled/altered capture layout rejected")
    if page.drawing_version != DRAW_PLAN_VERSION:
        raise ObservationLayoutError("unknown drawing plan version")
    if (page.spec.header_rectangle, page.spec.footer_rectangle) != (
        CaptureRectangle(36, 36, 420, 104), CaptureRectangle(36, 744, 540, 12)
    ):
        raise ObservationLayoutError("header/footer reservation conflict")
    if page.qr_area != CaptureRectangle(468, 40, 108, 108):
        raise ObservationLayoutError("QR reservation conflict")
    if page.route_text_area != CaptureRectangle(40, 115, 400, 20):
        raise ObservationLayoutError("future route fallback area is not reserved")
    if page.title.text != spec.title or tuple(
        line.text for line in page.instructions
    ) != _wrap_words(spec.instructions, 404, 8.0):
        raise ObservationLayoutError("title/instructions disagree with historical spec")
    if page.footer.text != f"Page {page.page_index} of {page.total_pages}":
        raise ObservationLayoutError("visible page label does not match packet")
    if len(page.entries) != len(spec.entries):
        raise ObservationLayoutError("missing capture entry")
    for entry, source in zip(page.entries, spec.entries, strict=True):
        if entry.entry_key != source.entry_key or entry.source_role != source.source_role:
            raise ObservationLayoutError("drawing entry identity mismatch")
        if entry.heading != _entry_drawing(spec, spec.entries.index(source)).heading:
            raise ObservationLayoutError("observation heading identity changed")
        if len(entry.fields) != len(source.fields):
            raise ObservationLayoutError("missing drawing field")
        for shown, declared in zip(entry.fields, source.fields, strict=True):
            if (
                shown.field_key != declared.field_key
                or shown.region_key != declared.region_key
                or shown.rectangle != declared.rectangle
                or shown.field_type != declared.field_type
                or shown.label.text != declared.label
            ):
                raise ObservationLayoutError("field meaning/geometry mismatch")
            if shown.field_type == "text" and not shown.writing_rules:
                raise ObservationLayoutError("text field must be writable")
            if shown.field_type == "choice" and tuple(
                option.value for option in shown.mark_options
            ) != declared.choices:
                raise ObservationLayoutError("choice tokens changed")
        if entry.heading is not None and entry.heading.baseline_y < 149:
            raise ObservationLayoutError("entry heading intersects header/QR")
    if (
        not _fits(page.title)
        or any(not _fits(line) for line in page.instructions)
        or not _fits(page.footer)
    ):
        raise ObservationLayoutError("printed text exceeds its reserved width")
    if not 1 <= page.page_index <= page.total_pages <= MAX_CONTINUATION_PAGES + 1:
        raise ObservationLayoutError("invalid packet pagination")


def _page_drawing(
    spec: CapturePageSpec, page_index: int, total_pages: int
) -> ObservationPageDrawing:
    header = spec.header_rectangle
    title = TextRun(
        spec.title, header.x + 4, header.y + 28, 14.0, "bold", header.width - 8
    )
    instructions = tuple(
        TextRun(line, header.x + 4, header.y + 50 + n * 12, 8.0, "regular", 404)
        for n, line in enumerate(_wrap_words(spec.instructions, 404, 8.0))
    )
    footer = TextRun(
        f"Page {page_index} of {total_pages}",
        spec.footer_rectangle.x + 4,
        spec.footer_rectangle.y + 9,
        7.2,
        "regular",
        spec.footer_rectangle.width - 8,
    )
    plan = ObservationPageDrawing(
        spec=spec,
        page_index=page_index,
        total_pages=total_pages,
        title=title,
        instructions=instructions,
        footer=footer,
        entries=tuple(_entry_drawing(spec, n) for n in range(len(spec.entries))),
        route_text_area=CaptureRectangle(40, 115, 400, 20),
    )
    _validate_page_drawing(plan)
    return plan


def plan_daily_classroom_observation(
    *, continuation_pages: int = 0
) -> DailyObservationPacketDrawing:
    """Pure deterministic layouts for one blank daily sheet and continuations.

    This method cannot print a page and intentionally has no caller-supplied
    lesson values, class roster, source author, event occurrence or identities.
    Repeated continuation roles use page-local keys but distinct batch page
    indices; later preparation MUST allocate distinct Page Targets/routes.
    """
    if type(continuation_pages) is not int or not (
        0 <= continuation_pages <= MAX_CONTINUATION_PAGES
    ):
        raise ObservationLayoutError("continuation_pages must be an integer from 0 to 8")
    specs = capture_pages_for_form("daily_classroom_observation")
    if len(specs) != 2 or tuple(spec.page_role for spec in specs) != (
        "classroom_observation", "observation_continuation"
    ):
        raise ObservationLayoutError("required historical Daily Observation roles missing")
    page_count = continuation_pages + 1
    pages = tuple(
        _page_drawing(
            specs[0] if i == 0 else specs[1], i + 1, page_count
        )
        for i in range(page_count)
    )
    return DailyObservationPacketDrawing(pages)
