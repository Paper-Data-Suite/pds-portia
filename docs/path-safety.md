# Portia path-safety and generated-component policy

Issue #92 establishes Portia's application-level path-safety boundary. This
policy complements filesystem and Windows long-path support; it does not treat
machine-wide path policy as a correctness requirement.

## Core rule

Portia distinguishes domain identity from filesystem infrastructure identity.

Canonical records continue to use their accepted Portia/Core identities where
those identities define the storage contract. Temporary, staging, decode, and
other generated infrastructure components do not need to repeat those identities
verbatim. When a generated component only needs a stable local filesystem
identity, Portia may derive a bounded opaque token from the canonical inputs and
retain the full identity in authoritative records.

Human/display values such as student names, participant labels, Event text,
source filenames, or free text do not become generated filesystem identity by
default.

## Slice 1 generated-token contract

`portia.storage.generated_paths` introduces the first shared primitive:

```text
build_generated_path_token(domain, *identity_parts)
```

The v1 token is:

```text
pt_<32 lowercase hexadecimal characters>
```

and therefore has an exact length of 35 characters.

The hash input includes:

- the policy version;
- an explicit bounded domain separator; and
- the ordered canonical identity/provenance parts supplied by the caller.

The token is deterministic for the same inputs, domain-separated, and fixed in
length regardless of the length of the source identity text. It is filesystem
serialization only. It is not a Portia domain identifier and must not replace or
rewrite an `evt_`, `sup_`, `op_`, `step_`, `pexp_`, or other accepted identity.

Callers remain responsible for validating the semantic identity before passing
it to the helper. Display text must not be substituted for canonical identity
merely because the helper can hash arbitrary strings.

## Current path-surface audit

Slice 1 records the current path families before changing any writer.

| Surface | Representative shape | Class | Slice 1 finding |
| --- | --- | --- | --- |
| Work manifest | `.../work/<work_id>/work.json` | C + fixed leaf | Preserve canonical identity and fixed leaf. |
| Work child | `.../records/<kind>/<record_id>.json` | C | Canonical and potentially deep; qualify before changing. |
| Work storage history | new: `.../history/storage_revisions/<bounded-token>.json`; legacy identity-heavy hierarchy remains readable | B + C + F | New technical-history leaves are fixed at 40 characters and bind record kind, record ID, and full digest. |
| Actor root/child | `portia/actors/<actor_id>/...` | C | Opaque identity; audit history depth separately. |
| Actor storage history | new: `.../history/storage_revisions/<bounded-token>.json`; legacy identity-heavy hierarchy remains readable | B + C + F | New technical-history leaves are fixed at 40 characters with Actor-domain separation. |
| Operations / Quarantine / suppressions | revision directory + numeric/fixed leaf | C + fixed leaf | Slice 5 characterizes normal generated-ID relative paths at 72–84 characters; no writer rewrite is justified. |
| Derived generations | new: `portia/derived-v2/<projection-token>/generations/<generation-token>/...`; legacy scope-owned hierarchy remains readable | B + C + F | Slice 6 bounds every new representative metadata path at 115 relative characters while preserving exact legacy derived paths. |
| Teacher-reference export | `portia/exports/<pexp_id>/artifact.html` + `export.json` | C + fixed leaf | Slice 5 characterizes the generated-ID artifact path at 66 relative characters and confirms display/source text does not enter the path. |
| Coordinated staging | new: `portia/.staging/<bounded-op-token>/<bounded-candidate>.candidate`; legacy target-adjacent form remains readable | B + E + F | New writes are shallow and bounded; exact legacy candidates replay in place without migration. |
| Guarded replacement temp | `.portia-tmp-<bounded-token>.tmp` beside destination | B + E | Fixed 51-character leaf; does not repeat destination filename. |
| Workspace-file evidence/attachment | stored workspace-relative locator | D | Preserve exact provenance; never shorten or rewrite silently. |
| Existing persisted paths | previously accepted exact locations | F | Reader compatibility; no path migration solely for #92. |
| Core retained scans (future v0.3 consumer) | Core-owned retained-source provenance | D/F | Treat as opaque Core provenance; historical paths may remain long. |

Classification legend:

```text
A = fixed leaf
B = bounded opaque generated identity
C = durable canonical/domain identifier
D = external persisted path/provenance
E = temporary/staging infrastructure identity
F = legacy path that must remain readable
```

## Slice 2 bounded replacement temporaries

`guarded_replace()` retains its existing same-directory atomic replacement
boundary, expected-fingerprint check, immediate pre-replace recheck, fsync, and
readback verification. Its temporary leaf no longer repeats the destination
filename.

New replacement temporaries use:

```text
.portia-tmp-pt_<32 lowercase hexadecimal characters>.tmp
```

for an exact leaf length of 51 characters. A fresh 128-bit nonce is projected
through the Slice 1 domain-separated token primitive. Allocation is exclusive
and retries a bounded number of exact collisions. The temporary stays adjacent
to the destination so `os.replace()` preserves the established same-filesystem
atomicity assumption.

The leaf is infrastructure identity only. It is never persisted as domain or
provenance identity, and failure cleanup remains best-effort without deleting
the canonical destination.

## Slice 3 bounded coordinated staging

New coordinated byte candidates no longer inherit the destination directory
depth. Portia stages new candidates beneath:

```text
portia/.staging/
  pt_<operation-token>/
    pt_<candidate-token>.candidate
```

The operation directory token is exactly 35 characters. The candidate leaf is
exactly 45 characters and is deterministically bound to the validated operation
ID, step ID, and exact workspace-relative destination. The full operation, step,
and destination identities remain authoritative in the accepted Operation
Journal and `StagedArtifact`; the filesystem tokens are infrastructure
serialization only.

The pre-Issue-92 layout remains a reader/replay compatibility surface:

```text
<destination-parent>/
  .portia-staging/
    <operation_id>/
      <step_id>.candidate
```

`stage_bytes()` recognizes one exact legacy candidate and reuses it in place
when its bytes match the journaled candidate. It does not rename, copy, or
migrate that artifact. If both legacy and current staging identities exist for
one operation step, Portia fails closed rather than guessing which staged
evidence is authoritative.

Publication, fingerprint verification, idempotent replay, contradiction
detection, containment, and exact cleanup semantics remain unchanged.

## Slice 4 bounded technical storage history

New work and Actor technical storage revisions no longer serialize record kind,
record ID, and a full 64-character digest as nested filesystem components.

New work history uses:

```text
<work-root>/history/storage_revisions/
  pt_<32 lowercase hexadecimal characters>.json
```

New Actor history uses the same 40-character leaf shape beneath the Actor's
`history/storage_revisions/` directory, with a distinct Actor domain separator.

The token binds:

- owner domain (`work_storage_revision` or `actor_storage_revision`);
- exact record kind;
- exact record ID; and
- the full prior-byte SHA-256 digest.

The full semantic identity remains recoverable from the owning canonical record
and the caller's exact history lookup inputs; the bounded leaf is filesystem
serialization only.

Pre-Issue-92 history remains valid at:

```text
.../history/storage_revisions/<kind>/<record_id>/<sha256>.json
```

Before creating a new history artifact, repository replacement checks both the
new and legacy exact identities. An exact legacy artifact is verified and reused
in place without rename, copy, or migration. If both current and legacy
identities exist for the same revision, Portia fails closed rather than
manufacturing an authority preference.

Technical history remains exact prior-byte recovery evidence and does not become
domain history.

## Slice 5 canonical path-geometry characterization

The remaining canonical families were measured with Portia's ordinary generated
32-hex IDs and a representative 119-character deep workspace root. This is a
regression characterization, not a universal filesystem limit.

Routine workspace-level series remain shallow:

```text
operation revision              72 relative / 192 projected absolute
quarantine revision             74 relative / 194 projected absolute
finding-suppression revision    84 relative / 204 projected absolute
teacher-reference artifact      66 relative / 186 projected absolute
```

These families already use durable opaque IDs plus numeric or fixed leaves.
Changing their canonical identities would add compatibility cost without
addressing a demonstrated amplification defect, so Slice 5 deliberately leaves
their production writers unchanged.

Derived state is materially different. Representative metadata paths measure:

```text
work scope       184 relative / 304 projected absolute
class scope      142 relative / 262 projected absolute
workspace scope  128 relative / 248 projected absolute
operation scope  143 relative / 263 projected absolute
graph scope      142 relative / 262 projected absolute
```

The 260-character figure is used only as a historical Windows/native-tooling
pressure reference. Portia does not adopt it as a universal application maximum.

The result is that derived-state serialization remains the one canonical
Portia-owned path family requiring dedicated #92 hardening.

## Slice 6 bounded derived-state serialization

New derived projections use an internal storage-layout v2:

```text
portia/derived-v2/
  pt_<projection-scope-token>/
    current.json
    generations/
      pt_<generation-token>/
        data.json
        metadata.json
```

The projection token is exactly 35 characters and binds the projection kind plus
the same semantic scope identity that selected the legacy projection root. The
generation token is exactly 35 characters and binds the projection token plus
the exact `dgen_` identity. Domain IDs and `derived_*@1` record contracts are
unchanged.

For the Slice 5 representative matrix, every new metadata path is now exactly
115 workspace-relative characters, or 235 projected absolute characters under
the same 119-character deep root. `current.json` is 66 relative characters and
generation `data.json` is 111.

Pre-Issue-92 derived state remains readable in its exact original scope-owned
layout. Portia does not rename, copy, or delete legacy generations.

Reader selection is deterministic:

```text
bounded v2 current pointer exists -> use bounded layout
otherwise legacy current exists   -> use legacy layout
otherwise                         -> no selected generation
```

A corrupt bounded pointer is an error; Portia does not silently downgrade to a
legacy pointer.

When a legacy current projection receives a new generation, installation first
verifies the exact expected legacy-pointer fingerprint. The new generation is
written only to the bounded v2 layout, then a bounded `current.json` is created.
The legacy pointer and generation remain byte-for-byte untouched. From that
point forward, the bounded current pointer is authoritative for Portia's derived
reader. This is a prospective writer cutover, not a workspace migration.

Metadata continues to bind the exact `data_artifact.workspace_relative_path`.
Legacy metadata is checked against its legacy data path; newly written metadata
is checked against its bounded v2 data path.

## Slice 7 physical deep-workspace qualification

The hardened source tree now includes physical filesystem qualification beneath
a synthetic workspace root targeted at 119 absolute characters. The helper
creates the workspace directly under the host temporary root so pytest's own
nested test directory does not accidentally determine the geometry. If a host
temporary root is already unusually long, the test preserves that greater
stress rather than manufacturing a shorter path.

The qualification performs real writes and readback through three representative
flows:

- coordinated staging, publication, cleanup, canonical Event replacement, and
  bounded technical storage-history preservation;
- operation-backed bounded derived generation installation and current reload;
- complete reviewed teacher-reference export execution, including its operation
  journal, staged writes, artifact, and provenance.

The derived metadata artifact remains 115 workspace-relative characters in this
qualification and reaches at least 235 absolute characters under the requested
deep root. The tests exercise actual Python filesystem calls; they do not merely
calculate path strings and do not inspect or alter Windows `LongPathsEnabled`.

This slice intentionally changes no production writer. A failure here is a
qualification signal requiring a focused repair rather than a reason to shorten
unrelated canonical identities.

## Writer and reader compatibility

Issue #92 follows this compatibility model wherever a writer changes:

```text
reader:
    continue to honor valid existing stored paths

new writer:
    use the hardened bounded infrastructure policy
```

No Slice 1 code changes an existing writer. The token primitive is intentionally
unused by production persistence until a later slice changes one path family and
adds its compatibility/recovery tests at the same time.

## External workspace paths

The existing workspace-relative path contract is provenance, not a promise that
every host can open every valid path. A later #92 slice may improve current-use
failure classification, but it must not rewrite the stored locator, invent a
replacement identity, or treat path unavailability as substantive behavior
evidence.

## Future retained-source decoding rule

Core owns retained-source identity and custody. Core 0.6.4 bounds new retained
scan names but intentionally leaves historical Core 0.6 paths unchanged.

Future Portia paper/image/PDF processing must therefore prefer:

```text
validated Core retained-source provenance
    -> Python-controlled exact byte read
    -> decoder/interpreter
```

rather than requiring a native library to reopen the canonical retained path by
filename. If a native library requires a filename, Portia should use a bounded,
non-authoritative temporary decode boundary and must not persist that temporary
path as provenance.

## Explicit non-goals of Slice 1

Slice 1 does not:

- rename or migrate any existing path;
- change canonical Portia identity;
- change staging layout;
- change guarded replacement behavior;
- change workspace-relative path schemas;
- implement paper/PDF/image decoding;
- claim one universal absolute-path maximum.

Those changes require their own focused slices and compatibility tests.
