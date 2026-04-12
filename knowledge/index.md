---
title: Klawiter Bibliography
aliases: [MOC, map of content, index]
tags: [index]
created: 2026-04-12
updated: 2026-04-12
---

# Klawiter Bibliography Knowledge Base

Map of Content for the project documentation vault.

## Project Context

- [[about]] — Project provenance, Data Integrity Principle, Forschungsverbund, EIL curation

## Data & Pipeline

- [[data]] — Data model, 16 entity types, field coverage, known quality issues
- [[pipeline]] — 7-step extraction, encoding fix, regex patterns, data flow diagram
- [[architecture]] — 6 key technical decisions with rationale

## Semantics

- [[ontology]] — Schema.org + Dublin Core + klawiter: vocabulary blend, JSON-LD @context

## Frontend

- [[frontend]] — Design system, personas, user stories, views, components, routing
- [[exploration]] — D3.js interactive visualization: Timeline, Overview, Connections

## Quality

- [[testing]] — 326 tests, 5-category strategy, what we can and cannot guarantee

## Process

- [[journal]] — Work diary, 12 sessions (2026-03-29 to 2026-04-12)

## Reference

- [[references]] — Academic literature, standards, tools

---

## Open Items

Remaining items from the original project plan (milestones M1-M8 all complete, M5 out of scope).

### Manual Validation (M3.8)

- [ ] Browse 50+ entries in frontend, stratified by type, language, time period
- [ ] Compare displayed fields against raw wiki content
- [ ] Document accuracy: true positives, false positives, false negatives
- [ ] Fix any systematic extraction errors found

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

### Housekeeping

- [ ] Remove empty v2/ directory
- [ ] Remaining ~170 publisher + ~96 location FP in verification (encoding comparison artifacts, not real errors)
