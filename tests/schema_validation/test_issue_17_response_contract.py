from __future__ import annotations

from datetime import datetime
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
    / "issue-17"
    / "response"
)
RESPONSE_SCHEMA_PATH = "schemas/v1/responses/response.schema.json"

RESPONSE_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

RESPONSE_SUPERSESSION_REASONS = {
    "provider_corrected",
    "target_corrected",
    "action_corrected",
    "timing_corrected",
    "decision_context_corrected",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
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


def _same_event(response: dict[str, Any], ref: dict[str, Any]) -> bool:
    work = ref["work_ref"]
    return (
        work["class_id"] == response["class_id"]
        and work["work_id"] == response["work_id"]
        and work["work_kind"] == "event"
    )


def application_errors(response: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    created_at = _parse(response["created_at"])
    updated_at = _parse(response["updated_at"])
    started_at = _parse(response["started_at"])
    ended_at = _parse(response["ended_at"]) if "ended_at" in response else None

    if updated_at < created_at:
        errors.append("updated_at precedes created_at")
    if started_at > updated_at:
        errors.append("Response starts after the recorded revision")
    if ended_at is not None and ended_at < started_at:
        errors.append("Response ended_at precedes started_at")
    if ended_at is not None and ended_at > updated_at:
        errors.append("Response ended_at follows the recorded revision")
    if response["execution_state"] == "in_progress" and ended_at is not None:
        errors.append("in-progress Response cannot already have ended_at")

    creation = response["creation_source"]
    if creation["type"] in {"paper_capture", "import"} and response["status"] != "proposed":
        errors.append("paper/import activation requires accepted review history")

    if (
        response["execution_state"] == "unknown"
        and creation["type"] not in {"paper_capture", "import"}
    ):
        errors.append("unknown execution state is historical/import-only")

    review_ref = response.get("review_ref")
    if review_ref is not None and not _same_event(response, review_ref):
        errors.append("Review context belongs to a different Event")

    determination_ref = response.get("determination_ref")
    if determination_ref is not None and not _same_event(response, determination_ref):
        errors.append("Determination context belongs to a different Event")

    action = response["action"]
    if (
        action["family"] == "consequence"
        and action["consequence_context"] == "recorded_institutional"
        and determination_ref is None
    ):
        errors.append("recorded institutional consequence requires Determination context")

    provider = response["provider"]
    if (
        action["family"] == "consequence"
        and action["consequence_context"] == "teacher_local"
        and provider["kind"] in {"roster_student", "unidentified_person"}
    ):
        errors.append("teacher-local consequence requires eligible human provider")

    supersedes = response.get("supersedes", [])
    if supersedes:
        identities = [
            _work_record_identity(item["work_record_ref"])
            for item in supersedes
        ]
        reasons = [item["reason"] for item in supersedes]

        if len(identities) != len(set(identities)):
            errors.append("predecessor Response identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        for item in supersedes:
            ref = item["work_record_ref"]
            work = ref["work_ref"]
            record = ref["record_ref"]
            same_work = (
                work["class_id"] == response["class_id"]
                and work["work_id"] == response["work_id"]
            )
            same_id = record["record_id"] == response["response_id"]
            reason = item["reason"]

            if same_work and same_id and reason != "contract_migrated":
                errors.append("Response replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append("work-root correction requires different work")
                if not same_id:
                    errors.append("work-root correction must preserve Response ID")
            elif reason != "contract_migrated" and not same_work:
                errors.append("ordinary Response correction cannot cross work roots")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append("duplicate consolidation needs two predecessors")
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append("non-consolidation correction is one-to-one")

    return errors


class Issue17ResponseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "response",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")
        cls.schema = load_json(REPO_ROOT / RESPONSE_SCHEMA_PATH)

    def test_manifest_has_expected_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 17)
        self.assertEqual(self.manifest["contract"], "response")
        self.assertEqual(self.manifest["version"], "1")
        self.assertEqual(len(self.manifest["valid"]), 10)
        self.assertEqual(len(self.manifest["invalid"]), 13)
        self.assertEqual(len(self.manifest["application_invalid"]), 19)

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                self.assertEqual(application_errors(value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "invalid" / filename)
                self.assertTrue(list(self.validator.iter_errors(value)))

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "application-invalid" / filename
                )
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def test_application_invalid_fixtures_fail_application_rules(self) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "application-invalid" / filename
                )
                self.assertTrue(application_errors(value))

    def test_schema_keeps_action_judgment_and_outcome_boundaries(self) -> None:
        properties = self.schema["properties"]
        self.assertTrue(
            properties["work_id"]["$ref"].endswith(
                "/portia-event-id.schema.json"
            )
        )
        self.assertTrue(
            properties["target"]["$ref"].endswith(
                "/portia-target-ref.schema.json"
            )
        )
        self.assertTrue(
            properties["provider"]["$ref"].endswith(
                "/represented-human-attribution.schema.json"
            )
        )
        for prohibited in (
            "severity",
            "risk",
            "effectiveness",
            "outcome",
            "support",
            "credibility",
            "punishment_recommendation",
        ):
            self.assertNotIn(prohibited, properties)

    def test_lifecycle_and_supersession_vocabularies_are_closed(self) -> None:
        self.assertEqual(
            set(self.schema["properties"]["status"]["enum"]),
            set(RESPONSE_LIFECYCLE),
        )
        reasons = set(
            self.schema["$defs"]["supersessionEntry"]
            ["properties"]["reason"]["enum"]
        )
        self.assertEqual(reasons, RESPONSE_SUPERSESSION_REASONS)

    def test_application_invariants_declare_issue_17_boundaries(self) -> None:
        invariants = set(self.schema["x-portia-application-invariants"])
        required = {
            "portia.response.canonical_storage_scope",
            "portia.response.target_same_event",
            "portia.response.provider_role_eligibility",
            "portia.response.determination_same_event",
            "portia.response.recorded_institutional_determination_required",
            "portia.response.amendment_prohibited_v1",
            "portia.response.no_silent_successor_following",
            "portia.response.no_automatic_judgment",
            "portia.response.no_effectiveness_inference",
            "portia.response.restricted_workflow_boundary",
        }
        self.assertTrue(required.issubset(invariants))


if __name__ == "__main__":
    unittest.main()
