---
name: "Evaluation hook: provenance export"
about: Export the production, decision and verification layers per item
title: "[antrag-eval] Provenance export for <scope>"
labels: antrag-eval
---

## Proposal status

This template proposes additional evaluation work. It does not describe an implemented feature or an approved release requirement. See [current status](../../knowledge/status.md) and [acceptance scope](../../knowledge/production-readiness.md).

## What this issue is for

The repository holds provenance in two shapes: the per-field short form in the frontend JSON (`regex` / `llm` / `missing` / `editor`) and the correction history in the patch store. This hook asks for one export that carries all three layers per item:

- **production** — how the value was produced (rule-based extraction, LLM gap-fill, or not extracted), including the model and prompt identity where an LLM produced it
- **decision** — which step selected the value that shipped (merge rule, normalization rule, editor overlay)
- **verification** — what checked it and how (automatic verification flags, census reconciliation, human confirmation), keeping machine and human checks distinguishable

Criterion-independent: the export describes the layers, it derives no quality measure from them.

## Artefacts this touches

- `pipeline/inject_provenance.py` — per-field production labels
- `pipeline/build_triage.py`, `docs/data/triage.json` — verification flags per entry
- `pipeline/apply_patches.py` — `editor` label, `review` block, `edit_history`
- `knowledge/data.md` — current provenance layers and the canonical propagation gap

## Open before implementation

- Whether the export is a sidecar graph or a flat per-item record
- Which terms come from PROV-O and EARL before anything new is minted
