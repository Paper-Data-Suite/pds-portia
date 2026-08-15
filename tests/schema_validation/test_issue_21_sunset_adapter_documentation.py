import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

CAPABILITIES = {
    "enumerate_owned_custody",
    "classify_owned_custody",
    "describe_dependencies",
    "describe_trigger_facts",
    "describe_supported_actions",
    "evaluate_module_blockers",
    "validate_candidate_action",
    "execute_module_action",
    "verify_module_action",
    "describe_unresolved_foreign_custody",
}

SCENARIOS = {f"S{i:02d}" for i in range(1, 37)}


class Issue21SunsetAdapterDocumentationTests(unittest.TestCase):
    def read(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    def test_future_adapter_capabilities_are_complete(self) -> None:
        text = self.read(
            "docs/design/portia-future-sunset-retention-adapter-boundary.md"
        )
        self.assertEqual(10, len(CAPABILITIES))
        for capability in sorted(CAPABILITIES):
            self.assertIn(capability, text)
        self.assertIn(
            "conceptual capabilities, not accepted Python method names",
            text,
        )

    def test_sunset_absence_does_not_create_dependency(self) -> None:
        text = self.read(
            "docs/design/portia-future-sunset-retention-adapter-boundary.md"
        )
        self.assertIn("there is no `pds-sunset` repository", text)
        self.assertIn("from pds_sunset import ...", text)
        self.assertIn("No `pds-sunset` dependency is added", text)

    def test_semantic_authority_stays_with_module(self) -> None:
        text = self.read(
            "docs/design/portia-future-sunset-retention-adapter-boundary.md"
        )
        self.assertIn("Only Portia can authoritatively explain", text)
        self.assertIn("Path alone is never semantic identity", text)
        self.assertIn("The orchestrator coordinates", text)
        self.assertIn("The module mutates", text)
        self.assertIn(
            "Sunset should not directly unlink Portia canonical files",
            text,
        )

    def test_dry_run_is_distinct_from_execution(self) -> None:
        adapter = self.read(
            "docs/design/portia-future-sunset-retention-adapter-boundary.md"
        )
        recovery = self.read(
            "docs/design/portia-cross-module-disposition-planning-and-recovery.md"
        )
        self.assertIn("Dry-run plan", adapter)
        self.assertIn("No path-driven deletion", adapter)
        self.assertIn("Dry-run output must be non-destructive", recovery)
        self.assertIn("Planning and execution remain separate operations", recovery)

    def test_candidate_drift_blocks_execution(self) -> None:
        text = self.read(
            "docs/design/portia-cross-module-disposition-planning-and-recovery.md"
        )
        self.assertIn("Candidate snapshot", text)
        self.assertIn("stale_candidate", text)
        self.assertIn("re-evaluation", text)
        self.assertIn("candidate snapshot still current", text)

    def test_partial_cross_module_results_are_not_false_atomicity(self) -> None:
        text = self.read(
            "docs/design/portia-cross-module-disposition-planning-and-recovery.md"
        )
        self.assertIn("Partial success example", text)
        self.assertIn("No compensating resurrection", text)
        self.assertIn("recoverable, not magically transactional", text)

    def test_foreign_and_outside_suite_custody_remain_bounded(self) -> None:
        adapter = self.read(
            "docs/design/portia-future-sunset-retention-adapter-boundary.md"
        )
        recovery = self.read(
            "docs/design/portia-cross-module-disposition-planning-and-recovery.md"
        )
        self.assertIn("foreign_owner", adapter)
        self.assertIn("outside_suite_control", adapter)
        self.assertIn("district backups", adapter)
        self.assertIn("Outside-suite copies", recovery)

    def test_shared_protocol_is_not_published_as_portia_contract(self) -> None:
        text = self.read(
            "docs/design/portia-future-sunset-retention-adapter-boundary.md"
        )
        lower = text.lower()
        self.assertIn("shared-protocol candidates", lower)
        self.assertIn("likely core boundary", lower)
        self.assertIn(
            "does not publish these under portia's schema namespace",
            lower,
        )
        self.assertIn(
            "no suite-standard adapter schema is prematurely published",
            lower,
        )

    def test_scenario_matrix_has_complete_inventory(self) -> None:
        text = self.read(
            "docs/validation/issue-21-sunset-adapter-scenario-matrix.md"
        )
        found = set()
        for line in text.splitlines():
            if line.startswith("| `S"):
                found.add(line.split("`", 2)[1])
        self.assertEqual(SCENARIOS, found)
        self.assertIn("Exceptional Removal", text)
        self.assertIn("Vitrine", text)
        self.assertIn("outside_suite_control", text)
        self.assertIn("pds-sunset", text)

    def test_slice_5_authoritative_checkpoint_is_recorded(self) -> None:
        text = self.read(
            "docs/validation/issue-21-slice-5-retention-requests-checkpoint.md"
        )
        self.assertIn("Ran 1056 tests in 322.036s", text)
        self.assertIn("OK", text)
        self.assertIn("clean git diff --check", text)
        self.assertIn("11 stable Portia retention classes", text)


if __name__ == "__main__":
    unittest.main()
