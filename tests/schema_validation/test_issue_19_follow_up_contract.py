from __future__ import annotations

from datetime import date, datetime
from typing import Any
import unittest

try:
    from .schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )


FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-19"
    / "follow-up"
)
SCHEMA_PATH = "schemas/v1/follow-ups/follow-up.schema.json"

EVENT_OWNER_ELIGIBLE_KINDS = {"local_operator", "actor"}
OPERATIONAL_SUPPORT_CONTEXTS = {
    "provider_or_collaborator",
    "coordinator",
}


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _work_identity(value: dict[str, Any]) -> tuple[str, str, str]:
    return (
        value["class_id"],
        value["work_kind"],
        value["work_id"],
    )


def _ref_work_identity(ref: dict[str, Any]) -> tuple[str, str, str]:
    work = ref["work_ref"]
    return (
        work["class_id"],
        work["work_kind"],
        work["work_id"],
    )


def _ref_identity(ref: dict[str, Any]) -> tuple[str, str, str, str, str]:
    work = ref["work_ref"]
    record = ref["record_ref"]
    return (
        work["class_id"],
        work["work_kind"],
        work["work_id"],
        record["record_id"],
        record["contract_version"],
    )


def follow_up_application_errors(
    value: dict[str, Any],
    *,
    resolved_support_participants: dict[str, dict[str, Any]] | None = None,
    operational_actor_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []

    if _dt(value["updated_at"]) < _dt(value["created_at"]):
        errors.append("updated_at precedes created_at")

    timing = value["planned_timing"]
    if (
        timing["kind"] == "window"
        and "starts_on" in timing
        and date.fromisoformat(timing["ends_on"])
        < date.fromisoformat(timing["starts_on"])
    ):
        errors.append("date window ends before it starts")
    if (
        timing["kind"] == "window"
        and "starts_at" in timing
        and _dt(timing["ends_at"]) < _dt(timing["starts_at"])
    ):
        errors.append("exact window ends before it starts")

    creation = value["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and value["status"] == "active"
    ):
        errors.append(
            "paper/import activation requires accepted review history"
        )

    owner = value["owner"]
    if value["work_kind"] == "event" and value["status"] == "active":
        person = owner["person"]
        kind = person["kind"]
        if kind not in EVENT_OWNER_ELIGIBLE_KINDS:
            errors.append("Event Follow-Up owner is not operational")
        elif kind == "actor" and operational_actor_ids is not None:
            actor_id = person["actor_ref"]["actor_id"]
            if actor_id not in operational_actor_ids:
                errors.append("Actor owner is not operationally eligible")

    if (
        value["work_kind"] == "support_process"
        and value["status"] == "active"
        and resolved_support_participants is not None
    ):
        participant_id = owner["participant_ref"]["record_id"]
        participant = resolved_support_participants.get(participant_id)
        if participant is None:
            errors.append("Support Process owner does not resolve")
        else:
            if participant.get("status") != "active":
                errors.append("Support Process owner is not active")
            if participant.get("class_id") != value["class_id"]:
                errors.append("Support Process owner class mismatch")
            if participant.get("work_id") != value["work_id"]:
                errors.append("Support Process owner work mismatch")
            contexts = {
                item["kind"] for item in participant.get("contexts", [])
            }
            if not (contexts & OPERATIONAL_SUPPORT_CONTEXTS):
                errors.append(
                    "Support Process owner lacks operational context"
                )

    related = value.get("related_records", [])
    seen: set[tuple[str, str, str, str, str, str]] = set()
    current_work = _work_identity(value)
    for item in related:
        ref = item["record_ref"]
        identity = _ref_identity(ref) + (item["role"],)
        if identity in seen:
            errors.append("related record relation repeated")
        seen.add(identity)

        record = ref["record_ref"]
        if (
            record["record_kind"] == "follow_up"
            and record["record_id"] == value["follow_up_id"]
            and _ref_work_identity(ref) == current_work
        ):
            errors.append("Follow-Up relation self-reference")

        if (
            item["role"] == "produced"
            and _ref_work_identity(ref) != current_work
        ):
            errors.append("produced record must share Follow-Up work root")

        if (
            item["role"] == "follow_up_to"
            and record["record_kind"] != "follow_up"
        ):
            errors.append("follow_up_to must reference Follow-Up")

    supersedes = value.get("supersedes", [])
    if supersedes:
        identities = [
            _ref_identity(item["work_record_ref"])
            for item in supersedes
        ]
        reasons = [item["reason"] for item in supersedes]
        if len(identities) != len(set(identities)):
            errors.append("predecessor Follow-Up identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        current_id = value["follow_up_id"]
        for item in supersedes:
            ref = item["work_record_ref"]
            predecessor_work = _ref_work_identity(ref)
            predecessor_id = ref["record_ref"]["record_id"]
            reason = item["reason"]
            same_work = predecessor_work == current_work
            same_id = predecessor_id == current_id

            if same_work and same_id:
                errors.append("Follow-Up replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append(
                        "work-root correction requires different work"
                    )
                if not same_id:
                    errors.append(
                        "work-root correction must preserve Follow-Up ID"
                    )
            elif reason not in {"contract_migrated"} and not same_work:
                errors.append(
                    "ordinary Follow-Up correction cannot cross work roots"
                )

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two predecessors"
                    )
            elif len(set(identities)) != 1:
                errors.append(
                    "non-consolidation correction is one-to-one"
                )

    return errors


def _valid_support_owner_resolution() -> dict[str, dict[str, Any]]:
    return {
        "spp_coordinator": {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "participant_id": "spp_coordinator",
            "status": "active",
            "contexts": [{"kind": "coordinator"}],
        }
    }


def _non_operational_support_owner_resolution() -> dict[str, dict[str, Any]]:
    return {
        "spp_coordinator": {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "participant_id": "spp_coordinator",
            "status": "active",
            "contexts": [{"kind": "family_or_support_person"}],
        }
    }


class Issue19FollowUpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "follow_up",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def test_manifest_and_catalog(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 19)
        self.assertEqual(self.manifest["contract"], "follow_up")
        self.assertEqual(self.manifest["version"], "1")
        expected = {
            "schema_id": (
                "https://paper-data-suite.github.io/pds-portia/"
                + SCHEMA_PATH
            ),
            "path": SCHEMA_PATH,
        }
        self.assertEqual(
            self.catalog["contracts"]["follow_up"]["1"],
            expected,
        )

    def test_valid_fixtures_pass(self) -> None:
        support_resolution = _valid_support_owner_resolution()
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    follow_up_application_errors(
                        value,
                        resolved_support_participants=support_resolution,
                    ),
                    [],
                )

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "invalid" / filename)
                self.assertTrue(
                    list(self.validator.iter_errors(value)),
                    f"{filename} unexpectedly passed structural validation",
                )

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        valid_support = _valid_support_owner_resolution()
        bad_support = _non_operational_support_owner_resolution()
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "application-invalid" / filename
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                support_resolution = (
                    bad_support
                    if filename
                    == "support-owner-without-operational-context.json"
                    else valid_support
                )
                self.assertTrue(
                    follow_up_application_errors(
                        value,
                        resolved_support_participants=support_resolution,
                    )
                )

    def test_owner_branch_is_conditioned_by_work_kind(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        serialized = json_text = str(schema)
        self.assertIn("represented_human", json_text)
        self.assertIn("support_process_participant", json_text)
        self.assertIn("portia-event-id.schema.json", serialized)
        self.assertIn("portia-support-process-id.schema.json", serialized)

    def test_purpose_vocabulary_is_closed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        purposes = set(schema["$defs"]["purpose"]["properties"]["kind"]["enum"])
        self.assertEqual(
            purposes,
            {
                "student_check_in",
                "family_or_support_person_check_in",
                "affected_person_check_in",
                "event_review",
                "response_review",
                "support_process_review",
                "goal_review",
                "implementation_review",
                "fidelity_review",
                "reentry_check",
                "repair_check",
                "coordination",
                "other",
            },
        )

    def test_planned_timing_and_completion_are_separate(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        timing = schema["$defs"]["plannedTiming"]["oneOf"]
        self.assertEqual(len(timing), 4)
        self.assertIn("completed_at", schema["properties"])
        self.assertNotIn(
            "overdue",
            schema["properties"],
        )
        self.assertNotIn(
            "reminder_fired",
            schema["properties"],
        )

    def test_disposition_is_workflow_only(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        disposition = schema["$defs"]["disposition"]
        serialized = str(disposition).lower()
        self.assertIn("next workflow action", serialized)
        self.assertIn("not outcome", serialized)
        for forbidden in (
            "effective",
            "ineffective",
            "resolved",
            "successful",
        ):
            self.assertNotIn(
                forbidden,
                disposition["properties"]["kind"]["enum"],
            )

    def test_related_record_roles_are_exact_and_closed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        related = schema["$defs"]["relatedRecord"]
        self.assertEqual(
            set(related["properties"]["role"]["enum"]),
            {"context", "reviewed", "produced", "follow_up_to"},
        )
        self.assertEqual(
            related["properties"]["record_ref"]["$ref"],
            "https://paper-data-suite.github.io/pds-portia/"
            "schemas/v1/references/exact-portia-work-record-ref.schema.json",
        )

    def test_lifecycle_and_workflow_are_independent(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            {"proposed", "active", "invalidated", "superseded"},
        )
        self.assertEqual(
            set(schema["properties"]["workflow_state"]["enum"]),
            {
                "scheduled",
                "in_progress",
                "completed",
                "cancelled",
                "unable_to_complete",
            },
        )

    def test_supersession_reasons_match_adr(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        reasons = set(
            schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]
        )
        self.assertEqual(
            reasons,
            {
                "owner_corrected",
                "purpose_corrected",
                "target_corrected",
                "timing_corrected",
                "completion_corrected",
                "related_record_corrected",
                "duplicate_consolidated",
                "work_root_corrected",
                "contract_migrated",
                "other",
            },
        )

    def test_follow_up_does_not_absorb_outcome_or_evidence_payload(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        for forbidden in (
            "outcome",
            "effectiveness",
            "goal_status",
            "causal_effect",
            "remorse",
            "forgiveness",
            "compliance",
            "risk_score",
            "grade",
            "observation_measurement",
            "account_content",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_current_use_event_owner_restriction_is_application_level(self) -> None:
        roster = load_json(
            FIXTURE_ROOT
            / "application-invalid"
            / "active-event-roster-student-owner.json"
        )
        self.assertFalse(list(self.validator.iter_errors(roster)))
        self.assertIn(
            "Event Follow-Up owner is not operational",
            follow_up_application_errors(roster),
        )


if __name__ == "__main__":
    unittest.main()
