---
title: Project Context
aliases: [about, project context, klawiter, provenance]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: maintained
language: en
version: 1.0
tags: [project, context, provenance]
created: 2026-03-29
updated: 2026-09-05
authors: [Christopher Pollin]
related: [data, pipeline, frontend, testing, production-readiness]
---

# Project Context

## Subject and Origin

Randolph J. Klawiter compiled an international Stefan Zweig bibliography at the University of Notre Dame. The transmitted MediaWiki holdings contain first editions, translations, secondary literature, film adaptations, correspondence and further publication forms in more than 40 languages. After the wiki was decommissioned, an SQL dump and eight binary text stores remained.

From these the project reconstructs a static research interface, complete JSON-LD holdings and a source-bound curation layer. The source stays unmodified. All transformations are produced from versioned code, frozen inputs and traceable decisions.

## Responsibilities

- Randolph J. Klawiter is the author of the bibliography.
- Christopher Pollin is responsible for the digital edition, data model, software and documentation.
- Stefan Zweig Digital supplies the scholarly and institutional context as well as the frozen SZD work index for reconciliation candidates.
- Automated and agentic checks supply evidence. Institutionally content-changing work decisions remain with the responsible domain staff.

## Data Integrity

Bibliographic statements must be documented in the MediaWiki source. Source-conditioned gaps stay empty. Rule-based and frozen LLM extraction may only structure existing values. The frontend tracks provenance for publisher, location, translator and page count; this projection does not yet cover every field or every canonical artifact. Authority-data relations arise exclusively from documented `confirm` or `correct` decisions.

Uncertainty is a data state of its own. Contested statements have a stable identity, a documented occurrence, competing interpretations, review history and an open decision status. They belong to the final holdings, yet produce no confirmed relation.

## Research and Publication Frame

The methodological contribution consists in a lossless data rescue with two coupled control loops, systematic pipeline improvement through aggregated checks and object-level expert curation through versioned patches. This preservation claim concerns current page identity, not complete extraction of every bibliographic fact. [Current status](status.md) records that distinction and the remaining acceptance work. [[production-readiness]] describes the ratified contract, [[testing]] the reach of the evidence.

The deliverable subject comprises data, vocabulary, software, static interface, provenance and validation artifacts. A separate Klawiter blog post and a new Klawiter publication are not part of the repository mandate. The wiki/print merge, external live write-backs and institutional work decisions remain later options.

## Consortium and Design

The interface is connected with Stefan Zweig Digital and uses the established colour and typography language of the research consortium. The technical holdings stay independently deployable. Details are held in [[frontend]].

## Licenses and Citation

The code is licensed under MIT. Documentation and the structured edition are licensed under CC BY 4.0. `CITATION.cff` contains the machine-readable citation details; the bibliographic source must be credited expressly on reuse.
