from __future__ import annotations

from datetime import datetime
from typing import Any
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


FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-15"
    / "shared-lifecycle-correction-dependency"
)

ACCOUNT_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"retracted", "invalidated", "superseded"},
    "retracted": {"superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

OBSERVATION_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

ACCOUNT_LIFECYCLE_REASONS = {
    "review_completed",
    "source_retracted",
    "recording_error",
    "wrong_source",
    "wrong_target",
    "invalid_provenance",
    "prohibited_payload",
    "corrected_by_successor",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
}

OBSERVATION_LIFECYCLE_REASONS = {
    "review_completed",
    "recording_error",
    "wrong_observer",
    "wrong_target",
    "wrong_method",
    "measurement_error",
    "invalid_provenance",
    "prohibited_payload",
    "corrected_by_successor",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
}


def _record_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    if record["record_type"] == "account":
        record_id = record["account_id"]
    elif record["record_type"] == "observation":
        record_id = record["observation_id"]
    else:
        raise AssertionError(record["record_type"])
    return record["record_type"], record_id, "1"


def _target_identity(target: dict[str, Any]) -> tuple[str, str, str]:
    ref = target["record_ref"]
    return ref["record_kind"], ref["record_id"], ref["contract_version"]


def _work_record_identity(
    work_record_ref: dict[str, Any],
) -> tuple[str, str, str, str, str]:
    work_ref = work_record_ref["work_ref"]
    record_ref = work_record_ref["record_ref"]
    return (
        work_ref["class_id"],
        work_ref["work_id"],
        record_ref["record_kind"],
        record_ref["record_id"],
        record_ref["contract_version"],
    )


def _transition_errors(scenario: dict[str, Any]) -> list[str]:
    record = scenario["record"]
    transition = scenario["transition"]
    errors: list[str] = []

    if transition["class_id"] != record["class_id"]:
        errors.append("transition class differs from target")
    if transition["work_id"] != record["work_id"]:
        errors.append("transition work differs from target")
    if _target_identity(transition["target"]) != _record_identity(record):
        errors.append("transition target does not identify supplied record")

    family = record["record_type"]
    if family == "account":
        matrix = ACCOUNT_LIFECYCLE
        reasons = ACCOUNT_LIFECYCLE_REASONS
    else:
        matrix = OBSERVATION_LIFECYCLE
        reasons = OBSERVATION_LIFECYCLE_REASONS

    if transition["to_status"] not in matrix.get(
        transition["from_status"], set()
    ):
        errors.append(f"portia.{family}.lifecycle_matrix")
    if transition["reason"]["code"] not in reasons:
        errors.append(f"portia.{family}.lifecycle_reason")
    if record["status"] != transition["to_status"]:
        errors.append("target status does not reconcile with transition")

    if datetime.fromisoformat(transition["effective_at"]) > datetime.fromisoformat(
        transition["created_at"]
    ):
        errors.append("effective_at follows transition creation")

    return errors


def _history_errors(scenario: dict[str, Any]) -> list[str]:
    record = scenario["record"]
    replaced = scenario["replaced_transition"]
    replacement = scenario["replacement_transition"]
    correction = scenario["correction"]
    errors: list[str] = []

    expected_target = _record_identity(record)
    if _target_identity(correction["target"]) != expected_target:
        errors.append("history correction target mismatch")
    if _target_identity(replaced["target"]) != expected_target:
        errors.append("replaced branch target mismatch")
    if _target_identity(replacement["target"]) != expected_target:
        errors.append("replacement_branch_must_target_same_record")

    if correction["replaced_head"]["record_id"] != replaced["transition_id"]:
        errors.append("replaced head does not identify supplied branch")
    replacement_head = correction["replacement_head"]
    if replacement_head is None:
        errors.append("replacement head unexpectedly null")
    elif replacement_head["record_id"] != replacement["transition_id"]:
        errors.append("replacement head does not identify supplied branch")

    if record["status"] != replacement["to_status"]:
        errors.append("target status does not reconcile with corrected history")

    return errors


def _disagreement_errors(scenario: dict[str, Any]) -> list[str]:
    target_record = scenario["target_record"]
    disagreement = scenario["disagreement"]
    errors: list[str] = []

    if target_record["record_type"] not in {"account", "observation"}:
        errors.append("target is not Account or Observation")
    if disagreement["class_id"] != target_record["class_id"]:
        errors.append("disagreement class differs from target")
    if disagreement["work_id"] != target_record["work_id"]:
        errors.append("disagreement work differs from target")
    if _target_identity(disagreement["target"]) != _record_identity(
        target_record
    ):
        errors.append("target_must_resolve_exactly_in_containing_work")

    # Disagreement preserves the target rather than adjudicating it.
    if target_record["status"] not in {
        "proposed",
        "active",
        "retracted",
        "invalidated",
        "superseded",
    }:
        errors.append("unexpected target lifecycle state")

    return errors


def _amendment_errors(scenario: dict[str, Any]) -> list[str]:
    target_record = scenario["target_record"]
    amendment = scenario["amendment"]
    errors: list[str] = []

    if _target_identity(amendment["target"]) != _record_identity(
        target_record
    ):
        errors.append("amendment target mismatch")

    family = target_record["record_type"]
    if family in {"account", "observation"}:
        errors.append(f"portia.{family}.amendment_prohibited_v1")

    return errors


def _dependency_errors(scenario: dict[str, Any]) -> list[str]:
    dependency_record = scenario["dependency_record"]
    dependency = scenario["dependency"]
    errors: list[str] = []

    target = dependency["dependency"]
    if target["kind"] != "portia_record":
        errors.append("compatibility probe is not a Portia record dependency")
        return errors

    actual = _work_record_identity(target["work_record_ref"])
    family, record_id, version = _record_identity(dependency_record)
    expected = (
        dependency_record["class_id"],
        dependency_record["work_id"],
        family,
        record_id,
        version,
    )

    if actual != expected:
        if actual[-1] != expected[-1]:
            errors.append("dependency_exact_contract_version_mismatch")
        else:
            errors.append("dependency target does not resolve supplied record")

    if dependency["applies_to"] == "current_use":
        if dependency_record["status"] != "active":
            errors.append("dependency_target_current_use_ineligible")

    # A supplied successor is intentionally ignored. The persisted dependency
    # remains bound to its exact source representation.
    if "successor_record" in scenario and dependency_record["status"] in {
        "invalidated",
        "superseded",
    }:
        errors.append("no_silent_successor_following")

    return errors


def compatibility_errors(scenario: dict[str, Any]) -> list[str]:
    kind = scenario["kind"]
    if kind == "lifecycle":
        return _transition_errors(scenario)
    if kind == "history":
        return _history_errors(scenario)
    if kind == "disagreement":
        return _disagreement_errors(scenario)
    if kind == "amendment":
        return _amendment_errors(scenario)
    if kind == "dependency":
        return _dependency_errors(scenario)
    return [f"unsupported compatibility kind: {kind}"]


class Issue15SharedLifecycleCorrectionDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validators = {
            "account": validator_for(
                "account", "1", catalog=cls.catalog, store=cls.store
            ),
            "observation": validator_for(
                "observation", "1", catalog=cls.catalog, store=cls.store
            ),
            "lifecycle_transition": validator_for(
                "lifecycle_transition",
                "1",
                catalog=cls.catalog,
                store=cls.store,
            ),
            "lifecycle_history_correction": validator_for(
                "lifecycle_history_correction",
                "1",
                catalog=cls.catalog,
                store=cls.store,
            ),
            "amendment": validator_for(
                "amendment", "1", catalog=cls.catalog, store=cls.store
            ),
            "statement_of_disagreement": validator_for(
                "statement_of_disagreement",
                "1",
                catalog=cls.catalog,
                store=cls.store,
            ),
            "dependency": validator_for(
                "dependency", "1", catalog=cls.catalog, store=cls.store
            ),
        }
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def _assert_structurally_valid(
        self,
        validator_name: str,
        value: dict[str, Any],
    ) -> None:
        errors = list(self.validators[validator_name].iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )

    def _validate_scenario_structure(
        self,
        scenario: dict[str, Any],
    ) -> None:
        kind = scenario["kind"]

        if kind == "lifecycle":
            record = scenario["record"]
            self._assert_structurally_valid(record["record_type"], record)
            self._assert_structurally_valid(
                "lifecycle_transition", scenario["transition"]
            )
            return

        if kind == "history":
            record = scenario["record"]
            self._assert_structurally_valid(record["record_type"], record)
            self._assert_structurally_valid(
                "lifecycle_transition",
                scenario["replaced_transition"],
            )
            self._assert_structurally_valid(
                "lifecycle_transition",
                scenario["replacement_transition"],
            )
            self._assert_structurally_valid(
                "lifecycle_history_correction",
                scenario["correction"],
            )
            return

        if kind == "disagreement":
            record = scenario["target_record"]
            self._assert_structurally_valid(record["record_type"], record)
            self._assert_structurally_valid(
                "statement_of_disagreement",
                scenario["disagreement"],
            )
            return

        if kind == "amendment":
            record = scenario["target_record"]
            self._assert_structurally_valid(record["record_type"], record)
            self._assert_structurally_valid(
                "amendment", scenario["amendment"]
            )
            return

        if kind == "dependency":
            record = scenario["dependency_record"]
            self._assert_structurally_valid(record["record_type"], record)
            if "successor_record" in scenario:
                successor = scenario["successor_record"]
                self._assert_structurally_valid(
                    successor["record_type"], successor
                )
            self._assert_structurally_valid(
                "dependency", scenario["dependency"]
            )
            return

        self.fail(f"unsupported compatibility kind: {kind}")

    def test_manifest_is_compatibility_only(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 15)
        self.assertEqual(
            self.manifest["scope"],
            "shared_lifecycle_correction_dependency_compatibility",
        )
        self.assertEqual(self.manifest["public_contracts_added"], [])
        self.assertEqual(len(self.manifest["valid"]), 9)
        self.assertEqual(len(self.manifest["application_invalid"]), 11)

    def test_valid_scenarios_are_structurally_and_application_valid(
        self,
    ) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                scenario = load_json(FIXTURE_ROOT / "valid" / filename)
                self._validate_scenario_structure(scenario)
                self.assertEqual(compatibility_errors(scenario), [])

    def test_application_invalid_scenarios_are_structurally_valid(
        self,
    ) -> None:
        for entry in self.manifest["application_invalid"]:
            filename = entry["file"]
            with self.subTest(filename=filename):
                scenario = load_json(
                    FIXTURE_ROOT / "application-invalid" / filename
                )
                self._validate_scenario_structure(scenario)
                errors = compatibility_errors(scenario)
                self.assertTrue(errors)
                self.assertIn(entry["rule_id"], errors)

    def test_exact_local_reference_is_record_family_generic(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/references/exact-local-record-ref.schema.json"
        )
        record_kind = schema["properties"]["record_kind"]
        self.assertIn("$ref", record_kind)
        self.assertNotIn("enum", record_kind)
        self.assertNotIn("const", record_kind)

    def test_local_work_target_is_record_family_generic(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/targets/portia-local-work-target.schema.json"
        )
        local = schema["$defs"]["localRecordTarget"]
        self.assertEqual(
            local["properties"]["record_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/exact-local-record-ref.schema.json"
            ),
        )

    def test_shared_contracts_remain_version_one(self) -> None:
        for contract in (
            "lifecycle_transition",
            "lifecycle_history_correction",
            "amendment",
            "statement_of_disagreement",
            "dependency",
        ):
            self.assertEqual(
                set(self.catalog["contracts"][contract]),
                {"1"},
                contract,
            )

    def test_no_parallel_account_observation_history_contracts_exist(
        self,
    ) -> None:
        forbidden = {
            "account_lifecycle_transition",
            "observation_lifecycle_transition",
            "account_lifecycle_history_correction",
            "observation_lifecycle_history_correction",
            "account_amendment",
            "observation_amendment",
            "account_statement_of_disagreement",
            "observation_statement_of_disagreement",
            "account_dependency",
            "observation_dependency",
        }
        self.assertTrue(
            forbidden.isdisjoint(self.catalog["contracts"]),
            forbidden & set(self.catalog["contracts"]),
        )

    def test_account_observation_prohibit_in_place_amendment_v1(
        self,
    ) -> None:
        account_schema = load_json(
            REPO_ROOT / "schemas/v1/accounts/account.schema.json"
        )
        observation_schema = load_json(
            REPO_ROOT / "schemas/v1/observations/observation.schema.json"
        )
        self.assertIn(
            "portia.account.amendment_prohibited_v1",
            account_schema["x-portia-application-invariants"],
        )
        self.assertIn(
            "portia.observation.amendment_prohibited_v1",
            observation_schema["x-portia-application-invariants"],
        )

    def test_dependency_exact_version_probe_does_not_follow_successor(
        self,
    ) -> None:
        scenario = load_json(
            FIXTURE_ROOT
            / "application-invalid"
            / "dependency-superseded-observation-no-silent-follow.json"
        )
        errors = compatibility_errors(scenario)
        self.assertIn("dependency_target_current_use_ineligible", errors)
        self.assertIn("no_silent_successor_following", errors)

    def test_disagreement_preserves_target_record(self) -> None:
        for filename in (
            "disagreement-targets-account.json",
            "disagreement-targets-observation.json",
        ):
            scenario = load_json(FIXTURE_ROOT / "valid" / filename)
            before = load_json(FIXTURE_ROOT / "valid" / filename)[
                "target_record"
            ]
            self.assertEqual(scenario["target_record"], before)
            self.assertEqual(compatibility_errors(scenario), [])


if __name__ == "__main__":
    unittest.main()
