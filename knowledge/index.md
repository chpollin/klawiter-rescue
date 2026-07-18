---
title: Klawiter Bibliography
aliases: [MOC, map of content, index]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
template:
  name: Vorlage Index
  version: 0.1
  url: https://dhcraft.org/Promptotyping/promptotyping-document/index
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-index
status: complete
language: en
version: 0.3
tags: [index]
created: 2026-04-12
updated: 2026-07-18
authors: [Christopher Pollin]
related: [about, data, pipeline, frontend, production-readiness, testing, journal]
---

# Klawiter Bibliography Knowledge Base

Navigation node for the project knowledge base and the reading heuristic for its documents. This vault documents the data rescue of the Klawiter bibliography, addressed to a reviewer, a fresh coding agent, and the project maintainer returning after weeks. The current operational state and the open operator decisions live in the most recent entry of [[journal]], the volatile measured figures in their sources of truth (`data/output/quality-report.json`, `docs/data/klawiter.json` `_meta`, `.github/baseline-metrics.json`, and the pytest suite), never here.

## Documents

Each document carries one function. The function, not the file name, tells you which document to open for a given question.

| Document | Function | Reading it answers |
|---|---|---|
| [[about]] | Identity | What is this project, its provenance, the Data Integrity Principle, the Forschungsverbund and DIA-XAI frame |
| [[data]] | Material + model | The dataset: model, vocabulary blend, 16 entity types, entity fields, known quality issues, record census |
| [[pipeline]] | Bauweise + decisions | The extraction pipeline: source tables, 8 stages, extraction decisions, encoding fix, regex patterns, data flow |
| [[frontend]] | Gestalt + tool specification | Design system, personas, user stories, views, the exploration interface, and the EIL editing surface |
| [[production-readiness]] | Plan + gates + decision basis | The path to the production-ready curation tool: two loops, provenance layers, gold standard, work packages, operator gates, the work/edition decision basis |
| [[testing]] | Quality assurance | Test strategy in seven categories, field-level fidelity findings, what the suite can and cannot guarantee |
| [[journal]] | Genese | Work diary, one entry per session, holding the current operational state |

## Reading paths

- Onboarding a new contributor: [[about]] → [[data]] → [[pipeline]].
- Reproducing a data export: [[pipeline]] → [[data]] → [[journal]].
- Understanding the curation tool and its open decisions: [[frontend#eil-curation-interface]] → [[production-readiness]].
- Judging extraction quality: [[testing]] → [[data#record-census]].
- Resuming work: [[journal]] → [[production-readiness]].

## Convention

This knowledge base follows the convention for Promptotyping Documents. It regulates the frontmatter schema, the reading heuristic, and the structural principles against which every document is legible. See [[Konvention Promptotyping Documents]] in the vault.
