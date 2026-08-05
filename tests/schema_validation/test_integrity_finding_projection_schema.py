from __future__ import annotations

import unittest

try:
    from .schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )
except ImportError:
    from schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )


CONTRACT_NAME = "integrity_finding"
SCHEMA_PATH = "schemas/v1/projections/integrity-finding.schema.json"
PUBLIC_SCHEMA_PREFIX = "https://paper-data-suite.github.io/pds-portia/"
FIXTURE_DIRECTORY = FIXTURE_ROOT / "issue-12" / "integrity-finding"

CATEGORY_CODES = {
    "structure": {
        "schema_invalid", "unsupported_contract_version",
        "canonical_path_mismatch", "envelope_scope_mismatch",
        "identifier_collision",
    },
    "identity_scope": {
        "logical_identity_conflict", "ownership_scope_mismatch",
        "roster_identity_unresolved", "record_family_mismatch",
    },
    "reference": {
        "exact_target_missing", "reference_kind_mismatch",
        "reference_scope_mismatch", "silent_retarget_detected",
        "removed_target_in_current_use",
    },
    "lifecycle": {
        "status_history_mismatch", "illegal_transition",
        "history_chain_broken", "selected_history_ambiguous",
        "history_correction_invalid", "terminal_state_violation",
    },
    "replacement": {
        "supersession_reconciliation_broken", "replacement_cycle",
        "unsupported_replacement_topology", "multiple_current_representations",
        "replacement_frontier_ambiguous", "partial_consolidation",
        "partial_event_split",
    },
    "dependency": {
        "dependency_cycle", "duplicate_intrinsic_dependency",
        "dependency_declaration_conflict", "required_dependency_gate_violation",
        "dependency_target_resolution_ambiguous",
    },
    "migration": {
        "migration_reconciliation_broken", "migration_identity_mismatch",
        "migration_semantic_mismatch", "migration_branch",
        "migration_cycle", "migration_lifecycle_mismatch",
    },
    "ownership_correction": {
        "ownership_reconciliation_broken", "unresolved_source_child",
        "destination_graph_invalid", "cross_workspace_ownership_correction",
        "roster_mapping_unverified",
    },
    "removal": {
        "removal_reconciliation_broken", "payload_present_after_removal",
        "removal_certificate_without_target_history",
        "derived_payload_retained_after_removal",
        "duplicate_removal_certificate", "removed_target_resolved_as_not_found",
    },
    "chronology_provenance": {
        "timestamp_order_invalid", "observed_revision_mismatch",
        "creation_provenance_inconsistent", "attribution_invalid",
        "effective_time_mismatch",
    },
    "uniqueness_graph": {
        "active_uniqueness_violation", "graph_cycle",
        "duplicate_current_identity", "conflicting_exact_identity",
    },
    "authorization_compatibility": {
        "authorization_limited_resolution", "producer_contract_unavailable",
        "unsupported_cross_module_semantics", "policy_version_unavailable",
    },
    "persistence_recovery": {
        "operation_incomplete", "canonical_write_partial",
        "orphaned_canonical_artifact", "content_digest_mismatch",
        "recovery_required",
    },
    "derived_state": {
        "derived_index_drift", "projection_stale",
        "derived_reverse_link_mismatch", "derived_payload_policy_violation",
    },
}


class IntegrityFindingProjectionSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            CONTRACT_NAME, "1", catalog=cls.catalog, store=cls.store
        )
        cls.schema = cls.store.schema_for_id(
            schema_id_for(CONTRACT_NAME, "1", cls.catalog)
        )

    def test_contract_is_cataloged_with_canonical_path_id(self) -> None:
        expected = PUBLIC_SCHEMA_PREFIX + SCHEMA_PATH
        self.assertEqual(schema_id_for(CONTRACT_NAME, "1", self.catalog), expected)
        self.assertEqual(self.schema["$id"], expected)
        self.assertEqual(
            self.schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )

    def test_valid_manifest_fixtures_pass(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename in manifest["valid"]:
            with self.subTest(fixture=filename):
                errors = list(self.validator.iter_errors(
                    load_json(FIXTURE_DIRECTORY / "valid" / filename)
                ))
                self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_invalid_manifest_fixtures_fail(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename in manifest["invalid"]:
            with self.subTest(fixture=filename):
                errors = list(self.validator.iter_errors(
                    load_json(FIXTURE_DIRECTORY / "invalid" / filename)
                ))
                self.assertTrue(errors, f"{filename} unexpectedly passed")

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, metadata in manifest["application_invalid"].items():
            with self.subTest(fixture=filename, rule=metadata["rule_id"]):
                errors = list(self.validator.iter_errors(load_json(
                    FIXTURE_DIRECTORY / "application-invalid" / filename
                )))
                self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_exact_projection_envelope_is_closed(self) -> None:
        expected = {
            "finding_key", "evaluation_key", "rule_id", "rule_version",
            "category", "code", "severity", "assessment", "effects",
            "scope", "primary_target", "related_targets", "evidence",
            "observed_at",
        }
        self.assertEqual(set(self.schema["required"]), expected)
        self.assertEqual(set(self.schema["properties"]), expected)
        self.assertFalse(self.schema["additionalProperties"])

    def test_projection_excludes_canonical_record_fields(self) -> None:
        prohibited = {
            "schema_version", "record_type", "module_id", "class_id",
            "work_id", "status", "created_at", "created_by", "updated_at",
            "updated_by", "supersedes", "operation_id",
        }
        self.assertTrue(prohibited.isdisjoint(self.schema["properties"]))

    def test_category_vocabulary_is_exact(self) -> None:
        self.assertEqual(
            set(self.schema["properties"]["category"]["enum"]),
            set(CATEGORY_CODES),
        )

    def test_category_code_branches_are_exact(self) -> None:
        observed = {}
        for conditional in self.schema["allOf"]:
            category = conditional["if"]["properties"]["category"]["const"]
            observed[category] = set(
                conditional["then"]["properties"]["code"]["enum"]
            )
        self.assertEqual(observed, CATEGORY_CODES)
        self.assertEqual(
            set(self.schema["properties"]["code"]["enum"]),
            set().union(*CATEGORY_CODES.values()),
        )

    def test_assessment_distinguishes_confirmed_and_indeterminate(self) -> None:
        defs = self.schema["$defs"]
        confirmed = defs["confirmedAssessment"]
        indeterminate = defs["indeterminateAssessment"]
        self.assertEqual(confirmed["properties"]["result"]["const"], "confirmed")
        self.assertEqual(set(confirmed["required"]), {"result"})
        self.assertEqual(
            indeterminate["properties"]["result"]["const"], "indeterminate"
        )
        self.assertEqual(set(indeterminate["required"]), {"result", "limitation"})
        self.assertEqual(
            set(indeterminate["properties"]["limitation"]["enum"]),
            {
                "authorization_limited", "unsupported_contract",
                "external_module_unavailable", "incomplete_canonical_state",
                "recovery_in_progress", "insufficient_evidence",
            },
        )

    def test_severity_vocabulary_is_exact(self) -> None:
        self.assertEqual(
            self.schema["properties"]["severity"]["enum"],
            ["advisory", "warning", "error", "critical"],
        )

    def test_effects_are_nonempty_unique_and_closed(self) -> None:
        effects = self.schema["properties"]["effects"]
        self.assertEqual(effects["minItems"], 1)
        self.assertTrue(effects["uniqueItems"])
        self.assertEqual(
            set(effects["items"]["enum"]),
            {
                "attention", "review_required", "block_current_use",
                "block_lifecycle_writes", "block_operation_completion",
                "block_work_writes", "block_class_writes", "quarantine_target",
            },
        )

    def test_scope_vocabulary_is_exact(self) -> None:
        self.assertEqual(
            set(self.schema["properties"]["scope"]["enum"]),
            {"representation", "logical_record", "work", "class", "workspace", "operation", "graph"},
        )

    def test_target_union_has_six_closed_branches(self) -> None:
        defs = self.schema["$defs"]
        names = [entry["$ref"].split("/")[-1] for entry in defs["findingTarget"]["oneOf"]]
        self.assertEqual(
            names,
            [
                "portiaWorkTarget", "portiaWorkRecordTarget",
                "exceptionalRemovalTarget", "classTarget",
                "workspaceTarget", "operationTarget",
            ],
        )
        for name in names:
            self.assertFalse(defs[name]["additionalProperties"])

    def test_portia_targets_use_exact_references(self) -> None:
        defs = self.schema["$defs"]
        self.assertTrue(
            defs["portiaWorkTarget"]["properties"]["work_ref"]["$ref"].endswith(
                "exact-portia-work-ref.schema.json"
            )
        )
        self.assertTrue(
            defs["portiaWorkRecordTarget"]["properties"]["work_record_ref"]["$ref"].endswith(
                "exact-portia-work-record-ref.schema.json"
            )
        )

    def test_exceptional_removal_target_uses_exact_certificate_reference(self) -> None:
        ref = self.schema["$defs"]["exceptionalRemovalTarget"]["properties"]["removal_ref"]["$ref"]
        self.assertTrue(ref.endswith("exceptional-removal-ref.schema.json"))

    def test_workspace_and_operation_targets_are_explicit_fallbacks(self) -> None:
        defs = self.schema["$defs"]
        self.assertIn("Issue #13", defs["workspaceTarget"]["$comment"])
        self.assertIn("Issue #13", defs["operationTarget"]["$comment"])
        self.assertIn("structurally safe", defs["operationTarget"]["$comment"])

    def test_related_targets_are_bounded_and_unique(self) -> None:
        related = self.schema["properties"]["related_targets"]
        self.assertTrue(related["uniqueItems"])
        self.assertEqual(related["maxItems"], 64)
        self.assertNotIn("minItems", related)

    def test_evidence_is_nonempty_bounded_and_typed(self) -> None:
        evidence = self.schema["properties"]["evidence"]
        self.assertEqual(evidence["minItems"], 1)
        self.assertEqual(evidence["maxItems"], 64)
        self.assertTrue(evidence["uniqueItems"])
        names = {
            item["$ref"].split("/")[-1]
            for item in self.schema["$defs"]["evidenceFact"]["oneOf"]
        }
        self.assertEqual(
            names,
            {
                "tokenEvidence", "identifierEvidence", "integerEvidence",
                "booleanEvidence", "timestampEvidence", "pathEvidence",
                "targetEvidence",
            },
        )
        self.assertNotIn("textEvidence", self.schema["$defs"])
        self.assertNotIn("narrativeEvidence", self.schema["$defs"])

    def test_keys_and_rule_identity_are_structurally_bounded(self) -> None:
        key = self.schema["$defs"]["deterministicKey"]
        self.assertEqual(key["maxLength"], 256)
        self.assertIn(":", key["pattern"])
        rule = self.schema["properties"]["rule_id"]
        self.assertGreaterEqual(rule["pattern"].count("\\."), 1)
        self.assertEqual(rule["maxLength"], 256)

    def test_observed_at_requires_explicit_offset_timestamp(self) -> None:
        self.assertTrue(
            self.schema["properties"]["observed_at"]["$ref"].endswith(
                "explicit-offset-timestamp.schema.json"
            )
        )

    def test_operational_acknowledgement_and_scan_history_are_absent(self) -> None:
        for field in (
            "acknowledged", "suppressed", "first_seen_at", "last_seen_at",
            "cleared_at", "recurrence_count", "mark_resolved",
        ):
            self.assertNotIn(field, self.schema["properties"])

    def test_application_fixture_rules_are_declared(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        declared = set(self.schema["x-portia-application-invariants"])
        for metadata in manifest["application_invalid"].values():
            with self.subTest(rule=metadata["rule_id"]):
                self.assertIn(metadata["rule_id"], declared)

    def test_description_marks_projection_noncanonical_and_rebuildable(self) -> None:
        description = self.schema["description"].lower()
        for phrase in (
            "derived diagnostic", "not a canonical portia record",
            "canonical storage location", "deleted and rebuilt",
        ):
            self.assertIn(phrase, description)


if __name__ == "__main__":
    unittest.main()
