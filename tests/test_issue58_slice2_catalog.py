"""Synthetic immutable Portia capture catalog and historical identity tests."""

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
from portia.models import PageTargetV2

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/issue_58/catalog/v1"
RESOURCES = ROOT / "portia/capture/form_specs"
BASE_TARGET = ROOT / (
    "tests/fixtures/issue_56/slice_2/valid/"
    "page-target-v2-classroom-observation.json"
)


def raw_spec(filename: str) -> dict[str, object]:
    parsed: object = json.loads((RESOURCES / filename).read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def encoded(data: dict[str, object]) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def known_answers() -> list[dict[str, object]]:
    source = json.loads((FIXTURES / "identities.json").read_text(encoding="utf-8"))
    assert source["canonical_format"] == "portia_capture_layout_v1"
    answers: list[dict[str, object]] = source["known_answers"]
    return answers


def target_for(spec_index: int) -> PageTargetV2:
    source = json.loads(BASE_TARGET.read_text(encoding="utf-8"))
    spec = installed_capture_page_specs()[spec_index]
    source["template_identity"] = spec.template_identity()
    source["entry_layout"] = spec.entry_layout()
    return PageTargetV2(source)


def test_two_durable_page_specs_have_distinct_exact_identities() -> None:
    specs = installed_capture_page_specs()
    assert len(specs) == 2
    assert [spec.page_role for spec in specs] == [
        "classroom_observation", "observation_continuation"
    ]
    assert [spec.page_ordinal for spec in specs] == [1, 2]
    assert all(spec.page_purpose == "classroom_observation_capture" for spec in specs)
    assert all(spec.capture_mode == "mixed_recognition" for spec in specs)
    assert all(spec.context_entry_key == "session_context" for spec in specs)
    assert specs[0].template_identity() != specs[1].template_identity()


def test_fingerprints_match_independently_calculated_frozen_known_answers() -> None:
    specs = installed_capture_page_specs()
    answers = known_answers()
    assert len(specs) == len(answers)
    for spec, answer in zip(specs, answers, strict=True):
        resource = raw_spec(str(answer["resource"]))
        # Separate independent JSON/canonical SHA implementation, not a call
        # to the production fingerprint routine or Portia storage helpers.
        canonical = (
            json.dumps(
                resource, sort_keys=True, ensure_ascii=False,
                allow_nan=False, separators=(",", ":")
            ) + "\n"
        ).encode("utf-8")
        assert spec.canonical_bytes == canonical
        assert len(canonical) == answer["canonical_byte_length"]
        assert spec.layout_fingerprint == hashlib.sha256(canonical).hexdigest()
        assert spec.template_identity() == answer["template_identity"]
        assert list(spec.entry_keys) == answer["entry_keys"]
        assert sum(len(entry.fields) for entry in spec.entries) == answer["field_count"]


def test_exact_identity_resolves_and_unknown_history_fails_closed() -> None:
    for spec in installed_capture_page_specs():
        assert resolve_capture_page_spec(spec.template_identity()) is spec
        for key, changed in (
            ("template_id", "unknown_template"),
            ("template_version", "2"),
            ("layout_version", "layout_2"),
            ("capture_spec_version", "capture_2"),
            ("layout_fingerprint", "f" * 64),
            ("page_role", "another_role"),
            ("page_ordinal", 99),
        ):
            modified = {**spec.template_identity(), key: changed}
            with pytest.raises(UnsupportedCaptureFormError):
                resolve_capture_page_spec(modified)
        with pytest.raises(UnsupportedCaptureFormError):
            resolve_capture_page_spec({"template_id": spec.template_id})
        with pytest.raises(UnsupportedCaptureFormError):
            resolve_capture_page_spec({**spec.template_identity(), "surprise": 1})


def test_only_designed_form_is_supported() -> None:
    assert list_supported_capture_forms() == (
        ("daily_classroom_observation", "Daily Classroom Observation"),
    )
    assert len(capture_pages_for_form("daily_classroom_observation")) == 2
    for missing in (
        "focused_monitoring", "communication_log", "event_information",
        "implementation", "follow_up", "fidelity", "reentry", "repair", "other"
    ):
        with pytest.raises(UnsupportedCaptureFormError):
            capture_pages_for_form(missing)


def test_context_has_no_domain_mapping_and_slots_remain_independent() -> None:
    for spec in installed_capture_page_specs():
        assert spec.entries[0].entry_key == "session_context"
        assert spec.entries[0].source_role == "session_context"
        assert spec.entries[0].permitted_mapped_record_kinds == ()
        assert len(spec.entries) >= 3
        assert all(
            entry.permitted_mapped_record_kinds == ("observation", "event")
            for entry in spec.entries[1:]
        )
        assert len(spec.entry_keys) == len(set(spec.entry_keys))
        assert all(
            not field.required for entry in spec.entries for field in entry.fields
        )
        assert not any(
            field.field_key == "student_id"
            for entry in spec.entries for field in entry.fields
        )
        assert not any(
            token in spec.canonical_bytes
            for token in (b"route_id", b"scan_time", b"print_time", b"diagnosis")
        )


def test_tone_cues_are_source_marks_and_not_behavior_findings() -> None:
    for spec in installed_capture_page_specs():
        for entry in spec.entries[1:]:
            cues = [field for field in entry.fields if field.field_key == "tone"]
            assert len(cues) == 1
            assert cues[0].choices == ("positive", "general", "concern")
            assert cues[0].capture_method == "mark_recognition"
            assert cues[0].required is False


def test_all_regions_are_in_letter_page_and_clear_of_reserved_qr() -> None:
    for spec in installed_capture_page_specs():
        assert spec.qr_rectangle.width == spec.qr_rectangle.height == 108
        assert spec.qr_quiet_zone_modules == 4
        boxes = [f.rectangle for entry in spec.entries for f in entry.fields]
        for box in boxes:
            assert box.x >= 36 and box.y >= 154
            assert box.right <= 576 and box.bottom <= 742
            assert not (box.x < 576 and box.right > 468 and box.y < 148)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert not (
                    a.x < b.right and a.right > b.x
                    and a.y < b.bottom and a.bottom > b.y
                )


@pytest.mark.parametrize(
    ("path", "bad"),
    [
        (("entries", 0, "permitted_mapped_record_kinds"), ["event"]),
        (("entries", 1, "entry_key"), "session_context"),
        (("entries", 1, "fields", 0, "region_key"), "context_date"),
        (("entries", 1, "fields", 0, "required"), True),
        (("entries", 1, "fields", 0, "choices"), ["positive", "positive"]),
        (("entries", 1, "fields", 0, "capture_method"), "manual_transcription"),
        (("entries", 1, "fields", 3, "rectangle", "y"), 37),
        (("entries", 1, "fields", 3, "rectangle", "height"), 300),
        (("entries", 1, "fields", 0, "rectangle", "x"), 550),
        (("entries", 0, "fields", 0, "field_key"), "Invalid Key"),
    ],
)
def test_rejects_unsafe_or_ambiguous_semantic_regions(
    path: tuple[str | int, ...], bad: object
) -> None:
    data = raw_spec("classroom_observation_main_v1.json")
    cursor: object = data
    for piece in path[:-1]:
        assert isinstance(cursor, (dict, list))
        cursor = cursor[piece]
    assert isinstance(cursor, (dict, list))
    cursor[path[-1]] = bad
    with pytest.raises(CaptureCatalogError):
        parse_capture_page_spec(encoded(data))


def test_meaningful_change_requires_new_fingerprint() -> None:
    old = installed_capture_page_specs()[0]
    data = raw_spec("classroom_observation_main_v1.json")
    data["title"] = "Updated Daily Classroom Observation"
    modified = parse_capture_page_spec(encoded(data))
    assert modified.layout_fingerprint != old.layout_fingerprint
    with pytest.raises(UnsupportedCaptureFormError):
        resolve_capture_page_spec(modified.template_identity())


def test_stale_or_wrong_page_target_cannot_match_catalog() -> None:
    for i, spec in enumerate(installed_capture_page_specs()):
        target = target_for(i)
        spec.assert_page_target_exact(target)
        other = installed_capture_page_specs()[1 - i]
        with pytest.raises(CaptureCatalogError):
            other.assert_page_target_exact(target)
        mutated = target.to_dict()
        mutated["status"] = "retired"
        with pytest.raises(CaptureCatalogError):
            spec.assert_page_target_exact(PageTargetV2(mutated))
        mutated = target.to_dict()
        mutated["entry_layout"]["entry_keys"] = list(reversed(spec.entry_keys))
        with pytest.raises(CaptureCatalogError):
            spec.assert_page_target_exact(PageTargetV2(mutated))


def test_strict_resources_reject_duplicate_json_and_nonfinite_numbers() -> None:
    with pytest.raises(CaptureCatalogError, match="duplicate JSON key"):
        parse_capture_page_spec(b'{"schema_version":1,"schema_version":1}')
    source = (RESOURCES / "classroom_observation_main_v1.json").read_bytes()
    with pytest.raises(CaptureCatalogError):
        parse_capture_page_spec(
            source.replace(b'"schema_version": 1', b'"schema_version": NaN')
        )


def test_form_spec_cannot_embed_unknown_metadata_or_shift_qr() -> None:
    data = raw_spec("classroom_observation_main_v1.json")
    data["student_roster"] = []
    with pytest.raises(CaptureCatalogError):
        parse_capture_page_spec(encoded(data))
    data = raw_spec("classroom_observation_main_v1.json")
    data["qr_rectangle"]["x"] = 450
    with pytest.raises(CaptureCatalogError):
        parse_capture_page_spec(encoded(data))
