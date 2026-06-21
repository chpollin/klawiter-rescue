---
title: EIL Editing Interface
aliases: [eil-editing, in-tool editing, expert-in-the-loop editing, accept-correct-add]
tags: [design, eil, dia-xai]
created: 2026-06-21
updated: 2026-06-21
---

# EIL Editing Interface

Design for extending the in-tool editing capability so a domain expert can correct, confirm, or complete every field the pipeline cannot verify on its own, with the result saved as a durable, auditable record. This is the build-out path for EIL-Tool 1 of the DIA-XAI project. It describes the target design and the increments to get there, grounded in what `edit.js` already does today.

## Summary

The data rescue produces an extraction that is provably complete at record level (see [[data#record-census]]) but uncertain at field level: roughly half of all publisher and translator values are absent or LLM-inferred, titles fall back to page metadata, and one entry is a blanked stub. Machine extraction can flag this uncertainty but cannot resolve it; only a domain expert holds the knowledge to decide whether a value is right, wrong, or missing. The editing interface is where that judgment enters the dataset. The design rests on three commitments: the editor acts on the fields the integrity layer marks as uncertain, every action (Accept, Correct, Add) is captured as a typed, provenance-aware record, and the saved corrections form an audit trail that doubles as the EQUALIS measurement substrate.

## Current State

`edit.js` (localhost-only, gated by `App.state.isLocal && App.state.editMode`) provides the working core:

- Inline `contentEditable` editing of four provenance-tracked fields: publisher, location, translator, pageCount.
- Per-entry change tracking in `App.state.pendingEdits`, each change carrying `oldValue`, `newValue`, and the field's current `provenance` (regex / llm / missing, from `inject_provenance.py`).
- A Save action that serializes pending edits into a `patchVersion: 1` JSON document (`pageId`, `field`, `oldValue`, `newValue`, `previousProvenance`) and downloads it.
- A validation gate: `.github/workflows/validate-patch.yml` checks patch format, frontend JSON integrity, regression tests, and quality-report comparison on pull requests.

What it does not yet do: edit fields beyond the four (notably title, year, language, entry type); distinguish confirming a correct value from changing a wrong one from filling a missing one; survive a page reload without losing pending edits; or write the editor's verdict back into the dataset's provenance so a human-verified value is visibly distinct from a machine-extracted one.

## Target Design

### Editing scope

Extend editing from the four provenance fields to every field an expert can adjudicate against the entry's raw wiki source: title, year, language, publisher, location, translator, pageCount, entry type, and the relationship fields. Each editable field surfaces its raw-source context (the wiki text the value was or should have been extracted from) so the editor adjudicates against evidence, not from memory. The blanked stub (page 2979) is the limiting case: its title exists in the source page table but no content does, so the only meaningful editor action there is to confirm or supply the title.

### The three actions

Editor interactions are typed as one of three, the EQUALIS triad:

- **Accept** confirms a present value is correct. It changes no value but records the expert's endorsement, turning a machine guess into a verified fact.
- **Correct** replaces a present but wrong value. Captures old and new.
- **Add** supplies a value for a field the source contains but the pipeline left empty (a `missing`-provenance field). Distinct from Correct because it measures recall recovery, not precision repair.

The current interface captures only the Correct case implicitly. Accept and Add must become first-class, because the EQUALIS-I metrics (see [[data#equalis-metrics-planned]]) are ratios over exactly these three action types by provenance.

### The uncertainty surface

The editor should not hunt blindly through 4,751 entries; the interface ranks and marks what needs attention, driven by the integrity layer already in place:

- **Provenance badges** (regex / llm / missing) already mark each field's extraction source. `llm` and `missing` are the high-attention classes.
- **Verification flags** from `verify.py`: false positives (a value not found in the raw text) and false negatives (a value detectable in the raw text but absent from output) point the editor at probable errors.
- **Census anomalies** from `census.py`: the blanked stub, and any future record the reconciliation isolates.

Together these define a confidence ranking, so the editor's time goes to the fields most likely wrong or recoverable, not to the regex-extracted titles that are almost certainly right.

### Persistence and how it is saved

Three layers, from volatile to durable:

1. **Session durability**: mirror `App.state.pendingEdits` into `localStorage` so in-progress edits survive a reload or an accidental navigation. Today they are lost.
2. **The patch as portable audit artifact**: keep the downloadable JSON patch as the unit of exchange between editor and repository, extended to `patchVersion: 2` with `action` (accept/correct/add), `field`, `oldValue`, `newValue`, `previousProvenance`, `entryType`, `timestamp`, and an `editor` identifier. The patch is append-only evidence, never a silent in-place mutation of the dataset.
3. **Application back into the dataset**: a pipeline step (`apply_patches.py`, running after `05_to_jsonld` / `inject_provenance`) consumes accepted patches, writes the corrected values, and sets the field's provenance to a new state `editor` (or `verified` for an Accept that changed nothing). Re-running the extraction pipeline never overwrites an `editor` value silently; conflicts surface for review. This keeps the [[about#data-integrity-principle|Data Integrity Principle]] intact: corrections flow through review, not direct edits, and the dataset records who established each value.

### Traceability

Provenance gains a fourth state beyond regex / llm / missing: `editor`. After a correction round the badge on a field tells the reader not just how the machine extracted a value but that a human verified it. The patch log is the full history of who changed what, when, from what provenance, and under which action type. Because every Accept, Correct, and Add is logged with field, provenance, and entry type, the EQUALIS metrics fall out as a byproduct of curation, with no separate experiment and no time tracking: Accept/Correct/Add ratio overall and by provenance, correction rate per extraction method, correction distribution by entry type and field, and ratio shift across iterations.

## DIA-XAI Framing

This design is what makes the tool scholar-centred and expert-in-the-loop in the sense the proposal positions. Scholar-centred: the machine extraction is a proposal, the domain expert's judgment is the authority, and the interface is built around the expert's adjudication act rather than around the model's output. Expert-in-the-loop: corrections feed back into provenance and, in aggregate, signal the developer where the pipeline needs systematic improvement, closing the two interlocking loops described in [[about#two-eil-roles]]. The same surface serves frontier and local models without change, because the editor adjudicates extracted values regardless of which model produced them; the provenance state records the method, and the Accept/Correct ratio by provenance is exactly the measurement that would compare a frontier-cloud extraction against a local-model one on identical data.

## Build Increments

1. **Action typing + session durability**: add Accept/Add to the existing Correct tracking, type each interaction, and back `pendingEdits` with `localStorage`. Patch format moves to v2. Lowest risk, unlocks the EQUALIS triad.
2. **Uncertainty surface**: wire the verify.py flags and provenance classes into a per-entry attention ranking and field badges in the detail view.
3. **Editing scope**: extend inline editing to the remaining adjudicable fields with raw-source context shown alongside.
4. **Apply-back pipeline step**: `apply_patches.py` plus the `editor` provenance state and conflict handling on re-run.
5. **Metric read-out**: derive the EQUALIS-I ratios directly from the accumulated patch log.

Increments 1 to 3 are frontend-local and verifiable in the browser; 4 and 5 touch the pipeline and the provenance model. The minimal next step is increment 1.

## Related

- [[about#dia-xai-connection]] — EIL-Tool 1, the mandatory deliverable this design serves
- [[about#two-eil-roles]] — developer-in-the-loop and editor-in-the-loop
- [[data#record-census]] — the completeness proof the editing surface relies on
- [[data#equalis-metrics-planned]] — the metrics the action log produces
- [[frontend]] — the static site the editing mode extends
