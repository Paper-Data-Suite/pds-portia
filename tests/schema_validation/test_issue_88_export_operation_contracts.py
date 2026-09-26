from __future__ import annotations

from copy import deepcopy

from portia.models import (
    DeliberateExportRef,
    DeliberateExportTarget,
    OperationJournalV4,
    OperationLockV3,
    parse_portia_record,
)

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


EXPORT_REF = {
    "export_id": "pexp_issue88_demo_01",
    "contract_version": "1",
}
EXPORT_TARGET = {
    "kind": "deliberate_export",
    "export_ref": EXPORT_REF,
}


class TestIssue88DeliberateExportOperationContracts:
    @classmethod
    def setup_class(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str, version: str):
        return validator_for(
            contract,
            version,
            catalog=self.catalog,
            store=self.store,
        )

    def test_new_public_reference_and_target_are_cataloged(self) -> None:
        contracts = self.catalog["contracts"]
        assert contracts["deliberate_export_ref"]["1"]["path"] == (
            "schemas/v1/references/deliberate-export-ref.schema.json"
        )
        assert contracts["deliberate_export_target"]["1"]["path"] == (
            "schemas/v1/targets/deliberate-export-target.schema.json"
        )
        assert not list(
            self.validator("deliberate_export_ref", "1").iter_errors(EXPORT_REF)
        )
        assert not list(
            self.validator("deliberate_export_target", "1").iter_errors(
                EXPORT_TARGET
            )
        )

    def test_reference_and_target_fail_closed(self) -> None:
        bad_ref = dict(EXPORT_REF, export_id="evt_not_an_export")
        assert list(
            self.validator("deliberate_export_ref", "1").iter_errors(bad_ref)
        )

        bad_version = dict(EXPORT_REF, contract_version="2")
        assert list(
            self.validator("deliberate_export_ref", "1").iter_errors(
                bad_version
            )
        )

        extra_target = deepcopy(EXPORT_TARGET)
        extra_target["student_id"] = "student_001"
        assert list(
            self.validator("deliberate_export_target", "1").iter_errors(
                extra_target
            )
        )

    def test_runtime_reference_and_target_round_trip(self) -> None:
        reference = DeliberateExportRef.from_dict(EXPORT_REF)
        target = DeliberateExportTarget.from_dict(EXPORT_TARGET)
        assert reference.to_dict() == EXPORT_REF
        assert target.to_dict() == EXPORT_TARGET
        assert target.export_ref == reference

    def test_journal_v4_is_additive_and_v3_is_immutable(self) -> None:
        v3 = load_json(
            REPO_ROOT / "schemas/v3/operations/operation-journal.schema.json"
        )
        v4 = load_json(
            REPO_ROOT / "schemas/v4/operations/operation-journal.schema.json"
        )
        assert v3["properties"]["schema_version"]["const"] == "3"
        assert v4["properties"]["schema_version"]["const"] == "4"
        assert "generate_deliberate_export" not in (
            v3["properties"]["operation_kind"]["enum"]
        )
        assert "generate_deliberate_export" in (
            v4["properties"]["operation_kind"]["enum"]
        )

        old_roles = set(
            v3["$defs"]["writeStep"]["properties"]["representation_role"]["enum"]
        )
        new_roles = set(
            v4["$defs"]["writeStep"]["properties"]["representation_role"]["enum"]
        )
        assert "deliberate_export_artifact" not in old_roles
        assert "deliberate_export_provenance" not in old_roles
        assert {
            "deliberate_export_artifact",
            "deliberate_export_provenance",
        } <= new_roles

    def test_v4_accepts_exact_export_operation_shape(self) -> None:
        source = load_json(
            REPO_ROOT
            / "tests/schema_validation/fixtures/issue-47/"
            "operation-journal-v3/valid/v3-present-write.json"
        )
        value = deepcopy(source)
        value["schema_version"] = "4"
        value["operation_kind"] = "generate_deliberate_export"
        value["scope"] = "workspace"
        value["primary_target"] = deepcopy(EXPORT_TARGET)
        value["affected_targets"] = []

        for entry in value["preflight_snapshot"]:
            entry["target"] = deepcopy(EXPORT_TARGET)
        for entry in value["lock_set"]:
            entry["lock_scope"] = "deliberate_export"
            entry["protected_target"] = deepcopy(EXPORT_TARGET)
        for step in value["write_set"]:
            step["target"] = deepcopy(EXPORT_TARGET)
            step["representation_role"] = "deliberate_export_artifact"

        errors = list(
            self.validator("operation_journal", "4").iter_errors(value)
        )
        assert not errors, "\n".join(error.message for error in errors)

        record = parse_portia_record("operation_journal", "4", value)
        assert isinstance(record, OperationJournalV4)

        old_value = deepcopy(value)
        old_value["schema_version"] = "3"
        assert list(
            self.validator("operation_journal", "3").iter_errors(old_value)
        )

    def test_journal_v4_requires_export_primary_for_export_kind(self) -> None:
        source = load_json(
            REPO_ROOT
            / "tests/schema_validation/fixtures/issue-47/"
            "operation-journal-v3/valid/v3-present-write.json"
        )
        value = deepcopy(source)
        value["schema_version"] = "4"
        value["operation_kind"] = "generate_deliberate_export"
        value["scope"] = "workspace"
        assert list(
            self.validator("operation_journal", "4").iter_errors(value)
        )

    def test_lock_v3_is_additive_and_v2_is_immutable(self) -> None:
        v2 = load_json(
            REPO_ROOT / "schemas/v2/operations/operation-lock.schema.json"
        )
        v3 = load_json(
            REPO_ROOT / "schemas/v3/operations/operation-lock.schema.json"
        )
        assert v2["properties"]["schema_version"]["const"] == "2"
        assert v3["properties"]["schema_version"]["const"] == "3"
        assert "deliberate_export" not in v2["properties"]["lock_scope"]["enum"]
        assert "deliberate_export" in v3["properties"]["lock_scope"]["enum"]

    def test_lock_v3_accepts_exact_export_lock(self) -> None:
        source = load_json(
            REPO_ROOT
            / "tests/schema_validation/fixtures/issue-14/"
            "actor-aware-operations/operation-lock/valid/"
            "actor-directory-collection.json"
        )
        value = deepcopy(source)
        value["schema_version"] = "3"
        value["lock_scope"] = "deliberate_export"
        value["protected_target"] = deepcopy(EXPORT_TARGET)

        errors = list(
            self.validator("operation_lock", "3").iter_errors(value)
        )
        assert not errors, "\n".join(error.message for error in errors)

        record = parse_portia_record("operation_lock", "3", value)
        assert isinstance(record, OperationLockV3)

        old_value = deepcopy(value)
        old_value["schema_version"] = "2"
        assert list(
            self.validator("operation_lock", "2").iter_errors(old_value)
        )
