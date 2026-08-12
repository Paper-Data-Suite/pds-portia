# Portia Support Process / Support / Intervention / Implementation / Fidelity Examples

**Issue:** #18

All examples below are **synthetic** and illustrate Issue #18 contract boundaries.

```text
planned Support / Intervention
≠ actual Implementation

Implementation
≠ Fidelity

Fidelity
≠ effectiveness
≠ student compliance
≠ provider competence
≠ Outcome
```

| # | Synthetic scenario | Contract(s) | Boundary demonstrated |
|---:|---|---|---|
| 1 | Synthetic Active teacher-identified process | `support_process@1` | A bounded class-owned workflow begins from a teacher-identified access need; initiation is context, not diagnosis. |
| 2 | Synthetic Event-initiated process | `support_process@1 + work_relationship@2` | The process draws exact context from an Event without turning several Events into a causal pattern. |
| 3 | Synthetic Response handoff initiation | `support_process@1 + response@1` | An exact Response handoff may initiate planning but does not prove downstream delivery. |
| 4 | Synthetic Represented request initiation | `support_process@1` | A represented student/family request may initiate work without becoming consent or institutional authorization. |
| 5 | Synthetic Imported historical process | `support_process@1` | Historical import remains proposed until reviewed; imported labels do not establish current status. |
| 6 | Synthetic Cross-year continuation | `support_process@1` | A new class-owned Support Process continues from one exact predecessor without becoming one indefinite dossier. |
| 7 | Synthetic Supported roster participant | `support_process_participant@1` | A class-qualified roster student is included as supported_person; participation is not compliance. |
| 8 | Synthetic Cross-class participant | `support_process_participant@1` | A student from another legitimate roster may participate without splitting ownership. |
| 9 | Synthetic Actor collaborator participant | `support_process_participant@1` | A recurring Actor may collaborate; Actor category/title does not prove service authority. |
| 10 | Synthetic Descriptive family participant | `support_process_participant@1` | A descriptive family/support person can be represented without fabricating guardianship. |
| 11 | Synthetic Local coordinator participant | `support_process_participant@1` | A local operator may coordinate; process context remains distinct from persistence attribution. |
| 12 | Synthetic Observer participant | `support_process_participant@1` | Observer context does not by itself grant professional authority or provider status. |
| 13 | Synthetic Participant access need | `support_need@1` | A bounded access need is descriptive and non-diagnostic. |
| 14 | Synthetic Whole-process environmental need | `support_need@1` | An environmental need may target the process rather than become a student trait. |
| 15 | Synthetic Participant-set organizational need | `support_need@1` | An explicit participant set can share a need; ordering has no domain meaning. |
| 16 | Synthetic Skill-or-strategy need | `support_need@1` | A skill/support need does not become a behavioral-function or disability finding. |
| 17 | Synthetic Relationship/connection need | `support_need@1` | A relationship-support need is not a judgment of blame or character. |
| 18 | Synthetic Resource/coordination need | `support_need@1` | A resource-coordination need does not prove eligibility for an institutional service. |
| 19 | Synthetic Goal with planned criteria | `support_goal@1` | Criteria describe future review methodology, not current progress or attainment. |
| 20 | Synthetic Goal without criteria | `support_goal@1` | A desired future condition can remain qualitative without fabricated percentages. |
| 21 | Synthetic Whole-process goal | `support_goal@1` | A process-level goal guides planning without becoming an Outcome. |
| 22 | Synthetic Participant-set goal | `support_goal@1` | A goal may target an explicit set without becoming a compliance target. |
| 23 | Synthetic As-needed access Support | `support@1` | An as-needed access condition may honestly have no assigned human provider. |
| 24 | Synthetic Assigned recurring Support | `support@1 + planned_schedule@1` | A recurring Support names planned provider/cadence; the schedule is not Implementation history. |
| 25 | Synthetic Goal-linked Support | `support@1` | Support may reference one or more exact Goals without becoming an Intervention. |
| 26 | Synthetic Self-directed Support | `support@1` | A self-directed plan may lack an assigned provider without implying unsupported care. |
| 27 | Synthetic Resource-availability Support | `support@1` | A planned resource may be available without fabricating delivery occurrences. |
| 28 | Synthetic Paused Support | `support@1` | Plan state paused is distinct from invalidated and does not state effectiveness. |
| 29 | Synthetic Active recurring Intervention | `intervention@1 + planned_schedule@1` | An active Intervention requires exact Need/Goal links, assigned provider, and non-as-needed schedule. |
| 30 | Synthetic Condition-triggered Intervention | `intervention@1 + planned_schedule@1` | A bounded trigger can replace fabricated fixed frequency. |
| 31 | Synthetic Custom-schedule Intervention | `intervention@1 + planned_schedule@1` | A bounded custom schedule preserves honest planning when recurrence primitives are insufficient. |
| 32 | Synthetic Multi-provider Intervention | `intervention@1` | Several exact Participants may be assigned; assignment does not establish licensure or authorization. |
| 33 | Synthetic Proposed as-needed Intervention | `intervention@1` | As-needed may exist while proposed but is not eligible as an active Intervention schedule. |
| 34 | Synthetic Completed Implementation occurrence | `implementation@1` | One actual bounded occurrence records what happened and remains distinct from Fidelity and Outcome. |
| 35 | Synthetic Attempted Implementation | `implementation@1` | An attempt is preserved without converting failure to implement into student fault. |
| 36 | Synthetic In-progress Implementation | `implementation@1` | In-progress is a factual execution state, not a success label. |
| 37 | Synthetic Partially completed Implementation | `implementation@1` | Partial completion is factual and does not imply partial effectiveness. |
| 38 | Synthetic Unable-to-complete Implementation | `implementation@1` | Unable to complete records the occurrence without assigning blame. |
| 39 | Synthetic No-human-provider Implementation | `implementation@1` | Actual environmental/resource access may occur without a human provider. |
| 40 | Synthetic Provider variation | `implementation@1` | A one-off actual-provider difference is recorded as variation rather than rewriting the plan. |
| 41 | Synthetic Target variation | `implementation@1` | A one-off target difference is recorded without silently adapting future plan semantics. |
| 42 | Synthetic Multi-kind variation | `implementation@1` | Provider/target/timing/procedure/context variation can be described without creating a fidelity score. |
| 43 | Synthetic Imported unknown Implementation | `implementation@1` | Historical imported execution may remain unknown and proposed; digital entry cannot invent unknown delivery. |
| 44 | Synthetic One-Implementation Fidelity | `fidelity@1` | An attributed evaluator compares one exact Implementation with one exact plan. |
| 45 | Synthetic Implementation-set Fidelity | `fidelity@1` | Two or more exact Implementations may be evaluated together only against the same exact plan. |
| 46 | Synthetic Bounded-interval Fidelity | `fidelity@1` | A plan interval can be evaluated without implying an Implementation occurred at every scheduled time. |
| 47 | Synthetic Unscored checklist Fidelity | `fidelity@1` | An unscored checklist can support evaluation without fabricating a numeric score. |
| 48 | Synthetic Scored instrument Fidelity | `fidelity@1` | A numeric value is meaningful only within the identified source-defined instrument/version/scale. |
| 49 | Synthetic Combined-basis Fidelity | `fidelity@1` | Observation, records, and instrument evidence may combine without becoming an effectiveness claim. |
| 50 | Synthetic Support Process coordination Communication | `communication@1` | Support coordination records a contact act; it is not consent, service delivery, Implementation, Fidelity, or Outcome. |

## Executable evidence

```text
tests/schema_validation/fixtures/issue-18/
tests/schema_validation/test_issue_18_support_process_root_contracts.py
tests/schema_validation/test_issue_18_need_goal_contracts.py
tests/schema_validation/test_issue_18_support_intervention_contracts.py
tests/schema_validation/test_issue_18_implementation_contract.py
tests/schema_validation/test_issue_18_fidelity_contract.py
tests/schema_validation/test_issue_18_shared_infrastructure_integration.py
```

These examples are explanatory, not new wire contracts.
