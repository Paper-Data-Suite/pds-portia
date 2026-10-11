from __future__ import annotations

from copy import deepcopy
from pathlib import Path

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store

BASE_V1 = "https://paper-data-suite.github.io/pds-portia/schemas/v1"
BASE_V2 = "https://paper-data-suite.github.io/pds-portia/schemas/v2"
PAGE_TARGET_V1 = f"{BASE_V1}/capture/page-target.schema.json"
PAGE_TARGET_V2 = f"{BASE_V2}/capture/page-target.schema.json"

ROOT = Path(__file__).resolve().parents[2]
TIMESTAMP = "2026-10-11T10:00:00-04:00"
FINGERPRINT = "b" * 64
AGENT = {"type": "system_process", "process_id": "issue56_test"}


def page_target_v2() -> dict[str, object]:
    return {
        "schema_version": "2",
        "record_type": "capture_page_target",
        "module_id": "portia",
        "class_id": "class_english12_p3",
        "work_id": "cbat_classroom_20261011",
        "page_target_id": "ptgt_classroom_20261011",
        "page_index": 1,
        "page_purpose": "classroom_observation_capture",
        "template_identity": {
            "template_id": "portia_classroom_observation",
            "template_version": "1",
            "layout_version": "layout_1",
            "capture_spec_version": "capture_1",
            "layout_fingerprint": FINGERPRINT,
            "page_role": "classroom_observation",
            "page_ordinal": 1,
        },
        "capture_mode": "mixed_recognition",
        "entry_layout": {
            "mode": "multi_entry",
            "entry_keys": [
                "session_context",
                "observation_01",
                "observation_02",
            ],
            "context_entry_key": "session_context",
        },
        "status": "active",
        "created_at": TIMESTAMP,
        "created_by": deepcopy(AGENT),
        "updated_at": TIMESTAMP,
        "updated_by": deepcopy(AGENT),
    }


class TestIssue56PageTargetV2:
    @classmethod
    def setup_class(cls) -> None:
        cls.store = build_schema_store()

    def assert_valid(self, schema_id: str, value: object) -> None:
        errors = list(self.store.validator_for_id(schema_id).iter_errors(value))
        assert not errors, "\n".join(error.message for error in errors)

    def assert_invalid(self, schema_id: str, value: object) -> None:
        assert list(self.store.validator_for_id(schema_id).iter_errors(value))

    def test_v2_accepts_daily_classroom_observation_layout(self) -> None:
        self.assert_valid(PAGE_TARGET_V2, page_target_v2())

    def test_v1_does_not_silently_accept_new_primary_purpose(self) -> None:
        value = page_target_v2()
        value["schema_version"] = "1"
        self.assert_invalid(PAGE_TARGET_V1, value)

    def test_classroom_observation_requires_context_entry(self) -> None:
        value = page_target_v2()
        del value["entry_layout"]["context_entry_key"]
        self.assert_invalid(PAGE_TARGET_V2, value)

    def test_classroom_observation_requires_multi_entry_layout(self) -> None:
        value = page_target_v2()
        value["entry_layout"] = {
            "mode": "single_entry",
            "entry_keys": ["session_context"],
            "context_entry_key": "session_context",
        }
        self.assert_invalid(PAGE_TARGET_V2, value)

    def test_classroom_observation_does_not_prebind_existing_work(self) -> None:
        value = page_target_v2()
        value["existing_work_context"] = {
            "module_id": "portia",
            "class_id": "class_english12_p3",
            "work_id": "evt_existing_01",
            "work_kind": "event",
            "contract_version": "2",
        }
        self.assert_invalid(PAGE_TARGET_V2, value)

    def test_v2_accepts_focused_monitoring_with_existing_support_context(self) -> None:
        value = page_target_v2()
        value["page_purpose"] = "focused_monitoring_capture"
        value["entry_layout"] = {
            "mode": "single_entry",
            "entry_keys": ["monitoring_entry"],
        }
        value["existing_work_context"] = {
            "module_id": "portia",
            "class_id": "class_english12_p3",
            "work_id": "sup_monitoring_01",
            "work_kind": "support_process",
            "contract_version": "1",
        }
        self.assert_valid(PAGE_TARGET_V2, value)

    def test_v2_accepts_communication_capture(self) -> None:
        value = page_target_v2()
        value["page_purpose"] = "communication_capture"
        value["entry_layout"] = {
            "mode": "single_entry",
            "entry_keys": ["communication_entry"],
        }
        self.assert_valid(PAGE_TARGET_V2, value)

    def test_page_target_does_not_store_returned_lesson_values(self) -> None:
        value = page_target_v2()
        value["lesson_objective"] = "Analyze structural choices."
        self.assert_invalid(PAGE_TARGET_V2, value)

    def test_context_entry_membership_is_an_application_invariant(self) -> None:
        schema = (
            ROOT / "schemas/v2/capture/page-target.schema.json"
        ).read_text(encoding="utf-8")
        assert "page_target.v2_context_entry_key_declared" in schema
        assert "must name one exact entry_key" in schema
