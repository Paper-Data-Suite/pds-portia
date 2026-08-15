from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

ADR = (
    ROOT
    / "docs"
    / "decisions"
    / "0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md"
)


class Issue21AdrAcceptanceTests(unittest.TestCase):
    def read(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    def test_adr_0017_is_accepted_and_scoped_to_issue_21(self) -> None:
        text = ADR.read_text(encoding="utf-8")
        self.assertIn("# ADR 0017:", text)
        self.assertIn("- **Status:** Accepted", text)
        self.assertIn("Related issue:** `#21", text)
        self.assertIn("No `pds-sunset` repository exists", text)

    def test_pre_adr_drift_anchors_match_issue_21_checkpoint(self) -> None:
        text = self.read("docs/validation/issue-21-pre-adr-drift-checkpoint.md")
        expected = {
            "2ec841ffdf9c20850cbaef5811ca20720dc5954b",
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
            "3ae37eaaf89cf913020a5afc75bc11a68df0d5cc",
            "047e47f60730b8a5540b5e1d92f008ffad37eede",
            "9e5f9217ff2a935a98a12f7fc76ae2e74774159c",
            "16317d8764a2e79018aa2bc7082faf66759c13b6",
            "e6db668f0f8729b058f34cdda86a4cb443ca068d",
        }
        for sha in expected:
            self.assertIn(sha, text)
        self.assertIn("pre-ADR drift: clean", text)

    def test_adr_preserves_projection_redaction_distinctions(self) -> None:
        text = ADR.read_text(encoding="utf-8")
        for term in (
            "canonical record != projection",
            "projection != export",
            "export != disclosure",
            "withheld != absent",
            "unavailable != false/no",
            "requires_manual_review",
            "false",
            "de-identification",
            "verbatim_quote",
        ):
            self.assertIn(term, text)

    def test_adr_accepts_exact_export_contract_set(self) -> None:
        text = ADR.read_text(encoding="utf-8")
        for contract in (
            "portia_deliberate_export_id@1",
            "export_source_inventory@1",
            "deliberate_export@1",
        ):
            self.assertIn(contract, text)
        self.assertIn("pexp_", text)
        self.assertIn("source_snapshot@1` remains unchanged", text)
        self.assertIn("Export generation is not disclosure", text)

    def test_adr_accepts_retention_classes_without_legal_periods(self) -> None:
        text = ADR.read_text(encoding="utf-8")
        classes = (
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
        )
        for retention_class in classes:
            self.assertIn(retention_class, text)
        self.assertIn("not durations", text)
        self.assertIn("Exceptional Removal remains exceptional", text)

    def test_adr_assigns_portia_core_institution_and_sunset_ownership(self) -> None:
        text = ADR.read_text(encoding="utf-8")
        self.assertIn("## Responsibility Matrix", text)
        self.assertIn("Portia", text)
        self.assertIn("Core/shared", text)
        self.assertIn("Institution/deployment", text)
        self.assertIn("Future Sunset", text)
        self.assertIn("The orchestrator coordinates", text)
        self.assertIn("Portia mutates and verifies", text)

    def test_public_contract_inventory_lists_unresolved_policy_dependencies(self) -> None:
        text = self.read(
            "docs/validation/issue-21-public-contract-and-policy-boundary-inventory.md"
        )
        self.assertIn("exactly three public contracts", text)
        self.assertIn("Unresolved institutional-policy dependencies", text)
        for term in (
            "requester authentication",
            "retention schedule/profile selection",
            "legal/litigation/preservation holds and releases",
            "destruction approval",
            "backup/archive purge requirements",
        ):
            self.assertIn(term, text)

    def test_acceptance_matrix_is_complete_after_final_drift(self) -> None:
        text = self.read("docs/validation/issue-21-acceptance-matrix.md")
        rows = [
            line
            for line in text.splitlines()
            if line.startswith("| ")
            and not line.startswith("| ---")
            and "Acceptance criterion" not in line
        ]
        self.assertGreaterEqual(len(rows), 55)
        self.assertEqual(text.count("`PENDING`"), 0)
        self.assertIn("PASS: 58", text)
        self.assertIn("PENDING: 0", text)
        self.assertIn("Final drift check is recorded.", text)
        self.assertIn("issue-21-final-drift-checkpoint.md", text)
        self.assertIn("README/schema guide/design docs are reconciled.", text)

    def test_slice_7_authoritative_checkpoint_is_recorded(self) -> None:
        text = self.read(
            "docs/validation/issue-21-slice-7-failure-synthetic-checkpoint.md"
        )
        self.assertIn("Ran 1077 tests in 305.924s", text)
        self.assertIn("OK", text)
        self.assertIn("24 machine-checked synthetic", text)

        slice_8 = self.read(
            "docs/validation/issue-21-slice-8-adr-reconciliation-checkpoint.md"
        )
        self.assertIn("Ran 1087 tests in 203.152s", slice_8)
        self.assertIn("clean git diff --check", slice_8)

        drift = self.read("docs/validation/issue-21-final-drift-checkpoint.md")
        self.assertIn("repository drift: none", drift)
        self.assertIn("Sunset repository: absent", drift)
        self.assertIn("public contract drift: none", drift)

        closeout = self.read("docs/validation/issue-21-final-closeout.md")
        self.assertIn("PASS: 58", closeout)
        self.assertIn("PENDING: 0", closeout)
        self.assertIn("ready for a targeted senior/Codex review", closeout)

    def test_adr_explicitly_defers_shared_sunset_protocol(self) -> None:
        text = ADR.read_text(encoding="utf-8")
        self.assertIn("Shared adapter envelopes/version negotiation", text)
        self.assertIn("contracts are deferred", text)
        self.assertIn("to future suite architecture", text)
        self.assertIn("No `pds-sunset` repository exists", text)
        self.assertIn("must not directly unlink Portia canonical files", text)


if __name__ == "__main__":
    unittest.main()
