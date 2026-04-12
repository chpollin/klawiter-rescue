---
title: References
aliases: [bibliography, literature, sources]
tags: [references]
created: 2026-04-12
updated: 2026-04-12
---

# References

Academic literature, standards, and tools referenced in this project.

## Data Pipeline Testing

- [OpenCitations: Validating bibliographic data](https://arxiv.org/html/2504.12195) — 4-level validation (wellformedness, ID syntax, existence, semantics)
- [Golden Tests for Data-Driven APIs](https://medium.com/@nidhipandya1606/golden-tests-how-a-small-set-of-real-inputs-helped-me-keep-a-data-driven-api-correct-through-0926b6384e9f) — 6 bug categories caught by golden files
- [Integration Tests for Python Data Pipelines](https://www.startdataengineering.com/post/python-datapipeline-integration-test/)
- [LOD Quality Assessment for GLAM](https://www.semantic-web-journal.net/system/files/swj4008.pdf) — completeness as core quality dimension
- [Pandera](https://pandera.readthedocs.io/) — DataFrame schema contracts
- [Hypothesis](https://github.com/HypothesisWorks/hypothesis) — property-based testing / fuzzing
- [Risk-Based Data Quality Testing (Vinted)](https://vinted.engineering/2026/03/11/risk-based-testing/) — threshold calibration

## Information Visualization

- Shneiderman, B. (1996). "The Eyes Have It: A Task by Data Type Taxonomy for Information Visualizations." IEEE Symposium on Visual Languages.
- Moretti, F. (2005). *Graphs, Maps, Trees: Abstract Models for Literary History.* Verso.
- Jaenicke, S. et al. (2015). "On Close and Distant Reading in Digital Humanities." Eurographics Conference on Visualization.

## Ontology & Vocabulary Standards

- [Schema.org](https://schema.org/) — Web vocabulary for structured data (adopted)
- [Dublin Core Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) — Citation and provenance (adopted)
- [BIBFRAME](https://www.loc.gov/bibframe/) — Library of Congress bibliographic framework (evaluated, not adopted: no official JSON-LD context)
- [CIDOC-CRM](https://www.cidoc-crm.org/) — Conceptual reference model for cultural heritage (evaluated, not adopted: event-centric overkill for bibliographic records)
- LRMoo v1.0 (IFLA, April 2024) — Library Reference Model OO extension (evaluated, not adopted: no production-ready JSON-LD tooling)
