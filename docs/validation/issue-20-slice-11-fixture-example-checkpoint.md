# Issue #20 Slice 11 Fixture and Synthetic Example Checkpoint

Authoritative user-run validation after applying Slice 11:

```text
Ran 1013 tests in 135.276s

OK
```

`git diff --check` produced no output.

## Example inventory

Slice 11 established 52 synthetic examples:

```text
22 baseline-valid
22 structural-invalid
8 richer valid scenarios
52 total
```

Every one of the 22 public Issue #20 contracts has at least one valid and one
structural-invalid fixture.

The fixtures are structurally validated through the repository's normal offline
schema registry. Cross-record/runtime authority conditions remain in the
application-invalid matrix rather than being falsely represented as JSON Schema
facts.

This is the authoritative pre-ADR local checkpoint for Slice 12.
