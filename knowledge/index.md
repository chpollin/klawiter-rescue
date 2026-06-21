---
title: Klawiter Bibliography
aliases: [MOC, map of content, index]
tags: [index]
created: 2026-04-12
updated: 2026-06-21
---

# Klawiter Bibliography Knowledge Base

Map of Content for the project documentation vault.

## Project Context

- [[about]] — Project provenance, Data Integrity Principle, Forschungsverbund, EIL curation

## Data & Pipeline

- [[data]] — Data model, 16 entity types, field coverage, known quality issues
- [[pipeline]] — 8-step extraction, encoding fix, regex patterns, data flow diagram
- [[architecture]] — 6 key technical decisions with rationale

## Semantics

- [[ontology]] — Schema.org + Dublin Core + klawiter: vocabulary blend, JSON-LD @context

## Frontend

- [[frontend]] — Design system, personas, user stories, views, components, routing
- [[exploration]] — D3.js interactive visualization: Timeline, Geography, Connections
- [[eil-editing]] — In-tool expert editing design: Accept/Correct/Add, persistence, traceability (DIA-XAI EIL-Tool 1)

## Quality

- [[testing]] — 445 tests, 7-category strategy, what we can and cannot guarantee
- [[validation]] — Field-level fidelity check against source (M3.8): four error classes, Weimar root cause, provenance distribution

## Process

- [[journal]] — Work diary, 17 sessions (2026-03-29 to 2026-06-21)

## Reference

- [[references]] — Academic literature, standards, tools

---

## Open Items

Remaining items from the original project plan (milestones M1-M8 all complete, M5 out of scope).

### Manual Validation (M3.8)

Started Session 17, findings in [[validation]]. Error classes and mechanisms confirmed; the Weimar fix is designed and measured but not yet landed; per-field error rate across a stratified sample still open.

- [x] Browse entries in frontend, identify systematic error classes (see [[validation]])
- [x] Compare displayed fields against source text shown per entry
- [x] Design and measure the Weimar location fix (constrain extraction to publication line; diffed across all records, see [[validation]] class 1)
- [ ] Land the location fix: handle state codes, bracket alternates, and source mojibake; recover the 508 non-Western locations; pair with title/mojibake repair
- [ ] Extract location for the headerless excerpt entries (`[City, year]` bracket, separate path)
- [ ] Measure per-field error rate on a stratified sample (triage calibration input)

### Performance (M6.5)

- [ ] Measure initial load time (~9 MB JSON)
- [ ] Evaluate lazy loading if needed

### Accessibility (M6.6)

- [ ] WCAG 2.1 AA audit
- [ ] ARIA landmarks and labels

### Deployment & Publication (M7)

- [ ] Test live deployment: verify all routes, search, data loading
- [ ] Consider Zenodo deposit for DOI
- [ ] Add link from Stefan Zweig Digital to Klawiter bibliography (coordinate with project team)
- [ ] Announce / publish

### Wikidata Reconciliation Follow-up (Session 15)

- [ ] Manual review of 22 unmatched locations (encoding variants, composite slash-locations, obscure villages) + 3 low-score matches
- [x] Add `locationSameAs` field with Wikidata URIs to the JSON-LD output — done in Session 16 (`klawiter:locationSameAs`, see [[data#wikidata-reconciliation]])

### Browser Verification (Session 15 features)

- [ ] Browser-test new Explore features: Timeline Sparklines/Ranks modes, Geography Globe/Flat toggle, semantic zoom, Connections two-level drill-down

### Future Project

- [ ] Multi-edition page decomposition (LLM-based edition-block segmentation) — separate project, see [[pipeline#known-limitations--multi-edition-pages]]

### Housekeeping

- [ ] 170 publisher + 96 location verification false positives (encoding-comparison artifacts vs. raw text, not real extraction errors)
