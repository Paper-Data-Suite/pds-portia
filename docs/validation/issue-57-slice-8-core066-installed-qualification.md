# Issue #57 — Slice 8: Official Core 0.6.6 installed/platform qualification

## Qualified external authority

- Upstream repository: `Paper-Data-Suite/pds-core`
- Published release: `v0.6.6`, 2026-10-15T03:00:13Z
- Annotated tag object: `d0bfcb01949c28189eac53b9110975e7ce0c3bd6`
- Release source commit: `35af5d0642e84a625cd143285c4ef6de98dbcca4`
- Wheel: `pds_core-0.6.6-py3-none-any.whl`
- Wheel SHA-256: `d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301`
- Official artifact: `https://github.com/Paper-Data-Suite/pds-core/releases/download/v0.6.6/pds_core-0.6.6-py3-none-any.whl`
- Release: `https://github.com/Paper-Data-Suite/pds-core/releases/tag/v0.6.6`

The source commit and checksum above are verified release metadata, not a claim
that this Portia branch has passed installed acceptance yet. The existing
`scripts/verify_core_wheel.py` allowlist gains the published digest and continues
to reject any unrecognized/altered wheel, including unsigned local rebuilds
reusing the same version number.

## Installed-wheel gate

`scripts/smoke_test_issue57_core066_wheel.py` creates a fresh isolated Python
virtual environment, installs only the authenticated Core v0.6.6 wheel and the
**locally built Portia wheel**, and executes a synthetic workflow with `-I`
from a directory outside the repository. It rejects editable/source imports,
incorrect package identities, missing dependencies, and a Portia wheel version
other than the current `0.2.0` development version.

It validates a deep school-year workspace and two classroom-observation pages:

1. Class authorization, non-domain batch and Page Target persistence.
2. Exact persisted Core registrations and PDS2 serialize/parse agreement.
3. Template/version ownership and authorized multi-page readiness.
4. Replay preserving all canonical files and route IDs byte-for-byte.
5. Read-only inspection and no fabricated Event/Support Process work root.
6. Synthetic deep HTML/CSS viewer handoff through installed Core.
7. A real NTFS junction under the user's `LOCALAPPDATA` on Windows, with
   `os.path.samefile()` agreement, a short lexical shell path, preserved relative
   CSS, and explicit link-only cleanup. The shell invocation itself is mocked
   to avoid opening a desktop application during unattended tests.
8. On Ubuntu, the installed Core dispatches the unchanged non-Windows open
   contract; the external opener is mocked to avoid graphical dependencies.
9. Durable Portia target, registration, and PDS2 identity remains unchanged
   before/after the viewer handoff and cleanup.

**Do not confuse Core's temporary viewer junction with a PDS2 alias.** The
junction is never used in Capture Batch/Page Target fields, route payloads,
template identities, source digests, persisted paths, or Core registrations.
The production capture preparation service does not invoke `open_local_path`.
Only a subsequent teacher preview/open workflow may use that Core viewer API,
after separately validating authorization, provenance, and allowed file path.

A successful `open_local_path` means Windows/Linux accepted the handoff, **not**
that an external viewer rendered the document. Core's v0.6.6 release documents
separate physical Windows viewer-visibility checks; this automated Portia gate
qualifies the junction/filesystem boundary, not an interactive PDF viewer.

## CI sequencing and backward compatibility

Existing Issue #54 CI remains pinned to official Core 0.6.5, 0.6.4 and 0.6.3
for its frozen historical qualification assertions. The added independent
`issue57-core066` Windows/Ubuntu matrix verifies Core 0.6.6 while running the
focused Issue #57 tests and the installed-wheel smoke.

Portia's published `pds-core>=0.6.3,<0.7` dependency remains unchanged.
No new Core API is required by Portia's capture/routing implementation; the
viewer API is tested through Core's stable public `open_local_path` contract.

This slice does not ship a release, rewrite a frozen #54 validator, or claim
full repository/packaging/CI qualification. Those remain Issue #57 Slice 9
closeout gates, based on the exact results of both platform CI lanes.
