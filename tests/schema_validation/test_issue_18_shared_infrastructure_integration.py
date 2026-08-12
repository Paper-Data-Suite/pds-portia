from __future__ import annotations

import copy
import json
import unittest
from typing import Any

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


FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-18"
)
CROSS_ROOT = FIXTURE_ROOT / "cross-record"
SCENARIOS_PATH = CROSS_ROOT / "shared-infrastructure-scenarios.json"
RELATIONSHIP_PATH = CROSS_ROOT / "support-process-event-relationship.json"

ISSUE18_FAMILIES = {
    "support_process": "schemas/v1/support-processes/support-process.schema.json",
    "support_process_participant": "schemas/v1/support-processes/support-process-participant.schema.json",
    "support_need": "schemas/v1/support-processes/support-need.schema.json",
    "support_goal": "schemas/v1/support-processes/support-goal.schema.json",
    "support": "schemas/v1/support-processes/support.schema.json",
    "intervention": "schemas/v1/support-processes/intervention.schema.json",
    "implementation": "schemas/v1/support-processes/implementation.schema.json",
    "fidelity": "schemas/v1/support-processes/fidelity.schema.json",
}


def _ref_id(ref: dict[str, Any]) -> str:
    return ref["record_id"]


def _target_ids(target: dict[str, Any]) -> list[str]:
    if target["kind"] == "support_process":
        return []
    if target["kind"] == "support_process_participant":
        return [target["record_ref"]["record_id"]]
    return [
        item["record_ref"]["record_id"]
        for item in target["targets"]
    ]


class Issue18SharedInfrastructureIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.scenarios = load_json(SCENARIOS_PATH)

    def test_issue18_public_contract_inventory_is_complete(self) -> None:
        for family in ISSUE18_FAMILIES:
            with self.subTest(family=family):
                self.assertIn(family, self.catalog["contracts"])
                self.assertIn("1", self.catalog["contracts"][family])

        for identifier in (
            "portia_support_process_id",
            "portia_support_process_participant_id",
            "portia_support_need_id",
            "portia_support_goal_id",
            "portia_support_id",
            "portia_intervention_id",
            "portia_implementation_id",
            "portia_fidelity_id",
        ):
            with self.subTest(identifier=identifier):
                self.assertIn(identifier, self.catalog["contracts"])
                self.assertIn("1", self.catalog["contracts"][identifier])

        self.assertIn("planned_schedule", self.catalog["contracts"])
        self.assertIn("1", self.catalog["contracts"]["planned_schedule"])

    def test_end_to_end_support_graph_is_structurally_valid(self) -> None:
        records = [
            ("support_process", FIXTURE_ROOT / "support-process" / "valid" / "active-teacher-identified.json"),
            ("support_process_participant", FIXTURE_ROOT / "support-process-participant" / "valid" / "supported-roster-student.json"),
            ("support_process_participant", FIXTURE_ROOT / "support-process-participant" / "valid" / "local-operator-coordinator.json"),
            ("support_need", FIXTURE_ROOT / "support-need" / "valid" / "participant-access.json"),
            ("support_goal", FIXTURE_ROOT / "support-goal" / "valid" / "participant-goal-with-planning-fields.json"),
            ("support", FIXTURE_ROOT / "support" / "valid" / "as-needed-access-no-provider.json"),
            ("intervention", FIXTURE_ROOT / "intervention" / "valid" / "active-recurring-assigned.json"),
            ("implementation", FIXTURE_ROOT / "implementation" / "valid" / "completed-intervention-occurrence.json"),
        ]

        for family, path in records:
            with self.subTest(family=family, path=path.name):
                value = load_json(path)
                validator = validator_for(
                    family,
                    "1",
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

        fidelity = load_json(
            FIXTURE_ROOT
            / "fidelity"
            / "valid"
            / "one-implementation-direct-observation.json"
        )
        fidelity["evaluator_ref"] = {
            "record_kind": "support_process_participant",
            "record_id": "spp_teacher_1",
            "contract_version": "1",
        }
        errors = list(
            validator_for(
                "fidelity",
                "1",
                catalog=self.catalog,
                store=self.store,
            ).iter_errors(fidelity)
        )
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )

        communication_bundle = load_json(
            CROSS_ROOT / "support-process-communication.json"
        )
        errors = list(
            validator_for(
                "communication",
                "1",
                catalog=self.catalog,
                store=self.store,
            ).iter_errors(communication_bundle["communication"])
        )
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )

    def test_end_to_end_exact_references_resolve_within_one_support_process(self) -> None:
        student = load_json(
            FIXTURE_ROOT
            / "support-process-participant"
            / "valid"
            / "supported-roster-student.json"
        )
        teacher = load_json(
            FIXTURE_ROOT
            / "support-process-participant"
            / "valid"
            / "local-operator-coordinator.json"
        )
        need = load_json(
            FIXTURE_ROOT / "support-need" / "valid" / "participant-access.json"
        )
        goal = load_json(
            FIXTURE_ROOT
            / "support-goal"
            / "valid"
            / "participant-goal-with-planning-fields.json"
        )
        intervention = load_json(
            FIXTURE_ROOT
            / "intervention"
            / "valid"
            / "active-recurring-assigned.json"
        )
        implementation = load_json(
            FIXTURE_ROOT
            / "implementation"
            / "valid"
            / "completed-intervention-occurrence.json"
        )
        fidelity = load_json(
            FIXTURE_ROOT
            / "fidelity"
            / "valid"
            / "one-implementation-direct-observation.json"
        )

        participants = {
            student["participant_id"],
            teacher["participant_id"],
        }
        self.assertEqual(set(_target_ids(need["target"])), {"spp_student_1"})
        self.assertEqual(set(_target_ids(goal["target"])), {"spp_student_1"})
        self.assertTrue(set(_target_ids(intervention["target"])) <= participants)
        self.assertTrue(
            {
                _ref_id(ref)
                for ref in intervention["provider_plan"]["participant_refs"]
            }
            <= participants
        )
        self.assertEqual(
            {_ref_id(ref) for ref in intervention["need_refs"]},
            {need["need_id"]},
        )
        self.assertEqual(
            {_ref_id(ref) for ref in intervention["goal_refs"]},
            {goal["goal_id"]},
        )
        self.assertEqual(
            implementation["plan_ref"]["record_id"],
            intervention["intervention_id"],
        )
        self.assertEqual(
            fidelity["plan_ref"]["record_id"],
            intervention["intervention_id"],
        )
        self.assertEqual(
            fidelity["scope"]["implementation_ref"]["record_id"],
            implementation["implementation_id"],
        )

    def test_support_process_to_event_relationship_v2_is_structurally_valid(self) -> None:
        value = load_json(RELATIONSHIP_PATH)
        validator = validator_for(
            "work_relationship",
            "2",
            catalog=self.catalog,
            store=self.store,
        )
        errors = list(validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )
        self.assertEqual(value["relationship_type"], "draws_context_from")
        self.assertEqual(value["source"]["work_kind"], "support_process")
        self.assertEqual(value["target"]["work_kind"], "event")

    def test_work_relationship_v2_does_not_become_generic_support_link(self) -> None:
        value = load_json(RELATIONSHIP_PATH)
        value["target"] = copy.deepcopy(value["source"])
        validator = validator_for(
            "work_relationship",
            "2",
            catalog=self.catalog,
            store=self.store,
        )
        self.assertTrue(list(validator.iter_errors(value)))

    def test_exact_operation_targets_accept_support_process_and_children(self) -> None:
        validator = validator_for(
            "exact_portia_work_or_record_target",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        for target in self.scenarios["operation_targets"]:
            with self.subTest(target=target):
                errors = list(validator.iter_errors(target))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def test_operation_journal_v2_reuses_exact_portia_targets(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas/v2/operations/operation-journal.schema.json"
        )
        operation_kinds = set(
            schema["properties"]["operation_kind"]["enum"]
        )
        self.assertTrue(
            {
                "create_work",
                "create_record",
                "update_record",
                "transition_lifecycle",
                "activate_successor",
                "rebuild_projection",
                "integrity_scan",
                "repair_operation",
            }
            <= operation_kinds
        )
        text = json.dumps(schema)
        self.assertIn(
            "exact-portia-work-or-record-target.schema.json",
            text,
        )
        description = schema["description"].lower()
        self.assertIn("coordinates", description)
        self.assertIn("does not replace canonical domain records", description)

    def test_shared_recovery_integrity_contract_versions_remain_available(self) -> None:
        expected = {
            "operation_journal": "2",
            "operation_lock": "2",
            "quarantine_record": "2",
            "integrity_finding": "2",
            "derived_index_metadata": "1",
            "derived_current_pointer": "1",
            "lifecycle_transition": "1",
            "lifecycle_history_correction": "1",
            "amendment": "1",
            "statement_of_disagreement": "1",
            "dependency": "1",
            "record_migration": "1",
            "ownership_correction": "1",
            "exceptional_removal": "1",
        }
        for contract, version in expected.items():
            with self.subTest(contract=contract):
                self.assertIn(contract, self.catalog["contracts"])
                self.assertIn(version, self.catalog["contracts"][contract])

    def test_derived_current_pointer_accepts_exact_support_process_scope(self) -> None:
        value = self.scenarios["derived_pointer"]
        validator = validator_for(
            "derived_current_pointer",
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        errors = list(validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )
        self.assertEqual(
            value["projection_scope"]["work_ref"]["work_kind"],
            "support_process",
        )

    def test_derived_current_pointer_is_not_authoritative_domain_state(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/projections/derived-current-pointer.schema.json"
        )
        text = (schema["description"] + " " + schema.get("$comment", "")).lower()
        self.assertIn("does not claim", text)
        self.assertIn("fresh", text)
        self.assertIn("complete", text)
        self.assertIn("current selection", text)

    def test_integrity_finding_v2_can_detect_issue18_exact_reference_failures(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v2/projections/integrity-finding.schema.json"
        )
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
        work_ref = (
            schema["$defs"]["portiaWorkTarget"]["properties"]["work_ref"]["$ref"]
        )
        record_ref = (
            schema["$defs"]["portiaWorkRecordTarget"]
            ["properties"]["work_record_ref"]["$ref"]
        )
        self.assertTrue(work_ref.endswith("exact-portia-work-ref.schema.json"))
        self.assertTrue(
            record_ref.endswith("exact-portia-work-record-ref.schema.json")
        )
        self.assertIn(
            "portia.integrity_finding.exact_target_normalization",
            schema["x-portia-application-invariants"],
        )

    def test_issue18_families_expose_no_v1_amendment_paths(self) -> None:
        for family, path in ISSUE18_FAMILIES.items():
            with self.subTest(family=family):
                schema = load_json(REPO_ROOT / path)
                properties = schema.get("properties", {})
                self.assertNotIn("amendments", properties)
                self.assertNotIn("amendment_paths", properties)
                invariants = schema.get("x-portia-application-invariants", [])
                self.assertTrue(
                    any(
                        "amendment_prohibited_v1" in invariant
                        for invariant in invariants
                    ),
                    f"{family} lacks the v1 Amendment prohibition",
                )

    def test_canonical_lifecycle_is_separate_from_domain_progress_state(self) -> None:
        for family, path in ISSUE18_FAMILIES.items():
            schema = load_json(REPO_ROOT / path)
            self.assertEqual(
                set(schema["properties"]["status"]["enum"]),
                {"proposed", "active", "invalidated", "superseded"},
                family,
            )

        process = load_json(
            REPO_ROOT / ISSUE18_FAMILIES["support_process"]
        )
        support = load_json(REPO_ROOT / ISSUE18_FAMILIES["support"])
        intervention = load_json(
            REPO_ROOT / ISSUE18_FAMILIES["intervention"]
        )
        implementation = load_json(
            REPO_ROOT / ISSUE18_FAMILIES["implementation"]
        )
        fidelity = load_json(REPO_ROOT / ISSUE18_FAMILIES["fidelity"])

        self.assertIn("workflow_state", process["properties"])
        self.assertIn("plan_state", support["properties"])
        self.assertIn("plan_state", intervention["properties"])
        self.assertIn("execution_state", implementation["properties"])
        self.assertIn("result", fidelity["properties"])
        self.assertNotIn("effective", process["properties"]["workflow_state"]["enum"])
        self.assertNotIn("effective", support["properties"]["plan_state"]["enum"])
        self.assertNotIn("effective", implementation["properties"]["execution_state"]["enum"])
        self.assertNotIn("effective", fidelity["properties"]["result"]["enum"])

    def test_plan_adaptation_does_not_retarget_existing_exact_refs(self) -> None:
        scenario = self.scenarios["plan_successor_exactness"]
        original = scenario["original_plan_ref"]
        successor = scenario["adapted_successor_ref"]
        self.assertNotEqual(original["record_id"], successor["record_id"])
        self.assertEqual(scenario["successor_reason"], "plan_adapted")
        self.assertEqual(scenario["implementation_plan_ref"], original)
        self.assertEqual(scenario["fidelity_plan_ref"], original)
        self.assertNotEqual(
            scenario["implementation_plan_ref"],
            successor,
        )
        self.assertNotEqual(
            scenario["fidelity_plan_ref"],
            successor,
        )

    def test_human_authored_schedule_does_not_create_implementation(self) -> None:
        scenario = self.scenarios["planning_without_history"]
        self.assertTrue(scenario["has_schedule"])
        self.assertEqual(scenario["implementation_refs"], [])

        intervention = load_json(
            REPO_ROOT / ISSUE18_FAMILIES["intervention"]
        )
        implementation = load_json(
            REPO_ROOT / ISSUE18_FAMILIES["implementation"]
        )
        self.assertIn(
            "portia.intervention.schedule_is_planning_only",
            intervention["x-portia-application-invariants"],
        )
        self.assertIn(
            "portia.implementation.scheduled_occurrence_never_auto_creates_record",
            implementation["x-portia-application-invariants"],
        )

    def test_implementation_history_does_not_create_or_infer_fidelity(self) -> None:
        implementation = load_json(
            REPO_ROOT / ISSUE18_FAMILIES["implementation"]
        )
        fidelity = load_json(REPO_ROOT / ISSUE18_FAMILIES["fidelity"])
        self.assertIn(
            "portia.implementation.no_fidelity_inference",
            implementation["x-portia-application-invariants"],
        )
        self.assertIn(
            "portia.fidelity.no_universal_score",
            fidelity["x-portia-application-invariants"],
        )
        for field in (
            "fidelity",
            "fidelity_score",
            "implementation_count",
            "occurrence_count",
        ):
            self.assertNotIn(field, implementation["properties"])

    def test_support_process_communication_does_not_establish_implementation(self) -> None:
        bundle = load_json(CROSS_ROOT / "support-process-communication.json")
        communication = bundle["communication"]
        self.assertEqual(communication["work_kind"], "support_process")
        self.assertEqual(
            communication["purpose"]["kind"],
            "support_coordination",
        )
        self.assertNotIn("implementation_id", communication)
        self.assertNotIn("service_delivered", communication)
        self.assertNotIn("consent", communication)
        self.assertNotIn("fidelity", communication)

    def test_paper_and_import_guardrails_do_not_fabricate_current_support_history(self) -> None:
        implementation = load_json(
            FIXTURE_ROOT
            / "implementation"
            / "invalid"
            / "preallocated-paper.json"
        )
        fidelity = load_json(
            FIXTURE_ROOT
            / "fidelity"
            / "invalid"
            / "preallocated-paper.json"
        )
        self.assertTrue(
            list(
                validator_for(
                    "implementation",
                    "1",
                    catalog=self.catalog,
                    store=self.store,
                ).iter_errors(implementation)
            )
        )
        self.assertTrue(
            list(
                validator_for(
                    "fidelity",
                    "1",
                    catalog=self.catalog,
                    store=self.store,
                ).iter_errors(fidelity)
            )
        )

        for family, directory in (
            ("support", "support"),
            ("intervention", "intervention"),
            ("implementation", "implementation"),
            ("fidelity", "fidelity"),
        ):
            with self.subTest(family=family):
                self.assertTrue(
                    (
                        FIXTURE_ROOT
                        / directory
                        / "application-invalid"
                        / "active-paper.json"
                    ).exists()
                )
                self.assertTrue(
                    (
                        FIXTURE_ROOT
                        / directory
                        / "application-invalid"
                        / "active-import.json"
                    ).exists()
                )

    def test_issue18_native_records_do_not_become_academic_results_or_publication_envelopes(self) -> None:
        forbidden_properties = {
            "grade",
            "score",
            "standards_rating",
            "academic_result_set",
            "intervention_record_set",
            "publication_manifest",
            "academic_work_registration",
            "meridian_report",
            "portfolio_entry",
        }
        for family, path in ISSUE18_FAMILIES.items():
            with self.subTest(family=family):
                schema = load_json(REPO_ROOT / path)
                properties = set(schema.get("properties", {}))
                self.assertFalse(properties & forbidden_properties)

    def test_shared_exact_targets_preserve_contract_versions(self) -> None:
        for target in self.scenarios["operation_targets"]:
            with self.subTest(target=target):
                if target["kind"] == "work":
                    self.assertEqual(
                        target["work_ref"]["contract_version"],
                        "1",
                    )
                else:
                    ref = target["work_record_ref"]
                    self.assertEqual(
                        ref["work_ref"]["contract_version"],
                        "1",
                    )
                    self.assertEqual(
                        ref["record_ref"]["contract_version"],
                        "1",
                    )

    def test_no_automatic_support_judgment_fields_appear_in_canonical_contracts(self) -> None:
        forbidden = {
            "risk_score",
            "diagnosis",
            "behavioral_function",
            "recommended_intervention",
            "predicted_effectiveness",
            "student_compliance",
            "family_engagement",
            "provider_competence",
        }
        for family, path in ISSUE18_FAMILIES.items():
            with self.subTest(family=family):
                schema = load_json(REPO_ROOT / path)
                self.assertFalse(
                    set(schema.get("properties", {})) & forbidden
                )


if __name__ == "__main__":
    unittest.main()
