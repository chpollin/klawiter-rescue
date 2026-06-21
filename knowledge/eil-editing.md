---
title: EIL Editing Interface
aliases: [eil-editing, in-tool editing, expert-in-the-loop editing, curation layer, three-status review]
tags: [design, eil, dia-xai]
created: 2026-06-21
updated: 2026-06-21
---

# EIL Editing Interface

Design for extending the in-tool editing capability so a domain expert can confirm, correct, or complete every field the pipeline cannot verify on its own, with the result saved as a durable, auditable record. This is the build-out path for EIL-Tool 1 of the DIA-XAI project. The design is modeled on the sibling tool `szd-htr` (SZD OCR/HTR pipeline), which already runs the mature version of this correction workflow; this document adapts its proven model to bibliographic records and names the shared spine the two tools have in common.

## Summary

The data rescue produces an extraction that is provably complete at record level (see [[data#record-census]]) but uncertain at field level: roughly half of all publisher and translator values are absent or LLM-inferred, titles fall back to page metadata, and one entry is a blanked stub. Machine extraction can flag this uncertainty but cannot resolve it; only a domain expert holds the knowledge to decide whether a value is right, wrong, or missing. The editing interface is where that judgment enters the dataset. The design rests on four commitments, all carried over from `szd-htr`: a three-status review lifecycle that records how far each record has been verified; a full edit history that preserves the machine original alongside every human change; a calibrated triage signal that points the expert at what to check first; and persistence through a local write-back with git history as the audit trail.

## Lineage: what szd-htr already solved

`szd-htr` corrects machine transcriptions of handwritten and printed sources through a localhost-only editing mode in its static frontend (`docs/app.js`). Its model, documented in that project's `verification-concept.md`, has the pieces the first klawiter `edit.js` lacked:

- A **three-status review model** (`Ungeprüft` / `Agent-geprüft` / `Mensch-geprüft`), stored as a `review.status` field on each record, summarized in the display layer by `isHumanChecked()` / `isAgentChecked()`.
- **Edit history per unit**: every correction stores the pre-edit value, who made it, when, and whether agent or human (`edit_history: [{original_transcription, edited_by, edited_at, source}]`); the machine original is never discarded and is shown as a side-by-side diff.
- A **calibrated triage signal** (`quality_signals` → `needs_review`): not a status but a "check this first" hint, with the explicit lesson that signals must be tuned against verified cases for precision before they are allowed to create review work.
- A **middle, automatic verification tier**: a vision agent compares the source image against the transcription and marks confirmed records `agent_verified`, so human time concentrates on the divergent cases.
- **Persistence and audit**: a local helper service (`serve.py`, endpoints `POST /api/edit` and `/api/approve`) writes corrections back into the dataset; the git history of the results is the audit trail, and the frontend shows the git state (recent commits, uncommitted count) in a workspace panel.

The klawiter design below maps each of these onto bibliographic fields. The differences are only the unit of correction (a record's fields rather than a page's transcription) and the source of the uncertainty signal (extraction provenance and verification flags rather than image-text quality signals). The spine is identical; see [[#shared-curation-spine]].

## Current klawiter state

`edit.js` (localhost-only, gated by `App.state.isLocal && App.state.editMode`) now implements increment 1. Inline editing of the four provenance-tracked fields (publisher, location, translator, pageCount) is typed as one of the three actions Accept / Correct / Add, every action carries the v2 edit-history shape (`action`, `oldValue`, `newValue`, `previousProvenance`, `edited_by` role, `edited_at`, `source`), the three-status review is surfaced per entry as a chip raised to Mensch-geprüft by pending human edits, pending edits persist in `localStorage` across reloads, and Save downloads a `patchVersion: 2` document that `pipeline/apply_patches.py` consumes directly. The frontend/backend patch contract is pinned by `tests/test_patch_contract.py`. `.github/workflows/validate-patch.yml` validates patches on pull requests. The dataset-side write-back is `pipeline/apply_patches.py` (Session 17, unit-tested): it applies approved corrections as an overlay, sets the corrected field's provenance to `editor`, preserves the machine original in an edit history, and raises the review status. What remains is increment 2 (a calibrated triage signal), increment 3 (per-field raw-wiki segmentation shown alongside each field; the full bibliographic source is already shown as the adjudication panel), and increment 4's live local write-back endpoint that lets the frontend apply corrections without the manual patch-file step.

## Target design

### Three-status review

Each entry carries a review status, the same three levels as szd-htr, adapted to extraction:

| Status (display) | `review.status` | Meaning for a bibliographic record |
|---|---|---|
| **Mensch-geprüft** | `approved` | The editor read the entry's fields against the raw wiki source and confirmed or corrected them. Counts as verified and as gold for the EQUALIS measurement. |
| **Agent-geprüft** | `agent_verified` | An automatic agent compared each extracted field against the raw wiki text and confirmed it. Likely correct, does not replace human review. |
| **Ungeprüft** | no `review` block | Pipeline extraction only. Field-level provenance (regex / llm / missing) still describes how each value was produced. |

`needs_review` is a triage hint within `Ungeprüft` ("check this first"), not a fourth status.

### The three actions

Editor interactions are typed as one of three, the EQUALIS triad, and each is recorded in the edit history:

- **Accept** confirms a present value is correct. Changes no value; promotes the field (and, when all fields are confirmed, the entry) toward `approved`.
- **Correct** replaces a present but wrong value.
- **Add** supplies a value for a field the source contains but the pipeline left empty (a `missing` field). Kept distinct from Correct because it measures recall recovery, not precision repair.

### Edit history and provenance

Every action writes an edit-history record on the field, mirroring szd-htr's structure:

```json
"edit_history": [{
  "field": "publisher",
  "action": "correct",
  "originalValue": "Leipzig",
  "newValue": "Insel-Verlag",
  "previousProvenance": "llm",
  "edited_by": "Editor (SZD)",
  "edited_at": "2026-06-21T...",
  "source": "human"
}]
```

The machine original is preserved and shown as a before/after diff. After an Accept or Correct, the field's provenance moves to `editor`; the badge then tells the reader not just how the machine produced a value but that a human verified it. `edited_by` records the role, not the personal name, per the project's data-privacy convention.

### The uncertainty surface

The editor does not hunt blindly through thousands of entries; the interface ranks and marks what needs attention, driven by signals already present:

- **Provenance badges** (regex / llm / missing): `llm` and `missing` are the high-attention classes.
- **Verification flags** from `verify.py`: false positives (a value not found in the raw text) and false negatives (a value detectable in the raw text but absent from output).
- **Census anomalies** from `census.py`: the blanked stub and any future record the reconciliation isolates.

szd-htr's lesson applies directly: a triage signal must be calibrated against verified cases before it creates work. The field-level content spot-check (reading a stratified sample of entries against their raw wiki source and recording the error rate per field) is exactly that calibration input; it tells the triage which fields and entry types most deserve the editor's time.

### Persistence and how it is saved

Three layers, volatile to durable, following szd-htr:

1. **Session durability**: mirror pending edits into `localStorage` so in-progress work survives a reload. szd-htr keeps its `editedTranscriptions` map this way; klawiter currently loses pending edits.
2. **Write-back**: a local helper (a small `serve.py`-style endpoint, or the existing patch-export as the portable fallback) applies confirmed edits into the dataset and into a new pipeline step (`apply_patches.py`) that sets the field provenance to `editor`. Re-running the extraction pipeline never overwrites an `editor` value silently; conflicts surface for review. This preserves the [[about#data-integrity-principle|Data Integrity Principle]]: corrections flow through review, not direct edits.
3. **Audit trail**: the git history of the dataset is the full record of who changed what, when, from which provenance, under which action. A workspace panel in the frontend can show the git state, as szd-htr's does.

### Metrics fall out

Because every Accept, Correct, and Add is logged with field, provenance, action, and entry type, the EQUALIS-I metrics (see [[data#equalis-metrics-planned]]) are a byproduct of curation, no separate experiment: Accept/Correct/Add ratio overall and by provenance, correction rate per extraction method, correction distribution by entry type and field, and ratio shift across iterations. This is the same relationship szd-htr has between human approvals and its CER baseline: the human verdicts are the gold that measures the machine.

## Shared curation spine

klawiter and szd-htr are, at the core, the same system: a static site over a dataset of machine-produced record drafts, with a localhost expert-correction mode that (a) persists pending edits, (b) carries a three-status review lifecycle, (c) records every edit with original value, who, when, and source, (d) surfaces a calibrated triage signal for what to check first, (e) writes corrections back through a local endpoint and uses git history as the audit trail, and (f) treats human approvals as the gold standard that measures the machine. They differ only in the unit edited (bibliographic fields vs transcription pages) and the uncertainty signal (extraction provenance and verification flags vs image-text quality signals and model consensus).

That common spine is the DIA-XAI epistemic-infrastructure thesis made concrete: a reusable expert-curation layer for a family of scholar-centred tools, not a one-off per project. The intended path is to adopt szd-htr's model into klawiter now and document the spine as this reusable pattern; extracting the shared frontend into an actual common library is deferred until a third tool needs it, to avoid premature abstraction.

## Model-pluggable extraction

The extraction and the automatic `agent_verified` check are written behind a model-agnostic boundary so a model can be swapped without touching the curation layer. The cloud frontier model (currently Gemini, step 03b) stays the default path; a locally run model is a plug-in option, built only where it adds clear value. The curation layer is indifferent to which model produced a value: the editor adjudicates the extracted value, the provenance state records the method, and the Accept/Correct ratio by provenance is exactly the measurement that would compare a frontier-cloud extraction against a local-model one on identical data. This is what lets the project carry frontier and local models on the same surface, as a demonstrable capability rather than a headline.

## Build increments

1. **Review status + action typing + session durability** (done, Session 19): the three-status review is surfaced per entry, each interaction is typed Accept/Correct/Add with a v2 edit-history record, pending edits persist in `localStorage`, and Save exports a `patchVersion: 2` document that `apply_patches.py` consumes. Verified in the browser on localhost and pinned by `tests/test_patch_contract.py`. This unlocks the EQUALIS triad.
2. **Uncertainty surface**: wire provenance classes and verify.py flags into a per-entry attention ranking and field badges, calibrated by the content spot-check.
3. **Editing scope**: extend inline editing to all adjudicable fields with the raw wiki source shown alongside for evidence.
4. **Write-back + apply step**: `apply_patches.py` (the dataset overlay, `editor` provenance, edit history, idempotent re-application from the git-tracked store) is implemented and unit-tested; what remains is the live local endpoint that lets the frontend write corrections without a manual file step.
5. **Metric read-out**: derive the EQUALIS-I ratios directly from the accumulated edit history.

Increments 1 to 3 are frontend-local and need browser verification; 4 and 5 touch the pipeline and the provenance model. The minimal next step is increment 1.

## Related

- [[about#dia-xai-connection]] — EIL-Tool 1, the mandatory deliverable this design serves
- [[about#two-eil-roles]] — developer-in-the-loop and editor-in-the-loop
- [[data#record-census]] — the completeness proof the editing surface relies on
- [[data#equalis-metrics-planned]] — the metrics the edit history produces
- [[frontend]] — the static site the editing mode extends
- szd-htr `verification-concept.md` — the three-status model, edit history, and triage signal this design adapts
