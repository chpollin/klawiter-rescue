---
title: About
aliases: [project context, klawiter, provenance]
tags: [project, context]
created: 2026-03-29
updated: 2026-04-12
---

# About

## The Klawiter Bibliography

The bibliography was compiled by **Dr. Randolph J. Klawiter** (University of Notre Dame) over decades. It covers Stefan Zweig's global literary reception: 6,296 entries spanning first editions, translations, secondary literature, film adaptations, correspondence, and more — in over 40 languages, from 402 publication locations, across 200 years (1815-2020).

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
- Semantic enrichment via external authority data (Wikidata, GND, VIAF) is out of scope — see [[pipeline#reconciliation--out-of-scope]]

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
