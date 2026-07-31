from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from .schema_support import (
        SchemaCatalogError,
        build_schema_store,
        load_validated_catalog_and_store,
        schema_id_for,
    )
except ImportError:
    from schema_support import (
        SchemaCatalogError,
        build_schema_store,
        load_validated_catalog_and_store,
        schema_id_for,
    )


EXPECTED_LEGACY_SCHEMA_IDS = {
    "event": (
        "https://paper-data-suite.github.io/"
        "pds-portia/schemas/event.schema.json"
    ),
    "event_participant": (
        "https://paper-data-suite.github.io/"
        "pds-portia/schemas/event-participant.schema.json"
    ),
    "event_participant_role": (
        "https://paper-data-suite.github.io/"
        "pds-portia/schemas/event-participant-role.schema.json"
    ),
}


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )


class SchemaCatalogIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = (
            load_validated_catalog_and_store()
        )

    def test_expected_legacy_contracts_are_cataloged(self) -> None:
        self.assertTrue(
            set(EXPECTED_LEGACY_SCHEMA_IDS)
            <= set(self.catalog["contracts"])
        )
        for contract_name, expected_id in (
            EXPECTED_LEGACY_SCHEMA_IDS.items()
        ):
            with self.subTest(contract=contract_name):
                self.assertEqual(
                    schema_id_for(
                        contract_name,
                        "1",
                        self.catalog,
                    ),
                    expected_id,
                )

    def test_catalog_covers_all_schemas(self) -> None:
        cataloged_ids = {
            entry["schema_id"]
            for versions in self.catalog["contracts"].values()
            for entry in versions.values()
        }
        self.assertEqual(
            cataloged_ids,
            set(self.store.schemas_by_id),
        )

    def test_catalog_paths_match_loaded_resources(self) -> None:
        for contract_name, versions in (
            self.catalog["contracts"].items()
        ):
            for version, entry in versions.items():
                with self.subTest(
                    contract=contract_name,
                    version=version,
                ):
                    self.assertIn(
                        entry["schema_id"],
                        self.store.paths_by_id,
                    )

    def test_unknown_contract_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            SchemaCatalogError,
            "Unknown schema contract/version",
        ):
            schema_id_for("event", "999", self.catalog)


class SchemaResourceFailureTests(unittest.TestCase):
    def test_duplicate_canonical_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            schema_id = "https://example.test/duplicate"
            first = root / "first.schema.json"
            second = root / "second.schema.json"
            for path in (first, second):
                write_json(
                    path,
                    {
                        "$schema": (
                            "https://json-schema.org/"
                            "draft/2020-12/schema"
                        ),
                        "$id": schema_id,
                        "type": "object",
                    },
                )
            with self.assertRaisesRegex(
                SchemaCatalogError,
                "Duplicate canonical schema ID",
            ):
                build_schema_store([first, second])

    def test_unresolved_reference_is_rejected_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "broken.schema.json"
            write_json(
                schema_path,
                {
                    "$schema": (
                        "https://json-schema.org/"
                        "draft/2020-12/schema"
                    ),
                    "$id": "https://example.test/broken.schema.json",
                    "type": "object",
                    "properties": {
                        "value": {
                            "$ref": (
                                "https://example.test/"
                                "missing.schema.json"
                            )
                        }
                    },
                },
            )
            with self.assertRaisesRegex(
                SchemaCatalogError,
                r"Unresolved \$ref",
            ):
                build_schema_store([schema_path])

    def test_missing_schema_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "missing-id.schema.json"
            write_json(
                schema_path,
                {
                    "$schema": (
                        "https://json-schema.org/"
                        "draft/2020-12/schema"
                    ),
                    "type": "object",
                },
            )
            with self.assertRaisesRegex(
                SchemaCatalogError,
                r"missing a nonempty string \$id",
            ):
                build_schema_store([schema_path])


if __name__ == "__main__":
    unittest.main()
