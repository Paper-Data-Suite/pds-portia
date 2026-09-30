# Issue #51 Bounded Deliberate Local Exports Validation

## Scope

Issue #51 implements Portia's first production deliberate local teacher-reference export workflow on top of the accepted Issue #21 privacy/provenance contracts, Issue #48 student-view boundary, Issue #50 teacher-menu taxonomy, and Issue #88 coordinated-operation/recovery authority.

The production path is one exact current `event@2` or `support_process@1` -> exact source discovery -> closed privacy projection -> explicit manual-review resolution where required -> exact source inventory -> deterministic HTML -> zero-write preview -> `EXPORT` confirmation -> final revalidation -> Issue #88 persistence -> immutable history verification.

## Preserved boundaries

Qualification requires all of the following:

- `teacher_current` and `participant_specific` are the only v0.2 export purposes;
- scope remains one exact work and related-work references do not recursively widen it;
- unknown contracts/fields fail closed;
- Core roster data and Actor Directory/Contact Point data are not live-enrichment channels for output;
- manual-review content is either included exactly or omitted, never automatically rewritten;
- source inventory contains exact materially contributing Portia representations only;
- HTML is deterministic, self-contained, and script-free;
- preparation and cancellation are zero-write;
- confirmation binds one exact preparation fingerprint;
- execution revalidates rather than silently repreparing;
- persistence and recovery reuse Issue #88's specialized journal/lock/staging services;
- historical exports are immutable and verification failures do not trigger regeneration;
- export generation remains distinct from disclosure, delivery, receipt, filing, or official-record status;
- runtime dependency direction remains `pds-portia -> pds-core` only.

## Acceptance evidence

`docs/validation/issue-51-acceptance-matrix.md` maps all 98 ticket-level acceptance obligations to the focused tests, package checker, and installed-wheel smoke that exercise them.

The dedicated mechanical validator is:

```text
python scripts/validate_teacher_reference_exports.py --stage source
python scripts/validate_teacher_reference_exports.py --stage distribution
python scripts/validate_teacher_reference_exports.py --stage repository
```

## Distribution qualification

The Issue #51 package checker requires every export runtime module and contextual menu module in the wheel. The source distribution must additionally contain the Issue #51 tests, documentation, validator, package checker, and installed-wheel smoke. The raw repository schema tree remains excluded from the runtime wheel.

The isolated Issue #51 wheel smoke installs only authenticated Core 0.6.3 plus the built Portia wheel and proves:

- exact Event HTML export and verification;
- exact Support Process HTML export and verification;
- participant-specific focal export;
- `operation_journal@4` and `operation_lock@3` candidates;
- immutable artifact/provenance bytes and committed/completed revisions;
- work-scoped verified history;
- real artifact-only partial-commit recovery through the Issue #88 path;
- no sibling-PDS runtime dependency.

## Authoritative repository qualification

Run:

```text
python scripts/validate_repository.py --core-wheel <pds_core-0.6.3-py3-none-any.whl>
```

That command reruns the complete pytest suite, Ruff, strict MyPy, `pip check`, historical validators, Issue #51 validation, build/Twine checks, generic and historical package inventories, generic and historical installed-wheel smokes, Issue #88 installed-wheel smoke, and Issue #51 installed-wheel smoke.

Observed test counts are intentionally not hard-coded here as acceptance authority; the current command output is authoritative.
