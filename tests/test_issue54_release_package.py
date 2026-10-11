from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_checker():
    path = ROOT / "scripts" / "check_issue54_release_package.py"
    spec = importlib.util.spec_from_file_location("issue54_release_package", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue54_release_package_names_are_exact() -> None:
    checker = _load_checker()
    assert checker.EXPECTED_WHEEL == "pds_portia-0.2.0-py3-none-any.whl"
    assert checker.EXPECTED_SDIST == "pds_portia-0.2.0.tar.gz"
    assert checker.EXPECTED_SDIST_ROOT == "pds_portia-0.2.0"


def test_issue54_release_package_requires_audit_evidence_in_sdist() -> None:
    checker = _load_checker()
    assert {
        "RELEASE_NOTES_v0.2.0.md",
        "docs/audits/portia-v0.2.0-release-audit.json",
        "docs/audits/portia-v0.2.0-release-audit.md",
        "docs/audits/portia-v0.2.0-release-findings.md",
        "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
        "scripts/check_issue54_release_package.py",
        "scripts/validate_issue54_release_mechanics.py",
    } <= checker.REQUIRED_SDIST_EVIDENCE


def test_issue54_release_package_rejects_extra_dist_files(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / checker.EXPECTED_WHEEL).write_bytes(b"not-a-wheel")
    (tmp_path / checker.EXPECTED_SDIST).write_bytes(b"not-an-sdist")
    (tmp_path / "extra.whl").write_bytes(b"extra")
    findings = checker.validate_target(tmp_path)
    assert len(findings) == 1
    assert "exactly the two Issue #54 candidate artifacts" in findings[0]


def test_issue54_release_package_keeps_hashes_explicitly_nonfinal() -> None:
    source = (ROOT / "scripts" / "check_issue54_release_package.py").read_text(
        encoding="utf-8"
    )
    assert "candidate wheel SHA-256 (NOT FINAL)" in source
    assert "candidate sdist SHA-256 (NOT FINAL)" in source
    assert "Phase 2 must rebuild from exact qualified main" in source

def _audit_fixture(
    *,
    verdict: str,
    publication_status: str,
) -> dict[str, object]:
    publication: dict[str, object] = {
        "status": publication_status,
        "release_commit": None,
        "release_tree": None,
        "tag": None,
        "github_release_url": None,
        "wheel_filename": None,
        "wheel_sha256": None,
        "sdist_filename": None,
        "sdist_sha256": None,
        "sha256sums_sha256": None,
    }
    if publication_status == "verified":
        publication.update(
            {
                "release_commit": "83cfe05ef6b03d8453fdb60d1a1702f138d5293d",
                "release_tree": "2050bd1c7aabb47ccf2df4a8285c7a61ac360f2e",
                "tag": "v0.2.0",
                "github_release_url": (
                    "https://github.com/Paper-Data-Suite/pds-portia/"
                    "releases/tag/v0.2.0"
                ),
                "wheel_filename": "pds_portia-0.2.0-py3-none-any.whl",
                "wheel_sha256": (
                    "7ae545e62740b4411736fc55e572a86384ed8714f1f65346d65e36a7943f3550"
                ),
                "sdist_filename": "pds_portia-0.2.0.tar.gz",
                "sdist_sha256": (
                    "ea78dd74b6c9bbabb7da71397c9cdc4985479428b679856040f7fb2fcbcad0c8"
                ),
                "sha256sums_sha256": (
                    "aa7f972a6dcc5f1113fe85298827ec7d0b2a11d08b01e8c83d77784980d93403"
                ),
            }
        )
    return {
        "target_distribution": "pds-portia",
        "target_version": "0.2.0",
        "core_qualification": {
            "current": {
                "version": "0.6.5",
                "sha256": (
                    "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
                ),
            }
        },
        "final_verdict": verdict,
        "release_publication": publication,
        "audit_domains": [
            {
                "domain_id": "release_contract_mechanical",
                "status": "pass",
            },
            {
                "domain_id": "cumulative_repository_qualification",
                "status": "pass",
            },
            {
                "domain_id": "python_platform_qualification",
                "status": "pass",
            },
        ],
    }


def test_issue54_sdist_audit_accepts_prefreeze_state() -> None:
    checker = _load_checker()
    findings = checker._sdist_audit_findings(
        _audit_fixture(
            verdict="PENDING",
            publication_status="not_started",
        )
    )
    assert findings == []


def test_issue54_sdist_audit_accepts_verified_final_state() -> None:
    checker = _load_checker()
    findings = checker._sdist_audit_findings(
        _audit_fixture(
            verdict="RELEASED — VERIFIED",
            publication_status="verified",
        )
    )
    assert findings == []


def test_issue54_sdist_audit_rejects_mixed_release_state() -> None:
    checker = _load_checker()
    findings = checker._sdist_audit_findings(
        _audit_fixture(
            verdict="RELEASED — VERIFIED",
            publication_status="not_started",
        )
    )
    assert findings == [
        "sdist release audit must preserve a coherent pre-freeze or "
        "verified-final state"
    ]


def test_issue54_sdist_audit_rejects_verified_identity_drift() -> None:
    checker = _load_checker()
    audit = _audit_fixture(
        verdict="RELEASED — VERIFIED",
        publication_status="verified",
    )
    publication = audit["release_publication"]
    assert isinstance(publication, dict)
    publication["wheel_sha256"] = "0" * 64

    findings = checker._sdist_audit_findings(audit)
    assert findings == [
        "verified release publication wheel_sha256 does not match "
        "the immutable v0.2.0 release identity"
    ]
