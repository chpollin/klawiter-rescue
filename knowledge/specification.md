---
title: Specification
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: draft
language: en
created: 2026-10-24
updated: 2026-10-24
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Opus 5.5)
template:
  name: Vorlage Specification
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/specification
topics: ["[[Requirements Engineering]]", "[[User Stories]]", "[[Scholar-Centered Design]]"]
related: [design, frontend, print-viewer, print-wiki-merge, production-readiness, plan, data, about]
---

# Specification

The Klawiter bibliography is research data for Zweig research and Stefan Zweig Digital, and its interface counts as carried when the people who use it can complete their research and review tasks in it. Its criterion of done is the Goal of [Merged bibliography](print-wiki-merge.md#goal), and what a person must accept, with the moment it becomes ready, stands in [Production readiness](production-readiness.md#what-the-operator-accepts). The user groups change rarely, the research tasks are proposals until the operator adopts them, and each acceptance criterion names the source it rests on. Visual rules stand in [Design](design.md), the behaviour of the published reader in [Interface and Curation](frontend.md), the behaviour of the local card workbench in [Print viewer](print-viewer.md), the meaning of every field in [Data and model](data.md), and the order of the remaining work in [Plan](plan.md).

Development is local. The print strand, the concordance and the merge are built and checked under `data/print/`, and nothing of them is published until the operator instructs it ([Production readiness](production-readiness.md#operator-principles)). The published reader stays as it is meanwhile, so a criterion it misses is closed in the local surface that succeeds it and reaches the public site only with the operator's instruction. Every criterion below that concerns print data is therefore checked on the local surfaces, and no criterion requires publishing print data.

## Basis of the tasks

The knowledge does not yet fix the research tasks. [Merged bibliography](print-wiki-merge.md#open-questions) leaves to the operator and Stefan Zweig Digital which research tasks the merged bibliography must support, and [Production readiness](production-readiness.md#what-the-operator-accepts) lists the trial tasks as an open acceptance item. A task leaves the state of a proposal when the operator adopts it there.

The tasks rest on bases of different weight, and the Basis column of the task table names the one each task rests on.

- The operator's requirements carry the tasks of the desk, the page check tool and data quality. They are the workbench requirements of [Print viewer](print-viewer.md#requirements), the principle "An interface people like working in" and the decision of 2026-10-24 for one record desk, the three-part sitemap and a local page check tool ([Production readiness](production-readiness.md#operator-principles), [Plan](plan.md#m1-ready-for-review)).
- The measurement design of 2026-10-24 with blind second review and adjudication carries T7. The main instance decided it under the operator principles, and it is revisable ([Merged bibliography](print-wiki-merge.md#measurement)).
- Cases 1 to 4 of the [owner worksheet](evaluations/2026-09-05/owner-evaluation.md) were accepted by the main instance under delegation and not by the operator, and case 5, the operator's own research task, was withdrawn on 2026-09-23 ([Status](status.md)). Tasks derived from them are assumptions, since no research episode has been observed.
- What [Data and model](data.md), [Project Context](about.md#how-the-bibliography-is-cited) and the merge model say the product must do carries the remaining tasks, without a stated user task behind them.

## User groups

### G1 Zweig researchers

Literary scholars working on Zweig's works and life. [Production readiness](production-readiness.md#operator-principles) names the product as research data for Zweig research, and [Merged bibliography](print-wiki-merge.md#how-results-are-checked) sends the complex checks, edition against later printing or which translation is meant, to Zweig specialists alone. They need to find the editions of a work and tell edition, later printing and reprint apart, which the record model distinguishes as relations between objects ([Merged bibliography](print-wiki-merge.md#record-model), Object). They cite with a locator where they locate at all, by page, by print address or by both, and a bare running number is ambiguous without its edition ([Project Context](about.md#how-the-bibliography-is-cited)). They need each value with its passage, producer and state before they rely on it (Goal, second point). The vault note on scholar-centred design suggests that they alternate between looking up a known item and investigating a question, which no observed episode confirms yet.

### G2 Translation and reception researchers

The project overview in the operator's vault (`Projects/szd/Project Overview Klawiter-Rescue.md`) names questions of literary, publishing and translation history on Zweig's worldwide reception as what the graph makes answerable. Worksheet cases 1 to 4 concern translators of contributions, two editions on one page, a German book beside an Arabic article and a name variant. [Data and model](data.md#publication-fields) requires an interface to read `credits` and `contributions[].credits` before it says anything about the translators of a publication. This group needs the translations of a work by language with their translators, distributions over time and place, and name variants kept without an asserted identity.

### G3 Editors of Stefan Zweig Digital

They take over Klawiter as an object of its own and link it to their curated work index, which is linked and never extended ([Merged bibliography](print-wiki-merge.md#principles)). They need one agreed sample object, JSON-LD with provenance per value, work links with evidence and state, and a stable group identifier ([Merged bibliography](print-wiki-merge.md#merged-bibliography-and-delivery)). The data architecture note in the operator's vault adds reconciliation at publication level through `#entry=<id>&pub=<n>`, explicit contribution roles and an Expression level for translations reprinted across editions. The Gate 1 ratification of 2026-07-19, recorded in the vault log of the research coordination (`Projects/Forschungsleitstelle/Forschungsleitstelle Log.md`), names that level as a third depth decision through `schema:translationOfWork`, which `pipeline/lib/editions.py` emits. The repository knowledge does not record it yet.

### G4 The antiquarian trade and librarians

The trade cites print addresses systematically, often beside the running number of the bibliography of 1965 ([Project Context](about.md#how-the-bibliography-is-cited)). It needs to resolve such a citation to a record and to identify an item in hand by edition statement, imprint in source wording and extent notation, which [Data and model](data.md#publication-fields) keeps. Librarians appear in no source of the knowledge, so their inclusion is a proposal for the operator, with needs inferred from those of the trade.

### G5 Reviewers and the adjudicator

The first reviewer decides values on the record desk, a second reviewer decides a marked subset blind to the first, and an adjudicator settles their disagreements ([Merged bibliography](print-wiki-merge.md#measurement)). Since the operator's decision of 2026-10-24 the desk carries the review of print values and of wiki values alike. Reviewers need the source text beside each value with its passages marked, keys that act only on the active card, a blind mode and a low cost per decision, which the principle "An interface people like working in" makes the measure of the interface. Checks are assigned by the kind of task, deterministic, simple or complex ([Merged bibliography](print-wiki-merge.md#how-results-are-checked)).

### Further roles

The operator accepts the interface by reading, reviewing and citing on the operator's own tasks ([Production readiness](production-readiness.md#what-the-operator-accepts), Interface on real tasks), and so stands in for G1 until specialists join a session. The vault project overview names a developer in the loop who reads aggregated correction patterns and invariant breaks to sharpen parser rules. How that role uses the desk is an assumption, which T20 and T19 make concrete.

## Research tasks

| ID | Task | Groups | Surface | Data | Basis |
|---|---|---|---|---|---|
| T1 | All translations of one work into one language, with their translators | G2, G1 | Records with language and translator filters, publication blocks | `originalTitle`, `languageCode`, `credits`, `contributions[].credits`, translation statements | worksheet case 2 |
| T2 | Cite one edition with a stable address and, where one exists, its print address | G1, G4 | publication block, BibTeX and RIS export, permalink | publication `id`, `#entry=…&pub=…`, imprint, extent, credits | worksheet case 1 |
| T3 | Resolve a citation found in research or the trade | G4, G1 | search, Overview section table, record desk | `printAddressCitations`, print records (local) | knowledge |
| T4 | See where print and wiki disagree on a field | G1, G5 | record desk (local) | concordance claims, field conflicts, passages on both sides | knowledge |
| T5 | Follow a value to its passage, record, source file and producer | all | open card, provenance chain | `sourceSlice`, `textStart`/`textEnd`, provenance class, `_meta` producers | Goal, second point |
| T6 | Decide a print value on the record desk | G5 | record desk, active card | print values with spans, entry text, decision log | operator requirements |
| T7 | Review blind as second reviewer, and adjudicate a disagreement | G5 | record desk with reviewer filter | decision log by reviewer, marked subset | main instance |
| T8 | Tell which publication each field describes on a page with several | G1, G2, G4 | card head, publication blocks, result line | publication layer, page-level arrays | worksheet cases 1 and 3 |
| T9 | See what has been decided, by whom and with what scope | all | state and producer words, Documentation | `review.scope`, decider, typed producer | operator principles |
| T10 | Inspect an open claim and see what it leaves open | G1, G3 | claim block, contested filter | claim ID, evidence with hash, interpretations, review history | `CLAUDE.md`, Data Integrity |
| T11 | Survey reception across decades, languages and places | G2 | Explore as an arrangement of the filtered records | publication-layer axes | knowledge |
| T12 | Find what exists only in print, only in the wiki or in both, by section | G1, G3 | Overview section table, source filters of the desk (local) | print structure counts, overlap report (local) | knowledge |
| T13 | Follow the compiler's references and the wiki's See-also | G1 | links in the source text, desk references (local) | `seeAlso`, redirect map, `printAddressCitations`, typed print references | knowledge |
| T14 | Identify an item in hand against the bibliography | G4, G1 | search, publication block, source text | `editionStatement`, imprint in source wording, `extent.raw`, series | knowledge |
| T15 | Export the citations of a filtered set for a reference list | G1, G2 | batch export of the filtered records | per-page publication files | knowledge |
| T16 | Link a publication to a work of the Stefan Zweig Digital work index and take it over as a sample object | G3 | work link on the card, JSON-LD export | work index candidates, decisions, `publishable-links.json`, contested claims | knowledge |
| T17 | Read, review and cite on the operator's own tasks | operator | all surfaces | all of the above | worksheet case 5 |
| T18 | Decide a wiki value on the record desk | G5, operator | record desk, active wiki card | flat and publication values, source text, patch store | operator decision |
| T19 | Check what was read from one print page | G5, developer | page check tool (local) | print lines and values with their PDF page | operator decision |
| T20 | Work through one data quality class | G5, developer | filter and review mode of the desk | completeness, evidence, LLM-derived and claim classes | operator decision |

### T1 Translations of one work into one language

- Starting from the work's title, one route yields a list restricted to one language.
- Every item names its translators from `credits` and `contributions[].credits`. Page 1891 shows the translators credited under its contributions.
- The count shown equals the length of the list.

Sources are [Data and model](data.md#publication-fields), worksheet case 2, and the translation statements and original-title links of [Merged bibliography](print-wiki-merge.md#claims). The committed reader fails the second criterion on page 4426, whose source credits a translator that neither card nor citation carries. The translator filter and the translator flow of Explore read only the flat `translator` (`translatorKeys` in `docs/js/utils.js`), and whether they must read credits is an open question below. Original titles are searchable and do not yet link to a work, which the work links of [Plan](plan.md#m2-merged-and-accepted) take up.

### T2 Cite one edition

- The export of the 1960 edition on page 1800 carries `#entry=1800&pub=1800-1960-a`, its own imprint and `383/(1)p.` in the note, and the export of the 1947 edition on the same page differs in all three.
- An open place claim on the cited publication is noted in the citation under the rule of [Interface and Curation](frontend.md#export).
- A print address appears only as a cited address and never as an identity.
- Once groups exist, the citation carries the group identifier and the aliases the operator decides on.

Sources are [Project Context](about.md#how-the-bibliography-is-cited), worksheet case 1 and [Interface and Curation](frontend.md#export). The committed exports meet the first three criteria. Page 4426 carries no contested note, because its imprint spells the place differently from the claim's subject and the documented rule applies a claim only on equality, which the open questions take up. Groups and aliases wait for the identifier decision ([Plan](plan.md#m2-merged-and-accepted), Identifiers).

### T3 Resolve a citation

- A query for a print address returns the wiki pages whose text cites it, each in the state `cites`.
- On the local desk the same query also returns the print record with its PDF page and every concordance candidate in the state `proposed`.
- A bare running number reads as ambiguous between the bibliography of 1965 and the volumes of 1991 until its edition is given.

Sources are [Project Context](about.md#how-the-bibliography-is-cited) and [Data and model](data.md#cited-print-addresses). The frozen file of print addresses and evidenced claims joins the production run only with the operator's release, and title-year candidates stay local in any case ([Production readiness](production-readiness.md#operator-principles)), so no criterion depends on it. The full-text index of the reader covers the source text, and an address query has not been run in a browser review. The local part waits for the record desk ([Plan](plan.md#m1-ready-for-review), record desk, increment 2). A dedicated address search field is a proposal.

### T4 Print and wiki side by side

- For a candidate pair with a conflict, the print value and the wiki value stand side by side, each with its passage, and "not read" stays apart from "not given" ([Print viewer](print-viewer.md#card)).
- The candidate reads as `proposed` with its route.

The committed workbench shows field conflicts in its wiki drawer, and no browser review has opened a conflict pair. The merged reading of a group is the reconstructed entry of [Plan](plan.md#m2-merged-and-accepted).

### T5 A value back to its passage and producer

- Every value found in its passage offers, as visible and operable content, a way to that passage, its record, its source file and its producer with its state.
- The record coverage test counts only what a reader sees, and an element hidden from the reader satisfies no criterion.
- `check_render.mjs` reports no error over all print objects.

Sources are the Goal, second point, and the record desk exit condition of [Plan](plan.md#m1-ready-for-review). The workbench meets the criterion for print values, and `check_render.mjs` passes over all print objects. The reader card does not yet. Its pinned zero coverage gaps of fffcb29 rested on hidden `data-key` and `data-provenance-for` markers that `docs/js/detail.js` emits and the committed test counts, so a reader sees no provenance disclosure for those values, and the "Source slice" row shows character offsets as plain text. Correcting the test to visible content is in progress and showing the chain per value belongs to the record desk ([Plan](plan.md#m1-ready-for-review), record desk, increment 2).

### T6 Decide a print value

- The key, focus and message rules of [Print viewer](print-viewer.md#decisions) hold on every print card of the desk.
- The number of actions per value is reported, since it is the stated measure.
- At narrow width and at 200 % zoom the decision bar and the way to the next slip stay reachable without scrolling past the whole card.

Sources are [Print viewer](print-viewer.md#decisions) and the principle "An interface people like working in". The committed workbench carried one trial decision in a browser review with the reviewer dialog, one active card, the skip link and a status line naming the object. The forms for wrong, missing and boundary were not exercised there, and `smoke.mjs` covers them. Actions per value are not reported, and at 390 px and 200 % zoom the decision bar lies below the whole card, both open under [Plan](plan.md#m1-ready-for-review), record desk, increment 2.

### T7 Blind second review and adjudication

- A second reviewer loads none of the first reviewer's decisions.
- The adjudicator sees both decisions and records which one stands.
- Reports give the decisions of reviewer 1, reviewer 2 and the adjudicated state.

Sources are [Merged bibliography](print-wiki-merge.md#measurement) and [Production readiness](production-readiness.md#what-the-operator-accepts). The committed review server filters by reviewer, `_review.py` and the server validate an adjudication as one that settles two decisions and adopts one of them, and `p13_review.py` reports the three figures. No control of the workbench records an adjudication. The operator sketched an adjudication board, recorded in the [Journal](journal.md) as not decided, and the acceptance item Second reviewer and adjudication waits for the first reviewer to start.

### T8 Which publication a field describes

- On page 4445 the German book of 2000 and the Arabic article of 2015 stand in separate blocks, each with its own language and imprint, and a filter on Arabic finds the page.
- No block and no page-level row shows a value that belongs to one publication only. A flat value that no publication carries is labelled as a first match in the page text.
- After a filter, the step from the list to the card reaches the first matching publication.

Sources are worksheet cases 1 and 3, [Data and model](data.md#publication-and-contribution-scope) and [Interface and Curation](frontend.md#research-views), which reserves the page level for what holds for every publication. The committed card meets the first criterion. It renders a flat translator or contents list that no publication carries as a page-level row without a first-match note (`_pageRows` in `detail.js`), and a filtered list opens the card at its top. Both are open under [Plan](plan.md#m1-ready-for-review), record desk, increment 2.

### T9 Decision scope and producer

- Every state word has a producer word beside it as visible text, readable on touch and never only in a tooltip.
- No agent decision reads `confirmed` or produces `schema:sameAs`.
- A place decision never reads as a check of the whole entry.
- The default producer statement is visible on arrival at a permalink.

Sources are the principle "Who confirms" and the decisions of 2026-10-24 in [Production readiness](production-readiness.md#operator-principles), and [Data and model](data.md#provenance-and-review-scope). The committed card writes publication headings as an LLM agent review with no person and publishes no agent link. The About and Data pages still say that authority links were decided by LLM agents under delegation, which reads as a decision where the data hold proposals, and the default-producer disclosure of a permalink sits under the sticky header on arrival. Documentation corrects the first ([Plan](plan.md#m1-ready-for-review), record desk, increment 1).

### T10 An open claim

- The claim block stays open, with each interpretation under its authority identifier and with enough of its description (country, Wikidata description) to tell the readings apart on the card.
- Evidence pages are links to their records.
- No clickable confirmed link appears.
- The count of open claims is separate from the count of published links and from the count of affected pages, and each names its unit.
- A withheld redirect shows "Redirect withheld" with its open claim.

Sources are `CLAUDE.md` (Data Integrity), [Interface and Curation](frontend.md#rendering-of-contested-statements) and [Data and model](data.md#statement-states). The description beside each reading and the linked evidence pages follow the requirement of the vault note on agentically generated interfaces (`Coding/Webentwicklung/UI-Praxis für agentisch erzeugte Frontends.md`) that claim and evidence be judgeable together. The committed claim block stays open and the list marks the page contested. Its readings can carry identical labels, its evidence pages are plain text, and the data-quality page counts claims and pages under similar labels, open under [Plan](plan.md#m1-ready-for-review), record desk, increments 2 and 5.

### T11 Reception across time and space

- Every decade bar states the number its list holds, and the unit stands in the label.
- Records without a year or a language stay a visible group, and the map reports unlocated records separately.
- A filter in one view reaches the linked views without the colour scale silently renormalising.
- Explore arranges the records the desk has filtered and hands its selection back to them.

Sources are [Interface and Curation](frontend.md#explore), the synthesis on coordinated views in the vault note on agentically generated interfaces, and the decision that Explore becomes an arrangement of the filtered records ([Production readiness](production-readiness.md#operator-principles)). The committed Explore labels its bars in pages and keeps missing years as a linked group, and a browser review did not check coordinated filtering or the colour scale. The fourth is [Plan](plan.md#m1-ready-for-review), record desk, increment 4. Whether reception research counts pages, publications, contributions or works is open.

### T12 Print only, wiki only, or both

- Every count on the Overview opens a list of exactly that many records, in the unit its label names.
- A link that needs the local review server is rendered only where that server answers.
- Locally, the source filters select text, field and title-year candidates, records with none and unlinked wiki pages, and an unlinked page never reads as absent from print ([Print viewer](print-viewer.md#desk)).
- The overlap report rebuilds identically.

Sources are [Interface and Curation](frontend.md#start-page), [Print viewer](print-viewer.md#desk) and step 7 of [Merged bibliography](print-wiki-merge.md#steps). On the committed start page a count of print entries opens a workbench view that counts print objects, and on a phone and at 200 % zoom the section and model tables break their layout, open under [Plan](plan.md#m1-ready-for-review), record desk, increment 1. The overlap report belongs to the print data item of the same milestone.

### T13 References and See-also

- An address printed in the source text is a link, and an address that resolves nowhere reads as unresolved.
- The references to the Maria Stuart work resolve to page 35.
- A print reference is never presented as identity.
- Back returns to the card and position the reader left.

Sources are [Data and model](data.md#cited-print-addresses), [Production readiness](production-readiness.md#decisions-requiring-domain-or-publication-responsibility) for page 35, the Reference section of [Merged bibliography](print-wiki-merge.md#record-model), and the remark in [Project Context](about.md) that the one contemporary review praises the system of references. In the committed reader a See-also link lands on its target and Back restores the scroll position. The data reach audit found redirect aliases missing from the frontend map, which contradicts [Status](status.md), and it waits in [Handoff](handoff.md) for verification.

### T14 An item in hand

- Page 1891 shows `444/(3)p.` beside its numbered and unnumbered components and carries no overrun flag, because its contents end within the declared extent, while pages with a genuine overrun keep the flag.
- The imprint keeps its source wording and its co-imprint pairs.
- A field emptied because no rule binds it to the described publication reads differently from a field the source does not give.

Sources are [Data and model](data.md#publication-fields) and the principle "A gap before a wrong value". The needs of the trade are inferred, since no source states them. In the committed data a value emptied by the binding rule carries the provenance `missing` like a source gap, so the third criterion fails, and the distinction of gap kinds waits in [Handoff](handoff.md), Data reach audit, for the wiki data item of [Plan](plan.md#m1-ready-for-review).

### T15 Export of a filtered set

- The export writes one citation per publication and reports the number of citations rather than pages.
- Pages without a publication file fall back to flat citations.
- Open place claims on a cited publication are noted under the rule of T2.

Source is [Interface and Curation](frontend.md#export). The batch export has not been run in a browser review.

### T16 Work link and sample object

- A work link shows its evidence, state and producer.
- The single-entry JSON-LD carries contested claims and review actions as nodes of their own.
- The agreed sample object (entry, three sources, claim, group) rebuilds deterministically and passes a staging ingest.

Sources are steps 8 and 10 and the section Merged bibliography and delivery of [Merged bibliography](print-wiki-merge.md#merged-bibliography-and-delivery), and [Interface and Curation](frontend.md#export). The existing title matches to the work index are untyped and are superseded there. The sample object is agreed with Stefan Zweig Digital, and its publication waits for the operator ([Plan](plan.md#m2-merged-and-accepted), Delivery).

### T17 Acceptance on the operator's tasks

- On a known item the five worksheet steps succeed, finding with a language filter, telling which publication a field describes, inspecting evidence and review scope, exporting a usable citation, and repeating the essential steps "on a narrow screen or with the keyboard".
- The first point of confusion is recorded.

Source is worksheet case 5, withdrawn but still the only written task protocol, together with the item Interface on real tasks of [Production readiness](production-readiness.md#what-the-operator-accepts), which is ready once the record card with its provenance chain is built. Repeating on a narrow screen and with the keyboard is a proposal that tightens the worksheet. The task belongs to [Plan](plan.md#m2-merged-and-accepted), Interface acceptance.

### T18 Decide a wiki value

- A wiki card on the desk offers the decisions of a print card for every value it shows, right, wrong with a correction from the source text, and unsure, under the same key rules.
- A person's decision becomes a patch in the patch store with the producer person, `accept` for a confirmed value and `correct` for a replaced one, and after the rebuild the value reads confirmed with that producer in the canonical graphs, the frontend and the exports.
- A proposal of an LLM agent on the same value stays visible as a proposal with its producer and never turns into a confirmation.
- The reviewer filter and the blind rules of T7 hold for wiki values as for print values.

Sources are the decision for one record desk ([Production readiness](production-readiness.md#operator-principles)), the patch actions of [Interface and Curation](frontend.md#eil-curation-interface) and the principle "Who confirms". The committed edit mode of the reader decides four flat fields on the page record only. The task is [Plan](plan.md#m1-ready-for-review), record desk, increment 3, which also gives the end-to-end proof of a human patch that the release backlog asks for.

### T19 Check what was read from one print page

- For a chosen volume and PDF page, the tool shows the page beside every line read from it, in reading order with its line position and record address, and beside every value read from those lines.
- A line on the page that no record covers, and a value without a line, stand out as such.
- The tool runs locally over `data/print/` alone, and nothing it shows enters a versioned file.
- While the blind sheets of `p09_human_sample` are incomplete, the tool withholds the readings of their pages.

Sources are the decision for a local page check tool ([Plan](plan.md#m1-ready-for-review), record desk, increment 1), the guardrail that print stays local, and [Merged bibliography](print-wiki-merge.md#how-results-are-checked), which requires blind annotation from the source page alone before a person sees any method output. The tool is open.

### T20 Work through one data quality class

- Each class the data-quality page offers today (completeness gaps, values not evidenced in the source, detectable but unextracted values, LLM-derived fields, unresolvable cross-references, open claims, open candidates) is a filter of the desk whose count equals the records it opens.
- In review mode the desk steps through the filtered records with the keys of T6 and T18.
- A load failure stays distinct from a clean holding.

Sources are the decision that data quality becomes a filter and review mode of the desk ([Production readiness](production-readiness.md#operator-principles)) and the Data Quality Workbench section of [Interface and Curation](frontend.md). The task is [Plan](plan.md#m1-ready-for-review), record desk, increment 5.

## Requirements

Each requirement names an observable check and the sources that carry it. The check column says where a check is not built yet.

| ID | Requirement | Observable check | Source | Tasks |
|---|---|---|---|---|
| R1 | Evidence stands beside every value. A machine-derived value shows the wording it is checked against, and the source text stands beside the decision controls. | record coverage test over visible content, in progress; `check_render.mjs` | Goal, second point; [Print viewer](print-viewer.md#requirements); principle "An interface people like working in" | T5, T6, T18 |
| R2 | Producer and state are visible as text with equal weight, never conveyed by colour or tooltip alone. | not built beyond the per-fixture assertions of `entry_card.test.js` | principle "Who confirms"; [Interface and Curation](frontend.md#rendering-of-contested-statements); vault note on Critical-Expert-in-the-Loop | T9 |
| R3 | Uncertainty is never hidden. Contested claims stay open, a gap reads as a gap, "not read" stays apart from "not given", and no numeric or verbal confidence is shown for an LLM judgement. | `contested_claims.test.js` for open claims; no check for confidence values | `CLAUDE.md`, Data Integrity; principle "A gap before a wrong value" | T10, T14 |
| R4 | A proposal never looks confirmed. Decisions of a Large Language Model (LLM) agent read as proposals and never as a link-styled authority. | no `schema:sameAs` from an agent decision (Gate 2 manifest); link styling not built | decisions of 2026-10-24 in [Production readiness](production-readiness.md#operator-principles) | T9, T16, T18 |
| R5 | A citation names the publication it describes with its own address, and a print address or 1965 number appears as an alias only once the operator decides. | the criteria of T2 and T15 (`citation_export.test.js`) | [Project Context](about.md#how-the-bibliography-is-cited); [Interface and Curation](frontend.md#export) | T2, T15 |
| R6 | Every record leads to where it stands, as the first point of the Goal requires. | `check_render.mjs` for the PDF page of every print object; the permalink of every wiki card | [Merged bibliography](print-wiki-merge.md#goal) | T5, T13, T19 |
| R7 | Keys act on the active object alone, under the rules of [Print viewer](print-viewer.md#decisions) and [Interface and Curation](frontend.md#research-views). | `check_review.mjs`, `smoke.mjs`, `routing_guard.test.js` | the two linked sections | T6, T18 |
| R8 | Density follows the card catalogue, under the rules of [Design](design.md). | screen check of dense and scrolled states with the screenshots read | [Print viewer](print-viewer.md#requirements) | T6, T8 |
| R9 | Every count names its unit and opens the list it counts. | `search_logic.test.js` for the publication axis; Overview counts against the desk not built | [Interface and Curation](frontend.md#explore); vault UI-Praxis note | T11, T12, T20 |
| R10 | The interface is English, titles carry language tags and `dir="auto"`, search folds diacritics, source wording stays verbatim, and a non-Latin search that finds nothing explains the romanisation. | `search_logic.test.js` | [Interface and Curation](frontend.md#research-views) | T1, T14 |
| R11 | Measurement is blind where it needs to be, in the order of [Merged bibliography](print-wiki-merge.md#measurement). | reviewer filter of the server; claim sheet written only after both blind sheets; page check withholding not built | [Merged bibliography](print-wiki-merge.md#how-results-are-checked) | T7, T19 |
| R12 | States are addressable and the back path works, and a selection survives the step from list to card. | `routing_guard.test.js` for history; selection from list to card not built | [Interface and Curation](frontend.md#navigation-routes-and-page-layout) | T8, T13 |
| R13 | Narrow screens and zoom keep the task intact, with no horizontal page scroll and the relations a task needs kept together at 320 px and at 200 % zoom. | browser check at 320, 390 and 1440 px and at 200 % zoom | [Design](design.md#accessibility-minima); vault UI-Praxis note | T6, T12, T17 |
| R14 | The local boundary holds. Nothing of the print strand, the concordance or the merge reaches a versioned or published file until the operator instructs it, the public site shows no hint of the local data, and an unlinked wiki page never reads as absent from print. | leak check of `p14_gate.py` over versioned code and knowledge, which leaves out `docs/data/` and does not test for hints | guardrails; [Production readiness](production-readiness.md#operator-principles); [Data and model](data.md#cited-print-addresses) | T3, T12, T19 |
| R15 | A message with consequences names its object and stays until its cause is resolved, and a load failure differs visibly from a clean holding. | `smoke.mjs` (status error, live region); load states of the data-quality page | [Print viewer](print-viewer.md#decisions); [Interface and Curation](frontend.md) | T6, T20 |
| R16 | The local sitemap is Overview, Records and Documentation. Documentation joins the Data and About pages, help is a dialog, the imprint stands in the footer, and old addresses redirect. | redirect cases in `routing_guard.test.js` for the new addresses, not built | operator decision of 2026-10-24 ([Production readiness](production-readiness.md#operator-principles)); [Plan](plan.md#m1-ready-for-review), record desk, increment 1 | T9, T17 |
| R17 | A person's decision on a wiki value reaches every canonical artifact as a patch with the producer person. | end-to-end replay of one released patch, not built | [Production readiness](production-readiness.md#acceptance-matrix), Canonical curation; [Plan](plan.md#release-backlog-of-the-wiki-edition) | T18 |

The independent review on real tasks that [Plan](plan.md#m2-merged-and-accepted), Interface acceptance, names works through the adopted tasks on the running interface, and the operator's acceptance stays separate from it.

## Open questions

The open questions of [Merged bibliography](print-wiki-merge.md#open-questions) and the decisions listed in [Production readiness](production-readiness.md#what-the-operator-accepts) hold here as well, among them the task list itself, the identifier scheme, the aliases and what Stefan Zweig Digital wants. The questions below arise from the tasks and are held nowhere else.

- [Merged bibliography](print-wiki-merge.md#measurement) lets a third person or the operator settle a disagreement and names the operator as reviewer as well, while [Production readiness](production-readiness.md#what-the-operator-accepts) and `_review.py` exclude both reviewers from adjudication. Which holds when the operator is reviewer 1, and where an adjudication is recorded, is for the operator.
- [Production readiness](production-readiness.md#operator-principles) records the 1965 number as a citable alias, while its acceptance table lists citation identifiers as an open operator decision.
- [Interface and Curation](frontend.md#research-views) applies a claim to a value only where the subject equals the displayed value, so page 4426 carries no contested mark and no citation note. Whether a place claim reaches a spelling variant of its subject is for the operator, and a browser review of 2026-10-24 proposes that it does.
- The record desk decides values of both sources, while the patch contract addresses the source page and editing per publication stays outside version 1.0 ([Interface and Curation](frontend.md#deployment-and-limits)). Whether T18 covers publication values before that changes is for the operator.
- The rule of [Data and model](data.md#publication-fields) implies that the translator filter and the translator flow read credits, and no decision records it.
- The candidate queue of the data-quality page shows each candidate as a Wikidata link with a match score from the legacy reconciliation output. Whether a matcher score falls under R3, and whether the link counts as link-styled under R4, decides how T20 shows candidates.
- Explore counts pages by design, and no source says whether reception research needs pages, publications, contributions or works.
- The vault records the Expression level as ratified on 2026-07-19 and the code emits `schema:translationOfWork`, while the repository knowledge does not take it up.
- The governance table of the vault project overview moves a value attested by autopsy or a national bibliography into the main field with provenance `editor`, while `CLAUDE.md` admits only values documented in the MediaWiki source. The conflict is settled at its source.
- The vault project overview describes the hidden `data-key` and `data-provenance-for` markers as the binding of a wiki value to its provenance chain, which T5 rejects, so the overview needs correcting at its source.
- What a public user sees for a group with print members while print values stay local is open, addresses only or nothing.
- A target for the cost of a decision and a way to measure it, given that hours are deliberately not budgeted.
- Librarians as a user group, and whether repository and library sigla matter to them.
- Saved filters, personal lists and a comparison of two records outside the desk, which no source asks for and which stay proposals until an observed task calls for them.
