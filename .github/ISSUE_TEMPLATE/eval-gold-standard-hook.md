---
name: "Evaluation hook: gold-standard hook"
about: Attach reference answers with a required checking depth per item class
title: "[antrag-eval] Gold-standard hook for <item class>"
labels: antrag-eval
---

## Proposal status

This template proposes additional evaluation work. It does not describe an implemented feature or an approved release requirement. See [current status](../../knowledge/status.md) and [acceptance scope](../../knowledge/production-readiness.md).

## What this issue is for

An entry marked `approved` records released field decisions; it is not automatically a complete, independently verified reference answer. This hook asks for the attachment point that lets a reference answer be bound to an item together with the checking depth that item class requires, fixed in advance rather than chosen per case:

- the reference answer per field, with its source (raw wiki text, print version, authority record)
- the item class it belongs to (single-edition page, multi-edition page, redirect, blanked stub, and so on)
- the required checking depth for that class, declared before the checking starts

Criterion-independent: the hook stores reference and required depth, it computes no agreement figure.

## Artefacts this touches

- `tests/wiki_ground_truth.json` — the existing wiki-verified reference fixture
- `pipeline/apply_patches.py`, `data/corrections/` — the path an approved entry takes
- `knowledge/production-readiness.md` — gold standard as the measurable building block
- `knowledge/testing.md` — field-level error classes the item classes build on

## Open before implementation

- Whether the reference lives with the fixture, with the correction store, or in its own file
- How the work and edition levels are counted separately using the existing header-selected segmentation, including its uncovered compound pages
