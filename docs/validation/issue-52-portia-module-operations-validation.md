# Issue #52 Portia Module Operations Validation

## Scope

Issue #52 exposes Portia through Core module-operations contract v1 without moving Portia domain authority into Core or the Paper Data Suite shell. The installed distribution registers exactly one profile:

```text
paper_data_suite.module_operations
portia = portia.pds_operations:get_module_operations_profile
```

That profile exposes independent Portia-owned attention and readiness providers while preserving the existing public launcher:

```text
portia = portia.cli:main
```

## Authority boundaries

Portia native Issue #49 attention remains the semantic authority for teacher attention. The Core adapter captures one explicit timezone-aware invocation instant, delegates to `AttentionQueryService`, and projects only bounded shared codes, labels, counts, exact shared class/work context when safely common, and opaque owner-action identity.

The owner-action vocabulary is closed:

```text
open_complete_follow_up
open_add_information
open_manage_support
open_advanced_tools
```

Those values are routing identity only. Issue #52 does not execute actions, import Suite launch orchestration, or introduce a generic action executor.

Portia readiness is structural/contextual. It answers whether the exact supplied workspace/class context can be meaningfully used by Portia. A known structural blocker is `ready=False`; inability to inspect the authority safely is `evaluation="unavailable"` with `ready=None`. Readiness does not interpret behavior risk, attention backlog, integrity severity, recovery state, export history, or student need.

Both providers are read-only. Missing workspace context never falls back to environment/default workspace resolution, and provider discovery itself does not read teacher data.

## Distribution boundary

The wheel must contain:

```text
portia/pds_operations.py
portia/attention_provider.py
portia/readiness_provider.py
portia/attention/actions.py
```

and exactly the expected Core operations entry point. The existing `portia` console script remains unchanged. No `paper_data_suite.modules` routing provider or `paper_data_suite.publication_producers` provider is added by Issue #52.

Portia retains the runtime declaration:

```text
pds-core>=0.6.3,<0.7
```

with no sibling-PDS runtime dependency.

## Core qualification boundary

Final Issue #52 qualification uses two authenticated released Core artifacts for two different purposes:

- **Core 0.6.4** is the authoritative current closeout artifact for the complete source qualification and the Issue #52 installed module-operations smoke.
- **Core 0.6.3** remains the exact artifact for historical installed-wheel smokes that were accepted at earlier checkpoints. Those scripts are not rewritten merely to make old evidence look current.

Authenticated wheel identities are:

```text
pds_core-0.6.4-py3-none-any.whl
SHA-256 48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b

pds_core-0.6.3-py3-none-any.whl
SHA-256 98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5
```

This dual-artifact closeout preserves historical checkpoint semantics while also proving current Portia source and installed #52 interoperability against released Core 0.6.4. It does not raise Portia's declared minimum Core version.

## Mechanical validation

Run the focused validator with:

```text
python scripts/validate_module_operations.py --stage source
python scripts/validate_module_operations.py --stage distribution
python scripts/validate_module_operations.py --stage repository
```

The validator enforces the exact profile registration, profile/module identity, lazy provider boundary, native-attention reuse, closed owner-action map, structural readiness boundary, no menu dependency from provider metadata, Core-only runtime dependency direction, package inventory, authenticated Core release identities, and repository closeout wiring.

## Installed acceptance

`scripts/smoke_test_issue52_module_operations_wheel.py` creates an isolated noneditable environment containing only authenticated Core plus the built Portia wheel. It proves:

- exact entry-point discovery from installed metadata;
- the `portia.cli:main` launcher remains independently registered;
- missing workspace context is unavailable without implicit resolution;
- valid exact class readiness is true;
- safely missing exact class readiness is false;
- real native Review attention projects through Core with the expected owner action;
- readiness true may coexist with nonempty attention;
- shared results exclude student identity, private narrative, raw record identity, and workspace paths;
- provider invocation performs no workspace writes;
- no sibling module is required at runtime.

## Authoritative repository qualification

After the Slice 6 closeout commit is created, run:

```text
python scripts/validate_repository.py \
  --core-wheel <pds_core-0.6.4-py3-none-any.whl> \
  --historical-core-wheel <pds_core-0.6.3-py3-none-any.whl>
```

The command runs the full pytest suite, Ruff, strict MyPy, `pip check`, historical source validators, Issue #52 validation, build and Twine checks, generic/historical package inventories, historical installed-wheel smokes against Core 0.6.3, and the current Issue #52 installed-wheel smoke against Core 0.6.4.

Observed test counts are intentionally not hard-coded as acceptance authority. The final command output and the committed `HEAD` being qualified are authoritative.
