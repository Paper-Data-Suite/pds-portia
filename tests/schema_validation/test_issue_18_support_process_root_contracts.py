from __future__ import annotations

from datetime import date, datetime
import json
import unittest
from typing import Any

try:
    from .schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
    from .test_issue_17_communication_contract import (
        application_errors as communication_application_errors,
    )
except ImportError:
    from schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
    from test_issue_17_communication_contract import (
        application_errors as communication_application_errors,
    )


PROCESS_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "support-process"
)
PARTICIPANT_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "support-process-participant"
)
CROSS_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "cross-record"
)
PROCESS_SCHEMA_PATH = "schemas/v1/support-processes/support-process.schema.json"
PARTICIPANT_SCHEMA_PATH = (
    "schemas/v1/support-processes/support-process-participant.schema.json"
)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _school_year_is_consecutive(value: str) -> bool:
    start, end = value.split("-", 1)
    return int(end) == int(start) + 1


def _work_identity(ref: dict[str, Any]) -> tuple[str, str]:
    return (ref["class_id"], ref["work_id"])


def _same_work_ref(
    process: dict[str, Any],
    ref: dict[str, Any],
) -> bool:
    return (
        process["class_id"] == ref["class_id"]
        and process["work_id"] == ref["work_id"]
    )


def process_application_errors(process: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not _school_year_is_consecutive(process["school_year"]):
        errors.append("school_year is not a consecutive academic-year range")

    if _dt(process["updated_at"]) < _dt(process["created_at"]):
        errors.append("updated_at precedes created_at")

    start = (
        date.fromisoformat(process["planned_start_date"])
        if "planned_start_date" in process
        else None
    )
    end = (
        date.fromisoformat(process["planned_end_date"])
        if "planned_end_date" in process
        else None
    )
    review = (
        date.fromisoformat(process["review_on"])
        if "review_on" in process
        else None
    )
    if start is not None and end is not None and end < start:
        errors.append("planned_end_date precedes planned_start_date")
    if start is not None and review is not None and review < start:
        errors.append("review_on precedes planned_start_date")

    creation = process["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and process["status"] != "proposed"
    ):
        errors.append("paper/import activation requires accepted review history")
    if (
        process["initiation"]["kind"] == "imported_history"
        and creation["type"] != "import"
    ):
        errors.append("imported_history initiation requires import provenance")

    continuation = process.get("continues_from")
    if continuation is not None and _same_work_ref(process, continuation):
        errors.append("continues_from must identify a distinct Support Process")

    supersedes = process.get("supersedes", [])
    if supersedes:
        refs = [entry["work_ref"] for entry in supersedes]
        reasons = [entry["reason"] for entry in supersedes]
        identities = [_work_identity(ref) for ref in refs]

        if continuation is not None:
            if _work_identity(continuation) in identities:
                errors.append(
                    "continues_from must not also be a supersession predecessor"
                )

        if len(set(identities)) != len(identities):
            errors.append("Support Process predecessor identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed Support Process supersession reasons")

        for ref in refs:
            if _same_work_ref(process, ref):
                errors.append("Support Process cannot supersede itself")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two Support Process predecessors"
                    )
            elif reason == "work_root_corrected":
                if len(set(identities)) != 1:
                    errors.append("work-root correction is one-to-one")
                else:
                    ref = refs[0]
                    if ref["class_id"] == process["class_id"]:
                        errors.append(
                            "work-root correction requires a different owning class"
                        )
                    if ref["work_id"] != process["work_id"]:
                        errors.append(
                            "work-root correction must preserve Support Process work_id"
                        )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append(
                        "ordinary Support Process correction is one-to-one"
                    )
                else:
                    ref = refs[0]
                    if ref["class_id"] != process["class_id"]:
                        errors.append(
                            "ordinary Support Process correction cannot change owning class"
                        )

    return errors


def _person_identity(person: dict[str, Any]) -> tuple[Any, ...]:
    kind = person["kind"]
    if kind == "roster_student":
        ref = person["roster_student_ref"]
        return (kind, ref["class_id"], ref["student_id"])
    if kind == "actor":
        return (kind, person["actor_ref"]["actor_id"])
    if kind == "local_operator":
        return (kind, person["display_label"])
    if kind == "descriptive_person":
        return (kind, person["description_type"], person["display_label"])
    return (kind, person["identity_status"], person.get("display_label"))


def _participant_ref_identity(
    ref: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        ref["work_ref"]["class_id"],
        ref["work_ref"]["work_id"],
        ref["record_ref"]["record_id"],
    )


def participant_application_errors(
    participant: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if _dt(participant["updated_at"]) < _dt(participant["created_at"]):
        errors.append("updated_at precedes created_at")

    creation = participant["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and participant["status"] != "proposed"
    ):
        errors.append("paper/import activation requires accepted review history")

    if (
        participant["status"] == "active"
        and participant["person"]["kind"] == "unidentified_person"
    ):
        errors.append(
            "active current-use Support Process Participant must be resolved"
        )

    supersedes = participant.get("supersedes", [])
    if supersedes:
        refs = [entry["work_record_ref"] for entry in supersedes]
        reasons = [entry["reason"] for entry in supersedes]
        identities = [_participant_ref_identity(ref) for ref in refs]

        if len(set(identities)) != len(identities):
            errors.append("Participant predecessor identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed Participant supersession reasons")

        current_identity = (
            participant["class_id"],
            participant["work_id"],
            participant["participant_id"],
        )
        for identity in identities:
            if identity == current_identity:
                errors.append(
                    "Support Process Participant cannot supersede itself"
                )

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two Participant predecessors"
                    )
            elif reason == "work_root_corrected":
                if len(set(identities)) != 1:
                    errors.append("Participant work-root correction is one-to-one")
                else:
                    work = refs[0]["work_ref"]
                    record = refs[0]["record_ref"]
                    if (
                        work["class_id"] == participant["class_id"]
                        and work["work_id"] == participant["work_id"]
                    ):
                        errors.append(
                            "work-root correction requires a different Support Process root"
                        )
                    if record["record_id"] != participant["participant_id"]:
                        errors.append(
                            "work-root correction must preserve Participant ID"
                        )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append("ordinary Participant correction is one-to-one")
                else:
                    work = refs[0]["work_ref"]
                    if (
                        work["class_id"] != participant["class_id"]
                        or work["work_id"] != participant["work_id"]
                    ):
                        errors.append(
                            "ordinary Participant correction cannot cross Support Process roots"
                        )

    return errors


def graph_application_errors(
    process: dict[str, Any],
    participants: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []

    for participant in participants:
        if (
            participant["class_id"] != process["class_id"]
            or participant["work_id"] != process["work_id"]
        ):
            errors.append("Participant owner does not match Support Process")

    active = [item for item in participants if item["status"] == "active"]
    identities = [_person_identity(item["person"]) for item in active]
    if len(identities) != len(set(identities)):
        errors.append("logical human identity repeated within Support Process")

    if (
        process["status"] == "active"
        and not any(
            any(
                context["kind"] == "supported_person"
                for context in participant["contexts"]
            )
            for participant in active
        )
    ):
        errors.append(
            "active Support Process requires an active supported_person Participant"
        )

    return errors


class Issue18SupportProcessRootContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.process_validator = validator_for(
            "support_process", "1",
            catalog=cls.catalog, store=cls.store,
        )
        cls.participant_validator = validator_for(
            "support_process_participant", "1",
            catalog=cls.catalog, store=cls.store,
        )
        cls.communication_validator = validator_for(
            "communication", "1",
            catalog=cls.catalog, store=cls.store,
        )
        cls.process_manifest = load_json(PROCESS_ROOT / "manifest.json")
        cls.participant_manifest = load_json(
            PARTICIPANT_ROOT / "manifest.json"
        )

    def test_catalog_entries_and_manifest_metadata(self) -> None:
        base = "https://paper-data-suite.github.io/pds-portia/"
        self.assertEqual(
            self.catalog["contracts"]["support_process"]["1"],
            {
                "schema_id": base + PROCESS_SCHEMA_PATH,
                "path": PROCESS_SCHEMA_PATH,
            },
        )
        self.assertEqual(
            self.catalog["contracts"]["support_process_participant"]["1"],
            {
                "schema_id": base + PARTICIPANT_SCHEMA_PATH,
                "path": PARTICIPANT_SCHEMA_PATH,
            },
        )
        self.assertEqual(self.process_manifest["issue"], 18)
        self.assertEqual(self.process_manifest["contract"], "support_process")
        self.assertEqual(len(self.process_manifest["valid"]), 10)
        self.assertEqual(len(self.process_manifest["invalid"]), 12)
        self.assertEqual(len(self.process_manifest["application_invalid"]), 16)
        self.assertEqual(self.participant_manifest["issue"], 18)
        self.assertEqual(
            self.participant_manifest["contract"],
            "support_process_participant",
        )
        self.assertEqual(len(self.participant_manifest["valid"]), 8)
        self.assertEqual(len(self.participant_manifest["invalid"]), 12)
        self.assertEqual(
            len(self.participant_manifest["application_invalid"]),
            11,
        )

    def test_support_process_valid_fixtures_pass(self) -> None:
        for filename in self.process_manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(PROCESS_ROOT / "valid" / filename)
                structural = list(
                    self.process_validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(process_application_errors(value), [])

    def test_support_process_structural_invalid_fixtures_fail(self) -> None:
        for filename in self.process_manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(PROCESS_ROOT / "invalid" / filename)
                self.assertTrue(
                    list(self.process_validator.iter_errors(value))
                )

    def test_support_process_application_invalid_fixtures_fail(self) -> None:
        for item in self.process_manifest["application_invalid"]:
            with self.subTest(filename=item["file"]):
                value = load_json(
                    PROCESS_ROOT / "application-invalid" / item["file"]
                )
                structural = list(
                    self.process_validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertIn(
                    item["expected_error"],
                    process_application_errors(value),
                )

    def test_participant_valid_fixtures_pass(self) -> None:
        for filename in self.participant_manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(PARTICIPANT_ROOT / "valid" / filename)
                structural = list(
                    self.participant_validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    participant_application_errors(value),
                    [],
                )

    def test_participant_structural_invalid_fixtures_fail(self) -> None:
        for filename in self.participant_manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(PARTICIPANT_ROOT / "invalid" / filename)
                self.assertTrue(
                    list(self.participant_validator.iter_errors(value))
                )

    def test_participant_application_invalid_fixtures_fail(self) -> None:
        for item in self.participant_manifest["application_invalid"]:
            with self.subTest(filename=item["file"]):
                value = load_json(
                    PARTICIPANT_ROOT / "application-invalid" / item["file"]
                )
                structural = list(
                    self.participant_validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertIn(
                    item["expected_error"],
                    participant_application_errors(value),
                )

    def test_support_process_root_stays_small_and_neutral(self) -> None:
        schema = load_json(REPO_ROOT / PROCESS_SCHEMA_PATH)
        properties = schema["properties"]
        for forbidden in (
            "participants", "needs", "goals", "supports", "interventions",
            "implementations", "fidelity", "outcomes", "diagnosis",
            "iep_status", "risk_score", "effectiveness",
        ):
            self.assertNotIn(forbidden, properties)
        self.assertEqual(
            set(properties["status"]["enum"]),
            {"proposed", "active", "invalidated", "superseded"},
        )
        self.assertEqual(
            set(properties["workflow_state"]["enum"]),
            {
                "planning", "active", "paused",
                "completed", "discontinued", "cancelled",
            },
        )

    def test_participant_context_does_not_claim_authority(self) -> None:
        schema = load_json(REPO_ROOT / PARTICIPANT_SCHEMA_PATH)
        text = json.dumps(schema).lower()
        self.assertIn("context_not_authority", text)
        self.assertIn("context_not_plan_assignment", text)
        self.assertNotIn("guardian_authority", text)
        self.assertNotIn("authorized_provider", text)
        self.assertNotIn("consent_granted", text)

    def test_graph_requires_supported_person_and_logical_uniqueness(self) -> None:
        bundle = load_json(
            CROSS_ROOT / "support-process-communication.json"
        )
        self.assertEqual(
            graph_application_errors(
                bundle["support_process"],
                bundle["participants"],
            ),
            [],
        )

        no_supported = [
            json.loads(json.dumps(item))
            for item in bundle["participants"]
        ]
        no_supported[0]["contexts"] = [{"kind": "observer"}]
        self.assertIn(
            "active Support Process requires an active supported_person Participant",
            graph_application_errors(
                bundle["support_process"],
                no_supported,
            ),
        )

        duplicate = [
            json.loads(json.dumps(bundle["participants"][0])),
            json.loads(json.dumps(bundle["participants"][0])),
        ]
        duplicate[1]["participant_id"] = "spp_duplicate_2"
        self.assertIn(
            "logical human identity repeated within Support Process",
            graph_application_errors(
                bundle["support_process"],
                duplicate,
            ),
        )

    def test_support_process_owned_communication_uses_owner_resolution(self) -> None:
        bundle = load_json(
            CROSS_ROOT / "support-process-communication.json"
        )
        communication = bundle["communication"]

        structural = list(
            self.communication_validator.iter_errors(communication)
        )
        self.assertFalse(
            structural,
            "\n".join(error.message for error in structural),
        )

        unresolved = communication_application_errors(communication)
        self.assertIn(
            "Support Process owner must resolve and be current-use eligible",
            unresolved,
        )

        resolved = communication_application_errors(
            communication,
            resolved_support_process_owners={
                (
                    bundle["support_process"]["class_id"],
                    bundle["support_process"]["work_id"],
                )
            },
        )
        self.assertEqual(resolved, [])

    def test_feature_branch_identifier_descriptions_are_clean(self) -> None:
        selected = {
            "portia-support-process-participant-id.schema.json",
            "portia-support-need-id.schema.json",
            "portia-support-goal-id.schema.json",
            "portia-support-id.schema.json",
            "portia-intervention-id.schema.json",
            "portia-implementation-id.schema.json",
            "portia-fidelity-id.schema.json",
        }
        root = REPO_ROOT / "schemas" / "v1" / "identifiers"
        for path in root.glob("portia-*.schema.json"):
            if path.name in selected:
                value = load_json(path)
                self.assertNotIn(
                    "Portia Portia",
                    value["description"],
                )


if __name__ == "__main__":
    unittest.main()
