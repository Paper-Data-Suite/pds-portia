"""Issue #58 Slice 4: immutable, purpose-specific core capture forms."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from portia.capture.form_catalog import (
    CaptureCatalogError,
    UnsupportedCaptureFormError,
    capture_pages_for_form,
    installed_capture_page_specs,
    list_supported_capture_forms,
    parse_capture_page_spec,
    resolve_capture_page_spec,
)
from portia.capture.purposes import validate_page_purpose
from portia.models import PageTargetV2
from portia.models.errors import PortiaWireError

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "portia/capture/form_specs"
FIXTURE = ROOT / "tests/fixtures/issue_58/catalog/v1/additional_identities.json"
BASE_TARGET = ROOT / (
    "tests/fixtures/issue_56/slice_2/valid/"
    "page-target-v2-classroom-observation.json"
)
FORM_PURPOSES = {
    "focused_monitoring": "focused_monitoring_capture",
    "communication_log": "communication_capture",
    "event_information": "new_event_capture",
    "multi_event_information": "multi_entry_event_capture",
    "event_evidence": "event_evidence_capture",
    "support_implementation": "implementation_capture",
    "support_process_evidence": "support_process_evidence_capture",
    "follow_up": "follow_up_capture",
}


def raw_spec(filename: str) -> dict[str, object]:
    data = json.loads((RESOURCES / filename).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def encode(data: dict[str, object]) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def spec_for(form: str):
    specs = capture_pages_for_form(form)
    assert len(specs) == 1
    return specs[0]


def target_for(form: str, context: str | None = None) -> PageTargetV2:
    spec = spec_for(form)
    data = json.loads(BASE_TARGET.read_text(encoding="utf-8"))
    data["template_identity"] = spec.template_identity()
    data["entry_layout"] = spec.entry_layout()
    data["page_purpose"] = spec.page_purpose
    data["capture_mode"] = spec.capture_mode
    if context is not None:
        data["existing_work_context"] = {
            "module_id": "portia",
            "class_id": data["class_id"],
            "work_kind": context,
            "work_id": "evt_example_01" if context == "event" else "sup_example_01",
            "contract_version": "2" if context == "event" else "1",
        }
    return PageTargetV2(data)


def test_all_supported_core_forms_and_no_implicit_other() -> None:
    names = dict(list_supported_capture_forms())
    assert len(names) == 9
    assert set(names) == {"daily_classroom_observation", *FORM_PURPOSES}
    assert all(names[name] for name in names)
    assert len(installed_capture_page_specs()) == 10
    for name, purpose in FORM_PURPOSES.items():
        spec = spec_for(name)
        assert spec.page_purpose == purpose
        assert spec.page_ordinal == 1
        assert spec.capture_mode == "mixed_recognition"
        assert spec.entry_layout()["mode"] == "multi_entry"
        assert spec.entry_layout()["context_entry_key"] == spec.entries[0].entry_key
        assert spec.entries[0].permitted_mapped_record_kinds == ()
        assert len(spec.entries) >= 2
        assert all(entry.permitted_mapped_record_kinds for entry in spec.entries[1:])
        assert resolve_capture_page_spec(spec.template_identity()) is spec
    for missing in ("other", "fidelity", "reentry", "repair", "implementation", ""):
        with pytest.raises(UnsupportedCaptureFormError):
            capture_pages_for_form(missing)


def test_independent_known_answers_include_full_historical_identity() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == 1
    assert len(fixture["known_answers"]) == len(FORM_PURPOSES)
    for answer in fixture["known_answers"]:
        resource = raw_spec(answer["resource"])
        # The expectation is generated outside the catalog implementation and
        # committed independently; no fingerprint function is called here.
        canonical = (
            json.dumps(
                resource, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            ) + "\n"
        ).encode("utf-8")
        spec = spec_for(resource["form_id"])
        assert spec.canonical_bytes == canonical
        assert hashlib.sha256(canonical).hexdigest() == (
            answer["template_identity"]["layout_fingerprint"]
        )
        assert spec.template_identity() == answer["template_identity"]
        assert len(canonical) == answer["canonical_byte_length"]
        assert list(spec.entry_keys) == answer["entry_keys"]
        assert sum(len(entry.fields) for entry in spec.entries) == answer["field_count"]
        assert all(field.required is False for entry in spec.entries for field in entry.fields)
        assert len({f.region_key for e in spec.entries for f in e.fields}) == (
            answer["field_count"]
        )


def test_original_daily_fingerprints_and_roles_are_unchanged() -> None:
    specs = capture_pages_for_form("daily_classroom_observation")
    assert len(specs) == 2
    assert specs[0].layout_fingerprint == (
        "33483a2543ee50c636415a53dbca611c38b361a1d649f1e5f4533cc00aaa1518"
    )
    assert specs[1].layout_fingerprint == (
        "25fe7682a2ffab06309975194405be8020bd45935357702028f8e810b2908ee9"
    )
    assert specs[0].entry_keys == (
        "session_context", "observation_01", "observation_02"
    )
    assert specs[1].entry_keys == (
        "session_context", "observation_01", "observation_02", "observation_03"
    )


def test_purpose_context_crosswalk_and_target_exactness() -> None:
    for form, purpose in FORM_PURPOSES.items():
        spec = spec_for(form)
        if form == "event_evidence":
            with pytest.raises(CaptureCatalogError, match="requires exact"):
                spec.assert_page_target_exact(target_for(form))
            with pytest.raises(CaptureCatalogError, match="wrong existing"):
                spec.assert_page_target_exact(target_for(form, "support_process"))
            good = target_for(form, "event")
        elif form == "support_process_evidence":
            with pytest.raises(CaptureCatalogError, match="requires exact"):
                spec.assert_page_target_exact(target_for(form))
            with pytest.raises(CaptureCatalogError, match="wrong existing"):
                spec.assert_page_target_exact(target_for(form, "event"))
            good = target_for(form, "support_process")
        else:
            good = target_for(form)
            if form in {"event_information", "multi_event_information"}:
                # The runtime wire contract rejects this before catalog matching.
                with pytest.raises(PortiaWireError, match="prohibited contract branch"):
                    target_for(form, "event")
            else:
                spec.assert_page_target_exact(target_for(form, "event"))
                spec.assert_page_target_exact(target_for(form, "support_process"))
        assert good.field("page_purpose") == purpose
        validate_page_purpose(good)
        spec.assert_page_target_exact(good)
        mutated = good.to_dict()
        mutated["entry_layout"]["entry_keys"] = list(reversed(spec.entry_keys))
        with pytest.raises(CaptureCatalogError, match="entry layout"):
            spec.assert_page_target_exact(PageTargetV2(mutated))
        mutated = good.to_dict()
        mutated["template_identity"]["layout_fingerprint"] = "f" * 64
        with pytest.raises(CaptureCatalogError, match="template identity"):
            spec.assert_page_target_exact(PageTargetV2(mutated))


def test_multiple_event_slots_remain_separate_and_not_created() -> None:
    spec = spec_for("multi_event_information")
    assert spec.entry_keys == ("event_context", "event_01", "event_02")
    assert spec.entries[0].permitted_mapped_record_kinds == ()
    assert spec.entries[1].permitted_mapped_record_kinds == ("event",)
    assert spec.entries[2].permitted_mapped_record_kinds == ("event",)
    assert spec.entries[1].fields != spec.entries[2].fields
    assert all("student_id" != field.field_key for e in spec.entries for field in e.fields)
    assert not hasattr(spec, "record")
    assert not hasattr(spec, "route")


def test_planned_is_not_actual_and_no_completion_is_prechecked() -> None:
    implementation = spec_for("support_implementation")
    follow_up = spec_for("follow_up")
    assert {f.field_key for f in implementation.entries[1].fields} >= {
        "planned_step", "actual_step", "duration", "response"
    }
    assert {f.field_key for f in follow_up.entries[1].fields} >= {
        "proposed_activity", "activity_attempted", "unresolved_items"
    }
    assert not any(
        f.field_key in {"as_planned", "completed", "effective", "successful"}
        for form in FORM_PURPOSES
        for entry in spec_for(form).entries
        for f in entry.fields
    )


def test_all_print_geometry_is_bounded_writable_and_nonoverlapping() -> None:
    for form in FORM_PURPOSES:
        spec = spec_for(form)
        boxes = [field.rectangle for entry in spec.entries for field in entry.fields]
        assert all(box.x >= 36 and box.y >= 154 for box in boxes)
        assert all(box.right <= 576 and box.bottom <= 742 for box in boxes)
        assert all(box.height >= 20 and box.width >= 40 for box in boxes)
        for i, first in enumerate(boxes):
            for second in boxes[i + 1:]:
                assert not (
                    first.x < second.right and first.right > second.x
                    and first.y < second.bottom and first.bottom > second.y
                )
        assert spec.qr_rectangle.width == 108
        assert spec.qr_quiet_zone_modules == 4
        for entry in spec.entries:
            for field in entry.fields:
                # conservative Helvetica 6.6pt max label width estimate
                assert len(field.label) * 6.6 * 0.68 <= field.rectangle.width - 8


@pytest.mark.parametrize("mutator", [
    lambda data: data.update(page_purpose="other"),
    lambda data: data.update(form_id="other"),
    lambda data: data.update(page_role="communication_sheet"),
    lambda data: data["entries"][0].update(permitted_mapped_record_kinds=["observation"]),
    lambda data: data["entries"][1].update(permitted_mapped_record_kinds=["outcome"]),
    lambda data: data["entries"][1].update(source_role="fidelity"),
    lambda data: data["entries"][1]["fields"][0].update(required=True),
    lambda data: data["entries"][1]["fields"][0].update(capture_method="mark_recognition"),
    lambda data: data["entries"][1]["fields"][0].update(region_key="monitoring_context_observation_date"),
    lambda data: data["entries"][1]["fields"][0]["rectangle"].update(y=37),
    lambda data: data["qr_rectangle"].update(x=430),
])
def test_invalid_purpose_roles_semantics_and_geometry_fail_closed(mutator) -> None:
    data = raw_spec("focused_monitoring_v1.json")
    mutator(data)
    with pytest.raises(CaptureCatalogError):
        parse_capture_page_spec(encode(data))


def test_modified_semantics_cannot_silently_resolve_old_identity() -> None:
    data = raw_spec("follow_up_v1.json")
    original = spec_for("follow_up")
    data["entries"][1]["fields"][0]["label"] = "Amended proposed activity"
    altered = parse_capture_page_spec(encode(data))
    assert altered.layout_fingerprint != original.layout_fingerprint
    with pytest.raises(UnsupportedCaptureFormError):
        resolve_capture_page_spec(altered.template_identity())
    with pytest.raises(UnsupportedCaptureFormError):
        resolve_capture_page_spec({**original.template_identity(), "unexpected": True})
