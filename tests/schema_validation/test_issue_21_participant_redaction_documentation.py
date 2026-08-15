import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SCENARIO_IDS = {f"R{i:02d}" for i in range(1, 29)}


class Issue21ParticipantRedactionDocumentationTests(unittest.TestCase):
    def read(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    def test_redaction_pipeline_orders_identity_lifecycle_and_privacy(self):
        text = self.read(
            "docs/design/portia-participant-redaction-and-segregation.md"
        )
        required = (
            "resolve exact source work and supported contract version",
            "resolve exact focal participant/subject",
            "reconcile source lifecycle/currentness",
            "evaluate cross-field coherence and indirect-identification risk",
            "requires_manual_review",
        )
        for phrase in required:
            self.assertIn(phrase, text)

    def test_multi_party_scope_is_not_singularized(self):
        text = self.read(
            "docs/design/portia-participant-redaction-and-segregation.md"
        )
        self.assertIn("must not rewrite the native source as if its original target had been", text)
        self.assertIn("singular.", text)
        self.assertIn("applies_to_focal_subject = true", text)
        self.assertIn("hidden participant count", text)

    def test_account_observation_and_communication_rules_are_explicit(self):
        text = self.read(
            "docs/design/portia-participant-redaction-and-segregation.md"
        )
        for term in (
            "Account segregation",
            "verbatim_quote",
            "recorded_summary",
            "Observation segregation",
            "Measurements",
            "Communication segregation",
            "privacy_scope",
            "endpoint_ref",
            "attachments",
        ):
            self.assertIn(term, text)

    def test_actor_contact_and_relationship_do_not_create_authorization(self):
        text = self.read(
            "docs/design/portia-participant-redaction-and-segregation.md"
        )
        self.assertIn("Actor Contact Point segregation", text)
        self.assertIn("email address", text)
        self.assertIn("phone number", text)
        self.assertIn("guardianship", text)
        self.assertIn("FERPA entitlement", text)
        self.assertIn("Contact values require a deliberately selected", text)

    def test_disagreement_and_removal_rules_prevent_misleading_projection(self):
        text = self.read(
            "docs/design/portia-participant-redaction-and-segregation.md"
        )
        self.assertIn("Statement of Disagreement", text)
        self.assertIn(
            "Portia must not\n> simply omit the disagreement and export the contested material alone",
            text,
        )
        self.assertIn("Exceptional Removal and unavailable source", text)
        self.assertIn("stale derived output", text)
        self.assertIn("Do not convert removed/unresolvable content into `absent`", text)

    def test_student_and_family_are_distinct_non_authorizing_purposes(self):
        text = self.read(
            "docs/design/portia-student-family-projection-boundaries.md"
        )
        self.assertIn("Family-facing is not automatically broader", text)
        self.assertIn("family_facing != requester is legal parent/guardian", text)
        self.assertIn("Portia relationship != disclosure entitlement", text)
        self.assertIn("No adverse inference from omission", text)
        self.assertIn("No longitudinal dossier by convenience", text)

    def test_redaction_scenario_matrix_has_complete_inventory(self):
        text = self.read("docs/validation/issue-21-redaction-scenario-matrix.md")
        found = set()
        for line in text.splitlines():
            if line.startswith("| `R"):
                found.add(line.split("`", 2)[1])
        self.assertEqual(SCENARIO_IDS, found)
        self.assertIn("Multi-party source", text)
        self.assertIn("Statement of Disagreement", text)
        self.assertIn("Exceptional Removal", text)
        self.assertIn("privacy_scope=restricted", text)

    def test_slice_2_authoritative_checkpoint_is_recorded(self):
        text = self.read(
            "docs/validation/issue-21-slice-2-projection-policy-checkpoint.md"
        )
        self.assertIn("Ran 1025 tests in 205.944s", text)
        self.assertIn("OK", text)
        self.assertIn("Exit code: 0", text)
        self.assertIn("PowerShell/console stream-display observation", text)


if __name__ == "__main__":
    unittest.main()
