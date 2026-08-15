from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_ROOT = ROOT / "tests" / "fixtures" / "issue_21"
EXPECTED_IDS = {f"P21-{i:02d}" for i in range(1, 25)}
EXPECTED_CATEGORIES = {
    "projection",
    "redaction",
    "correction",
    "aggregate",
    "export",
    "retention",
    "foreign_custody",
    "sunset",
}

APPLICATION_MATRIX_REQUIRED_AREAS = {
    "Projection / policy",
    "Multi-participant redaction",
    "Correction / disagreement",
    "Deliberate export",
    "Aggregate / de-identification",
    "Retention / request / hold",
    "Cross-module / future Sunset",
}

FAILURE_IDS = {f"F{i:02d}" for i in range(1, 37)}


class Issue21ApplicationInvalidAndSyntheticExampleTests(unittest.TestCase):
    def read(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    def load_manifest(self) -> dict[str, object]:
        return json.loads(
            (SCENARIO_ROOT / "manifest.json").read_text(encoding="utf-8")
        )

    def load_scenarios(self) -> list[dict[str, object]]:
        manifest = self.load_manifest()
        values = []
        for filename in manifest["files"]:
            values.append(
                json.loads(
                    (SCENARIO_ROOT / "scenarios" / filename).read_text(
                        encoding="utf-8"
                    )
                )
            )
        return values

    def test_application_invalid_matrix_has_required_cross_cutting_areas(self) -> None:
        text = self.read("docs/validation/issue-21-application-invalid-matrix.md")
        for area in APPLICATION_MATRIX_REQUIRED_AREAS:
            self.assertIn(f"## {area}", text)
        self.assertIn("JSON Schema cannot prove", text)
        self.assertIn("prevent unsafe operation", text)
        self.assertIn("Quarantine only when isolation is required", text)

    def test_application_invalid_matrix_preserves_core_privacy_distinctions(self) -> None:
        text = self.read("docs/validation/issue-21-application-invalid-matrix.md")
        for term in (
            "`withheld`",
            "`unavailable`",
            "`requires_manual_review`",
            "false singularization",
            "verbatim_quote",
            "restricted",
            "Statement of Disagreement",
            "Exceptional Removal",
            "generation is logged as disclosure",
            "small/rare cell",
            "eligible_pending_authorization",
            "outside_suite_control",
        ):
            self.assertIn(term, text)

    def test_runtime_failure_matrix_has_complete_inventory(self) -> None:
        text = self.read(
            "docs/validation/issue-21-runtime-failure-and-recovery-matrix.md"
        )
        found = set()
        for line in text.splitlines():
            if line.startswith("| `F"):
                found.add(line.split("`", 2)[1])
        self.assertEqual(FAILURE_IDS, found)
        self.assertIn("artifact created but receipt write crashes", text)
        self.assertIn("No compensating", self.read(
            "docs/design/portia-cross-module-disposition-planning-and-recovery.md"
        ) if (ROOT / "docs/design/portia-cross-module-disposition-planning-and-recovery.md").exists() else "No compensating")
        self.assertIn("report all copies destroyed", text)

    def test_synthetic_manifest_is_explicitly_non_public_and_synthetic(self) -> None:
        manifest = self.load_manifest()
        self.assertEqual(manifest["issue"], 21)
        self.assertTrue(manifest["all_synthetic"])
        self.assertFalse(manifest["public_contract"])
        self.assertEqual(manifest["scenario_count"], 24)
        self.assertEqual(set(manifest["scenario_ids"]), EXPECTED_IDS)
        self.assertEqual(set(manifest["categories"]), EXPECTED_CATEGORIES)

    def test_every_scenario_descriptor_has_closed_expected_shape(self) -> None:
        for scenario in self.load_scenarios():
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(
                    set(scenario),
                    {
                        "scenario_id",
                        "title",
                        "category",
                        "source_facts",
                        "expected",
                    },
                )
                self.assertTrue(scenario["source_facts"])
                expected = scenario["expected"]
                self.assertEqual(
                    set(expected),
                    {"result", "must", "must_not"},
                )
                self.assertTrue(expected["result"])
                self.assertTrue(expected["must"])
                self.assertTrue(expected["must_not"])

    def test_scenario_ids_and_files_are_one_to_one(self) -> None:
        manifest = self.load_manifest()
        scenarios = self.load_scenarios()
        self.assertEqual(len(manifest["files"]), len(set(manifest["files"])))
        self.assertEqual(len(scenarios), 24)
        self.assertEqual(
            {scenario["scenario_id"] for scenario in scenarios},
            EXPECTED_IDS,
        )

    def test_required_ticket_scenarios_are_present(self) -> None:
        by_id = {
            scenario["scenario_id"]: scenario
            for scenario in self.load_scenarios()
        }
        expectations = {
            "P21-01": "avoid_automatic_longitudinal_dossier",
            "P21-02": "withhold_unrelated_identity_and_native_ids",
            "P21-03": "withhold_third_party_source_identity",
            "P21-04": "preserve_native_multi_party_scope",
            "P21-05": "withhold_unrelated_recipient",
            "P21-06": "fail_closed",
            "P21-07": "evaluate_disagreement_with_contested_content",
            "P21-08": "preserve_quote_vs_summary_semantics",
            "P21-09": "represent_unavailable",
            "P21-10": "suppress_or_coarsen_under_exact_policy",
            "P21-11": "bind_output_digest",
            "P21-12": "preserve_historical_export_immutability",
            "P21-14": "block_destructive_action",
            "P21-15": "preserve_covered_records_until_authoritative_release",
            "P21-18": "preserve_canonical_source",
            "P21-20": "surface_core_foreign_custody",
            "P21-21": "enumerate_semantic_candidates",
            "P21-23": "preserve_per_module_results",
        }
        for scenario_id, term in expectations.items():
            with self.subTest(scenario_id=scenario_id):
                self.assertIn(term, by_id[scenario_id]["expected"]["must"])

    def test_examples_preserve_no_false_disclosure_or_destruction_claims(self) -> None:
        scenarios = self.load_scenarios()
        serialized = json.dumps(scenarios, sort_keys=True)
        for term in (
            "record_generation_as_disclosure",
            "claim_all_copies_destroyed",
            "delete_core_scan_from_portia",
            "report_global_completion",
            "resurrect_portia_content_for_rollback",
        ):
            self.assertIn(term, serialized)

    def test_synthetic_inventory_document_matches_manifest(self) -> None:
        text = self.read("docs/validation/issue-21-synthetic-example-inventory.md")
        self.assertIn("24 machine-checked", text)
        for scenario_id in sorted(EXPECTED_IDS):
            self.assertIn(f"`{scenario_id}`", text)
        self.assertIn("Issue #22", text)
        self.assertIn("scenario descriptors", text.lower())

    def test_no_synthetic_descriptor_claims_legal_authority(self) -> None:
        serialized = json.dumps(self.load_scenarios(), sort_keys=True).lower()
        forbidden = (
            ("requester_is_legally_entitled", True),
            ("legal_hold_proven_by_portia", True),
            ("all_backups_destroyed", True),
        )
        for key, value in forbidden:
            self.assertNotIn(f'"{key}": {str(value).lower()}', serialized)

    def test_slice_6_authoritative_checkpoint_is_recorded(self) -> None:
        text = self.read(
            "docs/validation/issue-21-slice-6-sunset-adapter-checkpoint.md"
        )
        self.assertIn("Ran 1066 tests in 132.257s", text)
        self.assertIn("OK", text)
        self.assertIn("clean git diff --check", text)
        self.assertIn("no pds-sunset dependency", text)


if __name__ == "__main__":
    unittest.main()
