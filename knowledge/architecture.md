# Architecture

Key decisions in the Klawiter project with rationale and trade-offs.

## 1. Domain-Specific Vocabulary Instead of Schema.org

**Decision**: Custom `klawiter:` namespace instead of Schema.org, Dublin Core, or BibFrame.

**Rationale**:
- The bibliography contains entity types without Schema.org equivalent (e.g. "Dramatic Reading", "Symposium")
- BibFrame (FRBR-based: Work/Instance/Item) would be correct but overengineering for this dataset
- Dublin Core is too flat (no type distinction)
- A domain-specific model can represent the data 1:1

**Trade-off**: Not directly machine-readable for library systems. Mapping to Schema.org is planned as a later step — see [[ontology]].

## 2. Direct File Extraction Instead of MySQL

**Decision**: Parse SQL dump and binary files directly in Python, without MySQL installation.

**Rationale**:
- Eliminates the largest external dependency
- Pipeline becomes portable (runs anywhere with Python 3.10+)
- The 4-table join (page → revision → slots → content) can be parsed directly from INSERT statements

**Trade-off**: The SQL parser is more fragile than native MySQL queries. But it works deterministically and achieves 99.99% extraction.

## 3. Vanilla JS Frontend Without Framework

**Decision**: HTML + Tailwind (CDN) + vanilla JS. No React, Vue, Svelte, or Astro.

**Rationale**:
- 4,751 entries are small enough for full client-side rendering
- No build step → directly deployable on GitHub Pages
- No CI/CD configuration needed
- FlexSearch + Chart.js cover search and visualization

**Trade-off**:
- ~4 MB JSON must be loaded entirely (no lazy loading)
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
