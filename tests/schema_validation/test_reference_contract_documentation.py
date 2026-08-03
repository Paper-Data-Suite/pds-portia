from __future__ import annotations

from pathlib import Path
import unittest


TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parents[1]


class ReferenceContractDocumentationTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = REPO_ROOT / relative_path
        self.assertTrue(path.is_file(), relative_path)
        return path.read_text(encoding="utf-8")

    def test_accepted_documents_exist_and_are_linked(self) -> None:
        readme = self.read("README.md")
        design = self.read(
            "docs/design/portia-reference-targeting-and-relationship-contracts.md"
        )
        adr = self.read(
            "docs/decisions/0007-define-shared-reference-targeting-and-relationship-contracts.md"
        )
        examples = self.read(
            "docs/examples/portia-reference-targeting-and-relationship-examples.md"
        )

        self.assertIn("**Status:** Accepted", design)
        self.assertIn(
            "**Revision:** 2 — accepted contracts and implemented reconciliation",
            design,
        )
        self.assertIn("ADR 0007", readme)
        self.assertIn(
            "portia-reference-targeting-and-relationship-examples.md",
            readme,
        )
        self.assertIn("schemas/v2/event.schema.json", adr)
        self.assertIn("schemas/v2/event-participant.schema.json", adr)
        self.assertIn("schemas/v2/event-participant-role.schema.json", adr)
        self.assertIn("module_work_record_ref", examples)
        self.assertIn("draws_context_from", examples)

    def test_examples_cover_every_shared_contract_family(self) -> None:
        examples = self.read(
            "docs/examples/portia-reference-targeting-and-relationship-examples.md"
        )
        required_terms = {
            "roster_student_ref",
            "actor_ref",
            "record_kind",
            "work_ref",
            "record_ref",
            "display_snapshot",
            "event_participant",
            "event_participants",
            "support_process_participant",
            "work_relationship",
            "resolution_state",
        }
        for term in sorted(required_terms):
            with self.subTest(term=term):
                self.assertIn(term, examples)


if __name__ == "__main__":
    unittest.main()
