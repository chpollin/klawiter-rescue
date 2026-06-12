---
title: About
aliases: [project context, klawiter, provenance]
tags: [project, context]
created: 2026-03-29
updated: 2026-06-12
---

# About

## The Klawiter Bibliography

The bibliography was compiled by **Dr. Randolph J. Klawiter** (University of Notre Dame) over decades. It covers Stefan Zweig's global literary reception: 6,296 entries spanning first editions, translations, secondary literature, film adaptations, correspondence, and more — in over 40 languages, from 395 publication locations, across 200 years (1815-2020).

The bibliography was originally hosted as a MediaWiki instance. When the wiki was decommissioned, the underlying database (SQL dumps and 8 binary BLOB files, 363 MB total) was preserved but the structured access was lost.

## The Data Rescue

This project extracts and structures the raw database into [[pipeline|JSON-LD]], making the bibliography accessible again as a static website and a Linked Data dataset. The approach:

1. Parse the SQL dump and BLOB files directly in Python (no MySQL required)
2. Fix encoding damage (UTF-8 interpreted as Latin-1 during the original dump)
3. Extract structured fields from wiki markup via regex and LLM-assisted extraction
4. Classify entries into 16 types and 5 time periods
5. Output as JSON-LD with a Schema.org + Dublin Core + klawiter: [[ontology|vocabulary blend]]
6. Serve via a static [[frontend]] on GitHub Pages

## Data Integrity Principle

**The pipeline must never invent data.** Every extracted value must exist in the raw wiki source text. The pipeline's job is to extract, structure, and normalize — not to enrich or infer. Specifically:

- Fields left empty because the source text doesn't contain them are **correct** (e.g., anthology poems without a standalone publisher, German originals without a translator)
- Coverage gaps are only bugs if the value **is present in the raw text** but the pipeline fails to extract it (regex miss or LLM miss)
- The LLM enrichment step (03b) is constrained to extract **only explicitly stated** values. It has 5 anti-hallucination layers: prompt constraint, gap-fill-only merge, structured output schema, post-extraction validation, and mojibake re-validation. Verified: 0 hallucinated values found in full audit
- Provenance tracking (`_provenance` metadata) marks each field as `regex`, `llm`, or `missing` — making the extraction source transparent and auditable
- Linked Data enrichment — matching extracted entities against authority files (e.g. Wikidata) to add persistent IDs — is allowed and implemented for locations; inventing bibliographic *values* not present in the source remains out of scope. See [[pipeline#reconciliation--linked-data-enrichment]]

## Stefan Zweig Digital and the Forschungsverbund

This project is connected to [Stefan Zweig Digital](https://stefanzweig.digital/) at the Stefan Zweig Centre Salzburg (University of Salzburg). Three sites form the **Zweig Forschungsverbund**:

| Site | Role | URL |
|------|------|-----|
| SZD GAMS | Digital edition (reference) | stefanzweig.digital |
| Klawiter Bibliography | Publication bibliography | chpollin.github.io/klawiter-rescue |
| SZD GitHub | Nachlass ontology (planned) | chpollin.github.io/SZD |

All three share the GAMS institutional color palette (burgundy/gold/cream), Source Serif 4 + Source Sans 3 typography, and a shared Verbund navigation bar. See [[frontend#zweig-forschungsverbund]] for design details.

A separate research project is planned to develop a Nachlass ontology aligned with CIDOC-CRM that bridges both the SZD and Klawiter data models.

## EIL Curation Interface

The Expert-in-the-Loop (EIL) curation interface enables manual validation and correction of extracted data:

- **edit.js**: Localhost-only edit mode (`location.hostname === 'localhost'`) enabling inline field editing with provenance awareness
- **Provenance badges**: Visual indicators (regex/llm/missing) on publisher, location, translator, pageCount fields, driven by `_provenance` metadata from `inject_provenance.py`
- **JSON patch export**: Edits are collected as JSON patches and exported for review, not written directly to the dataset
- **GitHub Actions validation**: `.github/workflows/validate-patch.yml` runs patch format checks, frontend JSON integrity, regression tests, and quality report comparison on PRs

The EIL approach supports the Data Integrity Principle: corrections go through a review process with provenance tracking, rather than being applied silently.

### Two EIL Roles

The workflow distinguishes two complementary feedback loops that operate at different levels:

**Developer-in-the-Loop.** The DH developer works at pipeline level: reading test results and aggregated data diagnostics, identifying systematic errors (e.g. 1,368 section-header titles), implementing code fixes, re-running the pipeline. Feedback signal: tests and data visualisations. Output: systematic improvements affecting thousands of entries at once.

**Editor-in-the-Loop.** Domain experts at the archive work at data level: checking individual entries against raw text, correcting or adding field values, validating reconciliation proposals. Feedback signal: domain knowledge about Zweig's oeuvre and publication history. Output: individual corrections that, in aggregate, form the gold standard.

The two loops interlock: when the editor systematically corrects the same error type (e.g., wrong publishers on multi-edition pages), that signals the developer to improve the pipeline. When the developer solves multi-edition decomposition, the editor's correction effort decreases.

## DIA-XAI Connection

This project is EIL-Tool 1 in the DIA-XAI project (PLUS Early Career Grant 2025). The Klawiter verification workflow with provenance badges, confidence ranking, and Accept/Correct/Add actions is a mandatory deliverable. EQUALIS evaluation metrics (see [[data#equalis-metrics]]) measure the editor loop: Accept/Correct/Add ratio by provenance (regex/llm/missing), correction distribution by entity type and field, ratio shift across EIL iterations. No time-based metrics — ratios are measured as a byproduct of editor actions, not in controlled experiments.
