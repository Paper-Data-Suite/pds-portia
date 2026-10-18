# Portia #60 — Slice 1: baseline, authority, versioned profile and support matrix

## Verified repository baseline

- GitHub issue: https://github.com/Paper-Data-Suite/pds-portia/issues/60
- Existing branch: `60-paper-interpretation-candidates-capture-proposals`
- Remote `main` and branch when this slice was prepared: `2bf30bba4daca0dd523824b3bf4aef5e72478f14` (identical, clean main-relative diff).
- Prerequisite #59 was merged as PR #100. #56 froze the v1 contracts, #57 built Page Target/Batch services, #58 printed ten immutable layouts, #59 added Core-retained, independently routed physical Page Record intake.
- Local runtime environment and official installed Core version must be captured by the guarded runner; remote GitHub does **not** establish the teacher's currently installed Core wheel or the integrity of a local OneDrive workspace.

## Authority hierarchy and no-go boundaries

1. `pds_core.scan_retention` owns unchanged retained source bytes, exact SHA-256, original source-scan identity. Core's registration/dispatch owns PDS2 routing, **not** field meaning.
2. Portia `capture.batches`, `capture.page_targets`, `capture.form_catalog` own the persisted target, seven-part historical template identity, immutable layout digest and field/entry geometry; `capture.form_catalog.resolve_capture_page_spec` requires exact identity, not a floating current template.
3. Portia `intake.dispatch`, `intake.page_records` own verified route-to-physical-page receipts and their operational state. An accepted `page_record@1` is neither interpreted nor human-reviewed.
4. `paper_interpretation@1` represents uncertain literal/source candidates, distinct from `capture_proposal@1` mappings; `capture_review@1` (#61) provides attributable human decisions and #62 alone may materialize canonical domain records.
5. Existing `portia.storage.io`, `.paths`, `.locks` must be reused by durable #60 slices. Slice 1 is pure and does not open any workspace paths or import sibling runtimes.

Authoritative design: ADR 0016, ADR 0021, `docs/design/portia-paper-interpretation-staging.md`, `portia-paper-proposal-and-human-review.md`, and `portia-paper-import-operational-failure-recovery-and-integrity.md`. The unchanged frozen v1 runtime models and schemas `PaperInterpretationV1` and `CaptureProposalV1` govern later persistence. Schema `interpreter_profile` has exactly four keys. Nothing in this slice changes schema files.

## Ten historical layouts — support inventory

All below have **top-left PDF-point geometry**, unique page-local `entry_key` / `field_key` / `region_key`, exact seven-element template identities and SHA-256 semantic layout fingerprints. A printed `page_ordinal` is **not** an original PDF's `source_page_number` or its Page Target `page_index`.

| Form family | Historical page role / ordinal | Declared entry roles | Source fields | Target-kind hint only |
| --- | --- | --- | ---: | --- |
| Daily Classroom Observation | `classroom_observation` / 1 | `session_context`, 2 × `observation` | 13 | context none; observation or event needs a human target decision |
| Daily continuation | `observation_continuation` / 2 | `session_context`, 3 × `observation` | 14 | same; separate immutable layout |
| Focused Monitoring | `monitoring_sheet` / 1 | `monitoring_context`, `monitoring` | 7 | context none; observation hint |
| Communication Log | `communication_sheet` / 1 | `communication_context`, `communication` | 8 | context none; communication hint |
| Event Information | `event_information_sheet` / 1 | `event_context`, `event_information` | 6 | context none; event hint |
| Multi-Event Information | `multi_event_sheet` / 1 | `event_context`, 2 × `event_information` | 10 | context none; independent event hints |
| Event Evidence | `event_evidence_sheet` / 1 | `event_context`, `event_evidence` | 7 | context none; account vs. observation unresolved |
| Support Implementation | `implementation_sheet` / 1 | `implementation_context`, `implementation` | 7 | context none; implementation hint |
| Support Process Evidence | `support_evidence_sheet` / 1 | `support_context`, `support_evidence` | 5 | context none; observation hint |
| Follow-Up | `follow_up_sheet` / 1 | `follow_up_context`, `follow_up` | 8 | context none; follow-up hint |

Total: **10 layouts, 9 form families, 24 entry slots, 85 fields**; 79 declared text/handwriting regions and 6 choice/mark regions. These counts are independently checked against installed catalog resources by tests, not used to invent undocumented slots.

## Exact versioned selection

Frozen initial profile (`portia.intake.interpretation_profiles.LOCAL_CANDIDATES_V1`):

```json
{
  "interpreter_id": "portia_local_candidates",
  "interpreter_version": "1",
  "mapping_profile_id": "portia_capture_roles",
  "mapping_version": "1"
}
```

It is an **authority/inventory** profile, not an executable recognizer. It pins `text_provider=none`, `mark_provider=none`, `manual_provider=not_yet_implemented`, `external_network_allowed=false`. Historical profile resolution requires all four fields exactly, with no implicit `latest`, model download, cloud call, installed-provider auto-selection or version substitution. Later slices must explicitly version a qualified provider when introducing recognition or manual transcription. No interpretation record may claim `complete` simply because the planner ran.

| Source field type / declared method | Automated today | Human-assisted today | Meaning of absence |
| --- | --- | --- | --- |
| Text / `handwriting_recognition` | **Unavailable**: no qualifying field recognizer integrated | **Not yet implemented**; Slice 8 manual candidate procedure | No OCR result is **not** blank or a negative |
| Text / `manual_transcription` (if present in a historical spec) | **Unavailable** | **Not yet implemented**; later attributable candidate authoring | Cancelling/not transcribing is **not** blank |
| Choice / `mark_recognition` | **Unavailable**: #59 QR detector is not a checkbox OMR engine | **Not yet implemented**; later explicit inspection/transcription | Unread/unattempted is **not** unmarked/false/no |

This may look conservative but avoids a false claim that Portia currently reads student handwriting. Future Slice 3 can enable a *specific qualified local* text/mark provider with isolated tests, explicit versions, limits, and offline data handling. Printed `positive/general/concern` are note-type cues only.

## Historical Page Target handling

- **v2**: a *pure* `plan_historical_interpretation` accepts a modelled PageTargetV2 with exactly resolved seven-element identity, active target, matching entry layout, page purpose, capture mode and existing-work policy. It returns a read-only inventory; it is **not** permission to access class data or a source image.
- **v1**: explicitly unsupported for #58 ten-layout interpretation (`page_target_v1_not_interpretable`), since the accepted historical v1 runtime does not demonstrate the same frozen v2 layout/entry authority. No fallback to a similarly named v2/current form.
- An old/new fingerprint conflict or unknown historical profile fails shut; a context slot never receives a target-kind hint. Multiple permitted target kinds require human resolution. A single permitted kind is still only an **unimplemented mapping hint**, not a proposed record.

## Related PDS implementation precedent

- **Core:** `pds_core.scan_retention.RetainedSourceScan` preserves SHA-256 and exact retained path identity. Do not copy original files to build semantic staging. Official Core v0.6.6 and historical v0.6.3–0.6.5 must be qualified at final #60 acceptance.
- **Quillan:** its retained-page decoder validates Core custody and isolates one physical page and route at a time; useful for resource ceilings, failure isolation and original-page semantics, but Quillan recognition/academic-grade models are not imported.
- **ScoreForm:** its OMR workflow distinguishes failed scans and teacher-verified responses; **do not** copy grading/bubble-correctness assumptions to observational checkboxes. QR recognition in #59 is also not text/handwriting/mark recognition.
- **Suite:** module composition follows #55 later; no new operation is registered here.

## Next slices and gate economics

- **Slice 2:** authorize class/operation **before protected reads**; reload Page Record, exact frozen v2 Page Target, Batch, Core route, original retained-source SHA and original physical page number; then bounded alignment and extraction from declared regions, recording explicit limitations. Do not trust this pure planner as authorization.
- **Slice 3:** implement/characterize optional local providers, including a truthful unsupported provider and ambiguity/blank policy; do not assert human-writing accuracy from synthetic mocks.
- **Slices 4–7:** v1 schema-faithful candidate assembly, immutable generations, versioned domain path crosswalk and per-entry proposals, exclusive create/readback, replay and isolation.
- **Slice 8:** source-level teacher workflow and separate attributable staging transcription, preserving #61 human review as unavailable.

**Slice 1 validation:** a single focused `pytest` gate over this support registry and the existing #58 catalog tests, Ruff autofix/format followed by Ruff check, strict mypy on the new production module. The guarded runner commits/pushes only after these pass. Full suite, build, installed-wheel/legacy Core and hosted platform qualification are deliberately deferred per #60 test-economy policy. No real-paper acceptance claim is made by this slice.
