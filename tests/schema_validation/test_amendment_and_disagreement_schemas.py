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

CONTRACTS = {
    "amendment": "schemas/v1/corrections/amendment.schema.json",
    "statement_of_disagreement": (
        "schemas/v1/corrections/statement-of-disagreement.schema.json"
    ),
}
FIXTURE_DIRECTORY = (
    FIXTURE_ROOT / "issue-12" / "amendment-and-disagreement"
)
PUBLIC_SCHEMA_PREFIX = "https://paper-data-suite.github.io/pds-portia/"


class AmendmentAndDisagreementSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, name: str):
        return validator_for(
            name, "1", catalog=self.catalog, store=self.store
        )

    def schema(self, name: str):
        return self.store.schema_for_id(
            schema_id_for(name, "1", self.catalog)
        )

    def contract_for_path(self, path: str) -> str:
        return next(name for name, value in CONTRACTS.items() if value == path)

    def test_contracts_are_cataloged_with_canonical_path_ids(self) -> None:
        for name, path in CONTRACTS.items():
            with self.subTest(contract=name):
                expected = PUBLIC_SCHEMA_PREFIX + path
                self.assertEqual(
                    schema_id_for(name, "1", self.catalog), expected
                )
                schema = self.store.schema_for_id(expected)
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertEqual(schema["$id"], expected)

    def test_valid_manifest_fixtures_pass(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, path in manifest["valid"].items():
            with self.subTest(fixture=filename):
                errors = list(
                    self.validator(self.contract_for_path(path)).iter_errors(
                        load_json(FIXTURE_DIRECTORY / "valid" / filename)
                    )
                )
                self.assertFalse(errors, "\n".join(e.message for e in errors))

    def test_invalid_manifest_fixtures_fail(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, path in manifest["invalid"].items():
            with self.subTest(fixture=filename):
                errors = list(
                    self.validator(self.contract_for_path(path)).iter_errors(
                        load_json(FIXTURE_DIRECTORY / "invalid" / filename)
                    )
                )
                self.assertTrue(errors, f"{filename} unexpectedly passed")

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, metadata in manifest["application_invalid"].items():
            with self.subTest(fixture=filename, rule=metadata["rule_id"]):
                errors = list(
                    self.validator(
                        self.contract_for_path(metadata["schema_path"])
                    ).iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY / "application-invalid" / filename
                        )
                    )
                )
                self.assertFalse(errors, "\n".join(e.message for e in errors))

    def test_amendment_envelope_is_exact_and_immutable(self) -> None:
        schema = self.schema("amendment")
        expected = {
            "schema_version", "record_type", "module_id", "class_id",
            "work_id", "amendment_id", "target", "previous_amendment",
            "target_updated_at_before", "changes", "reason",
            "creation_source", "created_at", "created_by",
        }
        self.assertEqual(set(schema["required"]), expected)
        self.assertEqual(set(schema["properties"]), expected)
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("status", schema["properties"])
        self.assertNotIn("updated_at", schema["properties"])

    def test_disagreement_envelope_is_exact_and_lifecycle_bearing(self) -> None:
        schema = self.schema("statement_of_disagreement")
        required = {
            "schema_version", "record_type", "module_id", "class_id",
            "work_id", "disagreement_id", "status", "target", "source",
            "positions", "statement", "creation_source", "created_at",
            "created_by", "updated_at", "updated_by",
        }
        self.assertEqual(set(schema["required"]), required)
        self.assertEqual(set(schema["properties"]), required | {"supersedes"})
        self.assertFalse(schema["additionalProperties"])

    def test_amendment_change_objects_are_closed_and_typed(self) -> None:
        change = self.schema("amendment")["$defs"]["change"]
        self.assertEqual(
            set(change["required"]), {"path", "operation", "before", "after"}
        )
        self.assertFalse(change["additionalProperties"])
        self.assertEqual(
            set(change["properties"]["operation"]["enum"]),
            {"add", "replace", "remove"},
        )
        self.assertEqual(len(change["allOf"]), 3)

    def test_property_states_distinguish_absence_from_null(self) -> None:
        defs = self.schema("amendment")["$defs"]
        self.assertEqual(
            set(defs["presentState"]["required"]), {"present", "value"}
        )
        self.assertEqual(defs["presentState"]["properties"]["present"]["const"], True)
        self.assertEqual(set(defs["absentState"]["required"]), {"present"})
        self.assertNotIn("value", defs["absentState"]["properties"])

    def test_amendment_paths_are_nonempty_json_pointers(self) -> None:
        path = self.schema("amendment")["$defs"]["change"]["properties"]["path"]
        self.assertEqual(path["allOf"][1]["minLength"], 1)
        self.assertTrue(path["allOf"][0]["$ref"].endswith("json-pointer.schema.json"))

    def test_amendment_reason_vocabulary_is_closed(self) -> None:
        defs = self.schema("amendment")["$defs"]
        codes = set(
            defs["recognizedAmendmentReason"]["properties"]["code"]["enum"]
        )
        self.assertEqual(
            codes,
            {
                "spelling_corrected", "punctuation_corrected",
                "formatting_corrected", "transcription_corrected",
                "display_value_corrected", "nonsemantic_metadata_corrected",
            },
        )
        self.assertEqual(
            set(defs["otherAmendmentReason"]["required"]), {"code", "detail"}
        )

    def test_amendment_creation_source_excludes_paper_capture(self) -> None:
        source = self.schema("amendment")["$defs"]["digitalOrImportCreationSource"]
        self.assertEqual(
            set(source["allOf"][1]["properties"]["type"]["enum"]),
            {"digital_entry", "import"},
        )

    def test_disagreement_source_union_is_human_only(self) -> None:
        defs = self.schema("statement_of_disagreement")["$defs"]
        branches = {
            ref["$ref"].split("/")[-1]
            for ref in defs["disagreementSource"]["oneOf"]
        }
        self.assertEqual(
            branches,
            {
                "rosterStudentSource", "actorSource",
                "localOperatorSource", "descriptivePersonSource",
            },
        )
        self.assertNotIn("unknownPersonSource", defs)
        self.assertNotIn("systemProcessSource", defs)

    def test_disagreement_status_and_position_vocabularies_are_closed(self) -> None:
        schema = self.schema("statement_of_disagreement")
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            {"proposed", "active", "withdrawn", "invalidated", "superseded"},
        )
        self.assertEqual(len(schema["properties"]["positions"]["items"]["enum"]), 10)
        self.assertTrue(schema["properties"]["positions"]["uniqueItems"])

    def test_statement_representation_distinguishes_quote_and_summary(self) -> None:
        statement = self.schema("statement_of_disagreement")["$defs"]["statement"]
        self.assertEqual(
            set(statement["properties"]["representation"]["enum"]),
            {"verbatim_quote", "recorded_summary"},
        )
        self.assertFalse(statement["additionalProperties"])

    def test_disagreement_paper_source_requires_ingested_stage(self) -> None:
        source = self.schema("statement_of_disagreement")["$defs"]["disagreementCreationSource"]
        branches = source["allOf"][1]["oneOf"]
        paper = next(
            branch for branch in branches
            if branch["properties"]["type"]["const"] == "paper_capture"
        )
        self.assertEqual(paper["properties"]["stage"]["const"], "ingested")

    def test_disagreement_supersession_uses_exact_record_references(self) -> None:
        defs = self.schema("statement_of_disagreement")["$defs"]
        ref = defs["disagreementRecordRef"]["allOf"][0]["$ref"]
        self.assertTrue(ref.endswith("exact-portia-work-record-ref.schema.json"))
        nested = defs["disagreementRecordRef"]["allOf"][1]["properties"]["record_ref"]
        constrained = nested["allOf"][1]["properties"]
        self.assertEqual(constrained["record_kind"]["const"], "statement_of_disagreement")
        self.assertEqual(constrained["contract_version"]["const"], "1")

    def test_supersession_reason_other_requires_detail(self) -> None:
        defs = self.schema("statement_of_disagreement")["$defs"]
        self.assertEqual(
            set(defs["otherSupersessionRef"]["required"]),
            {"work_record_ref", "reason", "detail"},
        )

    def test_application_invariants_are_explicitly_documented(self) -> None:
        amendment = set(self.schema("amendment")["x-portia-application-invariants"])
        disagreement = set(
            self.schema("statement_of_disagreement")["x-portia-application-invariants"]
        )
        self.assertIn("individual_and_combined_changes_must_be_nonmaterial", amendment)
        self.assertIn("change_paths_must_not_traverse_array_indices", amendment)
        self.assertIn("target_lifecycle_changes_must_not_retarget_or_change_disagreement_automatically", disagreement)
        self.assertIn("withdrawal_must_represent_actual_source_withdrawal", disagreement)


if __name__ == "__main__":
    unittest.main()
