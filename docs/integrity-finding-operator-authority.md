# Integrity Finding operator authority

Portia v0.2 uses one closed application-local authority for Integrity Finding
operator workflows in its teacher-local deployment. This capability represents
the deliberate operator of the selected local workspace. It is not
authentication, institutional authorization, Actor Directory role authority, or
a general permissions system.

The package-owned suppression policy is:

```text
policy_id       = portia.finding_suppression.teacher_local
current version = 1
asserted_role   = teacher_local_operator
```

New suppression authorization requires `authorized_by.type = local_operator`
and this exact authorization reference:

```text
kind             = portia_local_authority
reference_id     = portia.teacher_local_workspace_operator
contract_version = 1
```

The local operator's display label is attribution only. It does not prove
identity, employment, professional role, or institutional decision authority.
Actor Directory categories, titles, organizations, contacts, and relationships
are not consulted as role evidence.

Policy versions are held in an immutable package registry. Exact historical
versions remain resolvable, while a separate explicit selector identifies the
current version. No maximum version, lexical ordering, timestamp, filesystem
order, or insertion order establishes currentness. A new suppression must use
the explicitly current version.

`policy_version_change` is proven only when the bound policy ID and historical
version are known, the policy has an explicit valid current selection, and that
selection differs from the bound version. Unknown versions and missing or
invalid current selection fail closed; they are neither treated as changed nor
unchanged.

The teacher-local operator may acknowledge the four categories published by
`finding_acknowledgement@1`. System processes are default-denied. A process can
act only when its exact process ID and category are present in a closed
application registration; the production v0.2 registry contains no such
system-process registrations.

This authority validates only the policy/operator facts required by the
published acknowledgement and suppression contracts. It does not decide
whether a finding is suppressible, persist acknowledgement or suppression
records, change finding state, clear blocking effects, or perform recovery or
quarantine work.
