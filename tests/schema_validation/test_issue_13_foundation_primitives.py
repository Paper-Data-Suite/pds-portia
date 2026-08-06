from __future__ import annotations

from pathlib import Path
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


EXPECTED_CONTRACT_PATHS = {
    "portia_operation_id": (
        "schemas/v1/identifiers/portia-operation-id.schema.json"
    ),
    "portia_operation_step_id": (
        "schemas/v1/identifiers/portia-operation-step-id.schema.json"
    ),
    "portia_lock_id": (
        "schemas/v1/identifiers/portia-lock-id.schema.json"
    ),
    "portia_quarantine_id": (
        "schemas/v1/identifiers/portia-quarantine-id.schema.json"
    ),
    "portia_finding_acknowledgement_id": (
        "schemas/v1/identifiers/"
        "portia-finding-acknowledgement-id.schema.json"
    ),
    "portia_finding_suppression_id": (
        "schemas/v1/identifiers/"
        "portia-finding-suppression-id.schema.json"
    ),
    "portia_derived_generation_id": (
        "schemas/v1/identifiers/"
        "portia-derived-generation-id.schema.json"
    ),
    "workspace_relative_path": (
        "schemas/v1/common/workspace-relative-path.schema.json"
    ),
    "sha256_digest": (
        "schemas/v1/common/sha256-digest.schema.json"
    ),
    "content_fingerprint": (
        "schemas/v1/common/content-fingerprint.schema.json"
    ),
    "operation_ref": (
        "schemas/v1/references/operation-ref.schema.json"
    ),
    "operation_journal_ref": (
        "schemas/v1/references/operation-journal-ref.schema.json"
    ),
    "quarantine_ref": (
        "schemas/v1/references/quarantine-ref.schema.json"
    ),
    "derived_generation_ref": (
        "schemas/v1/references/derived-generation-ref.schema.json"
    ),
}

VALID_IDENTIFIERS = {
    "portia_operation_id": (
        "op_a",
        "op_0001",
        "op_Mixed_Case-9",
    ),
    "portia_operation_step_id": (
        "step_a",
        "step_commit_01",
        "step_Mixed-9",
    ),
    "portia_lock_id": (
        "lock_" + ("a" * 64),
        "lock_" + ("0123456789abcdef" * 4),
    ),
    "portia_quarantine_id": (
        "qnt_a",
        "qnt_recovery-01",
    ),
    "portia_finding_acknowledgement_id": (
        "fack_a",
        "fack_review_01",
    ),
    "portia_finding_suppression_id": (
        "fsup_a",
        "fsup_warning-01",
    ),
    "portia_derived_generation_id": (
        "dgen_a",
        "dgen_current_01",
    ),
}

INVALID_IDENTIFIERS = {
    "portia_operation_id": (
        "op_",
        "operation_a",
        "op_.bad",
        "OP_a",
        "op_a/b",
    ),
    "portia_operation_step_id": (
        "step_",
        "step_.bad",
        "Step_a",
        "step_a/b",
    ),
    "portia_lock_id": (
        "lock_" + ("a" * 63),
        "lock_" + ("A" * 64),
        "lock_" + ("g" * 64),
        "lock_a",
    ),
    "portia_quarantine_id": (
        "qnt_",
        "qnt_.bad",
        "QNT_a",
    ),
    "portia_finding_acknowledgement_id": (
        "fack_",
        "fack_.bad",
        "FACK_a",
    ),
    "portia_finding_suppression_id": (
        "fsup_",
        "fsup_.bad",
        "FSUP_a",
    ),
    "portia_derived_generation_id": (
        "dgen_",
        "dgen_.bad",
        "DGEN_a",
    ),
}


class Issue13FoundationPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def assert_valid(self, contract: str, value: object) -> None:
        validator = validator_for(
            contract,
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        errors = list(validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )

    def assert_invalid(self, contract: str, value: object) -> None:
        validator = validator_for(
            contract,
            "1",
            catalog=self.catalog,
            store=self.store,
        )
        self.assertTrue(list(validator.iter_errors(value)))

    def test_contracts_are_cataloged_at_immutable_paths(self) -> None:
        for contract, expected_path in EXPECTED_CONTRACT_PATHS.items():
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["1"]
                self.assertEqual(entry["path"], expected_path)
                self.assertEqual(
                    entry["schema_id"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/"
                        + expected_path
                    ),
                )
                schema = load_json(REPO_ROOT / expected_path)
                self.assertEqual(schema["$id"], entry["schema_id"])
                self.assertNotIn("/latest/", entry["schema_id"])
                self.assertNotIn("/current/", entry["schema_id"])

    def test_identifier_prefix_and_case_contracts(self) -> None:
        for contract, values in VALID_IDENTIFIERS.items():
            for value in values:
                with self.subTest(contract=contract, value=value):
                    self.assert_valid(contract, value)

        for contract, values in INVALID_IDENTIFIERS.items():
            for value in values:
                with self.subTest(contract=contract, value=value):
                    self.assert_invalid(contract, value)

    def test_workspace_relative_paths(self) -> None:
        valid = (
            "classes/class_1/modules/portia/work/evt_1/work.json",
            "portia/operations/op_a/revisions/1.json",
            "portia/derived/current_state_view/current.json",
            "folder name/file name.json",
        )
        invalid = (
            "",
            "/absolute/path.json",
            "C:/workspace/file.json",
            "https://example.test/file.json",
            r"classes\class_1\file.json",
            "classes//file.json",
            "classes/./file.json",
            "classes/../file.json",
            "../file.json",
            "classes/",
            "file\x00name.json",
        )
        for value in valid:
            with self.subTest(valid=value):
                self.assert_valid("workspace_relative_path", value)
        for value in invalid:
            with self.subTest(invalid=value):
                self.assert_invalid("workspace_relative_path", value)

    def test_sha256_digest_requires_exact_lowercase_hex(self) -> None:
        self.assert_valid("sha256_digest", "a" * 64)
        self.assert_valid(
            "sha256_digest",
            "0123456789abcdef" * 4,
        )
        for value in (
            "a" * 63,
            "a" * 65,
            "A" * 64,
            "g" * 64,
            "",
        ):
            with self.subTest(value=value):
                self.assert_invalid("sha256_digest", value)

    def test_content_fingerprint_is_closed(self) -> None:
        valid = {
            "algorithm": "sha256",
            "digest": "a" * 64,
            "byte_length": 0,
        }
        self.assert_valid("content_fingerprint", valid)
        self.assert_invalid(
            "content_fingerprint",
            {**valid, "algorithm": "sha512"},
        )
        self.assert_invalid(
            "content_fingerprint",
            {**valid, "byte_length": -1},
        )
        self.assert_invalid(
            "content_fingerprint",
            {**valid, "extra": True},
        )

    def test_operation_reference_is_stable_not_exact_revision(self) -> None:
        self.assert_valid(
            "operation_ref",
            {"operation_id": "op_example"},
        )
        self.assert_invalid(
            "operation_ref",
            {
                "operation_id": "op_example",
                "journal_revision": 1,
            },
        )

    def test_exact_revision_references_are_closed(self) -> None:
        valid_values = (
            (
                "operation_journal_ref",
                {
                    "operation_id": "op_example",
                    "journal_revision": 1,
                    "contract_version": "1",
                },
            ),
            (
                "quarantine_ref",
                {
                    "quarantine_id": "qnt_example",
                    "quarantine_revision": 2,
                    "contract_version": "1",
                },
            ),
            (
                "derived_generation_ref",
                {
                    "generation_id": "dgen_example",
                    "contract_version": "1",
                },
            ),
        )
        for contract, value in valid_values:
            with self.subTest(contract=contract):
                self.assert_valid(contract, value)
                self.assert_invalid(
                    contract,
                    {**value, "unexpected": True},
                )

        self.assert_invalid(
            "operation_journal_ref",
            {
                "operation_id": "op_example",
                "journal_revision": 0,
                "contract_version": "1",
            },
        )
        self.assert_invalid(
            "quarantine_ref",
            {
                "quarantine_id": "qnt_example",
                "quarantine_revision": 0,
                "contract_version": "1",
            },
        )

    def test_valid_operation_id_is_wire_compatible_with_finding_target(self) -> None:
        operation_ref_schema = load_json(
            REPO_ROOT
            / "schemas/v1/references/operation-ref.schema.json"
        )
        integrity_schema = load_json(
            REPO_ROOT
            / "schemas/v1/projections/integrity-finding.schema.json"
        )
        self.assertEqual(
            operation_ref_schema["properties"]["operation_id"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/identifiers/"
                "portia-operation-id.schema.json"
            ),
        )

        finding_target = integrity_schema["$defs"]["findingTarget"]
        operation_target_ref = {"$ref": "#/$defs/operationTarget"}
        self.assertIn(
            operation_target_ref,
            finding_target["oneOf"],
        )

        operation_target = integrity_schema["$defs"]["operationTarget"]
        self.assertEqual(
            operation_target["properties"]["kind"]["const"],
            "operation",
        )
        self.assertIn(
            "operation_id",
            operation_target["required"],
        )
        self.assertFalse(
            operation_target["additionalProperties"]
        )
        self.assertEqual(
            operation_target["properties"]["operation_id"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/identifiers/"
                "structurally-safe-external-id.schema.json"
            ),
        )


if __name__ == "__main__":
    unittest.main()
