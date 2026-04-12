---
title: Architecture
aliases: [architecture decisions]
tags: [architecture, decisions]
created: 2026-03-29
updated: 2026-04-12
---

# Architecture

Key decisions in the Klawiter project with rationale and trade-offs.

## 1. Vocabulary Blend: Schema.org + Dublin Core + klawiter:

**Decision**: A blend of Schema.org (standard bibliographic fields), Dublin Core (citation/provenance), and a custom `klawiter:` namespace (domain-specific types and fields).

**Rationale**:
- Schema.org covers most standard bibliographic fields (name, datePublished, publisher, etc.)
- Dublin Core provides `bibliographicCitation` for the original entry text
- The bibliography contains entity types without Schema.org equivalent (e.g. "Dramatic Reading", "Symposium") — these use `klawiter:` types
- BibFrame (FRBR-based: Work/Instance/Item) would be correct but overengineering for this dataset
- Each entry gets a `@type` array combining a Schema.org type with a `klawiter:` type (e.g. `["schema:Book", "klawiter:FictionEntry"]`)

**Trade-off**: Not directly machine-readable for library systems. A vocabulary blend with Schema.org and Dublin Core has since been implemented — see [[ontology]].

## 2. Direct File Extraction Instead of MySQL

**Decision**: Parse SQL dump and binary files directly in Python, without MySQL installation.

**Rationale**:
- Eliminates the largest external dependency
- Pipeline becomes portable (runs anywhere with Python 3.10+)
- The 4-table join (page → revision → slots → content) can be parsed directly from INSERT statements

**Trade-off**: The SQL parser is more fragile than native MySQL queries. But it works deterministically and achieves 99.99% extraction.

## 3. Vanilla JS Frontend Without Framework

**Decision**: HTML + custom CSS (SZD design) + vanilla JS. No React, Vue, Svelte, or Astro.

**Rationale**:
- 4,751 entries are small enough for full client-side rendering
- No build step → directly deployable on GitHub Pages
- No CI/CD configuration needed
- FlexSearch + D3.js v7 cover search and visualization

**Trade-off**:
- ~9 MB JSON must be loaded entirely (no lazy loading)
- No SSR/SSG → no SEO for individual entries
- State management is manual (no reactive framework)

## 4. Redirects as Map Instead of Resolved Entries

**Decision**: 1,545 redirects are not integrated into main entries but stored as `{ "Title" → page_id }` map in the frontend.

**Rationale**:
- Redirects are not standalone content, but aliases
- The map enables URL resolution (`#title=Old+Name` → `#entry=123`)
- Keeps main data clean (4,751 real entries)

**Trade-off**: 314 redirects (20%) cannot be resolved because the target title does not exactly match an existing entry.

## 5. Encoding Fix Before Parsing

**Decision**: Mojibake is repaired in stage 2, before stage 3 parses fields.

**Rationale**: Regex patterns for title, publisher, location etc. only work on correct UTF-8. "Insel-Verlag" is recognized, "Insel-VÃ©rlag" is not.

## 6. page_title as Title Fallback

**Decision**: When title extraction from wiki markup yields a `[year]: Publisher` pattern, the MediaWiki page name is used instead.

**Rationale**: For collected-works entries, the publication info appears in the bold line (`'''[1922]: Insel-Verlag'''`), not the work title. The page_title always contains the correct work name.

**Result**: Bracket titles reduced from 1,579 (33%) to 33 (0.7%).
