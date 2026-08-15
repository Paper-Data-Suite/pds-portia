import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RETENTION_CLASSES = {
    "canonical_behavior_support",
    "source_evidence",
    "actor_identity",
    "actor_contact",
    "lifecycle_correction_disagreement",
    "paper_import_provenance",
    "operation_recovery_integrity",
    "derived_cache",
    "export_bytes",
    "export_provenance",
    "exceptional_removal_certificate",
}

EVALUATION_RESULTS = {
    "not_yet_eligible",
    "eligible_pending_authorization",
    "blocked",
    "unresolved",
    "authorized_for_module_action",
}

REQUEST_INTENTS = {
    "inspect_access",
    "export_copy",
    "amend_correct",
    "statement_of_disagreement",
    "restrict_withhold",
    "delete_destroy",
    "other",
}

SCENARIOS = {f"T{i:02d}" for i in range(1, 33)}


class Issue21RetentionRequestDocumentationTests(unittest.TestCase):
    def read(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    def test_retention_classes_are_complete_and_duration_free(self) -> None:
        text = self.read("docs/design/portia-retention-classes-and-policy-hooks.md")
        self.assertEqual(11, len(RETENTION_CLASSES))
        for value in sorted(RETENTION_CLASSES):
            self.assertIn(value, text)
        self.assertIn("retention class != retention duration", text)
        self.assertIn("These keys are deliberately", text)
        self.assertIn("non-duration-bearing", text)

    def test_retention_evaluation_separates_eligibility_authorization_and_blocks(self) -> None:
        text = self.read("docs/design/portia-retention-classes-and-policy-hooks.md")
        for value in sorted(EVALUATION_RESULTS):
            self.assertIn(value, text)
        self.assertIn("eligible_pending_authorization", text)
        self.assertIn("must never transform", text)
        self.assertIn("destructive execution", text)

    def test_no_retention_fields_are_added_to_domain_records(self) -> None:
        text = self.read("docs/design/portia-retention-classes-and-policy-hooks.md")
        self.assertIn('"retention_class"', text)
        self.assertIn('"retention_until"', text)
        self.assertIn('"delete_after"', text)
        self.assertIn('"legal_hold"', text)
        self.assertIn("Issue #21 rejects adding", text)

    def test_request_intents_are_explicit_but_do_not_grant_rights(self) -> None:
        text = self.read(
            "docs/design/portia-records-requests-holds-and-disposition-boundaries.md"
        )
        for value in sorted(REQUEST_INTENTS):
            self.assertIn(value, text)
        self.assertIn("not automatically granted rights", text)
        self.assertIn("deletion request", text.lower())
        self.assertIn("needs_policy_review", text)

    def test_no_portia_legal_case_or_hold_record_is_claimed(self) -> None:
        text = self.read(
            "docs/design/portia-records-requests-holds-and-disposition-boundaries.md"
        )
        for term in (
            "portia_privacy_request",
            "portia_legal_hold",
            "portia_records_case",
            "portia_retention_policy",
        ):
            self.assertIn(term, text)
        self.assertIn("does **not** add canonical", text)

    def test_disagreement_retention_dependency_is_preserved(self) -> None:
        text = self.read(
            "docs/design/portia-records-requests-holds-and-disposition-boundaries.md"
        )
        self.assertIn("Statement of Disagreement retention dependency", text)
        self.assertIn("while contested record is maintained", text)
        self.assertIn("dependency unit", text)
        self.assertIn("Preserve history", text)
        self.assertIn("retain forever", text)

    def test_exceptional_removal_is_not_routine_retention(self) -> None:
        text = self.read(
            "docs/design/portia-records-requests-holds-and-disposition-boundaries.md"
        )
        self.assertIn("Routine retention disposition", text)
        self.assertIn("It is not Exceptional Removal", text)
        self.assertIn("retention period expired", text)
        self.assertIn("school year ended", text)

    def test_foreign_custody_and_export_bytes_are_independent(self) -> None:
        retention = self.read("docs/design/portia-retention-classes-and-policy-hooks.md")
        requests = self.read(
            "docs/design/portia-records-requests-holds-and-disposition-boundaries.md"
        )
        self.assertIn("Portia Page Record disposition", retention)
        self.assertIn("Core RetainedSourceScan disposition", retention)
        self.assertIn("export bytes deleted != export provenance deleted", retention)
        self.assertIn("Portia must not delete foreign custody", requests)
        self.assertIn("export-byte deletion != external recall", requests)

    def test_current_policy_refresh_records_ferpa_and_nj_boundaries(self) -> None:
        text = self.read(
            "docs/research/issue-21-retention-policy-refresh-2026-08-14.md"
        )
        self.assertIn("must not be destroyed while", text)
        self.assertIn("M700106-001", text)
        self.assertIn("schedule eligibility != destruction authorization", text)
        self.assertIn("Routine schedule-based disposition must remain distinct", text)

    def test_scenario_matrix_has_complete_inventory(self) -> None:
        text = self.read(
            "docs/validation/issue-21-retention-and-request-scenario-matrix.md"
        )
        found = set()
        for line in text.splitlines():
            if line.startswith("| `T"):
                found.add(line.split("`", 2)[1])
        self.assertEqual(SCENARIOS, found)
        self.assertIn("Artemis", text)
        self.assertIn("Exceptional Removal", text)
        self.assertIn("Vitrine Snapshot", text)
        self.assertIn("workspace destruction", text.lower())

    def test_slice_4_authoritative_checkpoint_is_recorded(self) -> None:
        text = self.read(
            "docs/validation/issue-21-slice-4-deliberate-export-checkpoint.md"
        )
        self.assertIn("Ran 1045 tests in 181.338s", text)
        self.assertIn("OK", text)
        self.assertIn("clean git diff --check", text)
        self.assertIn("line-ending", text)


if __name__ == "__main__":
    unittest.main()
