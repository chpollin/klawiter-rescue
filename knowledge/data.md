---
title: Data and Model
aliases: [data, dataset, data model, JSON-LD, work-edition extension]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: en
version: 1.1
tags: [data, model, provenance, reconciliation]
created: 2026-03-29
updated: 2026-08-27
authors: [Christopher Pollin]
related: [about, pipeline, frontend, testing, production-readiness]
---

# Data and Model

## Data Levels

The repository preserves four clearly separated levels:

1. `data/raw/` contains the unmodified MediaWiki SQL dump and eight text stores.
2. `data/intermediate/` contains regenerable tabular stages and is not versioned.
3. `data/output/klawiter.jsonld` and `docs/data/klawiter.json` form the flat compatibility layer.
4. `data/output/editions/` and `data/output/reconciliation/` contain the structured edition model, reconciliation and validation artifacts.

Decision inputs are held under `data/reconciliation/`. Frozen external and model-supported inputs are held under `data/provenance/`. These directories are sources of the production run and not temporary outputs.

## Source Scope and Deliberate Omissions

The pipeline processes exclusively the latest version of each page. Alongside these, the dump contains roughly 45,200 historical revisions that deliberately stay unused; they are held complete in `data/raw/` and remain available for later analysis. The MediaWiki archive table records 207 deleted pages; their triage (which of them carried bibliographic value) is not commissioned and is registered as an open point, see [[production-readiness]].

## Record Census

The census reconciles the entire record chain:

| Level | Count |
|---|---:|
| MediaWiki pages | 6,725 |
| JSON-LD entries | 6,725 |
| Redirects | 1,546 |
| Frontend entries | 5,179 |
| Main namespace without redirects | 4,751 |

All five census invariants hold. JSON-LD is 1:1 with the source, the frontend corresponds to JSON-LD minus redirects, and every visible entry has a title. Four pages have no delivered BLOB text; only `page_id 2979` is bibliographic. This source-conditioned empty record is retained as a named stub.

## Flat Compatibility Model

The flat layer preserves the historical MediaWiki page as a record. It uses Schema.org, Dublin Core and the project-specific prefix `klawiter:`. Typical fields are title, year, publisher, place of publication, language, translator, page count, categories, cross-references, source identifiers and field provenance.

This representation is retained for search, citation and existing exports. On pages with several publication blocks, individual values may originate from different editions. For those pages, the edition model is the structurally more precise source.

## Work/Edition Model

Gate 1 captures every main-namespace page with at least two ratified edition headers. The current holdings comprise 443 works, 1,886 editions, 1,886 Web Annotations and six documented carrier occurrences.

- `schema:CreativeWork` denotes the work of the source page.
- `schema:Book` denotes the segmented publication block.
- `oa:Annotation` connects the edition to the exact source excerpt.
- `oa:TextPositionSelector` stores start, end and SHA-256 of the excerpt.
- `schema:PublicationVolume` denotes exclusively a source-documented carrier occurrence.

The identifiers are derived from source page, year and stable ordering. Identical inputs produce identical IDs, selectors and graph nodes.

## Statement States

Domain relations have an explicit status:

- `proposed`: deterministically produced and as yet unreviewed;
- `confirmed`: source-bound, reviewed and confirmed;
- `contested`: reviewed, still open and preserved with competing interpretations.

A `klawiter:ContestedClaim` carries a stable claim ID, subject and predicate, exact source evidence, at least two interpretations, review actions as well as `claimStatus = contested` and `decisionStatus = open`. The claim belongs to the final dataset. Its predicate is not emitted as a confirmed relation at the same time.

The open adaptation case `klawiter:claim/work-binding/4916-2016-b` preserves the interpretation as an edition of the "Schachnovelle" and the interpretation as an independent graphic novel adaptation work. The edition itself remains fully contained.

## Reconciliation

Gate 2 separates candidates, decisions, contested claims and publishable links. Candidates arise for location, work as well as translator and publisher subjects (the agent candidates from the frozen Wikidata comparison `data/provenance/agent-reconciliation.json`, threshold five occurrences). Documented decisions publish the confirmed location and SZD work links; the current counts are held in the Gate 2 manifest `data/output/reconciliation/manifest.json`. Open location decisions are preserved as contested claims.

Every subject carries its occurrences in the classified source. For a location, the scan documents every line that contains the place name or its components. For a translator or publisher name, the field first determines the entries carrying the name, and the scan then anchors it in the lines of exactly those entries; where no line spells it out, because it originates from enrichment or normalization, the field value itself remains the evidence and the occurrence says so with `sourceMatchMode: field-value`. An agent subject without any occurrence carries a spelled-out null finding. Only this evidence makes an unresolved agent decision representable, which then, as with locations, is preserved as an open claim.

`pipeline/05_to_jsonld.py` reads exclusively `publishable-links.json`. Candidates and open claims may be visible in the interface and the export, yet do not appear as `schema:sameAs`. The prioritized Gate 2 review list comprises all open location, work and agent cases; its size is held in the manifest.

## Provenance

Field values in the flat frontend layer carry `regex`, `llm`, `missing` or, after a confirmed correction, `editor`. The default run uses the versioned cache `data/provenance/llm-enrichment-cache.json`; a local working cache does not affect the production run.

Gate 1 and Gate 2 store input hashes, code hashes, PROV-O activities, SHACL respectively contract checks and EARL results. Agentic reviews name input, reviewer, result and reconciliation. Uncertain cases stay in the queue and are not smoothed into certain statements.

## Review Status per Entry

Alongside the field provenance, the frontend layer carries a review status. Stage 05 projects it as the field `review` and sets it exclusively where a Gate 2 decision covers a field value of the entry; an unreviewed entry does not carry the field. The assignment runs via the exact value the entry carries, for the place of publication via the place name and for translator and publisher via the agent name.

The field carries four keys:

- `status` with `agent_verified` for a completed decision (`confirm`, `correct`, `reject`), `contested` for an unresolved decision and `approved` for a released field correction from `data/corrections/`;
- `reviewed_by` with the deciding role, for example `independent-verification-agent` or `repository-ground-truth-fixture`;
- `reviewed_at` with the time of the decision, where the decision carries one;
- `fields` with the action per reviewed field.

The status of the entry is the strongest statement of its fields, `approved` over `agent_verified` over `contested`. After a field correction, `apply_patches.py` raises the status while preserving the projected field finding. The field provenance stays separate from this, because it says where a value originates, while the review status says who judged it.

## Correction Protocol

The interface exports a versioned curation document. Field corrections preserve the previous machine value in the `edit_history`; reconciliation decisions preserve replaced decisions in a `supersedes` chain. The browser does not write into the repository directly.

Released patches are held under `data/corrections/` and are re-applied on every run. `confirm` and `correct` produce publishable relations. `reject` discards the reviewed candidate. `unresolved` produces or updates an open claim.

## Quality Limits

The current field coverages are held exclusively in `data/output/quality-report.json`. The principal known limits are:

- 1,810 edition segments remain proposals; 75 segments are agentically confirmed and one binding is contested.
- The remaining unresolvable `seeAlso` references are genuine red links to pages never created; the redirect map additionally contains the page-title aliases from stage 05. The frozen counts are held in `.github/baseline-metrics.json` (`known_issues`).
- On 443 multi-edition pages, the flat layer may combine values from different editions.
- Missing bibliographic values may be source-conditioned and are not invented.
- The semantic ground-truth set is small and measures no corpus-wide error rate.

The precise test reach and all known limit values are held in [[testing]].

## Canonical Artifacts

| Artifact | Function |
|---|---|
| `data/output/klawiter.jsonld` | complete flat JSON-LD layer |
| `docs/data/klawiter.json` | frontend data with field provenance |
| `data/output/editions/work-editions.jsonld` | work/edition graph and edition claims |
| `data/output/editions/review-queue.json` | prioritized edition review |
| `data/output/reconciliation/candidates.json` | authority-data candidates |
| `data/output/reconciliation/decisions.json` | documented reconciliation decisions |
| `data/output/reconciliation/contested-claims.json` | open authority-data claims |
| `data/output/reconciliation/publishable-links.json` | confirmed public relations |
| `docs/data/reconciliation.json` | deterministic UI projection |
