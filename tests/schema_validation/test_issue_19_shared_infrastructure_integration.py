from __future__ import annotations

import copy
import json
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


SCENARIOS_PATH = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-19"
    / "cross-record"
    / "shared-infrastructure-scenarios.json"
)

ISSUE19_FAMILIES = {
    "follow_up": "1",
    "outcome": "1",
    "reentry": "1",
    "repair": "1",
}
ISSUE19_IDENTIFIERS = {
    "portia_follow_up_id",
    "portia_outcome_id",
    "portia_reentry_id",
    "portia_repair_id",
}

SHARED_INFRASTRUCTURE = {
    "lifecycle_transition": "1",
    "lifecycle_history_correction": "1",
    "statement_of_disagreement": "1",
    "dependency": "1",
    "record_migration": "1",
    "ownership_correction": "1",
    "exceptional_removal": "1",
    "operation_journal": "2",
    "operation_lock": "2",
    "quarantine_record": "2",
    "integrity_finding": "2",
    "source_snapshot": "1",
    "derived_index_metadata": "1",
    "derived_current_pointer": "1",
}


class Issue19SharedInfrastructureIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.scenarios = load_json(SCENARIOS_PATH)

    def _schema(self, contract: str, version: str):
        path = self.catalog["contracts"][contract][version]["path"]
        return load_json(REPO_ROOT / path)

    def test_issue19_public_contract_inventory_is_complete(self) -> None:
        for family, version in ISSUE19_FAMILIES.items():
            with self.subTest(family=family):
                self.assertIn(family, self.catalog["contracts"])
                self.assertIn(version, self.catalog["contracts"][family])

        self.assertIn("account", self.catalog["contracts"])
        self.assertIn("2", self.catalog["contracts"]["account"])
        self.assertIn("observation", self.catalog["contracts"])
        self.assertIn("2", self.catalog["contracts"]["observation"])

        for identifier in ISSUE19_IDENTIFIERS:
            with self.subTest(identifier=identifier):
                self.assertIn(identifier, self.catalog["contracts"])
                self.assertIn("1", self.catalog["contracts"][identifier])

    def test_shared_infrastructure_versions_remain_registered(self) -> None:
        for contract, version in SHARED_INFRASTRUCTURE.items():
            with self.subTest(contract=contract):
                self.assertIn(contract, self.catalog["contracts"])
                self.assertIn(version, self.catalog["contracts"][contract])

    def test_exact_operation_targets_accept_event_and_support_issue19_children(self) -> None:
        validator = validator_for(
            "exact_portia_work_or_record_target",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        seen = set()
        for target in self.scenarios["operation_targets"]:
            with self.subTest(target=target):
                errors = list(validator.iter_errors(target))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                ref = target["work_record_ref"]
                seen.add(
                    (
                        ref["work_ref"]["work_kind"],
                        ref["record_ref"]["record_kind"],
                    )
                )

        expected = {
            (owner, family)
            for owner in ("event", "support_process")
            for family in ISSUE19_FAMILIES
        }
        self.assertEqual(seen, expected)

    def test_exact_issue19_target_rejects_missing_contract_version(self) -> None:
        validator = validator_for(
            "exact_portia_work_or_record_target",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        target = copy.deepcopy(self.scenarios["operation_targets"][0])
        target["work_record_ref"]["record_ref"].pop("contract_version")
        self.assertTrue(list(validator.iter_errors(target)))

    def test_exact_issue19_target_rejects_null_contract_version(self) -> None:
        validator = validator_for(
            "exact_portia_work_or_record_target",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        target = copy.deepcopy(self.scenarios["operation_targets"][0])
        target["work_record_ref"]["record_ref"]["contract_version"] = None
        self.assertTrue(list(validator.iter_errors(target)))

    def test_dependency_can_link_support_outcome_to_exact_event_evidence(self) -> None:
        value = self.scenarios["dependency"]
        validator = validator_for(
            "dependency",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        errors = list(validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )
        self.assertEqual(value["dependent"]["record_ref"]["record_kind"], "outcome")
        self.assertEqual(
            value["dependency"]["work_record_ref"]["record_ref"]["record_kind"],
            "observation",
        )
        self.assertEqual(
            value["dependency"]["work_record_ref"]["record_ref"]["contract_version"],
            "2",
        )

    def test_dependency_remains_declarative_not_lifecycle_cascade(self) -> None:
        schema = self._schema("dependency", "1")
        text = (
            schema["description"]
            + " "
            + schema.get("$comment", "")
        ).lower()
        self.assertIn("never silently retargeted", text)
        self.assertIn("no automatic lifecycle cascade", text)
        self.assertNotIn("outcome_result", schema["properties"])

    def test_statement_of_disagreement_can_target_issue19_outcome_additively(self) -> None:
        value = self.scenarios["statement_of_disagreement"]
        validator = validator_for(
            "statement_of_disagreement",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        errors = list(validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )
        self.assertEqual(value["target"]["record_ref"]["record_kind"], "outcome")

    def test_disagreement_does_not_rewrite_or_retarget_outcome(self) -> None:
        schema = self._schema("statement_of_disagreement", "1")
        text = schema["description"].lower()
        for phrase in (
            "does not rewrite",
            "adjudicate",
            "invalidate",
            "supersede",
            "silently retarget",
        ):
            self.assertIn(phrase, text)

    def test_event_owned_issue19_child_uses_existing_ownership_correction(self) -> None:
        value = self.scenarios["event_child_ownership_correction"]
        validator = validator_for(
            "ownership_correction",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        errors = list(validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )
        self.assertEqual(value["correction_kind"], "child_work_root")
        self.assertEqual(
            value["destination"]["work_record_ref"]["record_ref"]["record_kind"],
            "outcome",
        )

    def test_ownership_correction_v1_remains_event_oriented(self) -> None:
        schema = self._schema("ownership_correction", "1")
        work_id_ref = schema["properties"]["work_id"]["$ref"]
        self.assertTrue(work_id_ref.endswith("portia-event-id.schema.json"))

        serialized = json.dumps(schema["$defs"]["eventWorkRecordRef"])
        self.assertIn('"const": "event"', serialized)
        self.assertNotIn('"const": "support_process"', serialized)

    def test_support_process_root_correction_uses_family_successor_semantics(self) -> None:
        for family, version in ISSUE19_FAMILIES.items():
            with self.subTest(family=family):
                schema = self._schema(family, version)
                reasons = schema["$defs"]["supersessionEntry"]["properties"][
                    "reason"
                ]["enum"]
                self.assertIn("work_root_corrected", reasons)

                invariants = set(
                    schema.get("x-portia-application-invariants", [])
                )
                prefix = f"portia.{family}."
                for suffix in (
                    "predecessor_resolution",
                    "predecessor_identity_unique",
                    "self_supersession",
                    "supersession_reason_uniform",
                    "replacement_topology",
                    "no_silent_successor_following",
                ):
                    self.assertIn(prefix + suffix, invariants)

    def test_exceptional_removal_accepts_exact_issue19_child(self) -> None:
        value = self.scenarios["exceptional_removal"]
        validator = validator_for(
            "exceptional_removal",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        errors = list(validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )
        record = value["target"]["work_record_ref"]["record_ref"]
        self.assertEqual(record["record_kind"], "repair")
        self.assertEqual(record["contract_version"], "1")

    def test_exceptional_removal_preserves_history_and_incoming_refs(self) -> None:
        schema = self._schema("exceptional_removal", "1")
        invariants = set(schema["x-portia-application-invariants"])
        self.assertIn(
            "portia.removal.incoming_reference_rewritten",
            invariants,
        )
        self.assertIn(
            "portia.removal.target_not_canonically_accepted",
            invariants,
        )
        self.assertIn(
            "portia.removal.target_not_exactly_resolved",
            invariants,
        )
        self.assertIn(
            "portia.removal.derived_payload_retained",
            invariants,
        )

    def test_record_migration_reuses_family_neutral_exact_endpoints(self) -> None:
        schema = self._schema("record_migration", "1")
        endpoint = schema["$defs"]["workRecordEndpoint"]
        ref = endpoint["properties"]["work_record_ref"]["$ref"]
        self.assertTrue(ref.endswith("exact-portia-work-record-ref.schema.json"))

        invariants = set(schema["x-portia-application-invariants"])
        for invariant in (
            "portia.migration.logical_identity_mismatch",
            "portia.migration.record_family_mismatch",
            "portia.migration.work_root_changed",
            "portia.migration.semantic_mismatch",
            "portia.migration.ownership_scope_changed",
        ):
            self.assertIn(invariant, invariants)

    def test_no_issue19_specific_migration_or_removal_forks_exist(self) -> None:
        contracts = self.catalog["contracts"]
        for family in ISSUE19_FAMILIES:
            with self.subTest(family=family):
                self.assertNotIn(f"{family}_record_migration", contracts)
                self.assertNotIn(f"{family}_exceptional_removal", contracts)
                self.assertNotIn(f"{family}_ownership_correction", contracts)

    def test_operation_journal_reuses_exact_portia_targets(self) -> None:
        schema = self._schema("operation_journal", "2")
        serialized = json.dumps(schema["$defs"]["operationTarget"])
        self.assertIn(
            "exact-portia-work-or-record-target.schema.json",
            serialized,
        )
        operation_kinds = set(schema["properties"]["operation_kind"]["enum"])
        self.assertTrue(
            {
                "create_record",
                "update_record",
                "transition_lifecycle",
                "activate_successor",
                "create_dependency",
                "migrate_representation",
                "correct_ownership",
                "exceptionally_remove",
                "rebuild_projection",
                "integrity_scan",
                "repair_operation",
            }
            <= operation_kinds
        )
        self.assertIn(
            "does not replace canonical domain records",
            schema["description"].lower(),
        )

    def test_operation_lock_record_scope_reuses_exact_work_record_reference(self) -> None:
        schema = self._schema("operation_lock", "2")
        record_target = schema["$defs"]["recordLockTarget"]
        ref = record_target["properties"]["work_record_ref"]["$ref"]
        self.assertTrue(ref.endswith("exact-portia-work-record-ref.schema.json"))
        description = schema["description"].lower()
        self.assertIn("does not prove process liveness", description)
        self.assertIn("authorize mutation", description)

    def test_integrity_finding_remains_diagnostic_and_exact_reference_aware(self) -> None:
        schema = self._schema("integrity_finding", "2")
        codes = set(schema["properties"]["code"]["enum"])
        self.assertTrue(
            {
                "exact_target_missing",
                "reference_kind_mismatch",
                "reference_scope_mismatch",
                "silent_retarget_detected",
                "status_history_mismatch",
                "operation_incomplete",
                "canonical_write_partial",
                "derived_index_drift",
                "projection_stale",
            }
            <= codes
        )
        serialized = json.dumps(schema)
        self.assertIn("exact-portia-work-ref.schema.json", serialized)
        self.assertIn("exact-portia-work-record-ref.schema.json", serialized)

    def test_derived_current_pointers_accept_event_and_support_scopes(self) -> None:
        validator = validator_for(
            "derived_current_pointer",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        owners = set()
        for value in self.scenarios["derived_pointers"]:
            with self.subTest(value=value):
                errors = list(validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                owners.add(
                    value["projection_scope"]["work_ref"]["work_kind"]
                )
        self.assertEqual(owners, {"event", "support_process"})

    def test_derived_pointer_is_explicitly_nonauthoritative(self) -> None:
        schema = self._schema("derived_current_pointer", "1")
        text = (
            schema["description"]
            + " "
            + schema.get("$comment", "")
        ).lower()
        self.assertIn("does not claim", text)
        self.assertIn("fresh", text)
        self.assertIn("complete", text)
        self.assertIn("must not infer current selection", text)

        for value in self.scenarios["derived_pointers"]:
            self.assertTrue(
                {
                    "outcome",
                    "result",
                    "success",
                    "resolved",
                    "remorse",
                    "forgiveness",
                    "clearance",
                }.isdisjoint(value)
            )

    def test_issue19_lifecycle_remains_separate_from_domain_progress(self) -> None:
        for family, version in ISSUE19_FAMILIES.items():
            with self.subTest(family=family):
                schema = self._schema(family, version)
                self.assertEqual(
                    set(schema["properties"]["status"]["enum"]),
                    {"proposed", "active", "invalidated", "superseded"},
                )

        self.assertIn(
            "workflow_state",
            self._schema("follow_up", "1")["properties"],
        )
        self.assertIn(
            "result",
            self._schema("outcome", "1")["properties"],
        )
        self.assertIn(
            "workflow_state",
            self._schema("reentry", "1")["properties"],
        )
        self.assertIn(
            "workflow_state",
            self._schema("repair", "1")["properties"],
        )

    def test_issue19_families_expose_no_v1_amendment_paths(self) -> None:
        for family, version in ISSUE19_FAMILIES.items():
            with self.subTest(family=family):
                schema = self._schema(family, version)
                properties = schema.get("properties", {})
                self.assertNotIn("amendments", properties)
                self.assertNotIn("amendment_paths", properties)
                invariants = schema.get(
                    "x-portia-application-invariants", []
                )
                self.assertTrue(
                    any(
                        "amendment_prohibited_v1" in invariant
                        for invariant in invariants
                    )
                )

    def test_issue19_paper_and_import_activation_guards_remain_deferred_to_issue20(self) -> None:
        for family, version in ISSUE19_FAMILIES.items():
            with self.subTest(family=family):
                schema = self._schema(family, version)
                invariants = schema.get(
                    "x-portia-application-invariants", []
                )
                text = " ".join(invariants)
                self.assertIn("paper_activation_requires_review_history", text)
                self.assertIn("import_activation_requires_review_history", text)

    def test_issue19_families_do_not_publish_reporting_or_portfolio_state(self) -> None:
        forbidden = {
            "grade",
            "standards_proficiency",
            "publication",
            "publication_id",
            "portfolio",
            "report_card",
            "meridian",
            "vitrine",
        }
        for family, version in ISSUE19_FAMILIES.items():
            with self.subTest(family=family):
                properties = set(
                    self._schema(family, version)["properties"]
                )
                self.assertTrue(forbidden.isdisjoint(properties))

    def test_issue19_owner_envelopes_do_not_create_student_global_dossiers(self) -> None:
        forbidden = {
            "student_id",
            "student_global_id",
            "case_id",
            "dossier_id",
            "longitudinal_student_id",
        }
        for family, version in ISSUE19_FAMILIES.items():
            with self.subTest(family=family):
                schema = self._schema(family, version)
                self.assertEqual(
                    set(schema["properties"]["work_kind"]["enum"]),
                    {"event", "support_process"},
                )
                self.assertTrue(
                    forbidden.isdisjoint(schema["properties"])
                )


if __name__ == "__main__":
    unittest.main()
