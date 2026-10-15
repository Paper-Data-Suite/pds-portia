"""Validate Issue #56 final capture/import reconciliation closeout."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any, cast

from portia.models import runtime_coverage
from portia.models.base import IDENTITY_FIELDS
from portia.models.records import MODEL_REGISTRY

ROOT = Path(__file__).resolve().parents[1]

START_MAIN_COMMIT = "7794b577ab6da444a501efb198895f9e4ff5726c"
START_MAIN_TREE = "3da71310deb3cfb1f3bf05136909e6d660527b6d"
CORE_065_SHA256 = (
    "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
)

EXPECTED_RUNTIME: dict[tuple[str, str], tuple[str, bool]] = {
    ("capture_batch", "1"): ("current_v0_3", True),
    ("page_target", "1"): ("historical_read", True),
    ("page_target", "2"): ("current_v0_3", True),
    ("page_record", "1"): ("current_v0_3", True),
    ("paper_interpretation", "1"): ("current_v0_3", True),
    ("capture_proposal", "1"): ("current_v0_3", True),
    ("capture_review", "1"): ("current_v0_3", True),
    ("capture_materialization", "1"): ("current_v0_3", True),
    ("import_batch", "1"): ("current_v0_3", True),
    ("import_source_record", "1"): ("current_v0_3", True),
    ("import_proposal", "1"): ("current_v0_3", True),
    ("import_review", "1"): ("current_v0_3", True),
    ("import_materialization", "1"): ("current_v0_3", True),
}

EXPECTED_CORE_OWNED = {
    ("module_work_ref", "core-0.6"),
    ("module_record_ref", "core-0.6"),
    ("route_locator", "core-0.6"),
    ("route_registration", "core-0.6"),
    ("retained_source_scan", "core-0.6"),
}

V1_BASELINE_GIT_BLOBS: dict[str, str] = {
    "schemas/v1/capture/capture-batch.schema.json": "0a58a94ac90719e87cd9fc802136dd8729924ee5",
    "schemas/v1/capture/page-target.schema.json": "fe3d991d68700d88c566626bb91935820db66de5",
    "schemas/v1/capture/page-record.schema.json": "4d31c1b944735230341743525fdb1ccd896ba8e5",
    "schemas/v1/capture/paper-interpretation.schema.json": "aeb2b16481f7c466ce1c44d8ba63e5deae340631",
    "schemas/v1/capture/capture-proposal.schema.json": "899f463cd2dcbf37438b0847db727e2441babb58",
    "schemas/v1/capture/capture-review.schema.json": "3e716cee78fdfe0ed453354abba9aa7c033104b5",
    "schemas/v1/capture/capture-materialization.schema.json": "b216b3c76e8b67b31d3815b094c705b641de2640",
    "schemas/v1/imports/import-batch.schema.json": "3c8208e7a534e7d78924e81ff33ff9ed1b2cfa24",
    "schemas/v1/imports/import-source-record.schema.json": "e09e8c3ce76160c6b3132a5f3250b69c98067c44",
    "schemas/v1/imports/import-proposal.schema.json": "6b03916a266937a98a8b137a2a0e381c1ab40639",
    "schemas/v1/imports/import-review.schema.json": "cd47e42ca4d762ee4b53269ffbd757f519c76b2e",
    "schemas/v1/imports/import-materialization.schema.json": "f3a609d130e6ce3f2b6df85b4f167c0d613297d4",
    "schemas/v1/identifiers/portia-capture-batch-id.schema.json": "6869b5d33e8b8d94fc5025e4a556834fb3596472",
    "schemas/v1/identifiers/portia-page-target-id.schema.json": "9d568eff870288bb0399b5c492da8cba6993216e",
    "schemas/v1/identifiers/portia-page-record-id.schema.json": "8c670194b9ad37da50155bc19d6c90623bd45c8e",
    "schemas/v1/identifiers/portia-paper-interpretation-id.schema.json": "7ee714de39eb7c004b0105dfc6c69284f29e0daf",
    "schemas/v1/identifiers/portia-capture-proposal-id.schema.json": "bb77720e24d255844235d748610f402bcf77cab7",
    "schemas/v1/identifiers/portia-capture-review-id.schema.json": "dcbdf8c333a71e64f06bda0ba6e389c8a27b78ad",
    "schemas/v1/identifiers/portia-import-batch-id.schema.json": "08cb99ddfcf98a3f1db960f43a7506c046fe83a0",
    "schemas/v1/identifiers/portia-import-source-record-id.schema.json": "61dcbdfe7ea811faca39cf6953a41d06bf8aa00f",
    "schemas/v1/identifiers/portia-import-proposal-id.schema.json": "b9b9c3ed75f40ee1f30507326cb518a25742d69e",
    "schemas/v1/identifiers/portia-import-review-id.schema.json": "81048e9a452f7253fc0c700adf94cfc7b943dd07"
}


def _json(path: Path) -> dict[str, Any]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], raw)


def _git_blob_sha1(path: Path) -> str:
    # Git text blobs use LF. Windows checkouts may use CRLF even when the
    # staged/indexed schema is unchanged (core.autocrlf). Hash the canonical
    # text blob bytes, never platform-specific working-tree line endings.
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha1()
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


def _coverage_entries(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    raw = _json(root / "portia/runtime-coverage.json").get("contracts")
    if not isinstance(raw, list):
        raise ValueError("runtime coverage contracts must be an array")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        contract = item.get("contract")
        version = item.get("version")
        if isinstance(contract, str) and isinstance(version, str):
            result[(contract, version)] = cast(dict[str, Any], item)
    return result


def validate(root: Path = ROOT) -> tuple[str, ...]:
    root = root.resolve()
    findings: list[str] = []

    entries = _coverage_entries(root)
    for key, expected in EXPECTED_RUNTIME.items():
        item = entries.get(key)
        actual = None if item is None else (
            item.get("disposition"),
            item.get("modelled"),
        )
        if actual != expected:
            findings.append(
                f"runtime disposition mismatch for {key[0]}@{key[1]}: "
                f"expected={expected!r}, actual={actual!r}"
            )
        if expected[1] and key not in MODEL_REGISTRY:
            findings.append(f"runtime model registry missing {key[0]}@{key[1]}")

    if len(MODEL_REGISTRY) != 84:
        findings.append(
            f"expected 84 modelled contract versions, found {len(MODEL_REGISTRY)}"
        )

    active_deferred = sorted(
        f"{key[0]}@{key[1]}"
        for key, item in entries.items()
        if item.get("disposition") == "deferred_v0_3"
    )
    if active_deferred:
        findings.append(
            "Issue #56 closeout requires no active deferred_v0_3 entries: "
            f"{active_deferred}"
        )

    for key in EXPECTED_CORE_OWNED:
        item = entries.get(key)
        if item is None or (
            item.get("disposition"),
            item.get("modelled"),
            item.get("catalog_required"),
        ) != ("core_owned", False, False):
            findings.append(f"Core-owned boundary drifted for {key[0]}@{key[1]}")

    if "capture_materialization" in IDENTITY_FIELDS:
        findings.append("capture_materialization must not invent a logical ID")
    if "import_materialization" in IDENTITY_FIELDS:
        findings.append("import_materialization must not invent a logical ID")

    for relative, expected_blob in V1_BASELINE_GIT_BLOBS.items():
        path = root / relative
        if not path.exists():
            findings.append(f"baseline v1 schema missing: {relative}")
            continue
        actual_blob = _git_blob_sha1(path)
        if actual_blob != expected_blob:
            findings.append(
                f"published v1 schema changed in place: {relative} "
                f"expected Git blob {expected_blob}, found {actual_blob}"
            )

    catalog = _json(root / "schemas/schema-catalog.json")
    contracts = catalog.get("contracts")
    if not isinstance(contracts, dict):
        findings.append("schema catalog contracts are malformed")
    else:
        page_target = contracts.get("page_target")
        if not isinstance(page_target, dict) or set(page_target) != {"1", "2"}:
            findings.append("page_target catalog must contain exactly v1 and v2")
        observation = contracts.get("observation")
        if not isinstance(observation, dict) or "3" in observation:
            findings.append("Issue #56 must not introduce observation@3")
        capture_review = contracts.get("capture_review")
        if not isinstance(capture_review, dict) or set(capture_review) != {"1"}:
            findings.append("Issue #56 must keep capture_review@1 as sole version")

    page_v2 = _json(root / "schemas/v2/capture/page-target.schema.json")
    properties = page_v2.get("properties")
    purposes: object = None
    if isinstance(properties, dict):
        page_purpose = properties.get("page_purpose")
        if isinstance(page_purpose, dict):
            purposes = page_purpose.get("enum")
    if not isinstance(purposes, list):
        findings.append("page_target@2 purpose enum is unavailable")
    else:
        for required in (
            "classroom_observation_capture",
            "focused_monitoring_capture",
            "communication_capture",
        ):
            if required not in purposes:
                findings.append(f"page_target@2 missing purpose {required}")

    adr = (
        root
        / "docs/decisions/"
        "0021-reconcile-classroom-observation-paper-capture-with-released-runtime.md"
    ).read_text(encoding="utf-8")
    for marker in (
        "- **Status:** Accepted",
        "Keep `observation@2` ownership unchanged",
        "No class-day Event container",
        "Positive / general / concern cues are capture aids only",
        "Session-context values are returned-page source context",
    ):
        if marker not in adr:
            findings.append(f"ADR 0021 missing closeout marker: {marker!r}")

    design = (
        root / "docs/design/issue-56-v03-capture-import-runtime-reconciliation.md"
    ).read_text(encoding="utf-8")
    # Markdown wraps prose across lines; a semantically identical line break
    # must not fail the frozen closeout acceptance marker.
    normalized_design = " ".join(design.split())
    for marker in (
        "Status: **Reconciliation complete — PR qualification pending**",
        "## Final Issue #56 reconciliation — Slice 15 closeout",
        "no active `deferred_v0_3` capture/import contracts",
        "structured human-confirmed classroom-session analytics",
    ):
        if marker not in normalized_design:
            findings.append(f"Issue #56 design closeout marker missing: {marker!r}")

    acceptance = (
        root / "docs/validation/issue-56-acceptance-matrix.md"
    ).read_text(encoding="utf-8")
    if "0 pending" not in acceptance:
        findings.append("Issue #56 acceptance matrix does not record zero pending")
    if "| Pending |" in acceptance or "| PENDING |" in acceptance:
        findings.append("Issue #56 acceptance matrix still contains a pending row")
    if acceptance.count("| PASS |") < 90:
        findings.append("Issue #56 acceptance matrix is unexpectedly incomplete")

    final_record = (
        root
        / "docs/validation/issue-56-final-reconciliation-and-qualification.md"
    ).read_text(encoding="utf-8")
    for marker in (
        START_MAIN_COMMIT,
        START_MAIN_TREE,
        CORE_065_SHA256,
        "## Final runtime-support disposition matrix",
        "## Core 0.6.5 PDS2 reuse matrix",
        "## Initial v0.3 paper-form inventory",
        "## Authorization matrix",
        "## Storage / ownership matrix",
        "## Migration / history / correction matrix",
        "## Synthetic reconciliation scenario register",
        "## Explicit deferred-capability list",
        "Portia Issue #56 completed import runtime installed-wheel acceptance passed",
    ):
        if marker not in final_record:
            findings.append(f"final reconciliation record missing marker: {marker!r}")

    readme = (root / "README.md").read_text(encoding="utf-8")
    for marker in (
        "ADR 0001 through ADR 0021",
        "ADRs 0001–0021",
        "v0.3 paper/import runtime dispositions",
        "### Issue #56 current implementation",
        "no active `deferred_v0_3` capture/import contract remains",
        "production paper/import services beyond the reconciled v0.3 contract/runtime surface",
    ):
        if marker not in readme:
            findings.append(f"README closeout marker missing: {marker!r}")

    docs_readme = (root / "docs/README.md").read_text(encoding="utf-8")
    for marker in (
        "## v0.3 paper/import contract reconciliation",
        "validation/issue-56-acceptance-matrix.md",
        "validation/issue-56-final-reconciliation-and-qualification.md",
    ):
        if marker not in docs_readme:
            findings.append(f"docs/README closeout marker missing: {marker!r}")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    for marker in (
        "Issue #56 capture/import contract reconciliation",
        "`page_target@2`",
        "84 modeled contract versions",
    ):
        if marker not in changelog:
            findings.append(f"CHANGELOG closeout marker missing: {marker!r}")

    with (root / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    mypy_files = set(pyproject["tool"]["mypy"]["files"])
    if "scripts/validate_issue56_closeout.py" not in mypy_files:
        findings.append("strict mypy scope missing Issue #56 closeout validator")
    if "scripts/smoke_test_issue56_import_chain_runtime_wheel.py" not in mypy_files:
        findings.append("strict mypy scope missing Issue #56 import-chain smoke")

    repository_gate = (root / "scripts/validate_repository.py").read_text(
        encoding="utf-8"
    )
    for marker in (
        "scripts/validate_issue56_closeout.py",
        "scripts/smoke_test_issue56_import_chain_runtime_wheel.py",
        "Portia Issue #56 repository qualification passed",
    ):
        if marker not in repository_gate:
            findings.append(f"repository gate missing Issue #56 marker {marker!r}")
    closeout_pos = repository_gate.find("scripts/validate_issue56_closeout.py")
    pytest_pos = repository_gate.find('[sys.executable, "-m", "pytest"]')
    smoke54_pos = repository_gate.find("scripts/smoke_test_issue54_core065_wheel.py")
    smoke56_pos = repository_gate.find(
        "scripts/smoke_test_issue56_import_chain_runtime_wheel.py"
    )
    diff_pos = repository_gate.find('["git", "diff", "--check"]')
    if not (0 <= closeout_pos < pytest_pos):
        findings.append("Issue #56 closeout validator must run before full pytest")
    if not (0 <= smoke54_pos < smoke56_pos < diff_pos):
        findings.append(
            "Issue #56 installed smoke must run after Core 0.6.5 smoke "
            "and before diff check"
        )

    package_check = (root / "scripts/check_package.py").read_text(encoding="utf-8")
    for marker in (
        "docs/validation/issue-56-acceptance-matrix.md",
        "docs/validation/issue-56-final-reconciliation-and-qualification.md",
        "scripts/validate_issue56_closeout.py",
        "scripts/smoke_test_issue56_import_chain_runtime_wheel.py",
        "tests/test_issue56_closeout.py",
    ):
        if marker not in package_check:
            findings.append(f"package inventory missing Issue #56 artifact {marker!r}")

    verifier = (root / "scripts/verify_core_wheel.py").read_text(encoding="utf-8")
    for marker in ('"pds_core-0.6.5-py3-none-any.whl"', CORE_065_SHA256):
        if marker not in verifier:
            findings.append(f"Core 0.6.5 verifier authority missing {marker!r}")

    smoke = (
        root / "scripts/smoke_test_issue56_import_chain_runtime_wheel.py"
    ).read_text(encoding="utf-8")
    if (
        "Portia Issue #56 completed import runtime installed-wheel acceptance passed"
        not in smoke
    ):
        findings.append("Issue #56 import-chain smoke success marker drifted")

    live_pairs = {
        (entry.contract, entry.version): (entry.disposition, entry.modelled)
        for entry in runtime_coverage()
    }
    for key, expected in EXPECTED_RUNTIME.items():
        if live_pairs.get(key) != expected:
            findings.append(f"runtime_coverage() drift for {key[0]}@{key[1]}")

    return tuple(sorted(set(findings)))


def main() -> int:
    try:
        findings = validate(ROOT)
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        tomllib.TOMLDecodeError,
    ) as exc:
        print(f"Portia Issue #56 closeout validation failed: {exc}")
        return 1

    if findings:
        print("Portia Issue #56 closeout validation failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Portia Issue #56 final reconciliation closeout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
