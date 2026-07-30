---
name: "Evaluation hook: four-tuple protocol export"
about: Export editing episodes as the four-tuple the verification proposal evaluates on
title: "[antrag-eval] Four-tuple protocol export for <scope>"
labels: antrag-eval
---

## What this issue is for

The editing surface already logs typed episodes (Accept / Correct / Add) with field, previous provenance and entry type. This hook asks for an export that turns those episodes into the four-tuple the evaluation reads:

1. initial expert judgment (what the editor held before seeing the machine value, where the surface can capture it)
2. AI suggestion (the machine value with its production provenance)
3. final decision (the value the entry carries after the episode)
4. reference answer, where one exists for the item

Criterion-independent: the export carries the tuple, no score, no rate, no ranking derived from it.

## Artefacts this touches

- `docs/js/edit.js` — episode capture and the exported patch document
- `pipeline/apply_patches.py` — `edit_history` records the overlay writes back
- `data/corrections/` — the patch store whose git history is the audit trail
- `knowledge/production-readiness.md` — EIL increment 5, "Protocol-Read-out"

## Open before implementation

- Whether an initial expert judgment can be captured without turning the surface into an experiment
- Where a tuple with no reference answer is marked as such rather than left empty
