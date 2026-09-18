# Issue #47 Corrective Slice 33.1A Validation

## Decision and scope

ADR 0018 chooses immutable `operation_journal@3` over a sidecar record. A
sidecar could not keep canonical removal inside the complete bounded write set
without creating competing commit/recovery authority. Version 2 is unchanged
and remains current for existing non-removal operations. Version 3 is required
for `exceptional_remove`; each operation revision series has one contract
version, while independent v2 and v3 series may coexist.

This correction adds durable absence evidence only. It does not implement an
Exceptional Removal service, authorization policy, destructive primitive,
work/Actor removal executor, or derived-payload purge.

## Contract evidence

The v3 write action is `exceptional_remove`. Schema and application validation
bind it to `operation_kind = exceptionally_remove`, `phase = canonical_gate`,
`representation_role = canonical_domain`, an exact `must_match` prior
fingerprint/contract version, and an earlier exact certificate creation step.

The result branches are:

| Result | Required evidence |
| --- | --- |
| Intended present | `kind`, contract version, content fingerprint, selected state |
| Intended absent | `kind`, exact prior contract/fingerprint, exact certificate ref/path/fingerprint, selected state |
| Observed present | `kind`, path, content fingerprint, explicit-offset observation time |
| Observed absent | `kind`, checked path, explicit-offset observation time |

Absence carries neither removed bytes nor a fake fingerprint. Committed and
completed journals retain the existing rule that every canonical gate is
accepted, so unverified absence cannot reach the commit point. The existing
partial-state sets classify accepted, verified, durable-unverified,
indeterminate, and remaining removal steps without a parallel state model.

## Application-invalid coverage

Focused fixtures and runtime tests reject or classify:

| Condition | Deterministic result |
| --- | --- |
| Prior intent differs from precondition | application-invalid journal |
| Certificate ref/path/fingerprint missing or unresolved | removal-certificate defect |
| Certificate target or prior-content evidence differs | removal-certificate mismatch |
| Payload retained after accepted absence | `REMOVAL_TARGET_RETAINED` |
| Payload changed after preflight | `REMOVAL_TARGET_CHANGED` |
| Payload absent without certificate evidence | unexplained canonical absence / indeterminate |
| Certificate present and payload absent while journal lags | durable-unverified, safe to reconcile |
| Accepted absence while payload is present | fail closed |
| v2/v3 revisions in one operation series | conflict/corruption |
| `exceptional_remove` outside its operation/role/phase | schema-invalid |
| `remove_transient` against canonical domain | schema-invalid |

The certificate link is also required to match a preceding
`exclusive_create` step and exact planned certificate bytes. Class-scoped
certificates use `exceptional-removal-ref@1`. Actor-directory certificates use
the minimal exact removal ID/version branch and the existing workspace-level
certificate path; no Actor removal workflow is added.

## Recovery and integrity

Present-byte v2 behavior is unchanged: a missing accepted destination remains
`PORTIA.STORAGE.DURABLE_RESULT_MISSING`. Version 3 present-byte steps use the
same rule. For absence steps the evaluator checks the inverse postcondition and
validates exact certificate bytes, identity, target, operation linkage where
applicable, and prior evidence. Recovery distinguishes certificate/payload
partial states without using timestamps or filesystem order, never repeats a
destructive mutation merely because the journal lags, and never reconstructs
removed content.

The ordinary coordinator recognizes `exceptional_remove` as specialized and
refuses to send it through byte publication. The real handler remains deferred.

## Compatibility

`operation_current_pointer@1` still selects an exact revision number; the
selected revision body declares v2 or v3 explicitly. Existing operation
references already include `contract_version`, so no reference version is
needed. Runtime coverage and the installed contract bundle include v3 while
retaining v1/v2 reads.
