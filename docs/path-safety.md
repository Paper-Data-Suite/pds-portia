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
| Work storage history | `.../history/storage_revisions/<kind>/<record_id>/<sha256>.json` | C + fixed digest | High path-pressure surface; requires explicit deep-workspace qualification. |
| Actor root/child | `portia/actors/<actor_id>/...` | C | Opaque identity; audit history depth separately. |
| Actor storage history | `.../history/storage_revisions/<kind>/<record_id>/<sha256>.json` | C + fixed digest | High path-pressure surface. |
| Operations / Quarantine / suppressions | revision directory + numeric/fixed leaf | C + fixed leaf | Structurally bounded by durable IDs but still subject to workspace depth. |
| Derived generations | scope/projection hierarchy + `metadata.json` / `data.json` | C + fixed leaf | Fixed leaves are good; dynamic scope/projection geometry needs qualification. |
| Teacher-reference export | `portia/exports/<pexp_id>/artifact.html` + `export.json` | C + fixed leaf | Preserve; no human filename expansion. |
| Coordinated staging | `<destination-parent>/.portia-staging/<operation_id>/<step_id>.candidate` | E | Repeats operation/step identity and deepens the destination; candidate for a later #92 slice. |
| Guarded replacement temp | target-adjacent temporary name derived from `path.name` | E | Temporary leaf expands with destination filename; candidate for the next #92 slice. |
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
