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
    / "issue-16"
    / "review"
)
REVIEW_SCHEMA_PATH = "schemas/v1/reviews/review.schema.json"

REVIEW_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

REVIEW_LIFECYCLE_REASONS = {
    "review_started",
    "recording_error",
    "wrong_reviewer",
    "wrong_target",
    "wrong_question",
    "invalid_provenance",
    "prohibited_payload",
    "corrected_by_successor",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
}

REVIEW_SUPERSESSION_REASONS = {
    "review_corrected",
    "review_reframed",
    "reviewer_corrected",
    "target_corrected",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
}

WORKFLOW_ALLOWED = {
    "open": {"open", "in_review", "awaiting_information", "completed", "cancelled"},
    "in_review": {"in_review", "awaiting_information", "completed", "cancelled"},
    "awaiting_information": {"awaiting_information", "in_review", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _work_record_identity(ref: dict[str, Any]) -> tuple[str, str, str, str]:
    work = ref["work_ref"]
    record = ref["record_ref"]
    return (
        work["class_id"],
        work["work_id"],
        record["record_id"],
        record["contract_version"],
    )


def _subject_logical_identity(ref: dict[str, Any]) -> tuple[str, str, str, str]:
    work = ref["work_ref"]
    record = ref["record_ref"]
    return (
        work["class_id"],
        work["work_id"],
        record["record_kind"],
        record["record_id"],
    )


def _module_ref_mismatch(value: dict[str, Any]) -> bool:
    if value.get("kind") != "module_record":
        return False
    ref = value["module_work_record_ref"]
    return ref["work_ref"]["module_id"] != ref["record_ref"]["module_id"]


def application_errors(review: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if _parse(review["updated_at"]) < _parse(review["created_at"]):
        errors.append("updated_at precedes created_at")

    creation = review["creation_source"]
    if creation["type"] in {"paper_capture", "import"} and review["status"] != "proposed":
        errors.append("paper/import activation requires accepted review history")

    for evidence in review["evidence_considered"]:
        if _module_ref_mismatch(evidence):
            errors.append("sibling-module evidence has mismatched module IDs")

    subjects = review.get("review_subjects", [])
    subject_ids = [_subject_logical_identity(item) for item in subjects]
    if len(subject_ids) != len(set(subject_ids)):
        errors.append("review subject logical identity repeated")

    for item in subjects:
        work = item["work_ref"]
        record = item["record_ref"]
        if work["class_id"] != review["class_id"] or work["work_id"] != review["work_id"]:
            errors.append("review subject belongs to a different Event")
        if record["record_kind"] == "review" and record["record_id"] == review["review_id"]:
            errors.append("Review cannot name itself as subject")

    if (
        review["trigger"]["kind"] == "reconsideration"
        or review["question"]["kind"] == "reconsideration"
    ) and not subjects:
        errors.append("reconsideration requires an exact review subject")

    supersedes = review.get("supersedes", [])
    if supersedes:
        identities = [_work_record_identity(item["work_record_ref"]) for item in supersedes]
        reasons = [item["reason"] for item in supersedes]
        if len(identities) != len(set(identities)):
            errors.append("predecessor Review identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        for item in supersedes:
            work = item["work_record_ref"]["work_ref"]
            record = item["work_record_ref"]["record_ref"]
            same_work = work["class_id"] == review["class_id"] and work["work_id"] == review["work_id"]
            same_id = record["record_id"] == review["review_id"]
            reason = item["reason"]

            if same_work and same_id and reason != "contract_migrated":
                errors.append("Review replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append("work-root correction requires different work")
                if not same_id:
                    errors.append("work-root correction must preserve Review ID")
            elif reason != "contract_migrated" and not same_work:
                errors.append("ordinary Review correction cannot cross work roots")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append("duplicate consolidation needs two predecessors")
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append("non-consolidation correction is one-to-one")

    return errors


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def workflow_errors(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if previous["status"] != "active" or current["status"] != "active":
        errors.append("workflow scenario must keep Review lifecycle active")

    if previous["review_id"] != current["review_id"]:
        errors.append("workflow update changed Review identity")

    before = previous["review_state"]
    after = current["review_state"]
    if after not in WORKFLOW_ALLOWED[before]:
        errors.append("illegal Review workflow transition")

    if _parse(current["updated_at"]) <= _parse(previous["updated_at"]):
        errors.append("workflow update must advance updated_at")

    fixed_fields = (
        "schema_version",
        "record_type",
        "module_id",
        "class_id",
        "work_id",
        "review_id",
        "trigger",
        "question",
        "target",
        "reviewer",
        "requested_by",
        "review_subjects",
        "creation_source",
        "created_at",
        "created_by",
    )
    for field in fixed_fields:
        if previous.get(field) != current.get(field):
            errors.append(f"active substantive field changed: {field}")

    previous_evidence = {_canon(item) for item in previous["evidence_considered"]}
    current_evidence = {_canon(item) for item in current["evidence_considered"]}
    if not previous_evidence.issubset(current_evidence):
        errors.append("previously considered evidence was removed or rewritten")

    return errors


class Issue16ReviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for("review", "1", catalog=cls.catalog, store=cls.store)
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")
        cls.workflow_manifest = load_json(FIXTURE_ROOT / "workflow" / "manifest.json")

    def test_manifest_has_expected_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 16)
        self.assertEqual(self.manifest["contract"], "review")
        self.assertEqual(self.manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))
                self.assertEqual(application_errors(value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "invalid" / filename)
                self.assertTrue(list(self.validator.iter_errors(value)))

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "application-invalid" / filename)
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(structural, "\n".join(error.message for error in structural))
                self.assertTrue(application_errors(value))

    def test_guarded_workflow_valid_scenarios(self) -> None:
        for filename in self.workflow_manifest["valid"]:
            with self.subTest(filename=filename):
                scenario = load_json(FIXTURE_ROOT / "workflow" / "valid" / filename)
                for key in ("previous", "current"):
                    structural = list(self.validator.iter_errors(scenario[key]))
                    self.assertFalse(structural, "\n".join(error.message for error in structural))
                self.assertEqual(workflow_errors(scenario["previous"], scenario["current"]), [])

    def test_guarded_workflow_application_invalid_scenarios(self) -> None:
        for filename in self.workflow_manifest["application_invalid"]:
            with self.subTest(filename=filename):
                scenario = load_json(FIXTURE_ROOT / "workflow" / "application-invalid" / filename)
                for key in ("previous", "current"):
                    structural = list(self.validator.iter_errors(scenario[key]))
                    self.assertFalse(structural, "\n".join(error.message for error in structural))
                self.assertTrue(workflow_errors(scenario["previous"], scenario["current"]))

    def test_review_is_cataloged_at_immutable_path(self) -> None:
        entry = self.catalog["contracts"]["review"]["1"]
        self.assertEqual(entry["path"], REVIEW_SCHEMA_PATH)
        self.assertEqual(entry["schema_id"], "https://paper-data-suite.github.io/pds-portia/" + REVIEW_SCHEMA_PATH)
        schema = load_json(REPO_ROOT / REVIEW_SCHEMA_PATH)
        self.assertEqual(schema["$id"], entry["schema_id"])
        self.assertNotIn("/latest/", entry["schema_id"])
        self.assertNotIn("/current/", entry["schema_id"])

    def test_review_envelope_is_closed_and_event_local(self) -> None:
        schema = load_json(REPO_ROOT / REVIEW_SCHEMA_PATH)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), {
            "schema_version", "record_type", "module_id", "class_id", "work_id", "review_id",
            "status", "review_state", "trigger", "question", "target", "reviewer",
            "evidence_considered", "creation_source", "created_at", "created_by", "updated_at", "updated_by",
        })
        self.assertEqual(schema["properties"]["record_type"]["const"], "review")
        self.assertEqual(schema["properties"]["module_id"]["const"], "portia")
        for forbidden in (
            "finding", "classification", "hypothesis", "determination", "outcome",
            "credibility", "credibility_score", "severity", "risk_score", "policy_violation",
            "student_label", "urgency", "automatic_finding",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_review_status_workflow_trigger_and_question_vocabularies_are_closed(self) -> None:
        schema = load_json(REPO_ROOT / REVIEW_SCHEMA_PATH)
        self.assertEqual(set(schema["properties"]["status"]["enum"]), {"proposed", "active", "invalidated", "superseded"})
        self.assertEqual(set(schema["properties"]["review_state"]["enum"]), {"open", "in_review", "awaiting_information", "completed", "cancelled"})
        self.assertEqual(set(schema["$defs"]["reviewTrigger"]["properties"]["kind"]["enum"]), {"concern", "referral", "routine_review", "reconsideration", "support_related", "other"})
        self.assertEqual(set(schema["$defs"]["reviewQuestion"]["properties"]["kind"]["enum"]), {"evidence_review", "classification_review", "hypothesis_review", "determination_review", "reconsideration", "other"})

    def test_review_preserves_human_and_evidence_boundaries(self) -> None:
        schema = load_json(REPO_ROOT / REVIEW_SCHEMA_PATH)
        self.assertEqual(schema["properties"]["reviewer"]["$ref"], "https://paper-data-suite.github.io/pds-portia/schemas/v1/attribution/represented-human-attribution.schema.json")
        self.assertEqual(schema["properties"]["requested_by"]["$ref"], "https://paper-data-suite.github.io/pds-portia/schemas/v1/attribution/represented-human-attribution.schema.json")
        self.assertEqual(schema["properties"]["evidence_considered"]["items"]["$ref"], "https://paper-data-suite.github.io/pds-portia/schemas/v1/references/judgment-evidence-ref.schema.json")
        self.assertNotIn("source_artifacts", schema["properties"])

    def test_review_subjects_are_exact_judgment_records(self) -> None:
        schema = load_json(REPO_ROOT / REVIEW_SCHEMA_PATH)
        subject = schema["$defs"]["reviewSubjectRef"]
        text = json.dumps(subject, sort_keys=True)
        for record_kind in ("review", "classification", "hypothesis", "determination"):
            self.assertIn(f'"const": "{record_kind}"', text)
        self.assertNotIn('"const": "account"', text)
        self.assertNotIn('"const": "observation"', text)

    def test_review_lifecycle_and_supersession_vocabularies_match_adr(self) -> None:
        self.assertEqual(REVIEW_LIFECYCLE, {
            "proposed": {"active", "invalidated", "superseded"},
            "active": {"invalidated", "superseded"},
            "invalidated": {"superseded"},
            "superseded": set(),
        })
        self.assertEqual(REVIEW_LIFECYCLE_REASONS, {
            "review_started", "recording_error", "wrong_reviewer", "wrong_target", "wrong_question",
            "invalid_provenance", "prohibited_payload", "corrected_by_successor", "duplicate_consolidated",
            "work_root_corrected", "contract_migrated", "other",
        })
        schema = load_json(REPO_ROOT / REVIEW_SCHEMA_PATH)
        self.assertEqual(set(schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]), REVIEW_SUPERSESSION_REASONS)

    def test_review_v1_has_no_amendment_surface(self) -> None:
        schema = load_json(REPO_ROOT / REVIEW_SCHEMA_PATH)
        for forbidden in ("amendment", "amendments", "amendable_paths", "nonmaterial_metadata"):
            self.assertNotIn(forbidden, schema["properties"])
        invariants = set(schema["x-portia-application-invariants"])
        self.assertIn("portia.review.amendment_prohibited_v1", invariants)

    def test_review_does_not_publish_parallel_shared_contracts(self) -> None:
        contracts = self.catalog["contracts"]
        for forbidden in (
            "review_lifecycle_transition",
            "review_lifecycle_history_correction",
            "review_amendment",
            "review_dependency",
            "review_record_migration",
            "review_operation_journal",
            "review_quarantine",
        ):
            self.assertNotIn(forbidden, contracts)


if __name__ == "__main__":
    unittest.main()
