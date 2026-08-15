import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DISPOSITIONS = {
    "included",
    "absent",
    "withheld",
    "unavailable",
    "requires_manual_review",
}

PURPOSES = {
    "teacher_current",
    "participant_specific",
    "student_facing",
    "family_facing",
    "aggregate_equity",
    "administrative_export",
}

TRACKED_FAMILIES = {
    "event",
    "event_participant",
    "event_participant_role",
    "work_relationship",
    "account",
    "observation",
    "review",
    "classification",
    "hypothesis",
    "determination",
    "response",
    "communication",
    "actor",
    "actor_contact_point",
    "actor_student_relationship",
    "actor_roster_student_collision",
    "actor_directory_lifecycle_transition",
    "actor_directory_lifecycle_history_correction",
    "actor_directory_amendment",
    "actor_directory_record_migration",
    "actor_directory_exceptional_removal",
    "support_process",
    "support_process_participant",
    "support_need",
    "support_goal",
    "support",
    "intervention",
    "planned_schedule",
    "implementation",
    "fidelity",
    "follow_up",
    "outcome",
    "reentry",
    "repair",
    "lifecycle_transition",
    "lifecycle_history_correction",
    "amendment",
    "statement_of_disagreement",
    "ownership_correction",
    "record_migration",
    "dependency",
    "exceptional_removal",
    "capture_batch",
    "page_target",
    "page_record",
    "paper_interpretation",
    "capture_proposal",
    "capture_review",
    "capture_materialization",
    "import_batch",
    "import_source_record",
    "import_proposal",
    "import_review",
    "import_materialization",
    "operation_journal",
    "operation_lock",
    "operation_current_pointer",
    "quarantine_record",
    "quarantine_current_pointer",
    "integrity_finding",
    "finding_acknowledgement",
    "finding_suppression",
    "finding_suppression_current_pointer",
    "source_snapshot",
    "derived_index_metadata",
    "derived_current_pointer",
}


class Issue21PrivacyProjectionDocumentationTests(unittest.TestCase):
    def read(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    def test_projection_policy_has_closed_purpose_and_disposition_semantics(self):
        text = self.read("docs/design/portia-privacy-projection-policy.md")
        for value in sorted(DISPOSITIONS | PURPOSES):
            self.assertIn(value, text)
        self.assertIn("Unknown source fields", text)
        self.assertIn("unsupported contract versions", text)
        self.assertIn("fail closed", text)
        for bypass in (
            "include_private",
            "include_all",
            "raw_record",
            "admin_mode",
            "debug_export",
        ):
            self.assertIn(bypass, text)

    def test_projection_policy_separates_purpose_authorization_and_source_access(self):
        text = self.read("docs/design/portia-privacy-projection-policy.md")
        self.assertIn("These purposes define projection behavior only.", text)
        self.assertIn("They do **not** establish:", text)
        self.assertIn(
            "record projection authorization\n!= source-artifact authorization",
            text,
        )
        self.assertIn("privacy_scope", text)
        self.assertIn("does not authenticate a student", text)
        self.assertIn("does not establish that a requester is a parent", text)

    def test_sensitivity_matrix_tracks_complete_slice_2_inventory(self):
        text = self.read(
            "docs/design/portia-record-sensitivity-and-projection-matrix.md"
        )
        self.assertEqual(66, len(TRACKED_FAMILIES))
        self.assertIn("66 current top-level/operational record families", text)
        inventory = text.split("Tracked families:", 1)[1]
        for family in sorted(TRACKED_FAMILIES):
            self.assertIn(family, inventory)

    def test_high_risk_surfaces_have_explicit_rules(self):
        policy = self.read("docs/design/portia-privacy-projection-policy.md")
        matrix = self.read(
            "docs/design/portia-record-sensitivity-and-projection-matrix.md"
        )
        for term in (
            "Account rule",
            "Communication rule",
            "Actor and Contact Point rule",
            "Correction and disagreement rule",
            "Paper/import rule",
            "Operation/integrity rule",
        ):
            self.assertIn(term, policy)
        self.assertIn("verbatim_quote", policy)
        for term in (
            "endpoint_ref",
            "source_artifact_ref",
            "statement_of_disagreement",
            "integrity_finding",
            "import_source_record",
        ):
            self.assertIn(term, matrix)

    def test_slice_1_local_baseline_is_authoritative(self):
        text = self.read(
            "docs/validation/issue-21-slice-1-architecture-policy-checkpoint.md"
        )
        self.assertIn("Ran 1020 tests in 160.492s", text)
        self.assertIn("git diff --check", text)
        self.assertIn("1020 tests", text)
        self.assertIn("No schema, identifier, catalog, fixture, or test change", text)


if __name__ == "__main__":
    unittest.main()
