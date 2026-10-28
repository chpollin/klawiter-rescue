---
title: Production Readiness and Acceptance
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: maintained
language: en
created: 2026-07-18
updated: 2026-10-24
related: [status, data, pipeline, testing, frontend, journal]
---

# Production readiness and acceptance

A reproducible data core and an accepted research product are different milestones. The current implementation and open work are recorded in [Status](status.md); this document owns the durable acceptance contract and ratified decisions. “Technically complete” is not an adequate description while known model, provenance and interface gaps remain.

## Ratified scope

The July 2026 decisions, ratified on 19 July, remain in force:

1. Decompose multi-edition pages into work and edition.
2. Include reconciliation in the deliverable.
3. Treat the wiki/print merge as a later stage.
4. Use versioned patch export as the canonical write-back route.

The third point binds the production run. Since October 2026 the print strand works toward the merge outside it ([Merged bibliography](print-wiki-merge.md)), with one exception decided on 2026-10-24, a frozen file of print addresses and evidenced claims without print text (Operator principles below). Its frame questions (rights, print as a source of values, delivery shape) wait for the operator.

On 21 August, independent agentic source review and reconciliation became the initial evidence; external scholarly review adds validation. Contested cases were explicitly retained as final-data objects, distinguishable from confirmed relations. The exact decisions and their chronology remain in [Journal](journal.md).

The 27 August publication frame described version 0.9 as the release candidate and reserved 1.0 acceptance and its tag for the operator. Do not infer a new release from document frontmatter, a filename, a passing test count or this refactor. A separate Klawiter paper is outside the repository mandate, and the blog post is written outside the repository with its claim check kept as evidence. Live external write-backs, the wiki/print merge and institutional work-identity decisions remain separate work.

The operator's 5 September request explicitly reopens Explore as an interactive dashboard with linked information visualizations. Earlier documentation deferring cross-view interaction is superseded by that request.

## Acceptance matrix

| Capability | Required evidence | Current evidence and remaining work |
|---|---|---|
| Current-source preservation | exact source/canonical/frontend ID reconciliation; documented stubs | census and default tests; historical and archived content must remain explicitly scoped |
| Correct bibliographic units | source-bound publications/contributions with coherent field scope | Gate 1 segmentation exists; graph field coverage and compound pages outside its grammar remain open |
| Uncertainty and authority links | proposed/confirmed/contested separation; exact evidence and deterministic decisions | Gate 1/2 validators; scholarly adjudication of open cases remains distinct |
| Canonical curation | one released correction reaches all intended graphs, exports, histories and reports | frontend replay is hardened; full propagation is still open |
| Research interface | exact filter handover, source access, useful visualizations, clear review scope, edition navigation | browser/Node evidence for implemented paths; edition browsing and full task acceptance remain open |
| Accessibility and performance | keyboard/touch paths, readable contrast, mobile fit, representative device/network budgets | targeted checks support specific paths; no comprehensive certification or performance budget yet |
| Repeatability | locked environment, both gate checks, reviewed deterministic artifact comparison | full local locked-uv rebuild and reviewed-manifest checks pass; remote CI execution remains distinct |
| Public release | curated source package, consistent metadata, explicit release scope and acceptance | release scope set on 22 and 23 September (see below); `CITATION.cff`, licence texts, third-party notices and the source inventory aligned on 23 September, and release archives leave out only the account tables `zweig_part_03.sql`; rights basis confirmed and institution named by the operator on 23 September; the dump stays in the public Git history and the title is set by operator decision; partner acceptance and a Zenodo deposit are no longer part of the release (operator decision of 23 September) |

Technical verification compares implementation with these contracts. Validation compares the product with real scholarly questions and users' interpretation of the source. Neither replaces the other.

## Control loops

The development loop identifies error classes, reviews corpus-wide changes and reruns affected tests plus dependent gates. Lower field population is acceptable when a false assertion is removed. Baselines record exact remaining failures and reviewed improvements; they must not absorb new regressions.

The curation loop reviews individual fields, editions and authority candidates against exact evidence. Browser changes remain local until a released patch is integrated and rebuilt. A reviewed place does not certify an entry's year or translator.

## Decisions requiring domain or publication responsibility

On 22 September the operator delegated four open questions to the main instance. Its answers are recorded with the provenance "decided by the main instance after delegation by the operator on 2026-09-22, revisable" and are listed here with their place of record.

- Worksheet cases 1 to 4 accept the display as it stood that day, recorded in the [worksheet](../snapshots/evaluations/2026-09-05/owner-evaluation.md#responses). The operator withdrew case 5 on 2026-09-23, so it is no release condition.
- The author of a citation follows the role in the source, as described in [Frontend](frontend.md#export).
- The graphic novel on page 4916 is a work of its own, an adaptation of the Schachnovelle with a change of medium, whose German edition translates the French graphic novel of 2015. The claim is resolved in `data/reconciliation/edition-modeling-decisions.json`, see [Data](data.md#statement-states).
- The archive triage is outside version 1.0, see the release scope below.

On 23 September the operator approved the recommended course after four read-only reviews. The domain decisions of that round carry the provenance "decided by the main instance after delegation by the operator on 2026-09-23, revisable".

- A page the wiki's Redirect fixer overwrote with an unrelated redirect is published from the compiler's last revision before the overwrite, and the fixer redirect resolves no reference. Where that revision is not delivered, the redirect is withheld under an open claim. See [Data](data.md#pages-overwritten-by-the-redirect-fixer).
- The 26 Maria Stuart references resolve to the restored page 35.
- The compound place claims "Sofija, Varna", "Varna, Sofija" and "Bloemfontein, Kaapstad" are decided as two places each, and their components are decided on their own, except Sofija, whose standalone decision left with the fixture demotion of 2026-10-23. Tyresö is decided for the municipality; Saint-Aignan stays open.
- Systematic false review flags are removed by rule for version 1.0. Genuine source conflicts stay open claims, and version 1.0 does not require their resolution.
- Editing per publication stays outside version 1.0.

The operator confirmed on 23 September that permission to publish the compiled content under CC BY 4.0 exists and named the Literaturarchiv Salzburg as the institution the bibliography is published with. The archival dump stays in the public Git history by the operator's decision of the same day. Release archives carry its page and text tables and leave out its account tables. The operator also set the title "Stefan Zweig Bibliography", after the wiki, cited as "Stefan Zweig Bibliography (Klawiter)", and ruled that the publication is not called a digital edition. The operator also withdrew the partner acceptance and the Zenodo deposit with its DOI, which the decision of 8 September had tied to version 1.0. A Git tag remains the operator's decision.

In October the operator decided the following for the merged bibliography, recorded in the [Journal](journal.md) on the day.

- A test fixture confirms nothing (2026-10-23). The place decisions that rested only on a fixture were demoted to proposals.
- Checks are assigned by the kind of task (2026-10-23). A deterministic check needs no person, a simple check needs care but no domain knowledge, and only complex checks go to Zweig specialists ([Merged bibliography](print-wiki-merge.md), How results are checked).
- The rights in the print volumes may wait until delivery (2026-10-23). Until then only wiki values, print addresses and claims are published, and every print-derived file stays under `data/print/`.
- Schema validity is no correctness (2026-10-24). Whether a valid, span-bound value is right in its context is decided by a person in the interface, and only those decisions measure field correctness.

The release declaration and the publication form after acceptance remain with the responsible people. These decisions do not prevent bounded technical repairs or source transcription checks.

## Operator principles

The operator supervises and sets principles. The main instance decides details under them, names the principle each decision rests on, keeps every such decision revisable, and reports the decisions that change something as a list the operator may object to. A question goes to the operator only where no principle carries or two of them conflict. Each principle below is already stated in a binding source, which it names.

Purpose
: The product is the bibliography as research data for Zweig research and Stefan Zweig Digital. The DIA-XAI follow-up uses only documented review episodes and quality evidence and takes over neither the data nor the release state ([About](about.md), and the project overview in the operator's vault).

A gap before a wrong value
: A value stands only where its source passage documents it for the publication it describes, and a gap is a valid result. A proposal may be shown with its passage and producer, never as confirmed, and it never overwrites a rule value (`CLAUDE.md`, Data Integrity, and the commission's guardrails). Flat wiki fields that no rule binds to the described publication therefore stay empty, and a page the kind rules cannot decide stays undetermined.

Who confirms
: Only an exact deterministic rule or a person confirms. An LLM proposes and never confirms, a test fixture confirms nothing, and only `confirm` and `correct` produce a confirmed relation (`CLAUDE.md`, the guardrails, the decision of 2026-10-23, [Merged bibliography](print-wiki-merge.md), Principles). A rule class confirms automatically only once its precision is measured on a human sample under the decision rule of [Merged bibliography](print-wiki-merge.md), Measurement.

Print stays local
: Print PDFs and everything derived from them stay under `data/print/`; until the rights are settled only wiki values, print addresses and claims are published (the guardrails, the decision of 2026-10-23).

An interface people like working in
: The review happens through work in the interface, not through a planned budget of hours, so the interface is judged by the cost of a decision and by whether the evidence stands beside each value (operator, 2026-10-24).

Outward steps
: Push, deploy, tag and the live LLM mode happen only on the operator's explicit instruction (`CLAUDE.md`, the guardrails).

Decided under these principles by the main instance on 2026-10-24, revisable, each reported to the operator:

- No rule class confirms automatically in this phase. The frozen samples cannot carry the per-class estimate the decision rule needs, so the thresholds stay unset and every confirmation is a person's.
- Decisions of LLM agents, including those of the main instance under the operator's delegation, are proposals in both strands. Their records stay as evidence with the producer named, and they produce no `confirmed` state and no `schema:sameAs`.
- The Git history keeps the print quotations removed on 2026-10-24, because rewriting it would remove nothing from forks or caches and would break cited commits; they belong to the rights clarification.
- Until a second person reviews, the field figure is reported as acceptance by one reviewer after inspection.
- The blind supplement leaves the field route of the concordance below forty claims in every volume, and no third draw is made in this phase, because no class confirms automatically. A pre-sized third draw becomes necessary only when the operator sets a threshold.
- The bibliography of 1965 enters as an external identifier attached to print records (the 1965 number as a citable alias), not as a source with entities of its own, because citation is the stated use. Its licence (non-commercial, no derivatives) keeps its text local like the print volumes, while a table of print address and 1965 number pairs without text falls under what may be published, addresses and claims, every pair `proposed`. Research and trade citing the 1965 numbers ([About](about.md), How the bibliography is cited) carry the effort.
- The interface becomes one record desk (operator, 2026-10-24). Locally a single card view holds the print objects and the wiki records and replaces the wiki catalogue; values of both sources are decided there, and a person's decision on a wiki value becomes a patch that confirms it with the producer person. The sitemap shrinks to Overview, Records and Documentation: Documentation joins the former Data and About pages, help becomes a dialog, the imprint moves to the footer, Explore becomes an arrangement of the filtered records, and data quality becomes a filter and review mode of the desk. Old addresses redirect. On 2026-10-25 the operator had all work merged on main and pushed, so the public frontend carries the desk in its state of work.
- The design choices of the corrected measurement (weights per part from entries less hard entries, one random object per hard entry, adjudication by a third person that adopts one of the two decisions, the first reviewer as whoever decided an object first, code identity over whole modules, fingerprints of the older samples kept local) stand in [Merged bibliography](print-wiki-merge.md), Measurement, and in the code of `p13_review.py`.

Decided by the main instance on 2026-10-24 under the operator's explicit delegation of the two questions left open at the level of principle:

- Print addresses, the compiler's own notation applied by rule (references, corrections, errata) and the concordance claims with a text or field evidence join the production run as a frozen file under `data/provenance/` that holds identifiers, addresses, route, producer and state and no print text, every claim `proposed`. The title-year candidates stay local, because they are too weak to show in public. The file enters only once the containment predicate for contents lines and the shared claim schema stand and the operator releases it, and the leak check of `p14_gate.py` covers it. The operator decided on 2026-10-24 that development stays local: the print strand, the concordance and the merge are built and checked under `data/print/`, and nothing of them is published until the operator instructs it. `CLAUDE.md`, Known Limits, records the exception.
- The goal of [Merged bibliography](print-wiki-merge.md) is the criterion of done, extended by a point on the interface, because the principle that people like working in it is otherwise checked by nothing.

## What the operator accepts

The goal of [Merged bibliography](print-wiki-merge.md) is the criterion of done. Its points that a person must accept, and the decisions that only the operator or a partner can take, are these. Everything else is checked by rule, test or gate.

| Acceptance or decision | What it takes | Ready when |
|---|---|---|
| Human round of the print strand | deciding the four parts of the human round in the card workbench in the order of [Merged bibliography](print-wiki-merge.md), Measurement; this gives field precision and claim precision | the repaired workbench is committed |
| Second reviewer and adjudication | naming a second person for the marked subset of the review sample and a third person who settles disagreements, since an adjudicator may not be one of the two reviewers | the first reviewer has started |
| Wiki data before publication | inspecting the regenerated wiki data with the flat fields reduced to what a rule binds and every agent decision shown as a proposal | the wiki data batch is committed |
| Interface on real tasks | reading, reviewing and citing with the production frontend, the record card and the card workbench on the operator's own tasks | the record card with its provenance chain is built |
| Research tasks for the trial | naming the research tasks the merged bibliography must support, with Stefan Zweig Digital; [Specification](specification.md) proposes them | any time |
| Rights in the print volumes | settling with the rights holder whether print-derived structure and values, including the unpublished Addendum II, may be published | before delivery |
| Print as a source of values | deciding whether print becomes an admitted source of values or the merged bibliography stays a concordance | after the rights decision |
| Delivery shape | agreeing with Stefan Zweig Digital on one sample object (entry, three sources, claim, group) | after the reconstructed entry |
| Citation identifiers | deciding with a domain expert whether groups carry the print address and the 1965 number as citable aliases ([About](about.md), How the bibliography is cited) | any time |
| Decisions under the principles | reading the list under Operator principles and objecting where a decision should be taken otherwise | standing |

The redirect of the former public address and the release with its tag lie outside the project's planning (operator, 2026-10-24); pushes stay with the operator as before.

## Release scope

Version 1.0 covers the current pages of the wiki. The titles that the wiki's deletion archive and log record as deleted and that are absent from the current page table are excluded from the project scope of version 1.0 (decided by the main instance after delegation by the operator on 2026-09-22, revisable). A deletion was an editorial decision of the compiler, a large part of these titles are duplicates, renamed pages or empty pages, and one of them is a private message. The raw originals under `data/raw/` stay unchanged. A later read-only triage list of these titles is possible as a separate work package and is not part of 1.0. Eight current pages are published from the compiler's last revision before an overwrite by the wiki's Redirect fixer, the only departure from the current page state (decided by the main instance after delegation by the operator on 2026-09-23, revisable).

The version stays 0.9 in `pyproject.toml`, the single version source; the 0.9.1 tied to the owner worksheet on 2026-09-08 was never cut, and the next version number belongs to the operator's tag.

Use the [five-case worksheet](../snapshots/evaluations/2026-09-05/owner-evaluation.md) to evaluate concrete edition boundaries, contribution roles, conflicting imprints and the research workflow. The questions are not a request to reapprove the work/edition principle.

## Evidence ownership

- [Data](data.md): source and entity contracts, statuses and correction limits.
- [Pipeline](pipeline.md): stage order, inputs and deterministic boundary.
- [Testing](testing.md): executable checks, independent samples and CI limits.
- [Frontend](frontend.md): user-facing behaviour and export scope.
- [Status](status.md): one prioritized current work list and current artifact links.
- Dated reviews under `snapshots/`: observations at a particular state, preserved without silently rewriting history.
