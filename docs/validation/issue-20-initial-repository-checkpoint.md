# Issue #20 Initial Repository Checkpoint

**Status:** Initial remote checkpoint complete; local baseline pending exact branch run
**Issue:** `#20 — Define paper-assisted capture, PDS2 routing, and import contracts`
**Date:** 2026-08-13

## Exact starting anchors

```text
pds-portia/main
c69533fa980cf41aa92c52978617e170263f6135

pds-portia/20-paper-assisted-capture-pds2-routing-import-contracts
c69533fa980cf41aa92c52978617e170263f6135

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-quillan/main
5974c6436f5f34df6d869e846fbb638d02359451

pds-scoreform/main
047e47f60730b8a5540b5e1d92f008ffad37eede
```

## Initial Portia remote comparison

```text
status: identical
ahead:  0
behind: 0

merge base:
c69533fa980cf41aa92c52978617e170263f6135
```

The Issue #20 branch was therefore an exact remote branch point from reconciled
Portia main before Slice 1.

## Test baseline context

The final observed Issue #19 authoritative schema-validation run was:

```text
880 tests
OK
```

Issue #20 must still record an observed authoritative run on the exact local
Issue #20 checkout. Slice 1 intentionally does not claim that a remote
repository inspection executed the local suite.

Run after applying Slice 1:

```powershell
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```

The expected count is 880 because Slice 1 adds documentation only. Actual local
output is authoritative and will be recorded in the pre-ADR checkpoint.

## ADR availability

At the initial repository inspection, Portia decision records run through ADR
0015; `0016` appears available.

Recheck immediately before publishing ADR 0016.

## Core PDS2 checkpoint

Core's current routing model requires one physical page locator containing:

```text
module_id
class_id
work_id
route_id
```

and one `RouteRegistration` targeting an existing module-owned record.

The target therefore must exist before QR/PDS2 rendering.

Core also owns retained-source scan identity/provenance, including source-scan
identity and SHA-256 fingerprinting. Portia semantic failure must not erase or
rewrite that retained-source truth.

## Portia provenance checkpoint

Current `creation_source@1` already distinguishes:

```text
digital_entry
paper_capture
import
```

Paper provenance includes:

```text
stage = preallocated | ingested
route_id
page_record_id
```

Current `source_artifact_ref@1` already anticipates:

```text
kind = paper_capture
route_id
page_record_id
source_page_number?
```

and separately supports fingerprinted workspace files.

Issue #20 must reconcile these published contracts without mutating them in
place.

## Existing `source_snapshot@1` checkpoint

`source_snapshot@1` is **not** a generic ingest snapshot. Its published meaning
is a deterministic inventory for one derived-projection generation.

Its closed projection/source-role semantics make it unsuitable as the
authoritative import-source snapshot.

Issue #20 may reuse it for derived paper/import review indexes where its
projection semantics fit, but should not overload it for raw import-source
history.

## Initial architecture finding

The central conflict is:

```text
Core PDS2 requires module work_id before printing

but

Portia behavior-domain work_id means Event or Support Process
```

for pages such as:

```text
blank new-Event form
class-level multi-entry sheet
```

Creating a fake Event solely for routing would violate Portia's accepted Event
semantics.

The initial working design therefore recommends evaluating a bounded operational
Capture Batch work root that is Core-addressable but is **not** a third
behavior-domain `portia_work_ref@1` kind.

No schema or public contract is added by Slice 1.

## Files introduced by Slice 1

```text
docs/design/portia-paper-assisted-capture-pds2-routing-and-import.md
docs/validation/issue-20-initial-repository-checkpoint.md
```

## Drift policy

Before ADR acceptance:

1. rerun/fetch exact Portia/Core/Quillan/ScoreForm anchors;
2. compare the feature branch with current Portia main;
3. rerun the authoritative Portia suite;
4. recheck ADR 0016 availability;
5. reconcile any material PDS2 or source-provenance drift.

Before final Issue #20 acceptance, repeat the same drift audit.
