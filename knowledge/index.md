---
title: Klawiter Bibliography
aliases: [MOC, map of content, index]
tags: [index]
created: 2026-04-12
updated: 2026-07-18
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
- [[edition-model]] — Work/edition split for multi-edition pages, edition IDs, PROV/OA/SHACL layers, the llmprov profile (decision basis for the multi-edition operator gate)

## Frontend

- [[frontend]] — Design system, personas, user stories, views, components, routing
- [[exploration]] — D3.js interactive visualization: Timeline, Geography, Connections
- [[eil-editing]] — In-tool expert editing design: Accept/Correct/Add, persistence, traceability (DIA-XAI EIL-Tool 1)
- [[production-readiness]] — Concept for the production-ready EIL curation tool: two loops, provenance layers, gold standard, work packages, operator gates

## Quality

- [[testing]] — Test strategy in seven categories, what the suite can and cannot guarantee
- [[validation]] — Field-level fidelity check against source (M3.8): four error classes, Weimar root cause, provenance distribution

## Process

- [[journal]] — Work diary, one entry per session (from 2026-03-29)
- [[HANDOFF]] — Transient re-entry note for a fresh instance; overwritten each handoff

## Reference

- [[references]] — Academic literature, standards, tools

---

## Where the open work lives

The current operational state, the next step, and the open operator decisions live in [[HANDOFF]], not here; the navigation index carries no volatile status counts. The work packages toward the production-ready curation tool are ordered and scoped in [[production-readiness]]. The technical findings each package builds on live in their function documents:

- Field-level error classes and the Weimar location root cause in [[validation]]
- Multi-edition page decomposition and other pipeline limits in [[pipeline#known-limitations--multi-edition-pages]]; the work/edition target model that resolves it in [[edition-model]]
- Wikidata reconciliation state and the `locationSameAs` field in [[data#wikidata-reconciliation]]
- Deployment and citability (routes, DOI, Verbund link) in [[production-readiness]] work package Deployment
