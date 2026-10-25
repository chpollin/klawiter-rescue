---
title: Plan
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: active
language: en
created: 2026-10-24
updated: 2026-10-24
generated-with: Claude Code (Claude Opus 5.5)
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
template:
  name: Vorlage Plan
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/plan
related: [print-wiki-merge, production-readiness, specification, status, journal, index]
---

# Plan

This plan orders the work still to be done on the Klawiter bibliography into two milestones with their entry and exit conditions. It is the forward counterpart of the [Journal](journal.md): finished work leaves it, and the transition that finished it goes into the journal. What is built and why stands in the declarative documents, the merge model and its steps in [Merged bibliography](print-wiki-merge.md), the measurement rules there under Measurement, the interface in [Specification](specification.md), [Design](design.md), [Frontend](frontend.md) and [Print viewer](print-viewer.md), and what the operator accepts in [Production readiness](production-readiness.md). The exit conditions below point to those documents instead of restating them.

## Goal

The goal of [Merged bibliography](print-wiki-merge.md), Goal, is the criterion of done. The work reaches it in two milestones, cut at the operator's human round: everything that would change a reading or a proposal must be finished before the first review decision, because every rule change after it makes decisions stale, and everything after it rests on those decisions. Development stays local until the operator instructs a publication ([Production readiness](production-readiness.md), Operator principles).

## Milestones

| Milestone | Work | Gate |
|---|---|---|
| M1 Ready for review | wiki data, print data, the second correction of the measurement design, the record desk and sitemap, knowledge and action layer | no person needed; an independent review of method, code and knowledge closes it |
| M2 Merged and accepted | the human round, the concordance measured, shared claim schema and claims file, identifiers, the reconstructed entry, interface acceptance, delivery | needs the operator, a second person where available, and Stefan Zweig Digital for delivery |

### M1 Ready for review

Entry: none. Exit: all items below done, `p14_gate.py --export` green with an empty review log, the production run and both gates green, and a fresh-context review of method, code and knowledge with its findings closed.

Wiki data true to their source passage
- Done when every verified defect class has its root-cause fix, a real-record test and an invariant over all records; every statement carries a typed producer and decisions of LLM agents are proposals; flat values no rule binds are gaps; translations are one statement per printing ([Data](data.md)).
- Still open: the values that keep one damaged letter after the encoding repair become gaps by rule; the first and last revision of each wiki page enter the record as a deterministic rule over the dump's revision table, so that a page first recorded after Addendum II closed in August 2009 is datable as wiki-only; a value the binding rule emptied carries a provenance of its own and is no longer counted as a source gap or a false negative; redirects resolve namespace-aware, and a redirect whose target no current page carries becomes an open item with its kind and its own page title; the edition graph reads a place as a place in a single imprint, carries values in reader form and no longer segments year headers followed by a page locator as editions; category and infrastructure pages carry no author; a second fresh-context review round finds no new defect class.

Print data ready for review
- Done when the reading gaps of [Print pipeline](print-pipeline.md), Known reading gaps, that a rule can close are closed, a match to a contents line carries a containment predicate, the agreeing second field is named by its field, an overlap report states per volume and section what exists only in print, in both or only in the wiki, and p12 writes data only.
- Then the measurement base is frozen again: admissible classes fixed anew (`p13_review.py --fix-rule`), changed fingerprints recorded as rehash entries with their reason, moved identifiers as remap entries, no sample redrawn.

Measurement design, second correction
- Done when the points of [Merged bibliography](print-wiki-merge.md), Measurement, that the literature review of 2026-10-24 found missing are implemented: a decision rule that holds at zero observed errors with a minimum number of objects per class and a minimum sample derived from threshold and Holm level; Krippendorff's alpha with specific agreement; the second-reviewer subset blind to the proposals or reported as agreement under proposals, with the operator's double role named; the anchoring effect measured; the order inside each phase randomised; a hidden repeat set; reporting along GRRAS and GUILD.
- Entry: the print data are frozen again, because both change `pipeline/print_volumes/`.
- Before the human round, run `p13_review.py --fix-rule` again, because every later change of code in the hashed closure invalidates the fixed classes.
- Still open: the review mode of the desk presents each reviewer's queue in the order of `review-protocol.json`, hides a reviewer's earlier decision on a repeat showing, posts it as a repeat and never marks it as one; `p14_gate.py` pins the protocol among the frozen samples; the disagreements of the segmentation benchmark are shown in a seeded order.

Reviewable workbench
- Reached on 2026-10-24 (fffcb29), see the status tracker.

One record desk and the sitemap
- The operator decided on 2026-10-24 that one card view holds print objects and wiki records, replaces the wiki catalogue locally and carries the review of both sources, and that the sitemap becomes Overview, Records and Documentation ([Production readiness](production-readiness.md), Operator principles).
- Increments in order: (1) Documentation joining the Data and About pages, help as a dialog, the imprint in the footer, start-page clarity, and a local page check tool that shows a PDF page beside every line and value read from it; (2) the record desk with print and wiki cards in one design; (3) the review of wiki values in the desk, where a person's decision becomes a patch that confirms the value with the producer person, which also gives the end-to-end proof of a human patch through canonical graphs, frontend and exports; (4) Explore as an arrangement of the filtered records; (5) data quality as filters and the review mode of the desk.
- Every record with bibliographic text reaches a card, including the category pages whose text remains after their category links, and a gap by rule reads differently from a gap in the source.
- Increment 2 first cut committed (cb13e6c): `docs/js/record-card.js` renders wiki and print cards, `docs/js/records.js` is the Records view, `pipeline/print_volumes/viewer/records-print.js` adapts print objects, the workbench draws through the same component, and the pipeline supplies value positions (03bb9de, [Data](data.md), Value positions). Still open in increment 2, in this order:
  1. Browser review of the first cut at 1440x900, 390x844, 320x640 and 200 percent zoom on a trial review server, by keyboard and pointer, with read screenshots, then the integrated review of both card kinds side by side for one publication; the workflow that was to run both stopped at a session restart before them. `smoke.mjs` in both modes was green before the restart and has not run since.
  2. Close the pinned coverage gaps in `tests/record_coverage_expected.json`: record `_provenance` and `@type` (head in `app.js`), `fieldEvidence` and publication `provenance` and `valueSpans` (a declared map of derived fields, critique D4), one record each without `review` and `ruleGaps`, and the values without a visible chain; then make the test assert zero instead of pins.
  3. Align the gap words of `detail.js` with the data: the pipeline writes `category-markup` and `page-title`, which `_gapOf` does not yet name.
  4. The card head lost the colour and claim noun of the review state; check it against [Frontend](frontend.md), Rendering of contested statements. The facet sidebar still shows the raw type "category", and the wiki count label still says "entries" because `search_logic.test.js` pins it.
  5. Add `tests/` to the leak scope of `p14_gate.py`; `page.js` still links the public wiki; the workbench stacks at 60rem against the 64rem target and its slips do not yet draw through `RecordCard.slip`.
  6. The value positions grow `docs/data/klawiter.json` to about 21.6 MB and the publication files to about 13.4 MB; decide a compact form before any push of `docs/` to the public site.
  7. Bring Frontend, Print viewer, the departure rows of Design and the task states of Specification to the state of increments 1 and 2.
- Done when the record coverage test, counting only what a reader can see, pins no field gap and no rendered artefact, every value shows its provenance chain visibly, `check_render.mjs`, `check_review.mjs` and `smoke.mjs` are green, a browser review with read screenshots at a wide and a narrow width and at 200 percent zoom has its findings closed, and the old addresses redirect.

Knowledge and action layer
- Done when the knowledge follows the Promptotyping convention (`handoff.md` as the one inbox, this plan as the one place of future work, [Specification](specification.md) and [Design](design.md) adopted after their review), README and `CLAUDE.md` route into it and name the print strand, the producer rule and one list of check commands, and a fresh-context audit finds no contradiction between documents and code.

### M2 Merged and accepted

Entry: M1 done.

Human round
- The operator decides the blind sheets, the claim sheet, the review sample with its hard stratum and the disagreements of the segmentation benchmark in the order of [Merged bibliography](print-wiki-merge.md), Measurement, and the wiki values chosen for review in the record desk.
- Done when the report of `p13_review.py` gives field precision and recall, the precision of both concordance routes per volume and the anchoring effect, each labelled as acceptance by one reviewer until a second person decides the marked subset.

Concordance measured
- Done when the concordance runs as a pipeline stage under the shared claim schema, its recall on silver pairs and its precision from the human round are reported per route and volume, and the overlap report is reproducible.

Shared claim schema and claims file
- Done when concordance and reconciliation claims share one schema keyed by claim, with subject, predicate, object, evidence selector and hash, typed producer, state and decision chain, the existing gate artifacts rebuild under it identically or with a reasoned difference, and the text-free file of print addresses and evidenced claims is built and checked locally under `data/print/`; it joins the production run only with the operator's release.

Identifiers
- Done when every record belongs to exactly one group with a stable identifier that is never reused, print addresses with their volume, the 1965 numbers and wiki page identifiers resolve as aliases to their source records, and joins and splits are recorded ([About](about.md), How the bibliography is cited). Depends on the operator's decision on the identifier scheme.

Reconstructed entry
- Done when groups form from confirmed identity claims and the desk shows one merged reading per group with the source of every field, the deviations side by side and the open claims visible.

Interface acceptance
- Done when keyboard operation, a screen reader, 200 percent zoom and narrow widths are checked, an independent review given the research tasks of [Specification](specification.md) has its findings closed, and the operator has accepted reading, review and citation on real tasks.

Delivery
- Done when Stefan Zweig Digital has decided on the sample object between the two delivery routes of [Merged bibliography](print-wiki-merge.md), Merged bibliography and delivery, and the delivery is built locally; publishing it waits for the operator.

### Release backlog of the wiki edition

These items belong to the published wiki data and wait behind M1 unless a milestone takes them up.

- Provenance end to end: one released field correction reaches canonical graphs, frontend, exports, history and reports; M1 increment 3 provides the first real correction.
- Editing per publication stays outside version 1.0, because the acceptance contract asks for propagation of a page-level correction first.
- Page 1875 keeps its six volumes in one publication until a Gate 1 segmentation decision and a field contract for volumes exist.
- The stratified semantic sample is broadened, and curation and export get browser checks with recorded device and task budgets.
- The vocabulary represents the PROV-O sidecar, a DQV quality description and the publishable profile of the LLM provenance.

## Status tracker

Snapshot of 2026-10-24.

| Milestone or item | Status | Notes |
|---|---|---|
| Wiki data true to their source passage | in progress | proposals, gaps and translation statements (71a0fe0); section mentions typed and the coverage test made honest (217acef); revision dates, damaged letters, reader-form values, gaps by rule, namespace-aware redirects with a report of the broken ones, edition graph at Gate 1 algorithm 1.5 and no author on structure pages (64cbaea); the second fresh-context review round is open |
| Print data ready for review | completed | 7147b94: reading gaps closed, containment predicate, named second field, overlap report `p07b_overlap.py`, p12 writes data only; admissible classes refixed without rehash, remap or redrawn sample |
| Measurement design corrected | completed | 5db70c1 |
| Measurement design, second correction | in progress | decision rule at zero errors, agreement coefficients, anchoring, seeded order, hidden repeats and reporting fields implemented; protocol in the review mode, its pin in the gate and the benchmark order open |
| Reviewable workbench | completed | fffcb29 with the reviewer filter of the review server |
| Record desk and sitemap | in progress | increment 1 committed (53b9397: Documentation, help dialog, footer imprint, start-page labels, page check tool); increment 2 first cut committed (cb13e6c) with the open steps listed under One record desk; the coverage test counts only what a reader sees (217acef); Frontend and Print viewer describe the state before increment 1 until the knowledge pass |
| Knowledge and action layer | in progress | handoff and plan created; README and `CLAUDE.md` route into them, name the producer rule and the print strand, and testing.md holds the one list of check commands (c63ad3d); [Specification](specification.md) and [Design](design.md) brought to the record desk and the sitemap after their reviews, linked from the index, still drafts until the operator adopts the tasks; [Print volumes](print-volumes.md) split into the volumes as domain and [Print pipeline](print-pipeline.md) |
| M2 | pending | entry: M1 |

## Open decisions and dependencies

- The operator's acceptances and decisions are listed in [Production readiness](production-readiness.md), What the operator accepts. Before M2 the operator decides the unit of a group and the provenance model of claims (who asserts and by what means, apart from who decides), and the identifier scheme.
- Every change of a reading rule or a proposal comes before the first review decision of the human round.
- The shared claim schema follows the wiki data batch, because both touch the reconciliation layer.

## Deviations

The order changes only under the operator principles of [Production readiness](production-readiness.md) or on the operator's instruction, and the gates, the leak check and the rule that only a person or an exact rule confirms hold in any order. A changed assumption goes into the document that owns it, and the journal records the correction.
