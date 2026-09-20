from __future__ import annotations

import inspect
import json
from pathlib import Path

from portia.identity import ActorDirectoryService
from portia.workflows import (
    AmendmentWorkflowService,
    DependencyWorkflowService,
    ExceptionalRemovalWorkflowService,
    IntegrityWorkflowService,
    LifecycleWorkflowService,
    OwnershipCorrectionWorkflowService,
    RecordMigrationWorkflowService,
    RecoveryWorkflowService,
    StatementOfDisagreementWorkflowService,
)
from scripts.validate_issue47_workflows import findings

ROOT = Path(__file__).resolve().parents[1]


def test_final_issue47_public_services_are_bounded_and_exported() -> None:
    services = (
        LifecycleWorkflowService,
        AmendmentWorkflowService,
        StatementOfDisagreementWorkflowService,
        DependencyWorkflowService,
        RecordMigrationWorkflowService,
        OwnershipCorrectionWorkflowService,
        ExceptionalRemovalWorkflowService,
        RecoveryWorkflowService,
        IntegrityWorkflowService,
        ActorDirectoryService,
    )
    assert all(inspect.isclass(service) for service in services)
    for service in services:
        public = {
            name
            for name, _member in inspect.getmembers(service)
            if not name.startswith("_")
        }
        assert public.isdisjoint({"delete", "move", "resolve_latest"})


def test_final_issue47_runtime_version_authority_is_explicit() -> None:
    coverage = json.loads(
        (ROOT / "portia/runtime-coverage.json").read_text(encoding="utf-8")
    )
    observed = {
        (entry["contract"], entry["version"]): entry["disposition"]
        for entry in coverage["contracts"]
    }
    assert observed[("ownership_correction", "1")] == "historical_read"
    assert observed[("ownership_correction", "2")] == "current_v0_2"
    assert observed[("operation_journal", "2")] == "supporting_v0_2"
    assert observed[("operation_journal", "3")] == "supporting_v0_2"


def test_final_issue47_repository_validator_accepts_closeout() -> None:
    assert findings(ROOT, stage="repository") == []
