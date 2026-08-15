# Portia Student- and Family-Facing Projection Boundaries

**Status:** Issue #21 Slice 3 architecture
**Date:** 2026-08-14

## 1. Core principle

`student_facing` and `family_facing` are separate **projection purposes**.

They are not authorization states.

```text
student_facing != requester authenticated as student
family_facing != requester is legal parent/guardian
Portia relationship != disclosure entitlement
```

A deployment must supply the actual authorization decision.

## 2. Family-facing is not automatically broader

Do not implement:

```text
family_facing = student_facing + all adult/internal information
```

Family and student projections can differ, but neither is inherently a superset
of the other.

Differences must come from an explicit policy and authorization context.

## 3. Ordinary outward content floor

When safely projectable, student/family output should favor:

- understandable Event context;
- focal student's own participant relationship;
- focal-applicable observable evidence;
- clearly labeled human judgments;
- support goals/actions relevant to the focal student;
- truthful current status;
- applicable correction/supersession context;
- applicable disagreement context;
- bounded communication facts that are safe for the focal relationship.

It should avoid unnecessary:

- native IDs;
- Core roster references;
- Actor refs;
- Contact Point values;
- source artifact locators;
- paper/import IDs;
- operation/integrity internals;
- hidden participant counts;
- unrelated source identities;
- raw third-party narrative.

## 4. Evidence and judgment labels

Outward projections must preserve source type.

Examples:

```text
Account
    represented source report/perspective

Observation
    directly observable/measured evidence

Classification / Hypothesis / Determination
    attributed human judgment

Fidelity / Outcome
    attributed evaluation
```

Do not flatten them into one "behavior fact" list.

## 5. Uncertainty and unresolved state

Preserve honest states such as:

```text
proposed
stated_uncertain
mixed_or_qualified
not_recorded
unknown
unable_to_determine
inconclusive
withheld
unavailable
requires_manual_review
```

Do not improve uncertainty for readability.

## 6. Omission language

Recipient-facing output may use privacy-minimal wording.

It need not reveal:

```text
a witness exists
a restricted Communication exists
three other participants were hidden
an attachment exists
a private Account exists
```

merely to explain an omission.

Restricted internal projection provenance retains the actual disposition.

## 7. No adverse inference from omission

The user-facing presentation must not imply:

```text
withheld information is evidence against focal student
unavailable information was negative
manual review means wrongdoing
redaction means another student accused focal student
```

Privacy state is not a behavior-domain judgment.

## 8. Student as source

When the focal student is the represented source of an Account or Statement of
Disagreement:

- their source identity may be included;
- their exact words still require third-party privacy review;
- source wording must remain quote vs recorded summary;
- being the source does not make linked artifacts automatically available.

## 9. Family member as source

When a family member/Actor is the source:

- family-facing purpose does not prove the requester is that same Actor;
- Actor identity may be conditionally included;
- Contact Point remains separate;
- narrative still undergoes third-party review.

## 10. Communication toward family

A family-facing projection of a Communication may include bounded facts such as:

```text
method
purpose
act_state
date/time at approved precision
focal recipient participation state
```

only when policy permits.

It does not automatically include:

```text
other recipients
endpoint_ref
email address
phone number
summary
attachment
related hidden record
```

`completed` does not mean read, understood, consented, or acknowledged.

## 11. Human judgments

If judgment-bearing material is included:

- preserve attribution;
- preserve scope;
- preserve currentness;
- label it as judgment/evaluation;
- do not expose hidden evidence sources automatically;
- do not make teacher-local judgment look like institutional adjudication.

## 12. Support semantics

Student/family projection must preserve:

```text
Implementation completion != success
Fidelity != effectiveness
Outcome != causal proof
Reentry completion != clearance
Repair completion != admission/remorse/forgiveness/restoration
```

Readable presentation cannot weaken these semantic boundaries.

## 13. Correction presentation

When an included item has materially changed:

- prefer the current valid representation;
- provide bounded indication that history/correction exists when needed for
  truthful interpretation;
- do not show obsolete predecessor as another current event;
- do not silently rewrite the predecessor;
- preserve exact lineage internally.

## 14. Disagreement presentation

If an applicable disagreement must accompany contested content:

- preserve source/position/statement semantics;
- privacy-review the statement separately;
- do not omit the disagreement while presenting the contested content as
  uncontested;
- if safe automatic combined projection is impossible, require manual review.

## 15. No longitudinal dossier by convenience

Student/family export or screen generation must not automatically assemble every
historical Portia record across:

```text
classes
school years
Events
Support Processes
```

A broader longitudinal request requires explicit scope and policy.

The result remains derived and nonauthoritative.

## 16. Foreign and source artifacts

An outward projection may mention a bounded fact such as:

```text
supporting source exists
```

without exposing the source locator.

Authorization for:

```text
Core retained scan
workspace file
sibling module record
external record
```

is independent from Portia record projection.

## 17. Product-safe default

When the product cannot establish safe outward meaning:

```text
do not broaden
do not guess
do not paraphrase
do not expose native JSON
```

Return/route the item as:

```text
withheld
unavailable
requires_manual_review
```

according to the actual condition.
