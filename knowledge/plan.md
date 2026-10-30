---
title: Plan
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: active
language: en
created: 2026-10-24
updated: 2026-10-30
generated-with: Claude Code (Claude Opus 5.5)
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
template:
  name: Vorlage Plan
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/plan
related: [print-wiki-merge, governance, specification, status, journal, INDEX]
---

# Plan

This plan orders the work still to be done on the Klawiter bibliography into two milestones with their entry and exit conditions. It is the forward counterpart of the [Journal](journal.md): finished work leaves it, and the transition that finished it goes into the journal. What is built and why stands in the declarative documents, the merge model and its steps in [Merged bibliography](print-wiki-merge.md), the measurement rules there under Measurement, the interface in [Specification](specification.md), [Design](design.md), [Frontend architecture](frontend-architecture.md) and [Card workbench](design.md#card-workbench), and what the operator accepts in [Governance](governance.md). The exit conditions below point to those documents instead of restating them.

## Goal

The goal of [Merged bibliography](print-wiki-merge.md), Goal, is the criterion of done. The work reaches it in two milestones, cut at the operator's human round: everything that would change a reading or a proposal must be finished before the first review decision, because every rule change after it makes decisions stale, and everything after it rests on those decisions. Development stays local until the operator instructs a publication ([Governance](governance.md), Operator principles).

## Milestones

| Milestone | Work | Gate |
|---|---|---|
| M1 Ready for review | wiki data, print data, the second correction of the measurement design, the record desk and sitemap, knowledge and action layer | no person needed; an independent review of method, code and knowledge closes it |
| M2 Merged and accepted | the human round, the concordance measured, shared claim schema and claims file, identifiers, the reconstructed entry, interface acceptance, delivery | needs the operator, a second person where available, and Stefan Zweig Digital for delivery |

### M1 Ready for review

Entry: none. Exit: all items below done, `p14_gate.py --export` green with an empty review log, the production run and both gates green, and a fresh-context review of method, code and knowledge with its findings closed.

Wiki data true to their source passage
- Done when every verified defect class has its root-cause fix, a real-record test and an invariant over all records; every statement carries a typed producer and decisions of LLM agents are proposals; flat values no rule binds are gaps; translations are one statement per printing ([Data](data.md)).
- Still open: a second fresh-context review round finds no new defect class. The root-cause fixes of the data reach audit (damaged letters, revision dates, gaps by rule, namespace-aware redirects, the edition graph at Gate 1 algorithm 1.5, no author on structure pages) landed in 64cbaea.

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
- The operator decided on 2026-10-24 that one card view holds print objects and wiki records, replaces the wiki catalogue locally and carries the review of both sources, and that the sitemap becomes Overview, Records and Documentation ([Governance](governance.md), Operator principles).
- Increments in order: (1) Documentation joining the Data and About pages, help as a dialog, the imprint in the footer, start-page clarity, and a local page check tool that shows a PDF page beside every line and value read from it; (2) the record desk with print and wiki cards in one design; (3) the review of wiki values in the desk, where a person's decision becomes a patch that confirms the value with the producer person, which also gives the end-to-end proof of a human patch through canonical graphs, frontend and exports; (4) Explore as an arrangement of the filtered records; (5) data quality as filters and the review mode of the desk.
- Every record with bibliographic text reaches a card, including the category pages whose text remains after their category links, and a gap by rule reads differently from a gap in the source.
- Increment 2 first cut committed (cb13e6c): `docs/js/record-card.js` renders wiki and print cards, `docs/js/records.js` is the Records view, `pipeline/print_volumes/viewer/records-print.js` adapts print objects, the workbench draws through the same component, and the pipeline supplies value positions (03bb9de, [Data](data.md), Value positions). Still open in increment 2, in this order:
  1. Browser review of the first cut at 1440x900, 390x844, 320x640 and 200 percent zoom on a trial review server, by keyboard and pointer, with read screenshots, then the integrated review of both card kinds side by side for one publication; the workflow that was to run both stopped at a session restart before them. `smoke.mjs` in both modes was green before the restart and has not run since.
  2. Close the pinned coverage gaps in `tests/record_coverage_expected.json`: record `_provenance` and `@type` (head in `app.js`), `fieldEvidence` and publication `provenance` and `valueSpans` (a declared map of derived fields, critique D4), one record each without `review` and `ruleGaps`, and the values without a visible chain; then make the test assert zero instead of pins.
  3. Align the gap words of `detail.js` with the data: the pipeline writes `category-markup` and `page-title`, which `_gapOf` does not yet name.
  4. The card head lost the colour and claim noun of the review state; check it against [Frontend architecture](frontend-architecture.md), Rendering of contested statements. The facet sidebar still shows the raw type "category", and the wiki count label still says "entries" because `search_logic.test.js` pins it.
  5. Add `tests/` to the leak scope of `p14_gate.py`; `page.js` still links the public wiki; the workbench stacks at 60rem against the 64rem target and its slips do not yet draw through `RecordCard.slip`.
  6. The value positions grow `docs/data/klawiter.json` to about 21.6 MB (3.7 MB gzipped) and the publication files to about 17 MB, and since the push of 2026-10-25 the public site loads them; decide a compact form.
  7. Bring Frontend architecture, the card workbench sections of Design and Specification, the departure rows of Design and the task states of Specification to the state of increments 1 and 2. Of the departure rows, D2, D5, D7, D8, D10, D11 (reflow), D12 to D17 and D26 are met by the code of 53b9397, 8a01287 and cb13e6c and close; D3 is still open although its row names increment 1.
  8. Close the items of the UI work package of 2026-10-24 that the code does not yet meet (checked against 28e9962):
     - derive the authority sentence of Documentation (`AUTHORITY_DECISION_NOTE`, `pages.js`) from the summary of `reconciliation.json`, which holds proposals and no published link (D3);
     - open a card reached through a publication filter at its first matching publication, with the "matching" line as a link to it (D4);
     - link every evidence page of a claim to its record and line, and show the description of each reading once `reconciliation.json` carries one (D6);
     - label the page classification row as the rule-based wiki page kind, apart from the head's `pageKind`;
     - rename "Years in source" to "Years named in the source" and correct its help text, because it holds years that are no publication years;
     - in the stacked start-page table, write "Wiki: see A" in the second row of a merged wiki cell (D11, second half);
     - bring text, focus and boundary contrast, link underlines and 16px inputs to the minima of Design (D18 to D22, D25) as part of the browser review of step 1.
  9. After the operator's decision on the open question of [Specification](specification.md): apply an open place claim to a publication by its evidence (page and line within the block) in one function shared by card and export, with page 4426 as fixture, so that a differing spelling of the place is no longer missed.
  10. Done on 2026-10-30 (e6bef6f, 35f9574): producer signs with a legend per card, the source beside the values, print citations as exact address links with a stated reason when no print record carries the address, start-page counts of values with a located passage. The review of that day found what the reading card still lacks for checking; those points belong to the curation surface below, not to the reading card.
- Curation surface, prototyped as a local route `#review` on the same components and a trial log outside `data/print/review/` (operator, 2026-10-30: interfaces differ by problem type, and Klawiter's is data curation; the reading card stays calm). Its requirements, from the review of 2026-10-30 and the tool findings of the DIA-XAI repository (`knowledge/usecases.md`):
  - checkability first: a value with a located passage reads apart from one without at rest, and the page title and category line stand as source lines so their values can be checked;
  - text read into a value whose passage is ambiguous reads apart from text no value was read from, and deliberately unread text names its reason (such as the bare numbers after a See address, which may be entries or pages);
  - a mark in the source opens its value and a control leads back, Escape closes a chain and returns focus to its sign, and each sign is named by field and value;
  - a queue with progress and a count of what is unconfirmed, decisions per value (right, change, not in the source, unsure) with the producer person, and a blind mode that hides the proposal until a decision;
  - no decision of the trial log counts for the human round, which starts only after the reading rules are frozen.
  EDIT and the card workbench go into this surface once it replaces them.
- Increment 3 also restores the focus outline of `.editable-field`. Increment 4 lets the translator facet read the credits of the publication layer, from a page-level union of credited translators the pipeline writes, once the decision is recorded. Increment 5 labels the open-claim queue of data quality by entries with the claim count beside it (D9) and renames the workbench class of a card the reviewer flagged to `.is-flagged`, keeping "contested" for an open claim (U13).
- Done when the record coverage test, counting only what a reader can see, pins no field gap and no rendered artefact, every value shows its provenance chain visibly, `check_render.mjs`, `check_review.mjs` and `smoke.mjs` are green, a browser review with read screenshots at a wide and a narrow width and at 200 percent zoom has its findings closed, and the old addresses redirect.

Knowledge and action layer
- Done when the knowledge follows the Promptotyping convention (`handoff.md` as the one inbox, this plan as the one place of future work, [Specification](specification.md) and [Design](design.md) adopted after their review), README and `CLAUDE.md` route into it and name the print strand, the producer rule and one list of check commands, and a fresh-context audit finds no contradiction between documents and code.
- Still open: the three print documents take names under the naming contract of the convention, and the references to them in the files of the code identity of `p13_review.py` (`p03_records.py`, `_common.py`, `_fields.py`, `sections.json`, `p07_concordance.py`) follow. A changed byte in that closure invalidates the fixed admissible classes, so this rename runs together with the planned refreeze of the measurement base and the `p13_review.py --fix-rule` before the human round, never on its own. The comments of `pipeline/lib/editions.py` and `pipeline/lib/producers.py` still name `knowledge/production-readiness.md`, whose content [Governance](governance.md) now holds; both files enter the code hashes of the Gate 1 and Gate 2 manifests, so their comments follow with the next reviewed freeze of those manifests.

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
- Done when every record belongs to exactly one group with a stable identifier that is never reused, print addresses with their volume, the 1965 numbers and wiki page identifiers resolve as aliases to their source records, and joins and splits are recorded ([Project](project.md), How the bibliography is cited). Depends on the operator's decision on the identifier scheme.

Reconstructed entry
- Done when groups form from confirmed identity claims and the desk shows one merged reading per group with the source of every field, the deviations side by side and the open claims visible.

Interface acceptance
- Done when keyboard operation, a screen reader, 200 percent zoom and narrow widths are checked, an independent review given the research tasks of [Specification](specification.md) has its findings closed, and the operator has accepted reading, review and citation on real tasks.

Delivery
- The route is decided: TEI, projected from the canonical data, in the profile of [TEI profile](tei-profile.md) (operator for Stefan Zweig Digital, 2026-10-30). A first export of page 212 validates against `docs/schema/klawiter-tei.rng`.
- The first export is not faithful yet ([TEI profile](tei-profile.md), State of the first export). Its validation is built in this order, each fault fixed in the shared function it passes through and each check failing when the logic is wrong:
  1. The source text reproduced character for character, with every passage a `seg` that some exported value points to.
  2. Invariants over all records instead of page 212: every field of the record exported or listed as a documented exclusion, producer, passage and state of each value equal to the canonical record, internal consistency (date, extent, language), unique identifiers, sorted and deduplicated input, and no text that is not the record's own in the public export.
  3. The publication layer, one `biblStruct` per publication, and a record type for author pages and work hubs.
  4. Validation against tei_all at a pinned release beside the profile schema, and a tighter profile schema.
  5. The checks the ingest of GAMS and the stylesheets of Stefan Zweig Digital need, from the audit of their requirements.
  6. `szd-klawiter.xsl` and an RDF branch for `o:szd.klawiter`, built and tested in the local harness of Stefan Zweig Digital, then ingested into GAMS Staging by the operator.
- Done when these checks are green over all records, the profile is agreed on a sample object, and the export stands as `o:szd.klawiter` on GAMS Staging rendered by its stylesheet; the production instance follows the human round, and publishing waits for the operator.

### Release backlog of the wiki edition

These items belong to the published wiki data and wait behind M1 unless a milestone takes them up.

- Provenance end to end: one released field correction reaches canonical graphs, frontend, exports, history and reports; M1 increment 3 provides the first real correction.
- Editing per publication stays outside version 1.0, because the acceptance contract asks for propagation of a page-level correction first.
- Page 1875 keeps its six volumes in one publication until a Gate 1 segmentation decision and a field contract for volumes exist.
- The stratified semantic sample is broadened, and curation and export get browser checks with recorded device and task budgets.
- The vocabulary represents the PROV-O sidecar, a DQV quality description and the publishable profile of the LLM provenance.

### Taken over from the journal

These points stood only in the journal until its compaction on 2026-10-28. The date names the entry. Whether a point has been settled since is unchecked.

- The classes of the fifth print review not yet fixed, chief among them language headings glued to entries in Addendum II, lost hosts, forename-first host authors and the letter editions of main-volume K items (2026-10-24).
- Citations name contribution translators and page-level anchors per publication (2026-09-22).
- A read-only triage list of the titles recorded as deleted in the wiki, as a possible separate work package (2026-09-22).
- The neighbourhood check of the publishable PROV profile `llmprov` (2026-08-21).

## Program from 2026-10-30

The operator set on 2026-10-30 that the bibliography reaches Stefan Zweig Digital as TEI and is rendered there in its design, and that Klawiter's interface is a curation tool. The work runs as six milestones across four places: this repository (export, validation, curation surface), the data repository of Stefan Zweig Digital (`SZD`, the holding under `data/Klawiter/` and the local harness on the branch `gams-www-split` of the work tree `SZD-split`), the presentation repository of Stefan Zweig Digital (`gams-www`, local clone `ZIMLAB/szd`, the stylesheets) and the vault (project state, the Promptotyping case study and the DIA-XAI proposal as statement lists). M1 and M2 above keep their place; D1 to D4 lead to the delivery, C1 to the curation surface, and the human round of M2 precedes production.

| Milestone | Work | Verified by | Accepted by the operator |
|---|---|---|---|
| D1 Faithful export | source text character for character, review states, passages, producers, print records out of `sourceDesc`, TEI conformance; invariants over all records instead of page 212 | invariant tests over all records, tei_all at a pinned release, profile schema; a fresh agent whose hand mutations must all fail | no acceptance needed; the operator decides the profile questions it raises |
| D2 Complete model | one `biblStruct` per publication, author pages and work hubs as links to the work index and person index of Stefan Zweig Digital, the fields not yet exported | the same invariants extended, every field exported or a documented exclusion | three sample objects (a single publication, a page with several, a work hub) |
| D3 Page of Stefan Zweig Digital, local | `szd-klawiter.xsl`, the RDF branch for `o:szd.klawiter`, the navigation entry, the holding under `data/Klawiter/` | the harness of Stefan Zweig Digital (smoke, golden, RDF structure), screenshots in both languages, an independent interface review | none locally; Stefan Zweig Digital is accepted on staging only |
| D4 Staging | push of `gams-www`, sync of the mirror, ingest of `o:szd.klawiter` by the operator through Cirilo, stylesheet reference | read-only checks of the staging data streams and the RDF, rendered examples before and after | the rendered pages on GAMS Staging, in both languages |
| C1 Curation surface prototype | local route `#review` with queue, checkability first, decisions per value, trial log (see One record desk) | Node tests, browser screenshots, an independent review against the reviewer tasks | the operator tries it on real records |
| P Production | after the human round of M2 and the identifier scheme | the D1–D4 checks on the reviewed data | the operator instructs the production ingest |

Each milestone closes with a statement list for the Promptotyping case study and the DIA-XAI proposal, which the operator accepts or rejects; nothing enters the paper or the proposal text without that acceptance.

### Working mode

The operator stays in the loop at the points that only the operator can decide, and the coordinator settles the rest by its own research before asking:

- The coordinator decides and reports: code, tests, schema, export fixes and reversible technical choices, each with the principle it rests on.
- The coordinator finds out by research before asking: conventions of Stefan Zweig Digital and GAMS from both repositories and the vault, TEI from the Guidelines, the state of the data from the reports. Subagents run these in parallel, read-only, and their findings count only after a check against the files.
- The operator is asked, conceptually and with the context needed: domain readings (such as a series in a source entry or a numbering of print addresses), rights, identifiers, the place of Klawiter in the navigation of Stefan Zweig Digital, Cirilo and GAMS operations, which the operator knows from practice and which are asked early, pushes and publication, and every statement for the paper and the proposal.
- Visual acceptance of Stefan Zweig Digital happens on GAMS Staging, which needs the operator's VPN; until then everything is built and tested locally.



Snapshot of 2026-10-24.

| Milestone or item | Status | Notes |
|---|---|---|
| Wiki data true to their source passage | in progress | proposals, gaps and translation statements (71a0fe0); section mentions typed and the coverage test made honest (217acef); revision dates, damaged letters, reader-form values, gaps by rule, namespace-aware redirects with a report of the broken ones, edition graph at Gate 1 algorithm 1.5 and no author on structure pages (64cbaea); the second fresh-context review round is open |
| Print data ready for review | completed | 7147b94: reading gaps closed, containment predicate, named second field, overlap report `p07b_overlap.py`, p12 writes data only; admissible classes refixed without rehash, remap or redrawn sample |
| Measurement design corrected | completed | 5db70c1 |
| Measurement design, second correction | in progress | decision rule at zero errors, agreement coefficients, anchoring, seeded order, hidden repeats and reporting fields implemented; protocol in the review mode, its pin in the gate and the benchmark order open |
| Reviewable workbench | completed | fffcb29 with the reviewer filter of the review server |
| Record desk and sitemap | in progress | increment 1 committed (53b9397: Documentation, help dialog, footer imprint, start-page labels, page check tool); increment 2 first cut committed (cb13e6c) with the open steps listed under One record desk; the coverage test counts only what a reader sees (217acef); Frontend architecture and the card workbench sections of Design and Specification describe the state before increment 1 until the knowledge pass |
| Knowledge and action layer | in progress | unified along the Promptotyping templates on 2026-10-28: dated reviews and evaluations under `snapshots/`, INDEX with responsibility table and glossary, Project, Governance, Pipeline and Frontend architecture, the card workbench in Specification and Design; the print documents keep their names until the refreeze; handoff and plan created; README and `CLAUDE.md` route into them, name the producer rule and the print strand, and testing.md holds the one list of check commands (c63ad3d); [Specification](specification.md) and [Design](design.md) brought to the record desk and the sitemap after their reviews, linked from the index, still drafts until the operator adopts the tasks; [Print volumes](print-volumes.md) split into the volumes as domain and [Print pipeline](print-pipeline.md) |
| M2 | pending | entry: M1 |

## Tracks

The operator set on 2026-10-23 that the whole project advances together: the merged bibliography, the correctness of the published wiki data, the interface, the blog post, the DIA-XAI follow-up proposal and the vault knowledge, each tested, verified and reviewed critically before it counts, with milestones planned and reported. Each track has one owner and one plan.

| Track | Owner | Plan and milestones | Review before a milestone closes |
|---|---|---|---|
| Merged bibliography (print strand) | research coordinator | M1 and M2 above | independent agent review of method, code and document |
| Published wiki data | research coordinator | Wiki data true to their source passage; [Status](status.md) | full gate of CLAUDE.md, invariants over all records, fresh-context reviews of data fidelity, interface and tests after each fix batch |
| Interface | research coordinator | One record desk and the sitemap; [Card workbench](design.md#card-workbench); [Frontend architecture](frontend-architecture.md) | tests, record coverage test and read screenshots; a fresh-context review of the interface before a milestone closes |
| Blog post | research coordinator drafts, operator deploys | drafted outside the repository, claims checked against it | claim check against the artefacts; fresh-context review of the text |
| DIA-XAI proposal | sessions of the dia-xai repository, operator decides | kept in the dia-xai repository; since 2026-10-23 the operator's team draft "Grounds for Use" is the basis | reviews there; this repository supplies only evidenced review episodes |
| Vault knowledge | a session started in the vault | handoff list prepared by the coordinator; repository sessions read the vault, never write it | vault conventions and audit |

The coordinator reports to the operator as a short presentation per milestone reached and on request, with result, meaning, risks and the decisions needed.

## Open decisions and dependencies

- The operator's acceptances and decisions are listed in [Governance](governance.md), What the operator accepts. Before M2 the operator decides the unit of a group and the provenance model of claims (who asserts and by what means, apart from who decides), and the identifier scheme.
- Every change of a reading rule or a proposal comes before the first review decision of the human round.
- The shared claim schema follows the wiki data batch, because both touch the reconciliation layer.

## Deviations

The order changes only under the operator principles of [Governance](governance.md) or on the operator's instruction, and the gates, the leak check and the rule that only a person or an exact rule confirms hold in any order. A changed assumption goes into the document that owns it, and the journal records the correction.
