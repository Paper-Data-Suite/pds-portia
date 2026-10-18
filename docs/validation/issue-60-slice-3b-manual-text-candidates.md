# #60 Slice 3B - attributed manual text staging (not Capture Review)

**Starting authority:** Portia #60 branch commit `89cf4a7ca3cfe4a0b2d89be0aed45427c1feee14`, after Slice 3A local mark recognition. Uses the frozen `paper_interpretation@1` field vocabulary without persisting a Paper Interpretation yet.

## Contract and profile decision

Adds an explicit, version-pinned `portia_local_assisted_marks/1`, `portia_capture_roles/1` profile. `text_provider=none`, `mark_provider=local_checkbox_v1`, `manual_provider=local_operator_v1`, `external_network_allowed=False`. Original `portia_local_candidates/1` and `portia_local_marks/1` remain unchanged. **Never silently reinterpret an earlier generation as human-authored.** A future persisted manual candidate uses the new profile, retaining its human operator attribution separately from a later Capture Review (#61).

`ManualTextSelection` contains an exact historical `entry_key` and `field_key` plus an operator-supplied nonempty text literal. No caller-supplied source pages, Page Target, mapped record kinds, or person identities are accepted. The pure `add_one_manual_text` function verifies every page-local entry/field key and original capture method against the exact installed historical spec. The only permitted change is one **unreadable, declared text field** becoming `candidate_detected`, `capture_method=manual_transcription`, with the operator's literal unchanged. Original local mark results, ambiguous alternatives, and all other unreadable fields are copied untouched. The prior `LocalPageCandidates` is not mutated.

`FileManualTextCandidateService.transcribe_one` requires a trusted class authorization **before** protected reads, reads trusted actor attribution, reopens the exact already-retained physical page, uses the pinned Slice 3A mark provider without any OCR substitution, and revalidates Page Record/route/retained-source lineage, layout, authorization, and attribution after processing. No newly retained scan, generated PDF, extracted crop, persistent interpretation or proposal is produced. Cancellation means **do not call the service**, rather than writing a blank field.

## Source fidelity and limits

- Preserves whitespace, capitalization, dates, proper names, punctuation and embedded lines exactly. No spelling correction, semantic normalization, NLP, or confidence-based acceptance.
- Requires at least one non-whitespace character, upper bound 4000 characters and stricter *historical* `max_characters`, rejects NUL, disallowed controls and invalid Unicode surrogates. Secret literals are hidden from dataclass representations and never shown in diagnostics.
- An apparently unmarked checkbox is not `False`/`No`; an unreadable text field is not `blank`; ambiguity is preserved. `text_provider_unavailable` is cleared **only if every declared text field on the page has been explicitly resolved**, not merely because one field was transcribed.
- Only text fields (`handwriting_recognition` or `manual_transcription` declared capture method) may receive the manual literal. Choice fields remain under local checkbox recognition; manual mark correction is a distinct future decision.
- No student, source author, incident attribution, behavior classification or canonical domain record is inferred. This creates no `capture_review@1` and does not bypass Issue #61.

## Tests and limitations

The focused tests verify exact identities and old-profile stability; every one of the ten historical layouts; source literals and max length; copied ambiguous marks; unsupported fields and forged field tokens; authorization refusal before reads; change/revocation detection and operator attribution. No attempt is made to turn OCR, handwriting decoding, or person matching into a working capability. The richer teacher menu and restart-safe immutable `paper_interpretation@1` generations remain subsequent #60 increments.
