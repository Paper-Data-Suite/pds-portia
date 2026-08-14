# Issue #20 Pre-ADR Drift Checkpoint

Date: 2026-08-14

This checkpoint was performed immediately before accepting ADR 0016.

## Repository anchors

| Repository | Issue #20 starting checkpoint | Pre-ADR main | Result |
|---|---|---|---|
| `pds-portia` | `c69533fa980cf41aa92c52978617e170263f6135` | `c69533fa980cf41aa92c52978617e170263f6135` | unchanged |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | unchanged |
| `pds-quillan` | `5974c6436f5f34df6d869e846fbb638d02359451` | `b03ffad0749db0dce47e68f095a8d477fa69eb2d` | one commit ahead |
| `pds-scoreform` | `047e47f60730b8a5540b5e1d92f008ffad37eede` | `047e47f60730b8a5540b5e1d92f008ffad37eede` | unchanged |

## Quillan drift assessment

The Quillan delta is exactly one commit:

```text
b03ffad0749db0dce47e68f095a8d477fa69eb2d
Register Quillan publication producer profile (#362) (#373)
```

The compare result from the Issue #20 checkpoint to current Quillan main is
`ahead_by = 1`, `behind_by = 0`.

Changed Quillan surface is academic-publication/producer-profile integration:
README/documentation, publication producer profile, Academic Work Registration
and Academic Result Manifest integration, release inspection/acceptance,
`pds_contract.py`, and `pds_publication.py`.

No Quillan paper-retention, scan-intake, retained-source, or per-physical-page
precedent changed in this delta.

Result:

> No Issue #20 Portia paper/import decision requires revision because of the
> Quillan drift.

## ADR number

`docs/decisions/0016-define-paper-assisted-capture-pds2-routing-and-import-contracts.md`
did not exist on `pds-portia/main` immediately before ADR acceptance.

ADR 0016 is therefore available and accepted for Issue #20.

## Local branch checkpoint

Authoritative user-run validation immediately before this checkpoint:

```text
Ran 1013 tests in 135.276s

OK
```

`git diff --check` produced no output.

The branch also contains 52 synthetic Issue #20 fixtures, exceeding the required
40-example minimum.

## Scope conclusion

Pre-ADR drift does not require:

- a Core PDS2 contract fork;
- a Page Target redesign;
- a Page Record redesign;
- paper interpretation/review redesign;
- import source/replay redesign;
- operation/recovery redesign;
- or any new public Issue #20 schema.

ADR 0016 may be accepted over the Slice 2–11 implementation.
