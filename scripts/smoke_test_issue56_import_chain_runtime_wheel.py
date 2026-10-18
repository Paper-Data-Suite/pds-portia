"""Run installed-wheel acceptance for the completed Issue #56 import runtime chain."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

CORE_NAME = "pds_core-0.6.5-py3-none-any.whl"
PORTIA_NAME = "pds_portia-0.2.0-py3-none-any.whl"
IMPORT_CONTRACTS = (
    "import_batch",
    "import_source_record",
    "import_proposal",
    "import_review",
    "import_materialization",
)


def _run(
    command: list[str], *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _verify_candidate_payload(portia_wheel: Path) -> None:
    with zipfile.ZipFile(portia_wheel) as archive:
        init_text = archive.read("portia/models/__init__.py").decode("utf-8")
        records_text = archive.read("portia/models/records.py").decode("utf-8")
        coverage = json.loads(
            archive.read("portia/runtime-coverage.json").decode("utf-8")
        )
        bundle = json.loads(
            archive.read("portia/_runtime_contract_bundle.json").decode("utf-8")
        )

    for class_name in (
        "ImportBatchV1",
        "ImportSourceRecordV1",
        "ImportProposalV1",
        "ImportReviewV1",
        "ImportMaterializationV1",
    ):
        if class_name not in init_text:
            raise RuntimeError(f"candidate wheel is stale: {class_name} not exported")
        if f"class {class_name}" not in records_text:
            raise RuntimeError(f"candidate wheel is stale: {class_name} not defined")

    entries = coverage.get("contracts")
    if not isinstance(entries, list):
        raise RuntimeError("candidate wheel runtime coverage is malformed")
    indexed = {
        (item.get("contract"), item.get("version")): item
        for item in entries
        if isinstance(item, dict)
    }
    for contract in IMPORT_CONTRACTS:
        item = indexed.get((contract, "1"))
        if not isinstance(item, dict) or (
            item.get("disposition"),
            item.get("modelled"),
        ) != ("current_v0_3", True):
            raise RuntimeError(f"candidate wheel is stale: {contract}@1 not promoted")

    contracts = bundle.get("contracts")
    if not isinstance(contracts, dict):
        raise RuntimeError("candidate wheel runtime schema bundle is malformed")
    for contract in IMPORT_CONTRACTS:
        mapping = contracts.get(contract)
        if not isinstance(mapping, dict) or set(mapping) != {"1"}:
            raise RuntimeError(f"candidate wheel schema map malformed: {contract}@1")


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]

    if core_wheel.name != CORE_NAME:
        raise RuntimeError("expected authenticated Core 0.6.5 wheel")
    if portia_wheel.name != PORTIA_NAME:
        raise RuntimeError(f"expected candidate wheel {PORTIA_NAME}")

    _verify_candidate_payload(portia_wheel)

    verified = _run(
        [
            sys.executable,
            str(repository / "scripts/verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )
    if "Verified official pds-core 0.6.5 wheel" not in verified.stdout:
        raise RuntimeError("Core authentication did not complete")

    code = r"""
from portia.models import (
    ImportBatchV1,
    ImportMaterializationV1,
    ImportProposalV1,
    ImportReviewV1,
    ImportSourceRecordV1,
    MODEL_REGISTRY,
    parse_portia_record,
    runtime_coverage,
)
from portia.models.base import IDENTITY_FIELDS

agent = {"type": "system_process", "process_id": "issue56_chain_smoke"}
reviewer = {"kind": "local_operator", "display_label": "Synthetic Reviewer"}

batch = {
    "schema_version": "1",
    "record_type": "import_batch",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "import_batch_id": "ibat_chain_01",
    "source_profile": {
        "source_system_id": "synthetic_system",
        "profile_id": "synthetic_profile",
        "profile_version": "1",
    },
    "source_snapshot": {
        "locator": {"kind": "workspace_file", "path": "imports/synthetic.csv"},
        "fingerprint": {
            "algorithm": "sha256",
            "digest": "a" * 64,
            "byte_length": 123,
        },
        "observed_at": "2026-10-12T12:00:00-04:00",
    },
    "mapping_profile": {
        "mapping_profile_id": "synthetic_mapping",
        "mapping_version": "1",
        "mapping_digest": "b" * 64,
    },
    "import_identity_digest": "c" * 64,
    "status": "completed",
    "failure_codes": [],
    "started_at": "2026-10-12T12:00:00-04:00",
    "finished_at": "2026-10-12T12:01:00-04:00",
    "created_at": "2026-10-12T12:00:00-04:00",
    "created_by": agent,
}

source = {
    "schema_version": "1",
    "record_type": "import_source_record",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "import_batch_id": "ibat_chain_01",
    "source_record_id": "isrc_chain_01",
    "source_record_key_origin": "source_provided",
    "source_record_key": "SRC-1",
    "source_record_digest": "d" * 64,
    "source_record_identity_digest": "e" * 64,
    "source_fields": [
        {"field_key": "location", "value": "Room 101"},
        {"field_key": "occurred_at", "value": "2026-10-12T10:00:00-04:00"},
    ],
    "observed_at": "2026-10-12T12:00:00-04:00",
    "created_at": "2026-10-12T12:00:00-04:00",
    "created_by": agent,
}

proposal = {
    "schema_version": "1",
    "record_type": "import_proposal",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "import_batch_id": "ibat_chain_01",
    "source_record_id": "isrc_chain_01",
    "proposal_id": "iprp_chain_01",
    "proposal_key": "event",
    "proposal_identity_digest": "f" * 64,
    "target": {
        "record_kind": "event",
        "contract_version": "2",
        "context": {"kind": "new_work"},
    },
    "field_bindings": [
        {
            "target_path": "/location_text",
            "source_field_key": "location",
            "value_source": "source_value",
        }
    ],
    "review_flags": [],
    "proposed_at": "2026-10-12T12:02:00-04:00",
    "proposed_by": agent,
    "created_at": "2026-10-12T12:02:00-04:00",
    "created_by": agent,
}

review = {
    "schema_version": "1",
    "record_type": "import_review",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "import_batch_id": "ibat_chain_01",
    "source_record_ref": {
        "contract_version": "1",
        "source_record_id": "isrc_chain_01",
    },
    "review_id": "irev_chain_01",
    "review_sequence": 1,
    "proposal_ref": {
        "contract_version": "1",
        "proposal_id": "iprp_chain_01",
        "proposal_identity_digest": "f" * 64,
    },
    "reviewer": reviewer,
    "disposition": "accepted",
    "field_reviews": [],
    "reason_codes": [],
    "reviewed_at": "2026-10-12T12:03:00-04:00",
    "created_at": "2026-10-12T12:03:00-04:00",
    "created_by": agent,
}

receipt = {
    "schema_version": "1",
    "record_type": "import_materialization",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "import_batch_ref": {
        "contract_version": "1",
        "import_batch_id": "ibat_chain_01",
        "import_identity_digest": "c" * 64,
    },
    "source_record_ref": {
        "contract_version": "1",
        "source_record_id": "isrc_chain_01",
        "source_record_identity_digest": "e" * 64,
    },
    "proposal_ref": {
        "contract_version": "1",
        "proposal_id": "iprp_chain_01",
        "proposal_identity_digest": "f" * 64,
    },
    "review_ref": {
        "contract_version": "1",
        "review_id": "irev_chain_01",
        "review_sequence": 1,
    },
    "operation_journal_ref": {
        "operation_id": "op_import_chain_01",
        "journal_revision": 4,
        "contract_version": "1",
    },
    "canonical_results": [
        {
            "result_relation": "produced",
            "target": {
                "kind": "work",
                "work_ref": {
                    "module_id": "portia",
                    "class_id": "class_synthetic",
                    "work_id": "evt_chain_01",
                    "work_kind": "event",
                    "contract_version": "2",
                },
            },
        }
    ],
    "materialized_at": "2026-10-12T12:04:00-04:00",
    "recorded_at": "2026-10-12T12:04:00-04:00",
    "recorded_by": agent,
}

cases = (
    ("import_batch", ImportBatchV1, batch, "ibat_chain_01"),
    ("import_source_record", ImportSourceRecordV1, source, "isrc_chain_01"),
    ("import_proposal", ImportProposalV1, proposal, "iprp_chain_01"),
    ("import_review", ImportReviewV1, review, "irev_chain_01"),
    ("import_materialization", ImportMaterializationV1, receipt, None),
)
for contract, cls, wire, logical_id in cases:
    parsed = parse_portia_record(contract, "1", wire)
    assert isinstance(parsed, cls)
    assert parsed.to_dict() == wire
    assert parsed.logical_id == logical_id
    assert MODEL_REGISTRY[(contract, "1")] is cls

assert "import_materialization" not in IDENTITY_FIELDS
coverage = {
    (entry.contract, entry.version): (entry.disposition, entry.modelled)
    for entry in runtime_coverage()
}
for contract in (
    "import_batch",
    "import_source_record",
    "import_proposal",
    "import_review",
    "import_materialization",
):
    assert coverage[(contract, "1")] == ("current_v0_3", True)

print("installed Issue #56 import runtime chain OK")
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue56-import-chain-") as temp:
        temp_root = Path(temp)
        venv_root = temp_root / "venv"
        work = temp_root / "work"
        work.mkdir()

        venv.EnvBuilder(with_pip=True, clear=True).create(venv_root)
        python = _python(venv_root)

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PIP_NO_INDEX"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        for wheel in (core_wheel, portia_wheel):
            _run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    str(wheel.resolve()),
                ],
                cwd=work,
                env=env,
            )

        capture_dependency_env = env.copy()
        capture_dependency_env.pop("PIP_NO_INDEX", None)
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "reportlab>=4.2,<5",
                "qrcode>=7.4,<9",
                "pypdf>=5,<7",
            ],
            cwd=work,
            env=capture_dependency_env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)
        result = _run([str(python), "-c", code], cwd=work, env=env)
        if "installed Issue #56 import runtime chain OK" not in result.stdout:
            raise RuntimeError("installed import runtime chain smoke did not complete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()

    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        AssertionError,
        zipfile.BadZipFile,
        json.JSONDecodeError,
    ) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1

    print("Portia Issue #56 completed import runtime installed-wheel acceptance passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
