from __future__ import annotations

from datetime import date, datetime
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
    / "observation"
)

OBSERVATION_SCHEMA_PATH = "schemas/v1/observations/observation.schema.json"

OBSERVATION_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
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

OBSERVATION_SUPERSESSION_REASONS = {
    "observer_corrected",
    "instrument_corrected",
    "target_corrected",
    "observation_content_corrected",
    "measurement_corrected",
    "timing_corrected",
    "method_corrected",
    "provenance_corrected",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
}


def _parse_offset(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _observation_time_after_created(observation: dict[str, Any]) -> bool:
    observed = observation["observation_time"]
    created = _parse_offset(observation["created_at"])
    precision = observed["precision"]
    if precision == "exact":
        return _parse_offset(observed["at"]) > created
    if precision == "range":
        return _parse_offset(observed["ended_at"]) > created
    if precision == "date_only":
        return date.fromisoformat(observed["date"]) > created.date()
    if precision == "approximate" and observed["approximation"] == "about":
        return _parse_offset(observed["at"]) > created
    return False


def _measurement_types(observation: dict[str, Any]) -> set[str]:
    return {
        item["measure_type"]
        for item in observation["content"].get("measurements", [])
    }


def _work_record_identity(
    work_record_ref: dict[str, Any],
) -> tuple[str, str, str, str]:
    work_ref = work_record_ref["work_ref"]
    record_ref = work_record_ref["record_ref"]
    return (
        work_ref["class_id"],
        work_ref["work_id"],
        record_ref["record_id"],
        record_ref["contract_version"],
    )


def application_errors(observation: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if _parse_offset(observation["updated_at"]) < _parse_offset(
        observation["created_at"]
    ):
        errors.append("updated_at precedes created_at")

    if _observation_time_after_created(observation):
        errors.append("observation time follows record creation")

    creation = observation["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and observation["status"] != "proposed"
    ):
        errors.append(
            "paper/import activation requires accepted review history"
        )

    observer_kind = observation["observer"]["kind"]
    method = observation["method"]
    if observer_kind == "instrument" and method != "instrumented":
        errors.append("instrument observer requires instrumented method")
    if observer_kind == "human" and method == "instrumented":
        errors.append("instrumented method requires instrument observer")

    measure_types = _measurement_types(observation)
    if method == "manual_count" and not (
        {"count", "percentage"} & measure_types
    ):
        errors.append("manual_count requires count or percentage measurement")
    if method == "manual_timing" and not (
        {"duration", "latency"} & measure_types
    ):
        errors.append("manual_timing requires duration or latency measurement")
    if method == "artifact_review" and not observation.get(
        "source_artifacts"
    ):
        errors.append("artifact_review requires source artifact")

    supersedes = observation.get("supersedes", [])
    if supersedes:
        identities = [
            _work_record_identity(entry["work_record_ref"])
            for entry in supersedes
        ]
        reasons = [entry["reason"] for entry in supersedes]

        if len(identities) != len(set(identities)):
            errors.append("predecessor Observation identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        for entry in supersedes:
            work_ref = entry["work_record_ref"]["work_ref"]
            record_ref = entry["work_record_ref"]["record_ref"]
            same_work = (
                work_ref["class_id"] == observation["class_id"]
                and work_ref["work_id"] == observation["work_id"]
            )
            same_id = (
                record_ref["record_id"] == observation["observation_id"]
            )
            reason = entry["reason"]

            if same_work and same_id and reason != "contract_migrated":
                errors.append("Observation replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append(
                        "work-root correction requires different work"
                    )
                if not same_id:
                    errors.append(
                        "work-root correction must preserve Observation ID"
                    )
            elif reason != "contract_migrated" and not same_work:
                errors.append(
                    "ordinary Observation correction cannot cross work roots"
                )

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two predecessors"
                    )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append(
                        "non-consolidation correction is one-to-one"
                    )

    return errors


def _participant_ids(target: dict[str, Any]) -> set[str]:
    if target["kind"] == "event_participant":
        return {target["record_ref"]["record_id"]}
    if target["kind"] == "event_participants":
        return {
            item["record_ref"]["record_id"]
            for item in target["targets"]
        }
    return set()


def role_basis_errors(
    observation: dict[str, Any],
    role: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    observation_basis_ids = {
        entry["record_ref"]["record_id"]
        for entry in role.get("basis", [])
        if entry["kind"] == "observation_ref"
    }
    if observation["observation_id"] not in observation_basis_ids:
        errors.append("Role does not reference supplied Observation")

    if observation["work_id"] != role["work_id"]:
        errors.append("Observation and Role belong to different Events")

    if observation["status"] != "active":
        errors.append("Observation is not eligible for current use")

    role_participant = role["target"]["record_ref"]["record_id"]
    observation_participants = _participant_ids(observation["target"])
    if role_participant not in observation_participants:
        errors.append(
            "Observation target does not include Role Participant"
        )

    return errors


class Issue15ObservationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "observation",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.role_validator = validator_for(
            "event_participant_role",
            "3",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def test_manifest_has_expected_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 15)
        self.assertEqual(self.manifest["contract"], "observation")
        self.assertEqual(self.manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                self.assertEqual(application_errors(value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "invalid" / filename)
                self.assertTrue(list(self.validator.iter_errors(value)))

    def test_application_invalid_fixtures_are_structurally_valid(
        self,
    ) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "application-invalid" / filename
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertTrue(application_errors(value))

    def test_observation_is_cataloged_at_immutable_path(self) -> None:
        entry = self.catalog["contracts"]["observation"]["1"]
        self.assertEqual(entry["path"], OBSERVATION_SCHEMA_PATH)
        self.assertEqual(
            entry["schema_id"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/"
                + OBSERVATION_SCHEMA_PATH
            ),
        )
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        self.assertEqual(schema["$id"], entry["schema_id"])
        self.assertNotIn("/latest/", entry["schema_id"])
        self.assertNotIn("/current/", entry["schema_id"])

    def test_observation_envelope_is_closed_and_event_local(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "class_id",
                "work_id",
                "observation_id",
                "status",
                "target",
                "observer",
                "method",
                "content",
                "observation_time",
                "creation_source",
                "created_at",
                "created_by",
                "updated_at",
                "updated_by",
            },
        )
        self.assertEqual(
            schema["properties"]["record_type"]["const"],
            "observation",
        )
        for forbidden in (
            "finding",
            "classification",
            "hypothesis",
            "determination",
            "credibility",
            "reliability",
            "severity",
            "risk_score",
            "policy_violation",
            "diagnosis",
            "intent",
            "valence",
            "concerning",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_observer_union_is_human_or_instrument(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        human = schema["$defs"]["humanObserver"]
        instrument = schema["$defs"]["instrumentObserver"]
        self.assertEqual(human["properties"]["kind"]["const"], "human")
        self.assertEqual(
            instrument["properties"]["kind"]["const"],
            "instrument",
        )
        self.assertEqual(
            set(instrument["properties"]["instrument_type"]["enum"]),
            {"timer", "counter", "software", "sensor", "other"},
        )
        for forbidden in (
            "accuracy",
            "calibration",
            "scientific_validity",
            "clinical_validity",
            "institutional_approval",
        ):
            self.assertNotIn(forbidden, instrument["properties"])

    def test_method_vocabulary_matches_adr_0011(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        self.assertEqual(
            set(schema["properties"]["method"]["enum"]),
            {
                "live_direct",
                "artifact_review",
                "manual_count",
                "manual_timing",
                "instrumented",
                "other",
            },
        )

    def test_measurement_vocabulary_and_units_are_bounded(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        defs = schema["$defs"]
        self.assertEqual(
            defs["countMeasurement"]["properties"]["unit"]["const"],
            "count",
        )
        self.assertEqual(
            defs["percentageMeasurement"]["properties"]["unit"]["const"],
            "percent",
        )
        self.assertEqual(
            set(
                defs["durationMeasurement"]["properties"]["unit"]["enum"]
            ),
            {"milliseconds", "seconds", "minutes", "hours"},
        )
        self.assertEqual(
            set(
                defs["latencyMeasurement"]["properties"]["unit"]["enum"]
            ),
            {"milliseconds", "seconds", "minutes", "hours"},
        )
        self.assertEqual(
            defs["percentageMeasurement"]["properties"]["value"]["minimum"],
            0,
        )
        self.assertEqual(
            defs["percentageMeasurement"]["properties"]["value"]["maximum"],
            100,
        )

    def test_observation_has_no_valence_or_interpretation_field(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        self.assertNotIn("valence", schema["properties"])
        self.assertNotIn("positive", schema["properties"])
        self.assertNotIn("neutral", schema["properties"])
        self.assertNotIn("concerning", schema["properties"])
        self.assertNotIn("interpretation", schema["properties"])

    def test_observation_has_no_in_place_amendment_surface(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        for forbidden in (
            "amendable_paths",
            "amendment",
            "nonmaterial_metadata",
        ):
            self.assertNotIn(forbidden, schema["properties"])
        self.assertIn(
            "portia.observation.amendment_prohibited_v1",
            schema["x-portia-application-invariants"],
        )

    def test_paper_preallocation_is_structurally_prohibited(self) -> None:
        value = load_json(
            FIXTURE_ROOT / "invalid" / "paper-preallocated.json"
        )
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_lifecycle_matrix_matches_adr_0011(self) -> None:
        self.assertEqual(
            OBSERVATION_LIFECYCLE,
            {
                "proposed": {"active", "invalidated", "superseded"},
                "active": {"invalidated", "superseded"},
                "invalidated": {"superseded"},
                "superseded": set(),
            },
        )

    def test_lifecycle_reason_inventory_matches_adr_0011(self) -> None:
        self.assertEqual(
            OBSERVATION_LIFECYCLE_REASONS,
            {
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
            },
        )
        self.assertNotIn("retracted", OBSERVATION_LIFECYCLE)

    def test_supersession_reason_inventory_matches_design(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        actual = set(
            schema["$defs"]["supersessionEntry"]
            ["properties"]["reason"]["enum"]
        )
        self.assertEqual(actual, OBSERVATION_SUPERSESSION_REASONS)

    def test_role_basis_compatibility_scenarios(self) -> None:
        manifest = load_json(
            FIXTURE_ROOT / "role-compatibility" / "manifest.json"
        )

        for filename in manifest["valid"]:
            with self.subTest(valid=filename):
                scenario = load_json(
                    FIXTURE_ROOT
                    / "role-compatibility"
                    / "valid"
                    / filename
                )
                self.assertFalse(
                    list(self.validator.iter_errors(scenario["observation"]))
                )
                self.assertFalse(
                    list(self.role_validator.iter_errors(scenario["role"]))
                )
                self.assertEqual(
                    role_basis_errors(
                        scenario["observation"], scenario["role"]
                    ),
                    [],
                )

        for filename in manifest["application_invalid"]:
            with self.subTest(application_invalid=filename):
                scenario = load_json(
                    FIXTURE_ROOT
                    / "role-compatibility"
                    / "application-invalid"
                    / filename
                )
                self.assertFalse(
                    list(self.validator.iter_errors(scenario["observation"]))
                )
                self.assertFalse(
                    list(self.role_validator.iter_errors(scenario["role"]))
                )
                self.assertTrue(
                    role_basis_errors(
                        scenario["observation"], scenario["role"]
                    )
                )

        for filename in manifest["structural_invalid"]:
            with self.subTest(structural_invalid=filename):
                scenario = load_json(
                    FIXTURE_ROOT
                    / "role-compatibility"
                    / "structural-invalid"
                    / filename
                )
                self.assertFalse(
                    list(self.validator.iter_errors(scenario["observation"]))
                )
                self.assertTrue(
                    list(self.role_validator.iter_errors(scenario["role"]))
                )

    def test_reported_involved_observation_is_only_supplemental(self) -> None:
        scenario = load_json(
            FIXTURE_ROOT
            / "role-compatibility"
            / "valid"
            / "reported-involved-supplemental.json"
        )
        role = scenario["role"]
        self.assertEqual(role["role_type"], "reported_involved")
        self.assertTrue(
            any(item["kind"] == "account_ref" for item in role["basis"])
        )
        self.assertTrue(
            any(
                item["kind"] == "observation_ref"
                for item in role["basis"]
            )
        )

    def test_application_invariant_inventory_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_SCHEMA_PATH)
        self.assertEqual(
            set(schema["x-portia-application-invariants"]),
            {
                "portia.observation.canonical_storage_scope",
                "portia.observation.path_identity_agreement",
                "portia.observation.parent_event_resolution",
                "portia.observation.target_resolution",
                "portia.observation.target_same_event",
                "portia.observation.observer_resolution",
                "portia.observation.observer_recorder_distinction",
                "portia.observation.instrument_method_compatibility",
                "portia.observation.method_content_compatibility",
                "portia.observation.timestamp_chronology",
                "portia.observation.observation_time_chronology",
                "portia.observation.creation_provenance_immutable",
                "portia.observation.paper_provenance_agreement",
                "portia.observation.paper_activation_requires_review_history",
                "portia.observation.import_activation_requires_review_history",
                "portia.observation.measurement_value_unit_compatibility",
                "portia.observation.source_artifact_resolution",
                "portia.observation.external_reference_inert",
                "portia.observation.lifecycle_matrix",
                "portia.observation.lifecycle_history_reconciliation",
                "portia.observation.current_use_eligibility",
                "portia.observation.amendment_prohibited_v1",
                "portia.observation.predecessor_resolution",
                "portia.observation.predecessor_identity_unique",
                "portia.observation.self_supersession",
                "portia.observation.supersession_reason_uniform",
                "portia.observation.replacement_topology",
                "portia.observation.supersession_cycle",
                "portia.observation.ownership_reconciliation",
                "portia.observation.successor_effectiveness",
                "portia.observation.incoming_reference_complete",
                "portia.observation.no_silent_successor_following",
                "portia.observation.role_basis_target_alignment",
                "portia.observation.no_automatic_interpretation",
                "portia.observation.no_automatic_finding",
            },
        )


if __name__ == "__main__":
    unittest.main()
