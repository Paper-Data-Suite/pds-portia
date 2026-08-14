from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/design/portia-paper-import-operational-failure-recovery-and-integrity.md"
INVALID_MATRIX = ROOT / "docs/validation/issue-20-application-invalid-matrix.md"


def load_schema(relative_path: str) -> dict[str, object]:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def invariant_ids(relative_path: str) -> set[str]:
    schema = load_schema(relative_path)
    values = schema.get("x-portia-application-invariants", [])
    return {
        value["id"] if isinstance(value, dict) else value
        for value in values
    }


class Issue20OperationalFailureBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.design_text = DESIGN.read_text(encoding="utf-8")
        cls.invalid_text = INVALID_MATRIX.read_text(encoding="utf-8")

    def test_required_failure_scenarios_are_documented(self) -> None:
        required = [
            "Page Target created; Core registration fails",
            "Core registration succeeds; print fails",
            "Page printed; Page Target later invalidated",
            "Returned page resolves to missing/wrong target",
            "Historical template/layout version unavailable",
            "Core retains source; Portia dispatch crashes",
            "Page Record persists; interpretation/proposal creation crashes",
            "Human review accepted; canonical materialization partially fails",
            "Import source cannot be read as a bounded source snapshot",
            "Mapping profile/version unavailable",
            "One malformed import source record among valid records",
            "Ambiguous identity mapping",
            "Proposal fails domain validation",
            "Import review accepted; canonical write fails",
            "Unchanged import replay",
            "Same source snapshot, changed mapping",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.design_text)

    def test_review_integrity_and_quarantine_are_distinct(self) -> None:
        self.assertIn(
            "ordinary review/retry\n≠ Integrity Finding\n≠ Quarantine",
            self.design_text,
        )
        self.assertIn(
            "Quarantine is exceptional isolation",
            self.design_text,
        )
        self.assertIn(
            "Integrity Finding is appropriate",
            self.design_text,
        )

    def test_paper_retry_invariants_exist_in_public_contracts(self) -> None:
        page_record = invariant_ids("schemas/v1/capture/page-record.schema.json")
        interpretation = invariant_ids(
            "schemas/v1/capture/paper-interpretation.schema.json"
        )
        materialization = invariant_ids(
            "schemas/v1/capture/capture-materialization.schema.json"
        )
        self.assertIn("page_record.idempotent_same_source_same_route", page_record)
        self.assertIn("page_record.same_route_different_source_distinct", page_record)
        self.assertIn("page_record.same_hash_not_auto_collapsed", page_record)
        self.assertIn(
            "paper_interpretation.same_profile_replay_idempotent", interpretation
        )
        self.assertIn(
            "paper_interpretation.changed_profile_new_generation", interpretation
        )
        self.assertIn(
            "capture_materialization.no_duplicate_canonical_records", materialization
        )
        self.assertIn(
            "capture_materialization.receipt_after_canonical_acceptance",
            materialization,
        )

    def test_import_retry_invariants_exist_in_public_contracts(self) -> None:
        batch = invariant_ids("schemas/v1/imports/import-batch.schema.json")
        source = invariant_ids("schemas/v1/imports/import-source-record.schema.json")
        materialization = invariant_ids(
            "schemas/v1/imports/import-materialization.schema.json"
        )
        self.assertIn("import_batch.unchanged_replay_idempotent", batch)
        self.assertIn(
            "import_batch.changed_source_or_mapping_preserves_history", batch
        )
        self.assertIn("import_batch.missing_later_source_not_deletion", batch)
        self.assertIn("import_source_record.replay_no_duplicate_downstream", source)
        self.assertIn("import_source_record.changed_content_preserves_history", source)
        self.assertIn("import_source_record.later_absence_not_deletion", source)
        self.assertIn(
            "import_materialization.no_duplicate_canonical_records", materialization
        )
        self.assertIn(
            "import_materialization.receipt_after_canonical_acceptance",
            materialization,
        )

    def test_review_rejection_is_not_quarantine(self) -> None:
        capture_review = invariant_ids("schemas/v1/capture/capture-review.schema.json")
        import_review = invariant_ids("schemas/v1/imports/import-review.schema.json")
        self.assertIn("capture_review.rejection_not_quarantine", capture_review)
        self.assertIn("import_review.rejection_not_deletion", import_review)
        self.assertIn("capture_review.unreadable_and_unresolved_are_not_negative", capture_review)
        self.assertIn("import_review.unresolved_not_negative", import_review)

    def test_materialization_reuses_existing_operation_infrastructure(self) -> None:
        paper = invariant_ids("schemas/v1/capture/capture-materialization.schema.json")
        imported = invariant_ids("schemas/v1/imports/import-materialization.schema.json")
        for values, prefix in ((paper, "capture_materialization"), (imported, "import_materialization")):
            with self.subTest(prefix=prefix):
                self.assertIn(f"{prefix}.operation_reuse", values)
                self.assertIn(f"{prefix}.operation_journal_exactness", values)
                self.assertIn(f"{prefix}.lock_and_preflight_reuse", values)
                self.assertIn(f"{prefix}.not_quarantine", values)

    def test_scan_and_import_time_are_not_domain_time(self) -> None:
        paper = invariant_ids("schemas/v1/capture/capture-materialization.schema.json")
        imported = invariant_ids("schemas/v1/imports/import-materialization.schema.json")
        batch = invariant_ids("schemas/v1/imports/import-batch.schema.json")
        self.assertIn("capture_materialization.no_scan_time_as_domain_time", paper)
        self.assertIn("import_materialization.no_import_time_as_domain_time", imported)
        self.assertIn("import_batch.import_time_not_domain_time", batch)

    def test_exact_historical_context_rules_are_documented(self) -> None:
        required = [
            "never rewrite historical page purpose/template/context",
            "never rewrite the printed page to a newer target/template",
            "do not interpret with the current/latest template as a substitute",
            "never silently retarget exact references to successors",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.design_text)

    def test_missing_later_import_record_has_no_deletion_semantics(self) -> None:
        self.assertIn(
            "Source record absent from a later import snapshot",
            self.design_text,
        )
        self.assertIn(
            "absence is not deletion, retraction, correction, or supersession",
            self.design_text,
        )
        self.assertIn(
            "later import omission is interpreted as deletion/removal",
            self.invalid_text,
        )

    def test_application_invalid_matrix_covers_core_route_failures(self) -> None:
        required = [
            "no active Core RouteRegistration exactly targets",
            "route module, class, work, target kind, target ID, or exact contract version disagrees",
            "route does not resolve to the exact referenced Page Target",
            "Core retained-source scan/page/fingerprint does not resolve exactly",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.invalid_text)

    def test_application_invalid_matrix_covers_machine_judgment_prohibitions(self) -> None:
        self.assertIn(
            "machine proposal infers Actor identity, firsthand status, fault, intent, severity",
            self.invalid_text,
        )
        self.assertIn(
            "source label/category is automatically converted into Portia Classification",
            self.invalid_text,
        )
        self.assertIn(
            "fuzzy name/email similarity silently creates or selects Actor identity",
            self.invalid_text,
        )

    def test_application_invalid_matrix_covers_crash_replay_protection(self) -> None:
        required = [
            "retry creates a second canonical record",
            "unchanged replay starts a second canonical-creation intent",
            "journal says a step is accepted/completed but canonical readback disagrees",
            "canonical write may be durable but state is indeterminate",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.invalid_text)

    def test_lifecycle_matrix_covers_all_issue20_persistent_families(self) -> None:
        families = [
            "Capture Batch",
            "Page Target before route registration/print",
            "Page Target after registration/print",
            "Page Record",
            "Paper Interpretation",
            "Capture Proposal",
            "Capture Review",
            "Capture Materialization",
            "Import Batch",
            "Import Source Record",
            "Import Proposal",
            "Import Review",
            "Import Materialization",
        ]
        for family in families:
            with self.subTest(family=family):
                self.assertIn(f"| {family} |", self.design_text)

    def test_derived_queues_are_explicitly_nonauthoritative(self) -> None:
        self.assertIn(
            "Review queues, recovery queues, duplicate-candidate lists, and current-decision",
            self.design_text,
        )
        self.assertIn(
            "absence from review/recovery/duplicate/current queues is treated as proof",
            self.invalid_text,
        )

    def test_raw_binary_and_temp_path_persistence_remains_forbidden(self) -> None:
        self.assertIn(
            "Portia JSON embeds scan/PDF/file bytes or temp absolute paths",
            self.invalid_text,
        )
        paper = invariant_ids("schemas/v1/capture/capture-materialization.schema.json")
        imported = invariant_ids("schemas/v1/imports/import-materialization.schema.json")
        self.assertIn("capture_materialization.no_raw_source_payload", paper)
        self.assertIn("import_materialization.no_raw_source_payload", imported)


if __name__ == "__main__":
    unittest.main()
