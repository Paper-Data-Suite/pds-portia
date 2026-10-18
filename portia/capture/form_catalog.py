"""Immutable v1 capture form specifications for historically exact Page Targets.

This layer is deliberately read-only: no preparation, routing, PDF rendering,
student identity or domain record creation happens when a template is resolved.
Every printed region is a stable source/field locator for later interpretation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Literal, Mapping, cast

from portia.models import PageTargetV2

FORM_SPEC_FORMAT = "portia_capture_layout_v1"
_PAGE_WIDTH = 612
_PAGE_HEIGHT = 792
_MIN_MARGIN = 36
_CAPTURE_TOP = 154
_CAPTURE_BOTTOM = 742
_RESOURCE_FILES = (
    "classroom_observation_main_v1.json",
    "classroom_observation_continuation_v1.json",
    "focused_monitoring_v1.json",
    "communication_log_v1.json",
    "event_information_v1.json",
    "multi_event_information_v1.json",
    "event_evidence_v1.json",
    "support_implementation_v1.json",
    "support_process_evidence_v1.json",
    "follow_up_v1.json",
)
_IDENTITY_KEYS = frozenset(
    {
        "template_id",
        "template_version",
        "layout_version",
        "capture_spec_version",
        "layout_fingerprint",
        "page_role",
        "page_ordinal",
    }
)
_TEXT_METHODS = frozenset({"handwriting_recognition", "manual_transcription"})
# The role is a source/candidate mapping constraint, not materialization authority.
# Context entries must never acquire mapped_record_kind in #60.
_ROLE_MAPPINGS: Mapping[str, tuple[str, ...]] = {
    "session_context": (),
    "observation": ("observation", "event"),
    "monitoring_context": (),
    "monitoring": ("observation",),
    "communication_context": (),
    "communication": ("communication",),
    "event_context": (),
    "event_information": ("event",),
    "event_evidence": ("account", "observation"),
    "implementation_context": (),
    "implementation": ("implementation",),
    "support_context": (),
    "support_evidence": ("observation",),
    "follow_up_context": (),
    "follow_up": ("follow_up",),
}
# Exact frozen role/order/purpose inventory; no 'other' and no substitutions.
# The context entry is always non-domain; the additional roles can be
# independently reviewable slots on the same returned physical page.
_FORM_PROFILES: Mapping[
    tuple[str, str, int], tuple[str, tuple[str, ...]]
] = {
    ("daily_classroom_observation", "classroom_observation", 1): (
        "classroom_observation_capture",
        ("session_context", "observation", "observation"),
    ),
    ("daily_classroom_observation", "observation_continuation", 2): (
        "classroom_observation_capture",
        ("session_context", "observation", "observation", "observation"),
    ),
    ("focused_monitoring", "monitoring_sheet", 1): (
        "focused_monitoring_capture", ("monitoring_context", "monitoring")
    ),
    ("communication_log", "communication_sheet", 1): (
        "communication_capture", ("communication_context", "communication")
    ),
    ("event_information", "event_information_sheet", 1): (
        "new_event_capture", ("event_context", "event_information")
    ),
    ("multi_event_information", "multi_event_sheet", 1): (
        "multi_entry_event_capture",
        ("event_context", "event_information", "event_information"),
    ),
    ("event_evidence", "event_evidence_sheet", 1): (
        "event_evidence_capture", ("event_context", "event_evidence")
    ),
    ("support_implementation", "implementation_sheet", 1): (
        "implementation_capture",
        ("implementation_context", "implementation"),
    ),
    ("support_process_evidence", "support_evidence_sheet", 1): (
        "support_process_evidence_capture",
        ("support_context", "support_evidence"),
    ),
    ("follow_up", "follow_up_sheet", 1): (
        "follow_up_capture", ("follow_up_context", "follow_up")
    ),
}
_CONTEXT_REQUIRED_KIND: Mapping[str, str] = {
    "event_evidence_capture": "event",
    "support_process_evidence_capture": "support_process",
}
_NO_CONTEXT = frozenset({
    "classroom_observation_capture", "new_event_capture",
    "multi_entry_event_capture",
})


class CaptureCatalogError(ValueError):
    """A frozen catalog representation or a requested identity is invalid."""


class UnsupportedCaptureFormError(CaptureCatalogError):
    """A form/version/role is not in the immutable installed catalog."""


@dataclass(frozen=True, slots=True)
class CaptureRectangle:
    """Integer PDF points, using a *top-left* page origin."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class CaptureField:
    """One source-faithful, independently addressable printed capture region."""

    field_key: str
    region_key: str
    label: str
    field_type: Literal["text", "choice"]
    capture_method: Literal[
        "handwriting_recognition", "manual_transcription", "mark_recognition"
    ]
    rectangle: CaptureRectangle
    required: bool
    max_characters: int | None
    choices: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CaptureEntry:
    entry_key: str
    source_role: str
    permitted_mapped_record_kinds: tuple[str, ...]
    fields: tuple[CaptureField, ...]


@dataclass(frozen=True, slots=True)
class CapturePageSpec:
    """A frozen page whose fingerprint covers meaning, wording, and geometry.

    ``canonical_bytes`` is the exact versioned semantic representation. It is
    independent of generation timestamps, class, work IDs, routes, PDF output
    path, viewer aliases and QR image pixels. Changes to it change the digest.
    """

    form_id: str
    label: str
    template_id: str
    template_version: str
    layout_version: str
    capture_spec_version: str
    page_role: str
    page_ordinal: int
    page_purpose: str
    capture_mode: str
    title: str
    instructions: str
    context_entry_key: str
    qr_rectangle: CaptureRectangle
    header_rectangle: CaptureRectangle
    footer_rectangle: CaptureRectangle
    qr_quiet_zone_modules: int
    entries: tuple[CaptureEntry, ...]
    canonical_bytes: bytes
    layout_fingerprint: str

    @property
    def entry_keys(self) -> tuple[str, ...]:
        return tuple(entry.entry_key for entry in self.entries)

    def template_identity(self) -> dict[str, str | int]:
        return {
            "template_id": self.template_id,
            "template_version": self.template_version,
            "layout_version": self.layout_version,
            "capture_spec_version": self.capture_spec_version,
            "layout_fingerprint": self.layout_fingerprint,
            "page_role": self.page_role,
            "page_ordinal": self.page_ordinal,
        }

    def entry_layout(self) -> dict[str, object]:
        return {
            "mode": "multi_entry",
            "entry_keys": list(self.entry_keys),
            "context_entry_key": self.context_entry_key,
        }

    def assert_page_target_exact(self, target: PageTargetV2) -> None:
        """Check historical semantic agreement; *not* render authorization.

        Rendering must separately authorize/reload the active Batch, exact
        persisted Page Target and Core registration at the point of rendering.
        """
        if not isinstance(target, PageTargetV2):
            raise CaptureCatalogError("current page_target@2 is required")
        data = target.to_dict()
        if data.get("status") != "active":
            raise CaptureCatalogError("Page Target is not active")
        if data.get("template_identity") != self.template_identity():
            raise CaptureCatalogError("historical template identity mismatch")
        if data.get("page_purpose") != self.page_purpose:
            raise CaptureCatalogError("historical page purpose mismatch")
        if data.get("capture_mode") != self.capture_mode:
            raise CaptureCatalogError("historical capture mode mismatch")
        if data.get("entry_layout") != self.entry_layout():
            raise CaptureCatalogError("historical entry layout mismatch")
        work = data.get("existing_work_context")
        record = data.get("existing_record_context")
        if self.page_purpose in _NO_CONTEXT and (work is not None or record is not None):
            raise CaptureCatalogError("this form cannot prebind domain work")
        required_kind = _CONTEXT_REQUIRED_KIND.get(self.page_purpose)
        if required_kind and work is None and record is None:
            raise CaptureCatalogError("this form requires exact existing context")
        # This is a pure crosswalk, not verification of authoritative storage.
        # #57's resolver independently loads the exact historical representation.
        contexts: list[Mapping[str, object]] = []
        if work is not None:
            if not isinstance(work, dict):
                raise CaptureCatalogError("malformed existing work context")
            contexts.append(work)
        if record is not None:
            if not isinstance(record, dict):
                raise CaptureCatalogError("malformed existing record context")
            work_ref = record.get("work_ref")
            if not isinstance(work_ref, dict):
                raise CaptureCatalogError("malformed existing record context")
            contexts.append(work_ref)
        for ctx in contexts:
            kind = ctx.get("work_kind")
            if kind not in ("event", "support_process"):
                raise CaptureCatalogError("unknown existing work context kind")
            if required_kind and kind != required_kind:
                raise CaptureCatalogError("wrong existing work context kind")
        if len(contexts) == 2 and contexts[0] != contexts[1]:
            raise CaptureCatalogError("contradictory existing context references")


def _object(value: object, expected: frozenset[str], name: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise CaptureCatalogError(f"{name}: missing or unknown fields")
    if any(not isinstance(key, str) for key in value):
        raise CaptureCatalogError(f"{name}: non-text key")
    return cast(dict[str, object], value)


def _text(value: object, name: str, *, max_length: int = 96) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_length
        or any(ord(c) < 32 for c in value)
    ):
        raise CaptureCatalogError(f"{name}: invalid text")
    return value


def _token(value: object, name: str) -> str:
    result = _text(value, name)
    if not result[0].islower() or any(
        not (c.islower() or c.isdigit() or c == "_") for c in result
    ):
        raise CaptureCatalogError(f"{name}: expected lowercase ASCII-style token")
    if not result.isascii():
        raise CaptureCatalogError(f"{name}: token must be ASCII")
    return result


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise CaptureCatalogError(f"{name}: integer outside permitted bounds")
    return value


def _parse_rectangle(value: object, name: str) -> CaptureRectangle:
    raw = _object(value, frozenset({"x", "y", "width", "height"}), name)
    box = CaptureRectangle(
        _integer(raw["x"], f"{name}.x", _MIN_MARGIN, _PAGE_WIDTH),
        _integer(raw["y"], f"{name}.y", _CAPTURE_TOP, _PAGE_HEIGHT),
        _integer(raw["width"], f"{name}.width", 40, _PAGE_WIDTH),
        _integer(raw["height"], f"{name}.height", 20, _PAGE_HEIGHT),
    )
    if box.right > _PAGE_WIDTH - _MIN_MARGIN or box.bottom > _CAPTURE_BOTTOM:
        raise CaptureCatalogError(f"{name}: region exceeds printer-safe bounds")
    return box


def _parse_fixed_rectangle(value: object, name: str) -> CaptureRectangle:
    raw = _object(value, frozenset({"x", "y", "width", "height"}), name)
    return CaptureRectangle(
        _integer(raw["x"], f"{name}.x", 0, _PAGE_WIDTH),
        _integer(raw["y"], f"{name}.y", 0, _PAGE_HEIGHT),
        _integer(raw["width"], f"{name}.width", 1, _PAGE_WIDTH),
        _integer(raw["height"], f"{name}.height", 1, _PAGE_HEIGHT),
    )


def _intersects(a: CaptureRectangle, b: CaptureRectangle) -> bool:
    return a.x < b.right and a.right > b.x and a.y < b.bottom and a.bottom > b.y


def _parse_field(value: object, entry_key: str) -> CaptureField:
    name = f"entry[{entry_key}].field"
    raw = _object(
        value,
        frozenset(
            {
                "field_key", "region_key", "label", "field_type", "capture_method",
                "rectangle", "required", "max_characters", "choices",
            }
        ),
        name,
    )
    key = _token(raw["field_key"], f"{name}.field_key")
    kind = raw["field_type"]
    method = raw["capture_method"]
    if kind not in ("text", "choice"):
        raise CaptureCatalogError(f"{name}: unsupported field type")
    if not isinstance(method, str):
        raise CaptureCatalogError(f"{name}: invalid capture method")
    if kind == "text" and method not in _TEXT_METHODS:
        raise CaptureCatalogError(f"{name}: text requires a transcription method")
    if kind == "choice" and method != "mark_recognition":
        raise CaptureCatalogError(f"{name}: choice requires mark recognition")
    if raw["required"] is not False:
        raise CaptureCatalogError(f"{name}: blank printable fields must be optional")
    options = raw["choices"]
    if not isinstance(options, list):
        raise CaptureCatalogError(f"{name}: choices must be an array")
    choices = tuple(_token(item, f"{name}.choice") for item in options)
    if len(choices) != len(set(choices)):
        raise CaptureCatalogError(f"{name}: duplicate options")
    max_characters: int | None
    if kind == "text":
        if choices:
            raise CaptureCatalogError(f"{name}: text cannot contain options")
        max_characters = _integer(
            raw["max_characters"], f"{name}.max_characters", 1, 4000
        )
    else:
        if not 2 <= len(choices) <= 5 or raw["max_characters"] is not None:
            raise CaptureCatalogError(f"{name}: invalid choice specification")
        max_characters = None
    return CaptureField(
        field_key=key,
        region_key=_token(raw["region_key"], f"{name}.region_key"),
        label=_text(raw["label"], f"{name}.label", max_length=80),
        field_type=kind,
        capture_method=cast(
            Literal[
                "handwriting_recognition", "manual_transcription", "mark_recognition"
            ],
            method,
        ),
        rectangle=_parse_rectangle(raw["rectangle"], f"{name}.{key}.rectangle"),
        required=False,
        max_characters=max_characters,
        choices=choices,
    )


def _parse_entry(value: object) -> CaptureEntry:
    raw = _object(
        value,
        frozenset(
            {"entry_key", "source_role", "permitted_mapped_record_kinds", "fields"}
        ),
        "entry",
    )
    entry_key = _token(raw["entry_key"], "entry.entry_key")
    role = raw["source_role"]
    if not isinstance(role, str) or role not in _ROLE_MAPPINGS:
        raise CaptureCatalogError("unsupported entry source role")
    mapped = raw["permitted_mapped_record_kinds"]
    if not isinstance(mapped, list):
        raise CaptureCatalogError("entry mappings must be an array")
    kinds = tuple(_token(value, "entry.mapping") for value in mapped)
    if len(kinds) != len(set(kinds)) or kinds != _ROLE_MAPPINGS[role]:
        raise CaptureCatalogError("role needs exact permitted candidate mappings")
    fields_raw = raw["fields"]
    if not isinstance(fields_raw, list) or not fields_raw or len(fields_raw) > 12:
        raise CaptureCatalogError("entry must have bounded field definitions")
    fields_parsed = tuple(_parse_field(field, entry_key) for field in fields_raw)
    keys = [field.field_key for field in fields_parsed]
    if len(keys) != len(set(keys)):
        raise CaptureCatalogError("duplicate field_key within entry")
    return CaptureEntry(
        entry_key=entry_key,
        source_role=role,
        permitted_mapped_record_kinds=kinds,
        fields=fields_parsed,
    )


def _reject_nonfinite(value: str) -> None:
    raise CaptureCatalogError(f"invalid JSON constant: {value}")


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CaptureCatalogError("duplicate JSON key in catalog resource")
        result[key] = value
    return result


def parse_capture_page_spec(content: bytes) -> CapturePageSpec:
    """Parse a resource strictly; exported for synthetic/adversarial tests.

    A historical identity is never recovered by guessing from a digest or by
    editing resource data to make it agree with an already persisted target.
    """
    if len(content) > 128_000:
        raise CaptureCatalogError("capture spec resource is too large")
    try:
        raw: object = json.loads(
            content.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except CaptureCatalogError:
        raise
    except (UnicodeError, ValueError, TypeError) as exc:
        raise CaptureCatalogError("invalid capture spec JSON") from exc
    data = _object(
        raw,
        frozenset(
            {
                "spec_format", "schema_version", "form_id", "label", "template_id",
                "template_version", "layout_version", "capture_spec_version",
                "page_role", "page_ordinal", "page_purpose", "capture_mode",
                "page_width", "page_height", "page_margin_points",
                "geometry_coordinate_system", "qr_rectangle",
                "qr_quiet_zone_modules", "header_rectangle", "footer_rectangle",
                "title", "instructions", "context_entry_key", "entries",
            }
        ),
        "capture_page_spec",
    )
    if (
        data["spec_format"] != FORM_SPEC_FORMAT
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise CaptureCatalogError("unknown canonical capture spec format/version")
    if (
        type(data["page_width"]) is not int
        or type(data["page_height"]) is not int
        or data["page_width"] != _PAGE_WIDTH
        or data["page_height"] != _PAGE_HEIGHT
        or data["page_margin_points"] != _MIN_MARGIN
        or data["geometry_coordinate_system"] != "top_left_pdf_points"
    ):
        raise CaptureCatalogError("unsupported US Letter print geometry")
    if (
        data["qr_quiet_zone_modules"] != 4
        or type(data["qr_quiet_zone_modules"]) is not int
    ):
        raise CaptureCatalogError("QR requires a frozen 4-module quiet zone")
    qr_box = _parse_fixed_rectangle(data["qr_rectangle"], "qr_rectangle")
    header_box = _parse_fixed_rectangle(data["header_rectangle"], "header_rectangle")
    footer_box = _parse_fixed_rectangle(data["footer_rectangle"], "footer_rectangle")
    if (
        qr_box != CaptureRectangle(468, 40, 108, 108)
        or header_box != CaptureRectangle(36, 36, 420, 104)
        or footer_box != CaptureRectangle(36, 744, 540, 12)
        or _intersects(qr_box, header_box)
        or _intersects(qr_box, footer_box)
        or _intersects(header_box, footer_box)
    ):
        raise CaptureCatalogError("nonstandard reserved QR/header/footer geometry")
    if not isinstance(data["page_purpose"], str):
        raise CaptureCatalogError("page purpose is not a string")
    if data["capture_mode"] != "mixed_recognition":
        raise CaptureCatalogError("unsupported form recognition mode")
    raw_entries = data["entries"]
    if not isinstance(raw_entries, list) or not 2 <= len(raw_entries) <= 6:
        raise CaptureCatalogError("observation sheet needs bounded multiple entries")
    entries = tuple(_parse_entry(item) for item in raw_entries)
    entry_keys = tuple(entry.entry_key for entry in entries)
    if len(entry_keys) != len(set(entry_keys)):
        raise CaptureCatalogError("duplicate page-local entry_key")
    context_key = _token(data["context_entry_key"], "context_entry_key")
    if entries[0].entry_key != context_key:
        raise CaptureCatalogError("the context entry must be first and declared")
    used: list[CaptureRectangle] = []
    region_keys: set[str] = set()
    for entry in entries:
        for field in entry.fields:
            if field.region_key in region_keys:
                raise CaptureCatalogError("duplicate page-local region_key")
            region_keys.add(field.region_key)
            if any(_intersects(field.rectangle, other) for other in used):
                raise CaptureCatalogError("capture regions overlap")
            used.append(field.rectangle)
    role = _token(data["page_role"], "page_role")
    ordinal = _integer(data["page_ordinal"], "page_ordinal", 1, 32)
    template_id = _token(data["template_id"], "template_id")
    form_id = _token(data["form_id"], "form_id")
    profile = _FORM_PROFILES.get((form_id, role, ordinal))
    if profile is None:
        raise CaptureCatalogError("form/page role is not in the frozen catalog")
    expected_purpose, expected_roles = profile
    if data["page_purpose"] != expected_purpose:
        raise CaptureCatalogError("form role has wrong approved page purpose")
    if template_id != (
        "portia_classroom_observation" if form_id == "daily_classroom_observation"
        else f"portia_{form_id}"
    ):
        raise CaptureCatalogError("template ID disagrees with catalog form")
    if tuple(entry.source_role for entry in entries) != expected_roles:
        raise CaptureCatalogError("entry roles/order disagree with catalog form")
    if len([entry for entry in entries if entry.entry_key == context_key]) != 1:
        raise CaptureCatalogError("invalid form context entry")
    if data["template_version"] != "1" or data["layout_version"] != "layout_1" or data["capture_spec_version"] != "capture_1":
        raise CaptureCatalogError("historical form versions must not be redefined")
    # Deliberately hash all versioned printable semantics, including labels,
    # ordering, source mapping and geometry, but never a route/clock/output.
    canonical = (
        json.dumps(data, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    return CapturePageSpec(
        form_id=form_id,
        label=_text(data["label"], "label"),
        template_id=template_id,
        template_version=_text(data["template_version"], "template_version"),
        layout_version=_token(data["layout_version"], "layout_version"),
        capture_spec_version=_token(
            data["capture_spec_version"], "capture_spec_version"
        ),
        page_role=role,
        page_ordinal=ordinal,
        page_purpose=expected_purpose,
        capture_mode="mixed_recognition",
        title=_text(data["title"], "title"),
        instructions=_text(data["instructions"], "instructions", max_length=200),
        context_entry_key=context_key,
        qr_rectangle=qr_box,
        header_rectangle=header_box,
        footer_rectangle=footer_box,
        qr_quiet_zone_modules=4,
        entries=entries,
        canonical_bytes=canonical,
        layout_fingerprint=hashlib.sha256(canonical).hexdigest(),
    )


@lru_cache(maxsize=1)
def installed_capture_page_specs() -> tuple[CapturePageSpec, ...]:
    """Load only named, bundled v1 resources, preserving historical lookup."""
    directory = files("portia.capture.form_specs")
    result = tuple(
        parse_capture_page_spec(directory.joinpath(name).read_bytes())
        for name in _RESOURCE_FILES
    )
    identities = [tuple(spec.template_identity().items()) for spec in result]
    if len(identities) != len(set(identities)):
        raise CaptureCatalogError("duplicate historical template identity")
    keys = [(spec.form_id, spec.page_role) for spec in result]
    if len(set(keys)) != len(keys):
        raise CaptureCatalogError("duplicate form role")
    if len(result) != len(_FORM_PROFILES):
        raise CaptureCatalogError("catalog resource/profile inventory mismatch")
    for spec in result:
        if spec.canonical_bytes.count(b"\n") == 0:
            raise CaptureCatalogError("historical spec encoding invalid")
    return result


def list_supported_capture_forms() -> tuple[tuple[str, str], ...]:
    """Teacher-safe form identifier and label, not a generic 'other' fallback."""
    specs = installed_capture_page_specs()
    return tuple(
        (spec.form_id, spec.label)
        for spec in specs if spec.page_ordinal == 1
    )


def capture_pages_for_form(form_id: str) -> tuple[CapturePageSpec, ...]:
    matches = tuple(
        spec for spec in installed_capture_page_specs()
        if spec.form_id == form_id
    )
    if not matches:
        raise UnsupportedCaptureFormError(f"unsupported catalog form: {form_id}")
    return matches


def resolve_capture_page_spec(identity: Mapping[str, object]) -> CapturePageSpec:
    """Resolve *all seven* exact historical identity elements, or fail shut."""
    if not isinstance(identity, Mapping) or set(identity) != _IDENTITY_KEYS:
        raise UnsupportedCaptureFormError("incomplete or unexpected template identity")
    for spec in installed_capture_page_specs():
        if dict(identity) == spec.template_identity():
            return spec
    raise UnsupportedCaptureFormError("historical capture form/version unavailable")
