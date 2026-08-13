from __future__ import annotations

from datetime import datetime
import json
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
    / "repair"
)
SCHEMA_PATH = "schemas/v1/repairs/repair.schema.json"

EVENT_FACILITATOR_ELIGIBLE_KINDS = {"local_operator", "actor"}
SUPPORT_FACILITATOR_CONTEXTS = {"provider_or_collaborator", "coordinator"}


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _work_identity(value: dict[str, Any]) -> tuple[str, str, str]:
    return value["class_id"], value["work_kind"], value["work_id"]


def _ref_work_identity(ref: dict[str, Any]) -> tuple[str, str, str]:
    work = ref["work_ref"]
    return work["class_id"], work["work_kind"], work["work_id"]


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


def repair_application_errors(
    value: dict[str, Any],
    *,
    resolved_support_participants: dict[str, dict[str, Any]] | None = None,
    operational_actor_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []

    if _dt(value["updated_at"]) < _dt(value["created_at"]):
        errors.append("updated_at precedes created_at")

    creation = value["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and value["status"] == "active"
    ):
        errors.append("paper/import activation requires accepted review history")

    facilitator = value["facilitator"]
    if value["work_kind"] == "event" and value["status"] == "active":
        person = facilitator["person"]
        kind = person["kind"]
        if kind not in EVENT_FACILITATOR_ELIGIBLE_KINDS:
            errors.append("Event Repair facilitator is not operational")
        elif kind == "actor" and operational_actor_ids is not None:
            actor_id = person["actor_ref"]["actor_id"]
            if actor_id not in operational_actor_ids:
                errors.append("Actor facilitator is not operationally eligible")

    if (
        value["work_kind"] == "support_process"
        and value["status"] == "active"
        and resolved_support_participants is not None
    ):
        facilitator_id = facilitator["participant_ref"]["record_id"]
        facilitator_record = resolved_support_participants.get(facilitator_id)
        if facilitator_record is None:
            errors.append("Support Process facilitator does not resolve")
        else:
            if facilitator_record.get("status") != "active":
                errors.append("Support Process facilitator is not active")
            if facilitator_record.get("class_id") != value["class_id"]:
                errors.append("Support Process facilitator class mismatch")
            if facilitator_record.get("work_id") != value["work_id"]:
                errors.append("Support Process facilitator work mismatch")
            contexts = {
                item["kind"] for item in facilitator_record.get("contexts", [])
            }
            if not (contexts & SUPPORT_FACILITATOR_CONTEXTS):
                errors.append("Support Process facilitator lacks operational context")

    participant_keys: list[str] = []
    for participant in value["participants"]:
        key = participant["participant_key"]
        participant_keys.append(key)

        if value["status"] == "active" and participant["participation_state"] == "unknown":
            errors.append("active Repair participation state may not be unknown")

        person_locator = participant["person"]
        if value["work_kind"] == "event":
            person = person_locator["person"]
            if value["status"] == "active" and person["kind"] == "unidentified_person":
                errors.append("active Event Repair participant may not be unidentified")
        elif resolved_support_participants is not None:
            participant_id = person_locator["participant_ref"]["record_id"]
            resolved = resolved_support_participants.get(participant_id)
            if resolved is None:
                errors.append("Support Process Repair participant does not resolve")
            else:
                if resolved.get("status") != "active":
                    errors.append("Support Process Repair participant is not active")
                if resolved.get("class_id") != value["class_id"]:
                    errors.append("Support Process Repair participant class mismatch")
                if resolved.get("work_id") != value["work_id"]:
                    errors.append("Support Process Repair participant work mismatch")
                if (
                    value["status"] == "active"
                    and resolved.get("person", {}).get("kind") == "unidentified_person"
                ):
                    errors.append("active Support Process Repair participant may not be unidentified")

    if len(participant_keys) != len(set(participant_keys)):
        errors.append("Repair participant_key repeated")
    participant_key_set = set(participant_keys)

    action_keys: list[str] = []
    for action in value.get("actions", []):
        action_keys.append(action["action_key"])
        for key in action["agreed_by"]:
            if key not in participant_key_set:
                errors.append("Repair action agreed_by key does not resolve")
        for key in action.get("responsible_participant_keys", []):
            if key not in participant_key_set:
                errors.append("Repair action responsible key does not resolve")
        if "agreed_at" in action and "completed_at" in action:
            if _dt(action["completed_at"]) < _dt(action["agreed_at"]):
                errors.append("Repair action completed before agreement")

    if len(action_keys) != len(set(action_keys)):
        errors.append("Repair action_key repeated")

    for context in value["context_refs"]:
        if context["kind"] == "work":
            work = context["work_ref"]
        else:
            work = context["record_ref"]["work_ref"]
            record = context["record_ref"]["record_ref"]
            if (
                record["record_kind"] == "repair"
                and record["record_id"] == value["repair_id"]
                and _ref_work_identity(context["record_ref"]) == _work_identity(value)
            ):
                errors.append("Repair context self-reference")
        if work["class_id"] != value["class_id"]:
            errors.append("Repair context class mismatch")

    supersedes = value.get("supersedes", [])
    if supersedes:
        identities = [_ref_identity(item["work_record_ref"]) for item in supersedes]
        reasons = [item["reason"] for item in supersedes]
        if len(identities) != len(set(identities)):
            errors.append("predecessor Repair identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        current_work = _work_identity(value)
        for item in supersedes:
            ref = item["work_record_ref"]
            predecessor_work = _ref_work_identity(ref)
            predecessor_id = ref["record_ref"]["record_id"]
            reason = item["reason"]
            same_work = predecessor_work == current_work
            same_id = predecessor_id == value["repair_id"]

            if same_work and same_id:
                errors.append("Repair replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append("work-root correction requires different work")
                if not same_id:
                    errors.append("work-root correction must preserve Repair ID")
            elif reason != "contract_migrated" and not same_work:
                errors.append("ordinary Repair correction cannot cross work roots")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append("duplicate consolidation needs two predecessors")
            elif len(set(identities)) != 1:
                errors.append("non-consolidation correction is one-to-one")

    return errors


def _support_participants(*, bad_facilitator: bool = False, other_process: bool = False) -> dict[str, dict[str, Any]]:
    facilitator_context = (
        [{"kind": "family_or_support_person"}]
        if bad_facilitator
        else [{"kind": "coordinator"}]
    )
    result = {
        "spp_facilitator": {
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "status": "active",
            "contexts": facilitator_context,
            "person": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
        },
        "spp_student": {
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "status": "active",
            "contexts": [{"kind": "supported_person"}],
            "person": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "eng10_p2_2026",
                    "student_id": "stu_001",
                },
                "display_snapshot": {"display_name": "Synthetic Student"},
            },
        },
        "spp_family": {
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "status": "active",
            "contexts": [{"kind": "family_or_support_person"}],
            "person": {
                "kind": "descriptive_person",
                "description_type": "family_member",
                "display_label": "Synthetic Family Support",
            },
        },
        "spp_peer": {
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "status": "active",
            "contexts": [{"kind": "other", "detail": "Synthetic peer context"}],
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic Peer",
            },
        },
        "spp_other_process": {
            "class_id": "eng10_p2_2026",
            "work_id": "sup_other" if other_process else "sup_alpha",
            "status": "active",
            "contexts": [{"kind": "supporter"}],
            "person": {
                "kind": "descriptive_person",
                "description_type": "community_member",
                "display_label": "Synthetic Other Participant",
            },
        },
    }
    return result


class Issue19RepairContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "repair",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def test_manifest_and_catalog(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 19)
        self.assertEqual(self.manifest["contract"], "repair")
        self.assertEqual(self.manifest["version"], "1")
        expected = {
            "schema_id": (
                "https://paper-data-suite.github.io/pds-portia/"
                + SCHEMA_PATH
            ),
            "path": SCHEMA_PATH,
        }
        self.assertEqual(self.catalog["contracts"]["repair"]["1"], expected)

    def test_valid_fixtures_pass(self) -> None:
        participants = _support_participants()
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    repair_application_errors(
                        value,
                        resolved_support_participants=participants,
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
                participants = _support_participants(
                    bad_facilitator=(
                        filename
                        == "support-facilitator-without-operational-context.json"
                    ),
                    other_process=(
                        filename == "support-participant-other-process.json"
                    ),
                )
                self.assertTrue(
                    repair_application_errors(
                        value,
                        resolved_support_participants=participants,
                    )
                )

    def test_no_public_repair_participant_or_action_contracts(self) -> None:
        self.assertNotIn("repair_participant", self.catalog["contracts"])
        self.assertNotIn("repair_action", self.catalog["contracts"])

    def test_participant_roles_are_neutral_and_closed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        roles = set(
            schema["$defs"]["participantRole"]["properties"]["kind"]["enum"]
        )
        self.assertEqual(
            roles,
            {
                "affected_person",
                "person_addressing_impact",
                "supporter",
                "community_participant",
                "other",
            },
        )
        for forbidden in (
            "offender",
            "victim",
            "guilty_party",
            "noncompliant_student",
        ):
            self.assertNotIn(forbidden, roles)

    def test_participation_states_are_neutral_and_closed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        states = set(
            schema["$defs"]["eventParticipantEntry"]["properties"][
                "participation_state"
            ]["enum"]
        )
        self.assertEqual(
            states,
            {
                "invited",
                "agreed_to_participate",
                "participated",
                "declined",
                "unavailable",
                "withdrew",
                "not_applicable",
                "unknown",
            },
        )
        self.assertTrue(
            states.isdisjoint(
                {"cooperative", "uncooperative", "compliant", "remorseful"}
            )
        )

    def test_action_types_and_completion_states_are_closed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        action = schema["$defs"]["agreedAction"]
        self.assertEqual(
            set(action["properties"]["action_type"]["enum"]),
            {
                "return_or_restore_property",
                "repair_or_replace_property",
                "restorative_action",
                "community_or_relationship_action",
                "follow_up_conversation",
                "other",
            },
        )
        self.assertEqual(
            set(action["properties"]["completion_state"]["enum"]),
            {
                "planned",
                "in_progress",
                "completed",
                "unable_to_complete",
                "withdrawn",
            },
        )

    def test_actions_are_embedded_and_nonfinancial(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        action = schema["$defs"]["agreedAction"]
        for forbidden in (
            "amount",
            "amount_due",
            "balance",
            "currency",
            "debt",
            "collection_status",
        ):
            self.assertNotIn(forbidden, action["properties"])

    def test_focus_and_context_do_not_form_truth_finding(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertIn("focus", schema["properties"])
        self.assertIn("context_refs", schema["properties"])
        for forbidden in (
            "official_narrative",
            "truth_finding",
            "allegation_proven",
            "admission",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_facilitator_is_separate_from_participants(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertIn("facilitator", schema["properties"])
        participant_defs = (
            schema["$defs"]["eventParticipantEntry"]["properties"],
            schema["$defs"]["supportProcessParticipantEntry"]["properties"],
        )
        for props in participant_defs:
            self.assertNotIn("facilitator", props)

    def test_workflow_completion_is_not_outcome_or_restoration(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            set(schema["properties"]["workflow_state"]["enum"]),
            {
                "planning",
                "active",
                "completed",
                "cancelled",
                "unable_to_complete",
            },
        )
        for forbidden in (
            "remorse",
            "forgiveness",
            "relationship_restored",
            "rehabilitated",
            "recurrence_prevented",
            "success",
            "effectiveness",
            "outcome",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_no_mandatory_apology_or_affected_person_participation(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertNotIn("apology_required", schema["properties"])
        required = set(schema["required"])
        self.assertNotIn("actions", required)
        participant = schema["$defs"]["eventParticipantEntry"]
        serialized = json.dumps(participant)
        self.assertNotIn("affected_person_required", serialized)

    def test_lifecycle_is_separate_from_workflow(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            {"proposed", "active", "invalidated", "superseded"},
        )
        self.assertNotIn("completed", schema["properties"]["status"]["enum"])

    def test_successor_reason_vocabulary_matches_adr(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        reasons = set(
            schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]
        )
        self.assertEqual(
            reasons,
            {
                "facilitator_corrected",
                "participant_corrected",
                "focus_corrected",
                "agreement_corrected",
                "completion_corrected",
                "duplicate_consolidated",
                "work_root_corrected",
                "contract_migrated",
                "other",
            },
        )

    def test_no_engagement_remorse_sincerity_or_compliance_scores(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        forbidden = {
            "engagement_score",
            "cooperation_score",
            "remorse_score",
            "sincerity_score",
            "compliance_score",
            "forgiveness_score",
        }
        self.assertTrue(forbidden.isdisjoint(schema["properties"]))
        self.assertTrue(
            forbidden.isdisjoint(
                schema["$defs"]["eventParticipantEntry"]["properties"]
            )
        )

    def test_current_use_facilitator_restriction_is_application_level(self) -> None:
        roster = load_json(
            FIXTURE_ROOT
            / "application-invalid"
            / "active-event-roster-student-facilitator.json"
        )
        self.assertFalse(list(self.validator.iter_errors(roster)))
        self.assertIn(
            "Event Repair facilitator is not operational",
            repair_application_errors(roster),
        )


if __name__ == "__main__":
    unittest.main()
