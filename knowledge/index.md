---
title: Klawiter Bibliography
aliases: [MOC, map of content, index]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: en
version: 1.0
tags: [index]
created: 2026-04-12
updated: 2026-08-21
authors: [Christopher Pollin]
related: [about, data, pipeline, frontend, production-readiness, review-0.9, testing, journal]
---

# Klawiter Bibliography – Project Knowledge

This file is the entry point into the canonical project knowledge. Here the repository describes durable decisions and the documented production state. Running figures come from `data/output/quality-report.json`, the gate manifests, `.github/baseline-metrics.json` and the test suite.

## Documents

| Document | Responsibility |
|---|---|
| [[about]] | subject, origin, responsibilities and publication frame |
| [[data]] | data levels, model, provenance, reconciliation and limits |
| [[pipeline]] | executable transformation, inputs, stages and repeatability |
| [[frontend]] | static research interface and Expert-in-the-Loop curation |
| [[production-readiness]] | ratified production contract, gate results, open points and Operator Points |
| [[review-0.9]] | verified finding list of the 0.9 release review, work list toward acceptance |
| [[testing]] | test layers, quality evidence and limits of what is asserted |
| [[journal]] | chronological decisions and completed working sessions |

## Reading Paths

- Re-entry: [[journal]] → [[production-readiness]] → `git status -sb`.
- Production run: [[pipeline]] → [[testing]] → [[data]].
- Data model and contested statements: [[data]] → [[production-readiness]].
- Interface and curation: [[frontend]] → [[data#Correction Protocol]].
- Project context: [[about]] → [[production-readiness]].

## Authority and Maintenance

`README.md` is the executable user manual. `CLAUDE.md` is the single repository-specific agent instruction. Where statements conflict, code, versioned decision inputs and generated validation reports take precedence over descriptive documentation. Historical statements in the [[journal]] are preserved as a record and do not automatically hold as the current state.
