---
title: Production Readiness
aliases: [production-readiness, curation-tool, EIL production tool, edition-model, work-edition model, work-edition split, PROV, SHACL]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: complete
language: en
version: 1.1
tags: [eil, dia-xai, concept, provenance]
created: 2026-07-18
updated: 2026-08-27
authors: [Christopher Pollin]
related: [about, data, pipeline, testing, frontend, journal]
---

# Production Readiness

This document describes the ratified and implemented production state. [[pipeline]] explains the transformations, [[data]] the artifacts, [[frontend#EIL Curation Interface]] the interaction and [[testing]] the quality limits. The course of the decisions is held in [[journal]].

## Publication Frame

The published subject consists of the digital bibliography, the JSON-LD data, the software, the machine-readable vocabulary and the provenance and validation artifacts. A separate Klawiter paper and a separate blog post are closed publication lines. The wiki/print merge, external live write-backs and institutionally content-changing work decisions are not part of this production state.

## Definition of the Terminal State

In this repository, production readiness means the following:

- the MediaWiki source can be processed reproducibly without a database server and without a network request;
- the complete record chain of source, JSON-LD and frontend is reconciled by census;
- the relevant multi-edition corpus has a complete work/edition segmentation with exact source references;
- candidates, confirmed decisions, contested statements and published relations stay separate;
- automated and agentic review steps have provenance, input hashes and machine-readable results;
- a prioritized review list preserves every unreviewed or open case;
- corrections and new reconciliation decisions can be re-applied as versioned Expert-in-the-Loop patches;
- README, entry layer and `knowledge/` describe the executable state.

An external expert review can extend this state. It is not a prerequisite for its technical reproducibility.

## Two Control Loops

**Developer-in-the-Loop.** Aggregated tests and data diagnostics reveal systematic error classes. A code change is checked against the entire holdings, the regression limits and the production run. The work/edition separation resolves the central level error of the earlier flat extraction.

**Editor-in-the-Loop.** Domain staff review individual fields, editions and authority-data candidates against their sources. The browser exports typed decisions. The production run re-applies released patches and preserves value history or decision supersession.

Both loops use the same evidence chain. Machine values carry `regex`, `llm` or `missing`; reviewed field values carry `editor`. Editions and reconciliation statements distinguish `proposed`, `confirmed` and `contested`.

## Gate 1: Work/Edition Model

### Selection and Identity

A page belongs to the Gate 1 corpus where it holds, in the main namespace, at least two bold-marked publication headers with a four-digit or `ca.` year. This rule selects 443 pages completely and deterministically.

The model uses:

- `klawiter:work/{page_id}` for the work of the source page;
- `klawiter:edition/{page_id}-{year}-{suffix}` for each edition in stable source order;
- `klawiter:annotation/{page_id}-{year}-{suffix}` for the Web Annotation of the edition;
- `klawiter:carrier/source-{page_id}-{year}-{suffix}` exclusively for a documented carrier occurrence.

Every edition holds the unmodified header, `oa:start`, `oa:end` and the SHA-256 of the selected source block. The same input produces the same graph and the same IDs.

### Result

The current graph contains 443 works, 1,886 editions, 1,886 annotations and six carrier occurrences. The agentic sample comprises 76 cases from pages 54, 56 and 4916. Two independent initial reviews were reconciled by a more capable, independent verification agent. 75 editions are confirmed within their exact selectors. 1,810 further editions remain proposals. The complete Gate 1 review list contains 317 cases prioritized on account of flags or open status.

The test and decision artifacts are held under `data/output/edition-samples/`, `data/reconciliation/` and `data/output/editions/`.

### Contested Work Binding

`klawiter:edition/4916-2016-b` describes "Die Schachnovelle nach Stefan Zweig", a graphic novel adaptation. The source documents the publication, yet does not decide the institutional work identity.

The case remains in the final graph as `klawiter:claim/work-binding/4916-2016-b`. The claim contains:

- the exact selector `[6866, 7104)` and the SHA-256 of the source block;
- the competing assignment to the work `klawiter:work/4916`;
- the competing interpretation as an independent candidate `klawiter:work-candidate/4916-2016-b-adaptation`;
- the judgements of both initial reviews and of the reconciliation;
- `claimStatus = contested` and `decisionStatus = open`.

The edition is preserved in full. It does not appear in `schema:workExample` and carries no `schema:exampleOfWork` relation for as long as the domain decision stays open.

## Gate 2: Reconciliation

Gate 2 produces deterministic candidates for 382 location, 443 work as well as 101 translator and publisher subjects. The frozen SZD work index is provenanced by source path, repository commit and SHA-256. Location proposals preserve the results of the earlier reconciliation run and the independent review as candidates. The agent candidates come from the frozen Wikidata comparison (`data/provenance/agent-reconciliation.json`, threshold five occurrences, 78 subjects with at least one candidate); they form a new fail-closed review stock and publish nothing without a documented decision.

Decisions are held separately under `data/reconciliation/`. The current state comprises 31 location decisions and three work decisions. From these arise 26 publishable Wikidata location links and three publishable SZD work links. `pipeline/05_to_jsonld.py` reads exclusively this publishable layer.

Five location decisions remain open. Every case has a stable `klawiter:ContestedClaim`, exact occurrence lines from `04_classified.csv` with hash, competing authority-data interpretations, a fail-closed alternative without an assignment and the review history. Open claims produce no `schema:sameAs`.

The Gate 2 review list comprises every candidate without an accepted decision and every contested case across all three subject kinds; its current size is held in the Gate 2 manifest. Its extent denotes review demand and no error rate.

## Expert-in-the-Loop Interface

The localhost-bound editing mode implements:

- Accept, Correct and Add for provenance-tracked fields;
- field occurrences or the complete source text as evidence;
- triage hints from provenance, round-trip verification and census;
- location candidates as well as translator and publisher candidates with Confirm, Reject and Unresolved, where Unresolved in both cases rests on the occurrences of the occurrence scan;
- subject-level decisions with declared reach, reachable at the entry and in the candidate queue of the data quality workbench (`#quality`, with keyboard control);
- persistence of the running session in `localStorage`;
- a combined export with `patchVersion: 2` and `reconciliationPatchVersion: 1`.

The public detail view marks contested authority-data assignments. For page 4916 it shows the open work binding claim, both interpretations, the review history and the source identifier. The single-entry JSON-LD export adopts this claim; the complete export contains the contested edition and authority-data claims.

## Provenance and Quality Evidence

Gate 1 uses PROV-O for source corpus, software agent, plan, input hashes and produced nodes. SHACL checks work, edition, annotation, carrier, claim, interpretation, ReviewAction and work identity candidate. EARL records every automated check result.

Gate 2 preserves the input hashes for edition graph, location data, review evidence, decision files, SZD index, classified source and curation patches. Its validator checks deterministic rebuild, decision separation, claim completeness, input hashes and the projection into JSON-LD and frontend. The quality and census reports complement these object-level contracts.

## Ratification History

### Operator Decisions (2026-07-18)

The decisions of 2026-07-18 were ratified on 2026-07-19:

1. Multi-edition pages are decomposed into work and edition.
2. Reconciliation belongs to the production-ready deliverable state.
3. The wiki/print merge remains a later development stage.
4. The versioned patch export is the canonical write-back route.

On 2026-08-21 the agentic review replaced the external sample as the starting condition. Two independent initial reviews and a stronger reconciliation form the current evidence. A later external review is additional validation.

Likewise on 2026-08-21 it was decided that contested cases are a component of the final data. They are modelled as open claims and stay distinguishable from confirmed relations.

## Limits, Open Points and Operator Points

The flat compatibility layer stays structurally imprecise for multi-edition pages; there the Gate 1 graph is the more precise representation. The complete review stocks (unconfirmed editions, Gate 2 cases across locations, works, translators and publishers) are held in the queues and manifests. Known semantic ground-truth failures are held in [[testing]].

Registered open points that do not block the reproducible production state:

- Triage of the 207 pages in the MediaWiki archive table (not commissioned; decision with the operator).
- Cross-view brushing in the Explore views (deliberately deferred; the benefit of a linked selection across the views stands in no proportion to the complexity of a shared selection state, resumption only on operator decision). The remaining points of the cosmetics round (language and direction attributes, sorting in the URL hash, inline handlers in home and facets) are implemented.
- Working through the translator and publisher review stock as a curation task.
- External expert review as additional validation on the finished tool.
- Two titles (pages 4775 and 5913) carry a stray Arabic diacritic (U+0650) as an encoding residue; a candidate for the normalization stage, cosmetic.

Operator Points: the institutional work identity of the graphic novel adaptation `klawiter:edition/4916-2016-b` (the existing claim secures the case completely), the acceptance of version 1.0 and, after acceptance, the publication and citation form (release tag, Zenodo/DOI).

## Evidence Locations

| Statement | Canonical evidence |
|---|---|
| complete production run | `pipeline/run_pipeline.py` and final audit under `data/output/audits/` |
| work/edition graph | `data/output/editions/work-editions.jsonld` |
| Gate 1 contract | `data/schema/work-edition-shapes.ttl` and `data/output/editions/validation-report.json` |
| agentic sample review | `data/output/edition-samples/reviews/` |
| reconciliation candidates and decisions | `data/output/reconciliation/` and `data/reconciliation/` |
| contested authority-data claims | `data/output/reconciliation/contested-claims.json` |
| public link layer | `data/output/reconciliation/publishable-links.json` |
| Expert-in-the-Loop contract | `data/corrections/README.md` and [[frontend#EIL Curation Interface]] |
| overall quality | `data/output/quality-report.json`, census and verification report |
