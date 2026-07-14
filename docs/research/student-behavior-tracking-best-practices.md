# Best Practices for Tracking and Managing Student Behavior

**Project:** Portia (`pds-portia`)<br>
**Research issue:** [#1 — Research best practices for tracking and managing student behavior](https://github.com/Paper-Data-Suite/pds-portia/issues/1)<br>
**Status:** Completed research synthesis<br>
**Last reviewed:** July 14, 2026<br>
**Scope:** K–12 educational settings in the United States

> **Important limitation:** This document is product research, not legal advice. Federal law establishes only part of the governing framework. State law, district policy, collective-bargaining agreements, records schedules, special-education procedures, civil-rights obligations, and local crisis protocols may impose additional or stricter requirements. Portia should therefore be configurable and should require implementation review by each adopting organization.

---

## Executive Summary

Portia should be designed as a **student-support and decision-documentation system**, not as a digital punishment ledger.

The research supports ten foundational conclusions:

1. **Track support processes, not merely incidents.** Effective behavior systems connect observations to prevention, instruction, intervention, follow-up, implementation fidelity, and outcomes. A count of referrals or rule violations is not, by itself, a behavior-management system.

2. **Separate observation from interpretation and adjudication.** A direct account of what a person saw or heard is different from a category assigned by a reporter, a hypothesis about behavioral function, and an administrator's formal finding. Portia should preserve those distinctions in both its data model and interface.

3. **Use objective, operational descriptions.** Records should describe observable and measurable actions, relevant context, and concrete effects. Vague labels such as “defiant,” “disrespectful,” “out of control,” or “aggressive” should never substitute for a description of what occurred.

4. **Treat context as essential data.** Time, location, activity, instructional conditions, antecedents, people present, immediate adult response, and what happened afterward can make an observation interpretable. Context should not be treated as an excuse; it is information needed for prevention and fair decision-making.

5. **Use a tiered, preventive framework.** PBIS and MTSS organize supports from universal prevention through targeted and individualized intervention. Tiers should indicate the intensity of support provided, not become permanent labels attached to students.

6. **Do not infer behavioral function from an incident form.** Functional behavioral assessment is an individualized, collaborative process using direct and indirect data. “Motivation” or “function” entered during rapid reporting is only a hypothesis and must not be represented as fact.

7. **Build equity analysis into the system while separating it from individual judgment.** Discipline data are shaped by adult referral decisions, local definitions, opportunity to observe, and policy. Portia should support disaggregated aggregate analysis, expose subjective decision points, and calculate rates with valid denominators. It should not display protected demographic attributes as cues on routine individual decision screens.

8. **Make student and family perspectives first-class records.** Students and families should be able to contribute statements, identify inaccuracies, participate in support planning, and receive understandable information. Their statements should be linked to—not overwritten by—the institutional account.

9. **Apply privacy by design.** Behavior records are generally education records under FERPA when they are directly related to a student and maintained by a school or its agent. Portia needs least-privilege access, field-level sensitivity, amendment workflows, redaction for multi-student records, configurable retention, secure deletion, auditable access, and strong authentication.

10. **Reject high-risk product patterns.** Portia should not generate a single “behavior score,” predict which students will offend, recommend punishment automatically, rank students publicly, infer diagnoses or trauma, perform emotion or sentiment analysis, or escalate consequences solely because a threshold count was reached.

The recommended core record structure is:

> **Event → Accounts/Observations → Review and Classification → Determination → Immediate Responses → Supports/Interventions → Follow-Up and Outcomes**

This structure permits rapid classroom documentation while preserving due process, professional judgment, student voice, and longitudinal evaluation of what actually helps.

---

## 1. Purpose and Research Method

### 1.1 Purpose

This document translates evidence, federal guidance, privacy rules, and implementation research into design guidance for Portia. It is intended to inform:

- terminology;
- domain modeling;
- data fields;
- workflows;
- roles and permissions;
- reporting;
- data-quality controls;
- equity safeguards;
- privacy and retention;
- product requirements; and
- future architecture decision records.

It does **not** prescribe a single disciplinary philosophy for every district. Portia should allow districts to implement lawful local policy while preventing product design from encouraging unsupported, biased, or unnecessarily punitive practices.

### 1.2 Research hierarchy

The synthesis prioritizes:

1. U.S. Department of Education regulations and guidance;
2. federally funded technical-assistance centers, especially the Center on PBIS;
3. federal oversight and civil-rights research;
4. peer-reviewed and independently reviewed studies;
5. established research and professional organizations;
6. implementation studies of specific approaches.

Commercial behavior-management products were not treated as authorities on best practice. Their common patterns—incident counts, points, rewards, parent notifications, and dashboards—are useful only as feature comparisons and do not establish educational or ethical validity.

### 1.3 Strength of conclusions

The evidence is strongest for the following broad practices:

- preventive, positive, tiered systems;
- clear expectations and explicit teaching;
- objective and measurable behavior definitions;
- function-based individualized supports;
- team-based data review;
- family and student partnership;
- monitoring both implementation fidelity and outcomes;
- disaggregated discipline analysis;
- limiting exclusionary responses; and
- privacy and access safeguards.

Evidence varies by program, implementation quality, school level, local context, and outcome. For example, a randomized evaluation of restorative practices in Pittsburgh found improved teacher-rated climate and reduced suspensions, but no academic improvement and worse academic outcomes in grades 6–8 during the study period. Portia should therefore help organizations evaluate implementation and outcomes rather than encode any framework as automatically effective.

---

## 2. Foundational Design Principles for Portia

### Principle 1: Support is the product objective

Portia's primary question should be:

> **What information will help educators prevent recurrence, teach a usable replacement skill, repair harm, and evaluate whether support worked?**

The product should not optimize for the number of reports entered, sanctions imposed, parent contacts made, or students placed in increasingly intensive tiers.

### Principle 2: Preserve epistemic status

Every substantive assertion should have an explicit status:

| Status | Meaning | Example |
|---|---|---|
| Direct observation | What the author personally saw or heard | “The student pushed the chair approximately two feet from the desk.” |
| Reported account | What another named or role-identified person reported | “A peer reported that…” |
| Quoted statement | Exact or substantially exact words attributed to a speaker | “The student said, ‘I am leaving.’” |
| Reporter classification | A category selected for routing or local reporting | “Disruption — pending review” |
| Hypothesis | A tentative explanation requiring evidence | “The team is evaluating whether task avoidance may be a maintaining function.” |
| Formal determination | A finding made by an authorized reviewer under policy | “Administrator determined that policy section X applied.” |
| Outcome measurement | A later observation or metric used to evaluate change | “Frequency decreased from five to two occurrences per class period.” |

The interface should never visually flatten these into equivalent “facts.”

### Principle 3: Use the least data necessary

Collect only information needed for:

- immediate safety and response;
- educational support;
- required documentation;
- review and due process;
- evaluation of interventions;
- lawful aggregate reporting; or
- operational integrity and security.

“Potentially useful someday” is not a sufficient reason to collect highly sensitive student information.

### Principle 4: Design for prevention and instruction

A behavior-management record should be able to connect to:

- environmental or instructional prevention;
- explicit teaching or reteaching;
- replacement skills;
- accommodations and access supports;
- relationship-building;
- restorative or reparative steps;
- reinforcement or specific positive feedback;
- de-escalation;
- follow-up;
- fidelity checks; and
- outcome measurement.

### Principle 5: Preserve agency and multiple perspectives

A single event may have several incomplete or conflicting accounts. Portia should permit them to coexist. A system that forces one canonical narrative too early will convert uncertainty into false certainty.

### Principle 6: Distinguish support intensity from student identity

“Tier 2” or “Tier 3” should describe the current intensity of a support process. Portia should not label a student as a “Tier 3 student,” “frequent offender,” “high risk,” or similar identity.

### Principle 7: Make consequential actions reviewable

The more consequential the action, the more Portia should require:

- an authorized decision-maker;
- stated policy basis;
- consideration of required factors;
- documentation of alternatives or supports;
- notification and due-process steps;
- disability-related safeguards where applicable;
- a reasoned explanation; and
- a complete audit trail.

### Principle 8: Measure system behavior as well as student behavior

Data should help answer not only “What did students do?” but also:

- Where are expectations unclear?
- Which settings generate the most referrals after accounting for exposure?
- Which categories rely heavily on subjective judgment?
- Which adults, settings, or decision points produce disproportionate outcomes?
- Are supports available equitably?
- Are interventions implemented as designed?
- How much instructional time is lost through removals?
- Are different groups receiving different responses for comparable categories?
- Are records complete and timely?

### Principle 9: Favor reversible, configurable decisions

Terminology, categories, severity levels, required fields, retention schedules, workflows, and permissions vary by jurisdiction. Portia should ship with defensible defaults but allow controlled local configuration with versioning and governance.

### Principle 10: Never automate moral or disciplinary judgment

Software can:

- validate completeness;
- calculate descriptive rates;
- identify missing follow-ups;
- surface a local policy checklist;
- display comparable historical interventions;
- warn that a category is subjective; or
- flag that a required review may be due.

Software should not:

- decide that a student is deceptive, dangerous, malicious, remorseful, or noncompliant;
- infer intent from text;
- determine behavioral function;
- diagnose a condition;
- decide whether an allegation is substantiated;
- recommend exclusionary discipline; or
- calculate a predictive risk score from historical behavior records.

---

## 3. Behavior Documentation

### 3.1 What constitutes a useful behavior record

A useful record is sufficiently precise that another trained person can understand:

- **what occurred;**
- **where and when it occurred;**
- **what activity or conditions were present;**
- **who directly observed it;**
- **what immediate response occurred;**
- **what concrete effect or safety concern followed;**
- **what is known versus inferred;**
- **whether additional accounts or review are pending;** and
- **what follow-up is required.**

It need not be long. A brief objective description is better than a long interpretive narrative.

### Poor record

> Jordan was very disrespectful and became aggressive for no reason.

### Better record

> During independent work at 10:18 a.m., after the teacher directed the class to put phones in backpacks, Jordan said, “No, this is stupid,” remained seated with the phone in hand, and spoke over the teacher three times during approximately 90 seconds. When the teacher approached the desk, Jordan pushed the chair backward and left the room. No physical contact or threat was observed.

The second example does not determine whether a policy violation occurred or why the student acted. It gives a reviewer and support team usable information.

### 3.2 Operational definitions

For recurring data collection or an intervention plan, a target behavior should be defined so that different observers could identify the same beginning and end with reasonable consistency.

An operational definition should include:

- observable actions;
- a clear start condition;
- a clear stop condition;
- examples;
- nonexamples;
- relevant setting or opportunity;
- the measurement method; and
- any intensity anchors.

Example:

> **Leaving assigned area:** The student's entire body crosses the classroom doorway without permission during scheduled class time. The event begins when both feet cross the threshold and ends when the student returns or reaches an approved destination. Walking to the pencil sharpener or a teacher-directed partner station is not included.

Portia should support versioned definitions because local teams may refine them after testing inter-observer clarity.

### 3.3 Recommended record layers

Portia should use linked record types instead of a single mutable incident form.

### A. Event

A neutral container for a real-world occurrence.

Recommended fields:

- event identifier;
- event type: concern, positive observation, safety event, conflict, policy referral, support observation, other;
- start date and time;
- end date and time or estimated duration;
- time precision: exact, approximate, unknown;
- location and sublocation;
- activity or schedule context;
- organization, school, course, program, or transportation context;
- participants and participant roles;
- whether immediate safety response was required;
- whether the event is ongoing;
- related event identifiers;
- source system, if imported;
- created and last-updated timestamps.

An event should not automatically equal “misconduct.” A conflict can include several participants without a preliminary designation of offender or victim.

### B. Account or observation

An author-attributed description.

Recommended fields:

- author;
- author's relationship to the event: direct observer, recipient of report, participant, reviewer;
- observation start/end;
- objective narrative;
- exact quotations, separately marked;
- observable behavior codes, if any;
- antecedent or setting-event observations;
- immediate consequences or changes in environment;
- people present;
- source reliability status: direct, reported, document-derived;
- attachments or evidence references;
- language of the account;
- interpreter or translation information;
- submission timestamp;
- correction/amendment history.

Each author should have a separate account. Editing one person's account into another's voice undermines provenance.

### C. Referral

A request for review or service, not a finding.

Recommended fields:

- referring person;
- referral destination;
- referral reason;
- urgency;
- requested action or support;
- classroom-managed steps already attempted;
- status;
- assigned reviewer;
- due date;
- date acknowledged;
- routing history.

### D. Classification

A controlled category used for routing and reporting.

Recommended fields:

- category;
- local definition version;
- selected by;
- status: reporter-selected, reviewer-confirmed, changed, unable to determine;
- rationale;
- prior and replacement values;
- timestamp.

A reporter's category and a reviewer-confirmed category should not overwrite each other.

### E. Determination

A formal institutional finding.

Recommended fields:

- decision-maker;
- allegation or policy question reviewed;
- applicable policy and version;
- finding: substantiated, not substantiated, insufficient information, not applicable, other local values;
- factual basis;
- date;
- due-process and notice steps;
- required disability-related review;
- appeal or reconsideration status;
- superseding determination, if any.

Portia must not treat “not substantiated” as proof that nothing occurred; it describes the institutional finding under the applicable standard.

### F. Immediate response

What staff did during or immediately after the event.

Possible values include:

- proximity or nonverbal cue;
- redirection;
- clarification/reteaching;
- change in task or environment;
- break or regulation support;
- check-in;
- peer separation;
- nurse or counselor contact;
- family contact;
- administrative assistance;
- emergency response;
- removal from setting;
- restraint or seclusion, through a separate restricted workflow;
- no response;
- other.

The response should include duration, actor, result, and any instructional time lost.

### G. Support or intervention

A planned action intended to improve access, participation, safety, skill, or relationships.

Recommended fields:

- support name and type;
- tier/intensity;
- target skill or need;
- linked operational definition;
- prevention strategy;
- teaching strategy;
- reinforcement/recognition strategy;
- response strategy;
- person responsible;
- setting and schedule;
- start and review dates;
- expected dosage;
- fidelity measure;
- outcome measure;
- student and family participation;
- consent or procedural status where required;
- status and reason ended.

### H. Follow-up and outcome

Recommended fields:

- follow-up type;
- person responsible;
- due and completed dates;
- student check-in;
- affected-person check-in;
- family communication;
- restorative or reparative completion;
- intervention fidelity;
- outcome measure;
- adverse or unintended effects;
- continuation, modification, fading, or closure decision;
- rationale.

### I. Communication

A communication log should record:

- date/time;
- participants;
- direction;
- channel;
- language and interpreter;
- purpose;
- concise factual summary;
- documents shared;
- response or questions;
- next step;
- confidentiality limitations.

It should not encourage staff to paste entire email threads or unrelated family details into a behavior record.

### J. Amendment, disagreement, or additional statement

Recommended fields:

- requester;
- record challenged;
- claimed issue: inaccurate, misleading, privacy concern, incomplete, contextual disagreement;
- requested correction;
- decision;
- reviewer;
- hearing or local review status;
- linked statement of disagreement;
- date;
- records disclosed with the contested section.

### 3.4 Required, recommended, and optional fields

Portia should support a two-stage workflow.

### Stage 1: Rapid capture

Required only when applicable:

- student or event participant;
- date/time or approximation;
- location/context;
- objective description;
- author;
- immediate safety status;
- immediate response;
- routing destination if review is requested.

The system should autosave a draft and permit later completion. Urgent safety procedures must never depend on finishing the form.

### Stage 2: Completion and review

Required according to record type and local policy:

- duration or instructional time lost;
- category and definition;
- additional accounts;
- response details;
- notification;
- determination;
- follow-up owner and due date;
- support linkage;
- amendment status.

### Optional fields

Optional fields should be shown only when useful:

- antecedent;
- frequency;
- latency;
- intensity;
- environmental conditions;
- exact quote;
- attachment;
- perceived or hypothesized function;
- student reflection;
- family input.

“Optional” must not mean “safe to collect without purpose.” Sensitive optional fields should be disabled unless a district explicitly enables and governs them.

### 3.5 Antecedent–behavior–consequence data

ABC information is useful when teams are evaluating patterns:

- **Antecedent:** observable event or condition immediately before the behavior;
- **Behavior:** operationally defined action;
- **Consequence:** what occurred immediately afterward, including changes in demands, attention, access, stimulation, or environment.

The word *consequence* in an ABC analysis is descriptive, not synonymous with punishment.

Portia should avoid presenting every incident as a complete ABC chain. One account rarely proves what maintained behavior. Multiple observations, including occasions when the behavior does **not** occur, are important in an FBA.

### 3.6 Measurement methods

Portia should support several measurement types without pretending they are interchangeable.

| Measure | Use | Main caution |
|---|---|---|
| Count | Number of discrete occurrences | Misleading when observation periods differ |
| Rate | Count per unit of time or opportunity | Denominator and exposure must be explicit |
| Duration | Time from defined start to stop | Requires reliable start/stop rules |
| Latency | Time from a defined cue or opportunity to response | The cue and expected response must be precise |
| Inter-response time | Time between occurrences | Useful only for clearly discrete behaviors |
| Percentage of intervals | Proportion of observed intervals meeting a definition | Sampling method affects estimate |
| Opportunity-based percentage | Responses divided by relevant opportunities | Opportunities must be counted consistently |
| Intensity | Locally defined impact or magnitude rubric | Highly subjective unless anchored with examples |
| Instructional time lost | Minutes unavailable for ordinary instruction | Include removals caused by adult/system response |
| Unique students | Number of students represented | Does not show repeated events or exposure |
| Fidelity | Degree an intervention was implemented as planned | Must not be confused with student outcome |

The product should store numerator, denominator, unit, observation window, and collection method—not merely a calculated percentage.

### 3.7 Positive behavior and growth

Portia should support documentation of:

- use of a replacement skill;
- successful self-advocacy;
- conflict resolution;
- help-seeking;
- re-engagement after difficulty;
- repair of harm;
- progress toward an individualized goal;
- sustained participation under previously difficult conditions;
- successful environmental or instructional supports; and
- strengths identified by students, families, or staff.

Positive records should be **specific and contextual**, not generic points. “Used the agreed break request before leaving the room during writing workshop” is more useful than “+5 respect points.”

Safeguards:

- no public leaderboards;
- no competition based on compliance;
- no loss of earned recognition as punishment;
- no assumption that quietness, eye contact, stillness, or unquestioning compliance is universally appropriate;
- no comparative ranking of students;
- no permanent “positive/negative balance score.”

---

## 4. Intervention and Response Frameworks

### 4.1 PBIS and MTSS

PBIS is an evidence-based, tiered framework for supporting behavioral, academic, social, emotional, and mental-health outcomes. Its core elements are systems, data, practices, outcomes, and equity. It is not a packaged reward program, a discipline chart, or a one-time training.

For Portia, the important design implications are:

- support universal, targeted, and individualized practices;
- track the practices available at each tier;
- measure implementation fidelity as well as student outcomes;
- support team-based review;
- connect decisions to a defined question;
- preserve equity as a core dimension rather than a later report;
- permit movement into, between, and out of supports;
- record access to supports, not merely referrals for problems.

### Tier 1: Universal prevention

Portia may support:

- schoolwide expectations and operational definitions;
- teaching and reteaching records;
- acknowledgment practices;
- climate and belonging measures;
- classroom systems;
- universal screening only when locally authorized and psychometrically appropriate;
- aggregate discipline patterns;
- fidelity assessments;
- family and student feedback.

It should not create daily individual compliance profiles for every student merely because Tier 1 applies to everyone.

### Tier 2: Targeted support

Portia may support:

- referral criteria;
- multiple entry routes, including student/family request;
- intervention enrollment;
- goals;
- regular progress monitoring;
- dosage and fidelity;
- review schedules;
- family communication;
- response to intervention;
- exit, continuation, or intensification decisions.

Entry should not be triggered by referral count alone. Teams should consider data validity, context, screening information, academics, attendance, student/family input, and access barriers.

### Tier 3: Individualized support

Portia may support:

- team membership;
- individualized assessment;
- FBA processes;
- behavior support or intervention plans;
- wraparound planning;
- crisis prevention;
- detailed progress monitoring;
- student-centered goals;
- family participation;
- high-granularity permissions.

Tier 3 data are likely to be more sensitive and should have narrower access than routine classroom observations.

### 4.2 Functional behavioral assessment and behavior plans

The U.S. Department of Education's 2024 guidance describes an FBA as a process for identifying the reasons or factors contributing to a specific behavior so educators can develop positive, function-based supports. Common characteristics include:

- a clear, specific, measurable, observable, objective description;
- culturally and linguistically responsive language;
- direct and indirect data;
- data on occurrence and non-occurrence;
- analysis of antecedents, behavior, and consequences;
- a hypothesis about function;
- identification and teaching of needed skills; and
- collaborative planning with appropriately trained professionals, parents, and the student when appropriate.

### FBA product implications

Portia should provide a dedicated FBA workspace, not label a routine incident form “FBA.”

An FBA workspace should support:

- defined assessment question;
- consent/procedural status;
- team and roles;
- target behavior definition;
- examples and nonexamples;
- data sources;
- observation schedules;
- occurrence and non-occurrence data;
- interview summaries;
- environmental and academic factors;
- competing hypotheses;
- evidence for and against each hypothesis;
- team-approved hypothesis;
- skill and access needs;
- plan development;
- review timeline.

### “Perceived motivation” field

PBIS office-referral systems often include perceived motivation because it can assist team problem solving. However, the 2024 federal guidance makes clear that function is developed through individualized data collection and analysis.

Recommendation:

- do not require perceived motivation in rapid capture;
- label it **reporter's hypothesis**, not “motive” or “cause”;
- permit “unknown/not assessed”;
- display a notice that the field is not an FBA finding;
- retain author and timestamp;
- do not use it to drive automated decisions;
- exclude it from a formal function field until reviewed by an authorized team;
- allow competing hypotheses;
- show the supporting observations.

### 4.3 Components of a strong support plan

A support plan should include:

1. **Operational definition:** What exactly is being measured?
2. **Baseline:** What occurs now, in what conditions, and how often?
3. **Prevention:** What environmental, instructional, relational, communication, sensory, or scheduling changes reduce the likelihood of difficulty?
4. **Replacement skill:** What can the student do instead that serves the same need more safely or effectively?
5. **Teaching:** Who will teach, model, practice, prompt, and generalize the skill?
6. **Recognition:** How will adults provide specific feedback and meaningful reinforcement?
7. **Response:** How will staff respond consistently, safely, and instructionally if the behavior occurs?
8. **Safety:** What emergency steps are required, and what practices are prohibited?
9. **Implementation:** Who is responsible, where, how often, and with what training?
10. **Fidelity:** How will the team know the plan was implemented as intended?
11. **Outcome:** What measures and decision rules will indicate improvement, lack of effect, or harm?
12. **Voice and consent:** How did the student and family participate?
13. **Review:** When will the team reconvene, and who owns the next action?

Portia should not allow a plan to consist only of consequences.

### 4.4 Restorative practices

Restorative practices can include proactive relationship-building, circles, affective questions, conferencing, repair agreements, reentry, and other processes focused on community and harm.

A randomized controlled trial of a whole-school restorative program in Pittsburgh found:

- improved teacher-rated school climate;
- a greater reduction in suspensions than comparison schools;
- reduced Black–white and low-/higher-income suspension disparities;
- no reduction in arrest rates;
- no academic improvement; and
- worse academic outcomes for grades 6–8 during the study.

This supports a measured product stance: restorative practices are promising and can be documented, but they are not a universal or automatic remedy.

Portia should support:

- proactive and responsive restorative processes;
- facilitator;
- voluntary participation status;
- preparation;
- participants;
- harm and needs identified by participants;
- agreed actions;
- deadlines;
- completion;
- check-ins;
- safety or power-imbalance concerns;
- reentry.

Portia should discourage or prevent:

- forced apologies;
- treating a restorative conference as a prerequisite for access to school;
- requiring an affected person to meet with the person who caused harm;
- using “restorative” as a euphemism for an imposed sanction;
- recording sensitive disclosures in broadly visible fields;
- treating completion as proof of remorse or rehabilitation.

### 4.5 Social and emotional learning

CASEL describes SEL as development of self-awareness, self-management, social awareness, relationship skills, and responsible decision-making across classrooms, schools, families, and communities.

Portia may support SEL-aligned skill goals and instruction. It should not turn broad developmental competencies into personality ratings or disciplinary scores.

Appropriate:

- “Use a taught conflict-resolution script in two of three observed opportunities.”
- “Identify and request one of the available regulation supports.”
- “Participate in a planned reentry conversation.”

Inappropriate:

- “Self-management: 42/100.”
- “Low empathy.”
- “Poor character.”
- “Emotionally immature.”

Assessment of broad SEL competencies requires validated methods, developmental interpretation, cultural responsiveness, and local governance. Routine behavior reports are not valid SEL assessments.

### 4.6 Trauma-informed practice

The NCTSN describes trauma-informed schools through the “4 Rs”:

- realize the widespread impact of trauma;
- recognize signs and symptoms;
- respond by integrating knowledge throughout the system; and
- resist retraumatization.

Portia's design should embody safety, predictability, transparency, choice, collaboration, and restraint in data collection.

It should **not**:

- infer that a behavior was caused by trauma;
- invite untrained staff to diagnose trauma;
- require disclosure of traumatic experiences;
- place detailed trauma narratives in an ordinary behavior log;
- expose clinical or counseling notes to routine behavior-system users;
- label a student “trauma affected” based on an incident pattern.

It may:

- store a narrowly phrased, authorized support instruction such as “Offer choice of two seating locations”;
- link to a separately governed support plan;
- indicate that a restricted plan exists;
- support de-escalation preferences;
- record whether an action may have created avoidable triggers;
- monitor whether exclusion or coercive practices are being used.

### 4.7 Exclusionary discipline

Research and federal guidance associate exclusionary discipline with loss of instruction and adverse educational and justice-system outcomes; disparities affect Black students, boys, and students with disabilities.

Portia should not prohibit lawful local disciplinary actions. It should ensure they are not the easiest or least scrutinized workflow.

For removal, suspension, expulsion, informal removal, or exclusion from activities, Portia should capture:

- action type;
- start/end;
- instructional minutes or days lost;
- decision-maker;
- policy basis;
- notice;
- education/services provided during removal;
- required disability-related review;
- prior prevention/supports considered;
- reentry plan;
- appeal/review;
- aggregate disproportionality metrics.

“Sent home early,” “parent pickup requested,” shortened day, or repeated removal from class should not disappear into free text if they function as exclusion.

### 4.8 Restraint, seclusion, crisis, and highly sensitive events

Restraint and seclusion should not be modeled as ordinary consequences. They require a separate, restricted, jurisdiction-specific workflow.

At minimum, that workflow should support:

- emergency criterion;
- immediate danger described objectively;
- less restrictive steps attempted, when applicable;
- exact start and end time;
- type of intervention;
- trained staff involved;
- monitoring;
- injury or medical assessment;
- student and staff debrief;
- parent/guardian notification;
- administrative review;
- required state reporting;
- plan review;
- recurrence prevention;
- video or evidence handling under separate rules.

Portia should never present restraint or seclusion as a planned reward/consequence option or suggest it based on behavior history.

Other events that should be routed to specialized, access-restricted workflows rather than ordinary behavior records include:

- suspected child abuse or neglect;
- self-harm or suicide concern;
- threat assessment;
- sexual harassment or sexual violence;
- protected health or counseling records;
- law-enforcement investigations;
- special-education evaluations;
- bullying investigations governed by specific state law;
- discrimination complaints;
- substance-related medical emergencies.

Portia may preserve a minimal linkage such as “Referred to restricted safety workflow at 10:24 a.m.” without copying sensitive content.

---

## 5. Data Quality and Interpretation

### 5.1 Behavior data are generated by systems

An office discipline referral is not a direct census of student behavior. It represents several decision points:

1. an event occurred;
2. an adult observed or learned of it;
3. the adult interpreted it;
4. the adult decided whether to respond;
5. the adult decided whether to document;
6. the adult selected a category and severity;
7. a reviewer accepted, changed, or dismissed the classification;
8. the institution selected a response.

Differences in expectations, observation opportunities, relationships, workload, policy, category definitions, and bias affect the resulting data.

Therefore Portia should describe its dashboards as **records of documented events and institutional responses**, not as direct measures of a student's character, intent, or total behavior.

### 5.2 Data-quality controls

### Controlled vocabulary with local definitions

Each category should have:

- label;
- plain-language definition;
- examples;
- nonexamples;
- classroom-managed versus office-managed guidance;
- severity anchors;
- required fields;
- active dates;
- owner;
- version.

Historical records must retain the version used at the time.

### Narrative support

Portia may use transparent rule-based prompts to flag:

- no observable action;
- mental-state claims presented as fact;
- unsupported absolutes such as “always” or “never”;
- ambiguous pronouns;
- missing time or setting;
- vague magnitude;
- diagnostic or stigmatizing labels;
- duplicated narrative across several students;
- prohibited sensitive information.

The system should explain the prompt and let the author revise or state why the wording is necessary. It should not silently rewrite an account or use opaque AI to determine whether the author is “objective.”

### Duplicate detection

Portia may suggest that records appear related based on:

- same event time and location;
- overlapping participants;
- shared event identifier;
- similar author accounts.

It should not auto-merge. A reviewer should link or merge records with a reversible audit trail.

### Completeness and missingness

Dashboards must expose:

- missing fields;
- unknown values;
- records awaiting review;
- unresolved duplicates;
- late entries;
- incomplete follow-ups;
- changes in category definitions;
- imports with lower data quality.

Unknown is not zero.

### Timeliness

Store separately:

- event time;
- observation time;
- entry time;
- review time;
- determination time;
- follow-up time.

This permits evaluation of delays without falsifying chronology.

### Provenance

Every value should preserve:

- source;
- author or system;
- date;
- version;
- confidence/status where applicable;
- edits and reasons.

### 5.3 Appropriate metrics

Recommended descriptive measures include:

- events by type and time period;
- unique students represented;
- students with one, two, three, or more documented events;
- event rate per 100 students or student-days;
- rate per instructional hour or opportunity when available;
- classroom-managed and office-managed records;
- location, time, activity, and referring role;
- categories and category changes after review;
- subjective versus more objectively defined categories;
- immediate responses;
- removal events and instructional time lost;
- time to review;
- time to first support;
- overdue follow-ups;
- support access;
- intervention dosage and fidelity;
- student response to intervention;
- reentry completion;
- family/student participation;
- positive skill use;
- climate, belonging, attendance, and academic measures when lawfully linked for a defined purpose;
- missing data and data-quality indicators.

### Rates and denominators

Every rate should show:

- numerator;
- denominator;
- date range;
- population included;
- exclusions;
- whether a student can appear more than once;
- unit;
- comparison period;
- small-cell handling.

Raw counts should not be the default when enrollment, exposure, or opportunity differs.

### 5.4 Metrics requiring caution

### Recurrence

A later report may mean:

- behavior recurred;
- observation increased;
- definitions changed;
- reporting became easier;
- the student entered a more closely monitored setting; or
- staff implemented a new documentation expectation.

Portia should not label recurrence as intervention failure without fidelity and context.

### Severity

Severity is often subjective. If enabled, it should use locally defined anchors tied to observable impact, safety, or instructional disruption—not emotional reaction or staff inconvenience.

### Instructional time lost

This is a valuable measure because it captures the effect of institutional response. It should include minutes lost through:

- removal from class;
- office waiting;
- informal send-home;
- suspension;
- exclusion from activities;
- repeated crisis response.

It should not imply that all lost time was avoidable.

### Perceived motivation or function

This is a hypothesis, not a fact. Aggregate reports should not treat it as validated unless it comes from a completed assessment process.

### Positive-to-corrective ratios

Such ratios can inform adult practice in specific observation protocols. They should not become a quota, teacher ranking, or student worth measure.

### 5.5 Misleading or irresponsible metrics

Portia should not produce:

- a single student behavior score;
- “risk of suspension” or “risk of violence” predictions;
- rankings of “best” or “worst” students, teachers, classrooms, or families;
- comparisons based solely on raw counts;
- recurrence forecasts from historical referrals;
- causal claims from correlations;
- “effectiveness” without fidelity and baseline;
- average severity across incompatible categories;
- demographic comparisons without denominators and small-cell protections;
- compliance percentages for behaviors lacking defined opportunities;
- dashboards that omit category-definition changes;
- “parent engagement scores” based on response speed;
- sentiment, remorse, honesty, or attitude scores derived from text.

### 5.6 Visualization principles

Reports should:

- label data as documented records;
- show uncertainty and missingness;
- permit drill-down from aggregate to authorized source records;
- show numerator and denominator;
- use consistent scales;
- avoid alarming colors as the only signal;
- avoid default red student profiles;
- annotate policy or definition changes;
- permit comparison of student outcomes and system responses;
- show both level and trend;
- avoid charts with tiny cells;
- provide accessible tables and text summaries.

A dashboard should lead to a question and a team process, not a verdict.

---

## 6. Equity, Bias, and Disproportionality

### 6.1 Why equity must be a core requirement

Federal oversight and research consistently document disproportionate discipline for Black students, boys, and students with disabilities. The Department of Education's 2024 FBA guidance also notes that perceptions and classifications of student behavior can reflect implicit bias rather than differences in actual behavior.

Portia cannot eliminate institutional bias. It can either conceal it, amplify it, or help users examine it.

### 6.2 Five-part equity approach

The Center on PBIS recommends:

1. disaggregating and using discipline data;
2. implementing culturally responsive multi-tiered systems;
3. providing engaging instruction;
4. defining effective policies and procedures; and
5. identifying vulnerable decision points and neutralizing implicit bias.

Product implications:

- equity analytics are not an optional add-on;
- data alone are insufficient;
- reports should connect disparities to decision points and practices;
- policy definitions should be accessible at entry and review;
- local teams need action-planning and follow-up;
- the product must not respond to disparities by merely referring more students to intensive tiers.

### 6.3 Subjective categories

Categories such as “defiance,” “disrespect,” “disruption,” “inappropriate behavior,” “insubordination,” “attitude,” and “noncompliance” can require substantial interpretation.

Portia should:

- allow local organizations to replace or tightly define them;
- display examples and nonexamples;
- require an observable description;
- show them in equity reports as higher-subjectivity categories;
- analyze where and by whom they are used;
- compare reporter-selected and reviewer-confirmed categories;
- avoid using them as direct automated triggers.

A category can be administratively necessary and still require bias safeguards.

### 6.4 Recommended disproportionality measures

Authorized aggregate reports may include:

### Risk index

> Students in group receiving an outcome ÷ students enrolled in group

Example: Black students suspended at least once divided by Black students enrolled.

### Risk ratio

> Risk index for focal group ÷ risk index for comparison group

A ratio above 1 indicates higher recorded risk in the focal group. It does not by itself explain why.

### Rate difference

> Risk index for focal group − risk index for comparison group

This communicates the absolute gap, which can be more interpretable than a ratio when rates are low.

### Composition index

> Percentage of students receiving an outcome who belong to a group

This must be displayed with the group's enrollment share. Composition alone is easily misread.

### Event rate

> Number of documented events for group ÷ exposure measure

This captures repeated events but can be dominated by a small number of students. Always pair it with unique-student risk.

### Response disparity

Compare actions after similar categories or reviewer findings, while clearly stating that observational comparisons do not prove equal underlying circumstances or discrimination.

### Decision-point analysis

Disaggregate by:

- location;
- time;
- activity;
- category subjectivity;
- referring role;
- reviewer;
- classroom-managed versus office-managed;
- response type;
- lost instructional time;
- support access;
- disability status;
- race/ethnicity;
- gender, as locally lawful and defined;
- multilingual-learner status or other locally governed attributes.

### 6.5 Statistical and privacy cautions

Portia should:

- suppress or combine small cells according to district policy;
- avoid showing identifiable intersections;
- state when ratios are unstable;
- include numerator and denominator;
- allow confidence intervals or uncertainty indicators where appropriate;
- warn against causal conclusions;
- distinguish zero from missing;
- prevent exports that defeat suppression through repeated queries;
- log access to detailed equity reports;
- avoid demographic data on routine incident-entry screens unless needed for a specific lawful support.

No universal small-cell threshold should be hard-coded as legally sufficient. Districts and states use different rules, and re-identification depends on context.

### 6.6 Bias-interruption features

Potential safeguards include:

- hide prior incident counts until the reporter completes the current objective account;
- show current support instructions without foregrounding a negative history;
- require observable descriptions for subjective categories;
- prompt users to distinguish direct observation from hearsay;
- show local decision criteria at the point of referral and determination;
- flag inconsistent consequence fields;
- require a reason when overriding a standard workflow;
- show reviewers comparable categories and policy definitions—not an algorithmic recommendation;
- provide periodic private reflection reports to authorized teams;
- permit student/family correction or contextual statements;
- monitor category changes and dismissals by reporter and group;
- monitor time from concern to support, not just time to sanction.

### 6.7 Terminology to avoid

Avoid as uncontrolled labels:

- bad;
- good kid/bad kid;
- habitual offender;
- troublemaker;
- manipulative;
- attention-seeking;
- lazy;
- unmotivated;
- crazy;
- dangerous, unless describing an authorized threat/safety determination;
- violent, when a specific action can be described;
- aggressive, without observable definition;
- defiant;
- disrespectful;
- noncompliant;
- out of control;
- meltdown, unless it is locally defined and accepted by the student/family;
- low functioning/high functioning;
- normal/abnormal;
- emotionally disturbed as colloquial language;
- trauma behavior;
- autistic behavior;
- gang-related, without an authorized factual basis;
- parent refused, when “did not respond,” “declined,” or “was unavailable” is accurate.

Controlled policy terms may still be used where required, but Portia should retain the observable account and the applicable definition.

### 6.8 Asset-based alternatives

Prefer:

- “used/has not yet used the taught request strategy”;
- “remained outside the assigned area for four minutes”;
- “spoke while another person was speaking on five observed occasions”;
- “requested assistance”;
- “re-entered class and completed the final ten minutes”;
- “family declined this proposed meeting time”;
- “student disputes the account and provided a statement”;
- “support was not implemented during two of five scheduled periods.”

---

## 7. Privacy, Access, Retention, and Security

### 7.1 FERPA applicability

Under FERPA, education records include records directly related to a student and maintained by an educational agency/institution or a party acting for it. Records may be handwritten, printed, digital, audio, video, or otherwise recorded. Personally identifiable information includes direct identifiers and information that can identify a student when combined with other reasonably available information.

Portia should assume ordinary student behavior records are FERPA education records.

### 7.2 Inspection and amendment

FERPA gives parents—and eligible students after rights transfer—rights to inspect and review records, generally within no more than 45 days after a request. When a multi-student record contains information about more than one student, a parent or eligible student may inspect only the information specific to that student.

FERPA also permits a request to amend information claimed to be inaccurate, misleading, or privacy-violating. If the institution does not amend after the required process, the parent or eligible student may place a statement with the contested record, and the institution must maintain and disclose that statement with the contested portion.

### FERPA amendment product implications

Portia should support:

- searchable export by student;
- explanation-friendly field labels;
- redaction of other students;
- correction requests;
- authorized review;
- replacement of inaccurate active values;
- preserved change history;
- linked statements of disagreement;
- legal holds while access or amendment requests are pending;
- disclosure-ready views.

### Immutability recommendation

The original submission should be preserved in an audit history, but **immutability must not mean that inaccurate information remains the active or only visible truth**.

Recommended model:

- append-only audit events;
- versioned source accounts;
- authorized correction with reason;
- current canonical view;
- visible “corrected/superseded” status;
- linked contested statement;
- disclosure rules that include required statements;
- no silent alteration.

### 7.3 Consent, school officials, and legitimate educational interest

FERPA generally requires signed and dated consent before disclosure unless an exception applies. School officials, including qualifying contractors, may receive access without consent when they have legitimate educational interests and the institution uses reasonable methods to limit access accordingly. Contractors must perform an institutional function, remain under the institution's direct control regarding records, and comply with use and redisclosure limits.

Portia should implement:

- role-based access control;
- attribute-based scope: school, course, case assignment, relationship, date, sensitivity;
- field-level access;
- least privilege;
- regular access review;
- automatic deprovisioning;
- time-limited delegated access;
- “break glass” access with stated reason and immediate audit;
- vendor support access disabled by default;
- tenant control of user authorization;
- data-processing terms consistent with district obligations.

### 7.4 Proposed role model

| Role | Typical capabilities | Default restrictions |
|---|---|---|
| Reporter | Create account, view own submission and assigned follow-up | Cannot see unrelated history, demographics, clinical notes, or determinations outside scope |
| Classroom educator | Manage classroom observations and supports for current students | No broad schoolwide discipline search; no restricted safety records |
| Reviewer/administrator | Review referrals, classify, determine, assign responses | Access limited to assigned school/cases; cannot alter source accounts silently |
| Support-team member | View and manage assigned interventions and progress | No unrelated sanctions or confidential investigations |
| Case manager/special educator | Access authorized plans and implementation data | IEP/evaluation records remain separately governed |
| Counselor/psychologist | Access assigned support information | Clinical/treatment notes should remain outside ordinary Portia storage |
| Restorative facilitator | Access assigned process and necessary accounts | No unrestricted historical profile |
| Family liaison/interpreter | Access designated communication tasks | No full record unless separately authorized |
| Data analyst/equity team | De-identified or aggregate reports | No routine identifiable drill-down without additional authorization |
| Privacy/records officer | Manage access requests, amendments, retention, disclosures | Does not make discipline determinations by virtue of privacy role |
| Security administrator | Authentication, logs, incident response | No default access to narrative content |
| District configuration owner | Categories, policies, workflows, schedules | Configuration changes versioned and audited |
| Student/parent/guardian | Access authorized records, statements, correction requests | Other students' information redacted |
| Auditor | Read-only, time-bounded access for defined purpose | No export beyond approved scope |
| Vendor support | Temporary technical access only when approved | No standing production access; all access logged |

Permissions should be composed, not inferred solely from job title.

### 7.5 Audit requirements

Portia should audit:

- sign-in and authentication events;
- record creation;
- view of sensitive records;
- search and bulk export;
- field changes;
- category and severity changes;
- merges and links;
- permission changes;
- break-glass access;
- disclosures;
- retention holds;
- deletion;
- configuration changes;
- automated system actions;
- failed access attempts.

Audit logs should be tamper-evident, access-controlled, retained under a defined schedule, and reviewable without revealing unnecessary student content.

FERPA specifically requires records of many requests and disclosures, including the parties and their legitimate interests, though not every internal school-official access falls under that disclosure-log requirement. Portia should still log internal access as a security and accountability control.

### 7.6 De-identification and aggregate reporting

FERPA permits release of de-identified information only after a reasonable determination that identity is not personally identifiable, considering single or multiple releases and other reasonably available information.

Portia should not equate “remove the name” with de-identification.

Controls should include:

- small-cell suppression;
- minimum cohort sizes;
- removal or generalization of rare combinations;
- date and location generalization;
- query-budget or repeated-query controls;
- export review;
- pseudonymous research codes unrelated to student identifiers;
- no exposure of code-generation logic;
- tenant-specific de-identification settings;
- documented determination and purpose.

### 7.7 Retention and destruction

Federal privacy guidance emphasizes retaining data that must be kept and destroying sensitive data when no longer needed. There is no single product-wide retention period that Portia can safely impose across all record categories and jurisdictions.

Portia should provide a configurable records schedule by:

- tenant;
- jurisdiction;
- student age/status;
- record class;
- determination status;
- legal hold;
- special-education or civil-rights process;
- event closure date;
- disclosure/amendment request;
- backup lifecycle.

Required capabilities:

- schedule preview;
- hold and release;
- authorized disposition;
- deletion approval;
- deletion certificate/log;
- cascading treatment of attachments, indexes, exports, and caches;
- backup expiration;
- tenant export before termination;
- destruction after contract end;
- exception reports.

No record should be retained forever merely because storage is inexpensive.

### 7.8 Security baseline

The Department of Education notes that FERPA does not prescribe specific security controls, but schools should safeguard records and breaches can cause serious harm.

Portia should adopt a recognized security program and include at minimum:

- encryption in transit and at rest;
- modern identity federation;
- multifactor authentication for privileged users;
- secure session management;
- strong tenant isolation;
- secrets management;
- vulnerability and dependency management;
- secure development lifecycle;
- backups and tested restoration;
- incident detection and response;
- audit monitoring;
- rate limiting;
- export controls;
- data-loss prevention appropriate to risk;
- regular penetration testing;
- documented breach response;
- vendor/subprocessor governance;
- secure deletion;
- privacy and security reviews before new sensitive fields are added.

Specific architecture choices should be documented separately.

### 7.9 Information Portia should not collect by default

- diagnoses or suspected diagnoses;
- psychotherapy or counseling notes;
- detailed trauma histories;
- immigration status;
- family financial or legal details unrelated to an authorized process;
- religious or political beliefs;
- sexual history;
- passwords or authentication secrets;
- biometric identifiers;
- continuous audio/video;
- social-media scraping;
- facial recognition;
- emotion recognition;
- location tracking outside a defined educational purpose;
- hearsay about unrelated students;
- protected reports copied from specialized systems;
- speculative gang affiliation;
- unverified criminal allegations;
- broad “home life” narratives;
- AI-generated personality, risk, or intent labels.

---

## 8. Student and Family Involvement

### 8.1 Student participation

Students should have developmentally appropriate opportunities to:

- provide an account;
- identify missing context;
- dispute an account;
- contribute to operational definitions;
- identify triggers and helpful supports;
- select among appropriate support options;
- define personal goals;
- participate in FBA/BIP processes when appropriate;
- review progress;
- help plan reentry or repair;
- identify strengths;
- request assistance.

A student statement should be stored as the student's statement, not paraphrased into an adult's institutional narrative unless the student approves or the record clearly identifies the paraphrase.

### 8.2 Reflection

Reflection tools can support learning but should not become forced confession forms.

A voluntary or locally authorized reflection may ask:

- What happened from your perspective?
- What were you trying to accomplish or communicate?
- Who was affected, including you?
- What do you need now?
- What could help next time?
- What support would make the expected action more possible?
- Is any part of the record inaccurate or incomplete?
- Would you like an advocate, interpreter, or trusted adult involved?

Avoid:

- “Why did you choose to be disrespectful?”
- “Admit what you did.”
- required expressions of remorse;
- character judgments;
- public sharing;
- using silence or refusal as evidence of guilt.

### 8.3 Family partnership

PBIS and CASEL both emphasize authentic, two-way family partnership. Portia should support:

- communication preferences;
- preferred language;
- accessible formats;
- interpreter needs;
- trusted contacts;
- family observations and concerns;
- family strengths and strategies;
- participation in support decisions;
- progress updates;
- questions and disputes;
- consent/procedural status;
- agreed next steps.

The product should distinguish:

- sent;
- delivered;
- opened, if lawful and useful;
- response received;
- meaningful two-way contact;
- meeting held.

It should not score families as engaged or disengaged.

### 8.4 Multi-student privacy

When sharing an event involving several students:

- generate a student-specific view;
- redact names and identifying details of others;
- preserve enough context to make the record understandable;
- allow privacy officer review;
- avoid simply hiding a name while leaving obvious identity clues;
- handle quotations carefully;
- separate common event facts from student-specific determinations.

### 8.5 Disputed accounts

Portia should support disagreement without forcing the institution to erase a good-faith observation solely because someone disagrees.

A complete view may include:

- original account;
- correction of demonstrably inaccurate fields;
- reviewer determination;
- student statement;
- family statement;
- amendment decision;
- current status;
- superseded information clearly marked.

---

## 9. User Experience and Workflow

### 9.1 Fast capture without low-quality data

Recommended pattern:

1. **Safety first:** emergency instructions and contacts are visible without opening a form.
2. **Quick capture:** minimum objective details, autosaved.
3. **Route:** classroom follow-up, support request, administrative review, or restricted safety process.
4. **Complete:** prompts tailored to the selected route.
5. **Review:** another authorized person validates classification and next actions where required.
6. **Follow through:** assigned tasks, due dates, and notifications.
7. **Evaluate:** outcome and fidelity.
8. **Close or continue:** reasoned decision.

### 9.2 Interface safeguards

- Do not show a student's lifetime incident count before the reporter writes the current observation.
- Show active support instructions that the educator is authorized and expected to implement.
- Separate narrative boxes for observation, interpretation, and requested action.
- Mark categories as preliminary until reviewed.
- Display local definitions inline.
- Permit unknown and approximate values.
- Prevent forced guessing.
- Support keyboard-only and screen-reader operation.
- Preserve draft recovery.
- Make date/time zones explicit.
- Avoid “red flag” visual identities on student profiles.
- Use plain language.
- Support translation workflows without overwriting original language.
- Warn before entering third-party or highly sensitive information.
- Provide a structured correction process.
- Require confirmation before bulk export.

### 9.3 Accessibility

Portia should target WCAG 2.2 Level AA for complete workflows, including:

- perceivable labels and instructions;
- sufficient contrast;
- no reliance on color alone;
- reflow and zoom;
- full keyboard access;
- visible focus;
- adequate target size;
- clear error identification and suggestions;
- prevention or confirmation for consequential data actions;
- accessible authentication;
- programmatic status messages;
- understandable language;
- accessible charts with tables and text alternatives.

Accessibility testing should include users with visual, motor, cognitive, language, learning, and neurological disabilities—not only automated scans.

### 9.4 Notifications and alert fatigue

Notifications should be tied to:

- urgent safety routing;
- assigned responsibility;
- approaching due date;
- overdue follow-up;
- required notice;
- plan review;
- intervention data missing;
- unusual access or export;
- retention action.

Controls should include:

- immediate versus digest delivery;
- role-based routing;
- working-hour preferences where appropriate;
- escalation after nonresponse;
- deduplication;
- snooze with reason;
- closure when task completes;
- tenant-defined severity.

Do not notify broad groups merely because a student received a new record.

### 9.5 Work queues

Useful queues include:

- my drafts;
- reports awaiting my review;
- unassigned referrals;
- safety-critical pending actions;
- student/family statements awaiting response;
- interventions due for review;
- missing fidelity data;
- overdue follow-ups;
- amendment/access requests;
- records approaching disposition;
- data-quality exceptions.

Each item should show why it appears and what action will clear it.

### 9.6 Workflow for classroom-managed concerns

1. Educator documents objective observation when documentation is warranted.
2. Educator selects or records immediate classroom response.
3. Portia displays relevant active support instructions.
4. Educator may add a support or request assistance.
5. Follow-up is scheduled only when needed.
6. Repeated patterns go to a team review, not automatic punishment escalation.
7. Team evaluates context, data quality, support access, and fidelity.
8. Outcome is recorded.

### 9.7 Workflow for office-managed referral

1. Reporter creates event/account and referral.
2. System validates minimum facts and routes according to local policy.
3. Reviewer sees the current account, policy definition, student statement if available, and relevant authorized support information.
4. Reviewer gathers additional accounts.
5. Reviewer confirms/changes category and records a determination.
6. Required notices and procedural checks are completed.
7. Immediate and longer-term responses are linked separately.
8. Reentry/support/follow-up is assigned.
9. Closure requires status and rationale.

### 9.8 Workflow for intervention review

1. Define the question and target measure.
2. Confirm baseline and data quality.
3. Review fidelity first.
4. Review student outcome.
5. Review student/family experience and unintended effects.
6. Continue, modify, fade, intensify, or end.
7. Record decision and next review date.
8. Do not equate “more intensive” with “more punitive.”

---

## 10. Practices Portia Should Support

- objective, author-attributed observations;
- multiple perspectives;
- operational definitions;
- positive behavior and skill use;
- classroom-managed and office-managed distinctions;
- preventive and instructional responses;
- PBIS/MTSS tiered supports;
- FBA and function-based plans;
- restorative and reparative processes with safeguards;
- trauma-informed support instructions without trauma inference;
- student and family participation;
- language and accessibility support;
- configurable policies and definitions;
- versioned classifications and determinations;
- intervention dosage, fidelity, and outcomes;
- reentry planning;
- instructional time-loss measurement;
- aggregate equity analysis;
- data-quality reporting;
- privacy-aware export and redaction;
- FERPA access and amendment workflows;
- least-privilege permissions;
- retention and secure destruction;
- auditable changes and access;
- explicit open questions and local governance.

---

## 11. Practices Portia Should Discourage or Prevent

- negative-only incident ledgers;
- vague or judgmental narratives;
- treating a reporter's category as a finding;
- overwriting source accounts;
- requiring staff to guess motive;
- automatic escalation from incident count;
- tiers as student labels;
- punishment-only intervention plans;
- public behavior charts or leaderboards;
- point systems that equate compliance with worth;
- deleting positive points as punishment;
- forced apologies or restorative participation;
- storing detailed clinical, trauma, or mandated-reporting content in general records;
- broad access based only on job title;
- permanent retention by default;
- one-click unredacted bulk exports;
- raw-count demographic comparisons;
- dashboards that hide missing data;
- causal claims from observational data;
- predictive risk scoring;
- automated discipline recommendations;
- sentiment, emotion, remorse, or deception detection;
- facial recognition, passive surveillance, or social-media scraping;
- demographic cues on routine individual decision screens;
- using disability status to justify lower expectations or punitive escalation;
- treating family nonresponse as lack of care;
- closing an event without required follow-up;
- silent changes to policy definitions or historical records.

---

## 12. Suggested Terminology and Field Definitions

| Term | Recommended definition |
|---|---|
| Event | A time-bounded real-world occurrence that may involve one or more people and may generate several accounts or actions |
| Observation | An author-attributed record of directly perceived actions or conditions |
| Reported account | Information attributed to another person rather than directly observed by the author |
| Concern | A documented condition or pattern requesting support; not necessarily misconduct |
| Positive observation | A specific observation of a strength, skill, successful support, repair, or progress |
| Referral | A request for review, service, or support |
| Classification | A controlled category assigned for routing or reporting, with stated status and author |
| Allegation | A claim that a defined policy may have been violated |
| Determination | A formal finding by an authorized decision-maker |
| Response | An action taken during or immediately after an event |
| Consequence (ABC) | What occurred immediately after behavior and may affect future probability; not synonymous with punishment |
| Administrative consequence | A locally authorized disciplinary action |
| Support | An action or resource intended to increase access, participation, safety, skill, or wellbeing |
| Intervention | A planned support with defined implementation and outcome measures |
| Accommodation | A change in access or conditions required or provided without changing the underlying learning goal |
| Replacement skill | A teachable action that meets a need more effectively or safely |
| Antecedent | An observable event or condition occurring before a target behavior |
| Setting event | A broader condition that may alter the likelihood or value of antecedents/consequences |
| Function hypothesis | A tentative, evidence-based explanation of what maintains behavior |
| FBA | A collaborative process using multiple data sources to understand factors contributing to a specific interfering behavior |
| BIP/BSP | A plan of positive, function-based prevention, teaching, response, implementation, and evaluation |
| Fidelity | Extent to which a practice or plan was implemented as intended |
| Outcome | Measured change following support or response |
| Reentry | Planned support for return after absence, removal, crisis, or conflict |
| Repair | An agreed action addressing harm or restoring participation/relationship |
| Amendment | Authorized correction or addition to an education record |
| Statement of disagreement | A linked parent/eligible-student statement contesting maintained information |
| Restricted record | Information requiring narrower access due to legal, safety, clinical, or policy sensitivity |
| Instructional time lost | Time a student was unavailable for ordinary instruction because of an event or institutional response |
| Tier | Current intensity of support, not a student identity or diagnosis |

---

## 13. Preliminary Product Requirements

Priority labels:

- **P0:** foundational requirement before production use;
- **P1:** important for an initial complete release;
- **P2:** valuable extension after foundational controls are proven.

### 13.1 Records and data model

- **P0-R01:** Model event, account, referral, classification, determination, response, intervention, follow-up, communication, and amendment as separate linked records.
- **P0-R02:** Preserve author, source, timestamps, and version for every substantive assertion.
- **P0-R03:** Support multiple participants and participant roles without assigning blame at event creation.
- **P0-R04:** Support multiple accounts, including conflicting accounts.
- **P0-R05:** Separate direct observation, reported information, quotation, hypothesis, and formal finding.
- **P0-R06:** Support positive observations and strengths as first-class records.
- **P0-R07:** Support approximate/unknown times and values without forced guessing.
- **P0-R08:** Store category-definition and policy versions with records.
- **P0-R09:** Preserve correction and supersession history.
- **P1-R10:** Link related events and suggest potential duplicates for human review.
- **P1-R11:** Support multi-student common-event facts with student-specific accounts and determinations.
- **P1-R12:** Support imports with provenance and quality status.
- **P2-R13:** Support offline draft capture with conflict-safe synchronization.

### 13.2 Documentation quality

- **P0-DQ01:** Require an observable narrative for concern/referral records.
- **P0-DQ02:** Provide local definitions, examples, and nonexamples inline.
- **P0-DQ03:** Permit “unknown/not assessed.”
- **P0-DQ04:** Provide transparent prompts for vague, judgmental, or unsupported language.
- **P0-DQ05:** Never silently rewrite user-authored accounts.
- **P0-DQ06:** Display missingness and pending review in reports.
- **P1-DQ07:** Provide inter-observer agreement support for operational definitions.
- **P1-DQ08:** Track event time, entry time, review time, and follow-up time separately.
- **P1-DQ09:** Flag incompatible values and unexplained category changes.
- **P2-DQ10:** Provide configurable data-quality rules by record type.

### 13.3 Supports and interventions

- **P0-S01:** Link each intervention to a need/skill, owner, start date, review date, and outcome measure.
- **P0-S02:** Track prevention, teaching, recognition, response, fidelity, and outcome.
- **P0-S03:** Permit supports without requiring a disciplinary event.
- **P0-S04:** Treat tier as support intensity and preserve history of movement.
- **P1-S05:** Provide dedicated FBA and BIP/BSP workspaces.
- **P1-S06:** Mark perceived function as a hypothesis and prevent automatic use.
- **P1-S07:** Support student and family participation status and contributions.
- **P1-S08:** Support restorative processes without forced admission or participation.
- **P1-S09:** Track intervention dosage, missed implementation, and adverse effects.
- **P2-S10:** Provide reusable locally governed intervention templates.

### 13.4 Workflow

- **P0-W01:** Support quick capture followed by later completion.
- **P0-W02:** Route classroom-managed, office-managed, support-request, and restricted safety records differently.
- **P0-W03:** Require authorized review for formal determinations.
- **P0-W04:** Assign follow-up owner and due date.
- **P0-W05:** Expose active authorized support instructions to implementers.
- **P0-W06:** Keep prior negative history out of the initial observation-entry view by default.
- **P1-W07:** Provide work queues and digest notifications.
- **P1-W08:** Support reentry and closure criteria.
- **P1-W09:** Support local due-process and notice checklists without making legal conclusions.
- **P2-W10:** Support configurable approval workflows.

### 13.5 Equity and analytics

- **P0-E01:** Report counts and rates with numerator, denominator, date range, and population.
- **P0-E02:** Support disaggregation by locally governed attributes.
- **P0-E03:** Provide risk index, risk ratio, rate difference, composition, event rate, and instructional time-loss measures.
- **P0-E04:** Pair repeated-event rates with unique-student measures.
- **P0-E05:** Distinguish subjective categories and decision points.
- **P0-E06:** Implement small-cell and re-identification safeguards.
- **P0-E07:** Display missingness, definition changes, and data-quality warnings.
- **P0-E08:** Do not generate predictive student risk scores or automated discipline recommendations.
- **P1-E09:** Analyze category confirmation/change, response distribution, support access, and time to support.
- **P1-E10:** Support authorized team action plans linked to findings.
- **P2-E11:** Provide uncertainty intervals or stability warnings for small samples.
- **P2-E12:** Support privacy-preserving cross-period comparisons.

### 13.6 Privacy, permissions, and records rights

- **P0-P01:** Implement role- and attribute-based access control.
- **P0-P02:** Implement field-level sensitivity and restricted workflows.
- **P0-P03:** Support parent/eligible-student access and amendment processes.
- **P0-P04:** Generate redacted student-specific views of multi-student records.
- **P0-P05:** Maintain linked statements of disagreement.
- **P0-P06:** Audit access, edits, exports, permissions, and disclosures.
- **P0-P07:** Require reason and logging for break-glass access.
- **P0-P08:** Provide configurable retention, legal holds, and destruction.
- **P0-P09:** Disable standing vendor access to production student data.
- **P0-P10:** Support secure tenant export and contract-end deletion.
- **P1-P11:** Provide disclosure logs and disclosure-purpose fields.
- **P1-P12:** Provide de-identification and small-cell controls for export.
- **P1-P13:** Provide periodic access certification.
- **P2-P14:** Support tenant-configured research datasets with privacy review.

### 13.7 Security and accessibility

- **P0-SA01:** Encrypt data in transit and at rest.
- **P0-SA02:** Support SSO and multifactor authentication for privileged roles.
- **P0-SA03:** Enforce tenant isolation and least privilege.
- **P0-SA04:** Use tamper-evident audit logging.
- **P0-SA05:** Implement tested backup, recovery, and incident response.
- **P0-SA06:** Meet WCAG 2.2 Level AA across complete workflows.
- **P0-SA07:** Provide accessible tables/text alternatives for charts.
- **P1-SA08:** Complete independent security and accessibility testing before production.
- **P1-SA09:** Provide data-loss and anomalous-export controls.
- **P2-SA10:** Publish an accessibility conformance report and security documentation.

### 13.8 Explicit product prohibitions

- **P0-X01:** No public student behavior leaderboard.
- **P0-X02:** No single behavior, character, or compliance score.
- **P0-X03:** No predictive discipline, violence, or recidivism score.
- **P0-X04:** No automated punishment recommendation.
- **P0-X05:** No emotion, deception, remorse, or intent inference.
- **P0-X06:** No diagnostic or trauma inference.
- **P0-X07:** No facial recognition, passive audio surveillance, or social-media scraping.
- **P0-X08:** No automatic consequence escalation based only on count.
- **P0-X09:** No silent account rewriting or record alteration.
- **P0-X10:** No indefinite retention by default.

---

## 14. Candidate Acceptance Tests

Examples for future specification:

1. **Observation versus interpretation**
   - Given a reporter enters “Student was disrespectful,”
   - Portia asks for observable words/actions,
   - and stores the final objective account separately from any selected category.

2. **Multiple accounts**
   - Given two witnesses provide different accounts,
   - both remain author-attributed,
   - and a reviewer can make a determination without overwriting either.

3. **Reporter category versus reviewer category**
   - Given a reporter selects “disruption,”
   - and a reviewer changes it to “no policy category,”
   - both selections, definitions, authors, times, and rationale remain auditable.

4. **Function hypothesis**
   - Given a reporter selects “escape/avoid,”
   - Portia labels it as a reporter hypothesis,
   - does not display it as an FBA finding,
   - and does not trigger an intervention or consequence automatically.

5. **Multi-student access**
   - Given an event involves three students,
   - a parent export for one student contains only that student's information and non-identifying context.

6. **Amendment**
   - Given an authorized correction changes an inaccurate location,
   - the active view shows the corrected location,
   - the audit history preserves the original,
   - and any linked disagreement statement remains associated.

7. **Equity report**
   - Given a dashboard shows a risk ratio,
   - it also shows group numerators, denominators, date range, missingness, comparison group, and a caution against causal interpretation.

8. **Small cells**
   - Given a filter would reveal an identifiable small subgroup,
   - Portia suppresses or generalizes the output and prevents differencing through adjacent queries.

9. **Intervention review**
   - Given a student outcome did not improve,
   - the review requires consideration of fidelity before labeling the intervention ineffective.

10. **History priming**
    - Given a teacher starts a new observation,
    - the initial screen does not show lifetime negative incident counts.

11. **Removal**
    - Given a student is sent home early,
    - Portia captures the removal and instructional time lost rather than allowing it to exist only in narrative text.

12. **Restricted safety event**
    - Given a user selects restraint, seclusion, self-harm, abuse/neglect, or threat concern,
    - Portia routes to the appropriate restricted workflow and does not expose the sensitive narrative to ordinary behavior users.

13. **Retention hold**
    - Given a record is subject to an access/amendment request,
    - scheduled destruction pauses until the hold is released.

14. **Accessibility**
    - Given a keyboard-only or screen-reader user,
    - the user can create, review, correct, and submit the complete record and understand all errors/status changes.

---

## 15. Open Questions Requiring Stakeholder or Legal Input

### Governance and jurisdiction

- Which states and districts are initial targets?
- What records schedules apply to each record class?
- Which local policy terms must be represented verbatim?
- What constitutes classroom-managed versus office-managed behavior locally?
- Which state reporting formats are required?
- What student/parent access workflow will each tenant use?
- Which users are designated school officials with legitimate educational interests?
- Which fields are directory information, if any? Behavior data should not be presumed directory information.
- Which specialized systems should receive referrals rather than data copies?

### Educational practice

- Which PBIS/MTSS fidelity tools will Portia support or integrate with?
- Who is qualified locally to lead an FBA?
- When does local practice require consent?
- How will districts define and govern universal screening?
- Which positive-acknowledgment practices align with community values?
- What restorative processes are available, and who is trained to facilitate them?
- How will students and families co-design terminology and workflows?
- How will internalizing concerns be supported without turning Portia into a mental-health diagnostic tool?

### Data and analytics

- What are the approved demographic dimensions?
- What small-cell and complementary-suppression rules apply?
- What comparison group and risk measures does the district use?
- How should student mobility and partial-year enrollment affect denominators?
- What is the approved exposure measure for classroom or transportation comparisons?
- How will imports from legacy systems identify missing or unreliable data?
- Which outcome measures are valid for each intervention?
- How will local teams assess unintended consequences?

### Security and privacy

- What identity provider and provisioning model will be used?
- What data residency and subprocessor requirements apply?
- What backup and deletion service levels are required?
- How will break-glass access be reviewed?
- What events require field-level encryption or a separate datastore?
- What incident-notification obligations apply?
- Will Portia store attachments, or only references to a governed document system?
- How will districts review and approve new free-text fields?

### Product boundaries

- Should Portia include formal discipline adjudication or only route to an SIS?
- Should special-education FBA/BIP records live in Portia or be linked from an IEP system?
- Should crisis, restraint/seclusion, Title IX, bullying, threat assessment, and mandated-reporting modules be separate applications?
- What minimum functionality can be released without creating a negative-only incident tracker?
- What integrations are necessary to avoid duplicate records while preserving provenance?

---

## 16. Proposed Follow-Up Decision Records

The following decisions are consequential enough for separate ADRs:

1. **Separate observations, interpretations, classifications, and determinations.**
2. **Prohibit predictive behavioral scoring and automated discipline recommendations.**
3. **Use linked event/account records for multi-student incidents.**
4. **Use append-only audit history with correctable active records.**
5. **Implement role plus attribute and field-level authorization.**
6. **Route highly sensitive safety/clinical/legal matters outside the ordinary behavior workflow.**
7. **Treat tiers as support intensity rather than student identity.**
8. **Adopt WCAG 2.2 Level AA as the accessibility baseline.**
9. **Make retention tenant- and record-class-configurable rather than universal.**
10. **Hide prior negative history during initial incident capture to reduce confirmation bias.**

A proposed ADR accompanying this research addresses item 1.

---

## 17. Research-to-Design Traceability Matrix

| Research finding | Portia implication |
|---|---|
| PBIS is a framework of systems, data, practices, outcomes, and equity | Model supports, fidelity, outcomes, teams, and equity—not just incidents |
| Data collection should begin with a decision question | Reports and forms should identify purpose and intended decision |
| ODR data contain time, location, behavior, response, and other context | Provide structured context and rapid entry |
| FBA needs objective definitions and multiple direct/indirect data sources | Dedicated FBA workspace; no function inference from one event |
| Function-based supports outperform non-function-based responses in relevant research | Link hypotheses, prevention, skill teaching, and outcomes |
| Family and student partnership improves contextual relevance and implementation | First-class student/family statements and plan participation |
| Discipline disparities appear across race, gender, and disability | Built-in disaggregated aggregate analysis and bias safeguards |
| Subjective classifications create vulnerable decision points | Operational definitions, required observation, review status |
| Restorative practices show promising but mixed outcomes | Support implementation and outcome tracking; no automatic claim of effectiveness |
| Trauma-informed systems resist retraumatization | Minimize sensitive collection, support choice, separate clinical content |
| FERPA covers maintained student-related behavior records | Treat Portia data as education records |
| FERPA provides inspection and amendment rights | Export, redaction, correction, disagreement, and legal-hold workflows |
| School officials should access only records of legitimate educational interest | Least privilege, scoped access, authentication, auditing |
| De-identification requires contextual re-identification analysis | Small-cell and repeated-query controls |
| Sensitive data should be destroyed when no longer needed | Configurable retention and verified destruction |
| WCAG 2.2 addresses broad disability access | Design and test complete workflows to Level AA |

---

## 18. Sources and Bibliography

All online sources were accessed **July 14, 2026**, unless otherwise noted.

### Federal law, guidance, and oversight

1. U.S. Department of Education, Student Privacy Policy Office. **Family Educational Rights and Privacy Act (FERPA), 34 C.F.R. Part 99.**<br>
   https://studentprivacy.ed.gov/ferpa

2. U.S. Department of Education, Student Privacy Policy Office. **Data Security: K–12 and Higher Education.**<br>
   https://studentprivacy.ed.gov/data-security-k-12-and-higher-education

3. U.S. Department of Education, Student Privacy Policy Office. **Data Retention and Data Destruction.** Updated July 2, 2025.<br>
   https://studentprivacy.ed.gov/training/data-retention-and-data-destruction

4. U.S. Department of Education, Privacy Technical Assistance Center. **Best Practices for Data Destruction.** Updated March 2019.<br>
   https://studentprivacy.ed.gov/resources/best-practices-data-destruction

5. U.S. Department of Education, Privacy Technical Assistance Center. **Protecting Student Privacy While Using Online Educational Services: Requirements and Best Practices.**<br>
   https://studentprivacy.ed.gov/resources/protecting-student-privacy-while-using-online-educational-services-requirements-and-best

6. U.S. Department of Education, Office of Special Education and Rehabilitative Services and Office of Elementary and Secondary Education. **Using Functional Behavioral Assessments to Create Supportive Learning Environments.** November 2024.<br>
   https://sites.ed.gov/idea/idea-files/using-functional-behavioral-assessments-to-create-supportive-learning-environments/

7. Electronic Code of Federal Regulations. **34 C.F.R. § 300.324 — Development, review, and revision of IEP.**<br>
   https://www.ecfr.gov/current/title-34/subtitle-B/chapter-III/part-300/subpart-D/section-300.324

8. Electronic Code of Federal Regulations. **34 C.F.R. § 300.530 — Authority of school personnel.**<br>
   https://www.ecfr.gov/current/title-34/subtitle-B/chapter-III/part-300/subpart-E/section-300.530

9. U.S. Department of Education. **Restraint and Seclusion: Resource Document and related materials.**<br>
   https://www2.ed.gov/policy/seclusion/index.html

10. U.S. Government Accountability Office. **K–12 Education: Discipline Disparities for Black Students, Boys, and Students with Disabilities (GAO-18-258).** March 2018.<br>
    https://www.gao.gov/products/gao-18-258

### PBIS, MTSS, equity, and family partnership

11. Center on Positive Behavioral Interventions and Supports. **What Is PBIS?**<br>
    https://www.pbis.org/pbis/what-is-pbis

12. Center on Positive Behavioral Interventions and Supports. **Data-Based Decision Making.**<br>
    https://www.pbis.org/topics/data-based-decision-making

13. Center on Positive Behavioral Interventions and Supports. **Equitable Supports.**<br>
    https://www.pbis.org/equitable-supports

14. Center on Positive Behavioral Interventions and Supports. **Discipline Disproportionality Problem Solving: A Data Guide for School Teams.** Updated October 23, 2023.<br>
    https://www.pbis.org/resource/discipline-disproportionality-problem-solving-a-data-guide-for-school-teams

15. Center on Positive Behavioral Interventions and Supports. **Family.**<br>
    https://www.pbis.org/topics/family

16. Center on Positive Behavioral Interventions and Supports. **Students with Disabilities.**<br>
    https://www.pbis.org/topics/students-with-disabilities

17. IRIS Center, Vanderbilt University. **Functional Behavioral Assessment (Elementary): Identifying the Reasons for Student Behavior.**<br>
    https://iris.peabody.vanderbilt.edu/module/fba-elem/

### Restorative, trauma-informed, and social-emotional approaches

18. Augustine, Catherine H., et al. **Can Restorative Practices Improve School Climate and Curb Suspensions? An Evaluation of the Impact of Restorative Practices in a Mid-Sized Urban School District.** RAND Corporation, 2018. DOI: 10.7249/RR2840.<br>
    https://www.rand.org/pubs/research_reports/RR2840.html

19. National Child Traumatic Stress Network. **Creating, Supporting, and Sustaining Trauma-Informed Schools: A System Framework.** 2017.<br>
    https://www.nctsn.org/resources/creating-supporting-and-sustaining-trauma-informed-schools-system-framework

20. Collaborative for Academic, Social, and Emotional Learning. **What Is the CASEL Framework?**<br>
    https://casel.org/fundamentals-of-sel/what-is-the-casel-framework/

21. Durlak, Joseph A., Roger P. Weissberg, Allison B. Dymnicki, Rebecca D. Taylor, and Kriston B. Schellinger. **The Impact of Enhancing Students' Social and Emotional Learning: A Meta-Analysis of School-Based Universal Interventions.** *Child Development* 82, no. 1 (2011): 405–432. DOI: 10.1111/j.1467-8624.2010.01564.x.<br>
    https://doi.org/10.1111/j.1467-8624.2010.01564.x

### Accessibility

22. World Wide Web Consortium. **Web Content Accessibility Guidelines (WCAG) 2.2.** W3C Recommendation.<br>
    https://www.w3.org/TR/WCAG22/

### Selected peer-reviewed equity research

23. Smolkowski, Keith, Erik J. Girvan, Kent McIntosh, Rhonda N. T. Nese, and Robert H. Horner. **Vulnerable Decision Points for Disproportionate Office Discipline Referrals: Comparisons of Discipline for African American and White Elementary School Students.** *Behavioral Disorders* 41, no. 4 (2016): 178–195.<br>
    https://doi.org/10.17988/bedi-41-04-178-195.1

24. Okonofua, Jason A., and Jennifer L. Eberhardt. **Two Strikes: Race and the Disciplining of Young Students.** *Psychological Science* 26, no. 5 (2015): 617–624.<br>
    https://doi.org/10.1177/0956797615570365

25. Riddle, Travis, and Stacey Sinclair. **Racial Disparities in School-Based Disciplinary Actions Are Associated with County-Level Rates of Racial Bias.** *Proceedings of the National Academy of Sciences* 116, no. 17 (2019): 8255–8260.<br>
    https://doi.org/10.1073/pnas.1808307116

---

## 19. Final Recommendation

Portia should begin with a narrow but complete vertical slice:

1. objective observation and positive observation;
2. linked event and multi-perspective accounts;
3. classroom support/request for review routing;
4. reviewer classification and determination;
5. response, follow-up, and outcome;
6. student/family statement;
7. role- and field-scoped access;
8. audit, correction, redaction, retention, and export;
9. descriptive aggregate analytics with equity safeguards.

It should **not** launch first as a fast incident form with dashboards added later. That sequence would establish a punitive data model that is difficult to reverse. The minimum viable Portia should already connect documentation to support, review, rights, and outcomes.

The guiding product test is:

> **Does this feature help a school understand what happened, respond fairly, support learning and safety, evaluate what works, and protect the dignity and rights of everyone involved?**

If the answer is no—or if the feature primarily makes it easier to label, rank, predict, punish, or surveil students—it should not be part of Portia.
