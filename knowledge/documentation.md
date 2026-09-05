---
title: Documentation Ownership and Maintenance
status: maintained
language: en
updated: 2026-09-05
---

# Documentation ownership and maintenance

Project prose is English, following the operator's August 2026 decision. Historical source titles and persistent identifiers retain their original language. Markdown frontmatter describes document maintenance, not product completion: maintained guides use `status: maintained`; reviews and the journal are historical evidence.

## Responsibility map

| Files | Treatment |
|---|---|
| `README.md` | setup, common commands, concise project introduction and links |
| `CLAUDE.md` | sole repository agent instruction; no parallel AGENTS.md |
| `knowledge/index.md` | navigation and reading paths |
| `knowledge/status.md` | current assessment, volatile evidence snapshot and prioritized next steps |
| `knowledge/about.md` | origin, roles, mandate and citation context |
| `knowledge/data.md` | source scope, entity/field meanings, uncertainty, provenance and curation boundaries |
| `knowledge/pipeline.md`, `pipeline/README.md` | canonical stage architecture; local quick entry links back to it |
| `knowledge/frontend.md` | actual routes, interaction and export contracts |
| `knowledge/testing.md` | verification layers, test/oracle maintenance and limits |
| `knowledge/production-readiness.md` | ratified decisions and measurable acceptance contract |
| `.github/ISSUE_TEMPLATE/*.md` | explicitly labelled proposals; point to current scope and avoid claims of implemented evaluation features |
| `data/corrections/README.md` | exact patch-store examples, validation and replay semantics |
| `knowledge/journal.md` | append a newest-first session; preserve old statements as history |
| `knowledge/review-0.9.md`, dated `knowledge/*review*.md`, `knowledge/independent-evaluation-2026-09-05.md`, `knowledge/technical-remediation-2026-09-05.md` | dated reviews/change evidence; add a current-status pointer, preserve original findings |
| `knowledge/evaluations/2026-09-05/*.md` | independent review and owner worksheet; maintain manifest hashes when bytes change |
| `data/output/edition-samples/REVIEW.md`, `data/output/unmatched_locations_review.md` | evidence tied to its sampled/generated data; preserve as an artifact, not a live project guide |

Vendored dependency notices and the unchanged raw archive are not project prose to rewrite. Review every authored guide for contradictions; do not rewrite every Markdown file merely to make it look new.

## Updating a fact

1. Check the responsible code, versioned decision or generated report.
2. Update the owning guide; replace duplicate explanations with links where useful.
3. Put volatile corpus/test figures in Status with their date and source artifact. Keep sample counts in dated evidence.
4. Record a changed contract or verified implementation in the latest journal entry.
5. Check relative links, knowledge wikilinks, commands and text hashes. Use LF for versioned text, including evaluation JSON; hashes must survive Git checkout on another platform.

Source decisions, expected semantic values and observed incorrect baselines are separate records. A documentation edit must not silently ratify a modelling choice, remove a source finding or declare a release.

## Authority and evidence

Executable code plus versioned decisions and generated validation reports outrank prose claims about implementation. Ratified domain decisions outrank an assistant's inferred convention. If they disagree, document the gap rather than rewriting the decision as if implementation already complied.

CI compares its named deterministic artifact paths and now also checks the stable contents of both gate manifests against their committed HEAD blobs, with every referenced input/artifact hash. Explicitly timestamped content has a narrow allowance; its bytes must match the current manifest. This closes the formerly omitted candidate/queue comparison. A local explicit reference snapshot is review evidence, not a substitute for the eventual committed freeze or a successful remote CI run.
