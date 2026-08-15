# Portia Deliberate Export and Provenance Contracts

**Status:** Issue #21 Slice 4 accepted implementation direction
**Date:** 2026-08-14

## 1. Decision

Issue #21 adopts:

```text
export_source_inventory@1
deliberate_export@1
portia_deliberate_export_id@1
```

with new public prefix:

```text
pexp_
```

A deliberate export is durable operational provenance, not behavior-domain truth.

## 2. `source_snapshot@1` remains unchanged

`source_snapshot@1` is a filesystem/discovery inventory for rebuildable derived
projections. It includes discovery roots, workspace-relative source paths,
operational source roles, and a closed Issue #13 `projection_kind` vocabulary.

A deliberate outward export needs a different semantic object:

```text
exact contributing source representations
+ exact privacy policy
+ authorization provenance
+ projection-decision digest
+ one accepted immutable output artifact
```

Therefore:

```text
source_snapshot@1 unchanged
derived_index_metadata@1 unchanged
export_source_inventory@1 separate
```

Creating `source_snapshot@2` merely to add export kinds would preserve the wrong
discovery-oriented abstraction.

## 3. Vitrine precedent without Vitrine ownership

Vitrine correctly separates Snapshot Edition, Export Artifact, Issuance,
Submission, Delivery, Receipt, and external acceptance.

Portia adopts the separation principle, not the Portfolio custody model:

```text
export generated != disclosure
export generated != delivered
export generated != received
export generated != read
export generated != consent
export generated != legal notice
export generated != external acceptance
```

Portia does not create Snapshot Series/Editions, Issuance, Submission, or Receipt
for ordinary behavior/support export.

## 4. Export Source Inventory

`export_source_inventory@1` inventories only exact source representations that
materially contributed to the accepted output.

It deliberately does not persist exact references for every withheld,
unavailable, absent, or manual-review candidate considered by projection.

Supported source kinds:

```text
portia_work
portia_record
module_record
source_artifact
```

Each entry binds source role, exact reference, representation SHA-256, and byte
length. Foreign module records require a non-null exact contract version.

The representation digest is the exact authorized/public representation actually
consumed, not a claim about inaccessible private bytes.

Source roles:

```text
projected_domain
projection_context
correction_context
disagreement_context
included_artifact
foreign_projection
```

## 5. Inventory digest

`inventory_digest` binds canonical:

```text
inventory_algorithm
entries
```

Application validation resolves and fingerprints sources, sorts entries
deterministically, rejects duplicate semantic source identity, recomputes the
digest, and rechecks immediately before output acceptance.

## 6. One `pexp_` equals one accepted artifact

One PDF, CSV, JSON, HTML, or ZIP artifact gets one export identity.

A single user action requesting PDF and CSV produces two exports even if they
share source inventory and decision digest.

A digest never replaces business identity. Separate export actions may produce
identical bytes.

## 7. Purpose and scope

Purpose reuses the closed Issue #21 vocabulary:

```text
teacher_current
participant_specific
student_facing
family_facing
aggregate_equity
administrative_export
```

Scope:

```text
work
class
workspace
explicit_source_set
```

Broad scope never bypasses privacy policy.

Focal purposes require an exact focal Portia participant/subject reference and
application-level scope alignment.

## 8. Policy provenance

Every export requires exact:

```text
policy_id
policy_version
policy_digest
```

Changing policy never rewrites a historical export.

## 9. Authorization provenance

Every accepted export carries one positive authorization provenance branch:

```text
policy_rule
external_decision
```

Both record `result = authorized`, exact rule/decision identity, version, digest,
evaluation time, and recording attribution.

This records what Portia relied upon. It does not prove institutional identity,
FERPA entitlement, guardianship, consent, legal sufficiency, or completion of an
institutional disclosure log.

## 10. Projection decision and withheld/unavailable state

The export stores `projection_decision_digest`, binding the complete restricted
privacy-decision inventory used for generation without embedding every hidden
source identity.

It also stores privacy-minimized counts for:

```text
included
withheld
unavailable
absent
manual_review_resolved
```

Count unit is `projection_item`.

There is no accepted unresolved-manual-review state.

## 11. Manual review

Accepted states:

```text
not_required
resolved
```

Resolved review binds the exact reviewed projection digest, review time, and
local operator. Application validation requires reviewed digest equality with
the export's `projection_decision_digest`.

This is privacy review, not Portia domain Review/Classification/Hypothesis/
Determination/Fidelity/Outcome.

## 12. Output custody

Output bytes remain outside canonical JSON.

Receipt metadata binds:

```text
format
media type
workspace-relative path
byte length
SHA-256
```

Canonical output path is derived from opaque export identity, e.g.:

```text
portia/exports/pexp_example/artifact.pdf
```

Paths must not encode student/person names, class titles, behavior labels,
support labels, family names, or source titles.

## 13. Coordinated generation

Generation reuses Operation Journal/Lock:

```text
deliberate local-operator request
-> policy/authorization preflight
-> exact source resolution
-> privacy projection
-> manual review if required
-> source inventory
-> stage output
-> verify digest/length
-> exclusive final artifact creation
-> read-back verify
-> immutable deliberate_export receipt
-> read-back verify
-> commit operation
```

Crash after artifact acceptance but before receipt must reconcile the exact
artifact and operation, then create only the missing receipt. Recovery must not
create a duplicate artifact.

## 14. Historical immutability and supersession

Historical export bytes and receipts are never rewritten because source,
policy, authorization, redaction rules, or renderer later change.

A new export receives a new `pexp_`.

Optional `supersedes` identifies a prior export intentionally replaced for
current use. It does not erase or recall the old artifact.

## 15. Export is not disclosure logging

`deliberate_export@1` intentionally contains no recipient, delivery, receipt,
read, or external-acceptance fields.

If Portia later needs disclosure/audit records, they remain a separate contract
or institutional integration surface.

## 16. Retention preview

Slice 5 will distinguish:

```text
output artifact bytes -> export_bytes
deliberate_export receipt -> export_provenance
restricted privacy-decision material -> policy-specific operational retention
```

Deleting local export bytes does not imply external copies were deleted.

## 17. Reused contracts

No existing public contract is changed.

Reused:

```text
operation_journal_ref@1
attribution_agent@1
exact Portia work/record refs
module_work_record_ref@1 with non-null export constraint
source_artifact_ref@1
workspace_relative_path@1
sha256_digest@1
```
