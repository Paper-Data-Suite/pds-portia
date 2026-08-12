from __future__ import annotations

from datetime import date
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


IDENTIFIER_FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-18"
    / "identifiers"
)
SCHEDULE_FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-18"
    / "planned-schedule"
)

IDENTIFIER_SPECS = {
    "portia_support_process_participant_id": (
        "spp_",
        "schemas/v1/identifiers/portia-support-process-participant-id.schema.json",
    ),
    "portia_support_need_id": (
        "spn_",
        "schemas/v1/identifiers/portia-support-need-id.schema.json",
    ),
    "portia_support_goal_id": (
        "spg_",
        "schemas/v1/identifiers/portia-support-goal-id.schema.json",
    ),
    "portia_support_id": (
        "spt_",
        "schemas/v1/identifiers/portia-support-id.schema.json",
    ),
    "portia_intervention_id": (
        "int_",
        "schemas/v1/identifiers/portia-intervention-id.schema.json",
    ),
    "portia_implementation_id": (
        "imp_",
        "schemas/v1/identifiers/portia-implementation-id.schema.json",
    ),
    "portia_fidelity_id": (
        "fid_",
        "schemas/v1/identifiers/portia-fidelity-id.schema.json",
    ),
}
PLANNED_SCHEDULE_PATH = (
    "schemas/v1/support-processes/planned-schedule.schema.json"
)


def _application_errors(value: dict) -> list[str]:
    errors: list[str] = []

    window = value.get("window")
    if isinstance(window, dict):
        starts = (
            date.fromisoformat(window["starts_on"])
            if "starts_on" in window
            else None
        )
        ends = (
            date.fromisoformat(window["ends_on"])
            if "ends_on" in window
            else None
        )
        review = (
            date.fromisoformat(window["review_on"])
            if "review_on" in window
            else None
        )
        if starts is not None and ends is not None and ends < starts:
            errors.append("ends_on precedes starts_on")
        if starts is not None and review is not None and review < starts:
            errors.append("review_on precedes starts_on")

    duration = value.get("planned_duration")
    if (
        isinstance(duration, dict)
        and duration.get("kind") == "range_minutes"
        and duration["minimum_minutes"] > duration["maximum_minutes"]
    ):
        errors.append("minimum_minutes exceeds maximum_minutes")

    return errors


class Issue18PrimitiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.identifier_manifest = load_json(
            IDENTIFIER_FIXTURE_ROOT / "manifest.json"
        )
        cls.schedule_manifest = load_json(
            SCHEDULE_FIXTURE_ROOT / "manifest.json"
        )
        cls.identifier_validators = {
            name: validator_for(
                name,
                "1",
                catalog=cls.catalog,
                store=cls.store,
            )
            for name in IDENTIFIER_SPECS
        }
        cls.schedule_validator = validator_for(
            "planned_schedule",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )

    def test_manifest_metadata(self) -> None:
        self.assertEqual(self.identifier_manifest["manifest_version"], "1")
        self.assertEqual(self.identifier_manifest["issue"], 18)
        self.assertEqual(
            set(self.identifier_manifest["contracts"]),
            set(IDENTIFIER_SPECS),
        )
        self.assertEqual(self.schedule_manifest["manifest_version"], "1")
        self.assertEqual(self.schedule_manifest["issue"], 18)
        self.assertEqual(self.schedule_manifest["contract"], "planned_schedule")
        self.assertEqual(self.schedule_manifest["version"], "1")

    def test_catalog_entries_are_exact(self) -> None:
        contracts = self.catalog["contracts"]
        base = "https://paper-data-suite.github.io/pds-portia/"
        for name, (_prefix, path) in IDENTIFIER_SPECS.items():
            with self.subTest(contract=name):
                self.assertEqual(
                    contracts[name]["1"],
                    {
                        "schema_id": base + path,
                        "path": path,
                    },
                )
        self.assertEqual(
            contracts["planned_schedule"]["1"],
            {
                "schema_id": base + PLANNED_SCHEDULE_PATH,
                "path": PLANNED_SCHEDULE_PATH,
            },
        )

    def test_identifier_fixtures(self) -> None:
        for name, validator in self.identifier_validators.items():
            contract = self.identifier_manifest["contracts"][name]
            self.assertEqual(contract["version"], "1")
            for value in contract["valid"]:
                with self.subTest(contract=name, value=value, expected="valid"):
                    self.assertFalse(list(validator.iter_errors(value)))
            for value in contract["invalid"]:
                with self.subTest(contract=name, value=value, expected="invalid"):
                    self.assertTrue(list(validator.iter_errors(value)))

    def test_identifier_length_boundaries(self) -> None:
        for name, (prefix, _path) in IDENTIFIER_SPECS.items():
            validator = self.identifier_validators[name]
            at_limit = prefix + ("a" * (128 - len(prefix)))
            too_long = prefix + ("a" * (129 - len(prefix)))
            with self.subTest(contract=name):
                self.assertEqual(len(at_limit), 128)
                self.assertFalse(list(validator.iter_errors(at_limit)))
                self.assertTrue(list(validator.iter_errors(too_long)))

    def test_identifier_families_do_not_cross_validate(self) -> None:
        items = list(IDENTIFIER_SPECS.items())
        for index, (name, (_prefix, _path)) in enumerate(items):
            other_name, (other_prefix, _other_path) = items[(index + 1) % len(items)]
            with self.subTest(contract=name, wrong_family=other_name):
                self.assertTrue(
                    list(
                        self.identifier_validators[name].iter_errors(
                            other_prefix + "example"
                        )
                    )
                )

    def test_planned_schedule_valid_and_structural_invalid_fixtures(self) -> None:
        for item in self.schedule_manifest["valid"]:
            with self.subTest(name=item["name"], expected="valid"):
                self.assertFalse(
                    list(self.schedule_validator.iter_errors(item["value"]))
                )
                self.assertEqual(_application_errors(item["value"]), [])

        for item in self.schedule_manifest["structural_invalid"]:
            with self.subTest(name=item["name"], expected="structural-invalid"):
                self.assertTrue(
                    list(self.schedule_validator.iter_errors(item["value"]))
                )

    def test_planned_schedule_application_invalid_fixtures(self) -> None:
        for item in self.schedule_manifest["application_invalid"]:
            with self.subTest(name=item["name"]):
                self.assertFalse(
                    list(self.schedule_validator.iter_errors(item["value"]))
                )
                self.assertIn(
                    item["expected_error"],
                    _application_errors(item["value"]),
                )

    def test_planned_schedule_does_not_encode_implementation_or_outcome(self) -> None:
        schema = load_json(REPO_ROOT / PLANNED_SCHEDULE_PATH)
        serialized = str(schema).lower()
        self.assertNotIn("actual_count", serialized)
        self.assertNotIn("implemented_count", serialized)
        self.assertNotIn("effectiveness", serialized)
        self.assertNotIn("goal_attainment", serialized)
        self.assertIn("no_implementation_claim", serialized)


if __name__ == "__main__":
    unittest.main()
