from __future__ import annotations

from datetime import datetime
import hashlib
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


FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-13"
)
FAMILIES = (
    "source-snapshot",
    "derived-index-metadata",
    "derived-current-pointer",
)


def canonical_snapshot_digest(snapshot: dict[str, object]) -> str:
    payload = {
        key: snapshot[key]
        for key in (
            "snapshot_algorithm",
            "projection_kind",
            "projection_scope",
            "authorization_scope",
            "discovery_roots",
            "source_contracts",
            "entries",
        )
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def snapshot_application_errors(snapshot: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if snapshot["source_snapshot_digest"] != canonical_snapshot_digest(snapshot):
        errors.append("source snapshot digest mismatch")
    entries = snapshot["entries"]
    paths = [entry["workspace_relative_path"] for entry in entries]
    if paths != sorted(paths):
        errors.append("source entries are not deterministically sorted")
    if len(paths) != len(set(paths)):
        errors.append("source path appears more than once")
    return errors


def metadata_application_errors(metadata: dict[str, object]) -> list[str]:
    errors: list[str] = []
    snapshot = metadata["source_snapshot"]
    if metadata["projection_kind"] != snapshot["projection_kind"]:
        errors.append("projection kind disagrees with snapshot")
    if metadata["projection_scope"] != snapshot["projection_scope"]:
        errors.append("projection scope disagrees with snapshot")
    if metadata["authorization_scope"] != snapshot["authorization_scope"]:
        errors.append("authorization scope disagrees with snapshot")
    generated_at = datetime.fromisoformat(metadata["generated_at"].replace("Z", "+00:00"))
    observed_at = datetime.fromisoformat(snapshot["observed_at"].replace("Z", "+00:00"))
    if generated_at < observed_at:
        errors.append("generation predates source observation")
    errors.extend(snapshot_application_errors(snapshot))
    return errors


KNOWN_GENERATIONS = {
    "dgen_current_state_01": {
        "projection_kind": "current_state_view",
        "projection_scope": {
            "scope": "work",
            "work_ref": {
                "module_id": "portia",
                "class_id": "class_english10_p2",
                "work_id": "evt_example",
                "work_kind": "event",
                "contract_version": "2",
            },
        },
        "contract_version": "1",
    }
}


def pointer_application_errors(pointer: dict[str, object]) -> list[str]:
    generation_ref = pointer["generation_ref"]
    generation = KNOWN_GENERATIONS.get(generation_ref["generation_id"])
    if generation is None:
        return ["referenced generation is unknown"]
    errors: list[str] = []
    if pointer["projection_kind"] != generation["projection_kind"]:
        errors.append("pointer projection kind mismatch")
    if pointer["projection_scope"] != generation["projection_scope"]:
        errors.append("pointer projection scope mismatch")
    if generation_ref["contract_version"] != generation["contract_version"]:
        errors.append("generation contract version mismatch")
    return errors


class Issue13DerivedProjectionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str):
        return validator_for(contract, "1", catalog=self.catalog, store=self.store)

    def test_manifests_have_expected_contracts(self) -> None:
        expected = {
            "source-snapshot": "source_snapshot",
            "derived-index-metadata": "derived_index_metadata",
            "derived-current-pointer": "derived_current_pointer",
        }
        for family, contract in expected.items():
            with self.subTest(family=family):
                manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 13)
                self.assertEqual(manifest["contract"], contract)
                self.assertEqual(manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for family in FAMILIES:
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            validator = self.validator(manifest["contract"])
            for filename in manifest["valid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "valid" / filename)
                    errors = list(validator.iter_errors(value))
                    self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_invalid_fixtures_fail(self) -> None:
        for family in FAMILIES:
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            validator = self.validator(manifest["contract"])
            for filename in manifest["invalid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "invalid" / filename)
                    self.assertTrue(list(validator.iter_errors(value)))

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        checks = {
            "source-snapshot": (self.validator("source_snapshot"), snapshot_application_errors),
            "derived-index-metadata": (self.validator("derived_index_metadata"), metadata_application_errors),
            "derived-current-pointer": (self.validator("derived_current_pointer"), pointer_application_errors),
        }
        for family, (validator, checker) in checks.items():
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            for filename in manifest["application_invalid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "application-invalid" / filename)
                    structural_errors = list(validator.iter_errors(value))
                    self.assertFalse(structural_errors, "\n".join(error.message for error in structural_errors))
                    self.assertTrue(checker(value))

    def test_valid_values_pass_application_checks(self) -> None:
        checks = {
            "source-snapshot": snapshot_application_errors,
            "derived-index-metadata": metadata_application_errors,
            "derived-current-pointer": pointer_application_errors,
        }
        for family, checker in checks.items():
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            for filename in manifest["valid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "valid" / filename)
                    self.assertEqual(checker(value), [])

    def test_snapshot_digest_excludes_observation_time(self) -> None:
        value = load_json(
            FIXTURE_ROOT
            / "source-snapshot"
            / "valid"
            / "complete-current-state-view.json"
        )
        original = canonical_snapshot_digest(value)
        value["observed_at"] = "2030-01-01T00:00:00Z"
        self.assertEqual(canonical_snapshot_digest(value), original)

    def test_generation_metadata_is_complete_only(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "projections"
            / "derived-index-metadata.schema.json"
        )
        self.assertEqual(schema["properties"]["generation_state"]["const"], "complete")
        for field in (
            "builder",
            "source_snapshot",
            "data_artifact",
            "validation",
            "generating_operation",
        ):
            self.assertIn(field, schema["required"])

    def test_pointer_contains_no_freshness_claim(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "projections"
            / "derived-current-pointer.schema.json"
        )
        for forbidden in (
            "generated_at",
            "updated_at",
            "fresh",
            "source_snapshot_digest",
            "authorization_scope",
        ):
            self.assertNotIn(forbidden, schema["properties"])
        self.assertFalse(schema["additionalProperties"])

    def test_projection_kind_vocabularies_match(self) -> None:
        filenames = (
            "source-snapshot.schema.json",
            "derived-index-metadata.schema.json",
            "derived-current-pointer.schema.json",
        )
        vocabularies = []
        for filename in filenames:
            schema = load_json(REPO_ROOT / "schemas" / "v1" / "projections" / filename)
            vocabularies.append(tuple(schema["properties"]["projection_kind"]["enum"]))
        self.assertTrue(all(value == vocabularies[0] for value in vocabularies[1:]))

    def test_public_contract_paths_match_catalog(self) -> None:
        expected = {
            "source_snapshot": "schemas/v1/projections/source-snapshot.schema.json",
            "derived_index_metadata": "schemas/v1/projections/derived-index-metadata.schema.json",
            "derived_current_pointer": "schemas/v1/projections/derived-current-pointer.schema.json",
        }
        for contract, path in expected.items():
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["1"]
                self.assertEqual(entry["path"], path)
                self.assertEqual(entry["schema_id"], "https://paper-data-suite.github.io/pds-portia/" + path)
                schema = load_json(REPO_ROOT / path)
                self.assertEqual(schema["$id"], entry["schema_id"])


if __name__ == "__main__":
    unittest.main()
