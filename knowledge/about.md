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
updated: 2026-10-24
authors: [Christopher Pollin]
related: [data, pipeline, frontend, testing, production-readiness]
---

# Project Context

## Subject and Origin

Randolph J. Klawiter compiled an international Stefan Zweig bibliography at the University of Notre Dame. The transmitted MediaWiki holdings contain first editions, translations, secondary literature, film adaptations, correspondence and further publication forms in more than 40 languages. After the wiki was decommissioned, an SQL dump and eight binary text stores remained.

From these the project reconstructs a static research interface, complete JSON-LD holdings and a source-bound curation layer. The source stays unmodified. All transformations are produced from versioned code, frozen inputs and traceable decisions.

## Responsibilities

- Randolph J. Klawiter is the author of the bibliography.
- Christopher Pollin is responsible for the data rescue, data model, software and documentation.
- The Literaturarchiv Salzburg is the institution the bibliography is published with (operator decision of 2026-09-23). Its Stefan Zweig Digital initiative supplies the scholarly context as well as the frozen SZD work index for reconciliation candidates.
- Digital Humanities Craft, with Christopher Pollin as responsible editor, publishes the bibliography as open data (operator decision of 2026-09-08). The publication is titled "Stefan Zweig Bibliography", after the wiki, and cited as "Stefan Zweig Bibliography (Klawiter)" (operator decision of 2026-09-23). It is a data publication of the rescued bibliography, and the term digital edition is not used for it.
- Automated and agentic checks supply evidence. Institutionally content-changing work decisions remain with the responsible domain staff.

## Data Integrity

Bibliographic statements must be documented in the MediaWiki source. Source-conditioned gaps stay empty. Rule-based and frozen LLM extraction may only structure existing values. The frontend tracks provenance for publisher, location, translator and page count; this projection does not yet cover every field or every canonical artifact. Authority-data relations arise exclusively from documented `confirm` or `correct` decisions.

Uncertainty is a data state of its own. Contested statements have a stable identity, a documented occurrence, competing interpretations, review history and an open decision status. They belong to the final holdings, yet produce no confirmed relation.

## Research and Publication Frame

The methodological contribution consists in a lossless data rescue with two coupled control loops, systematic pipeline improvement through aggregated checks and object-level expert curation through versioned patches. This preservation claim concerns current page identity, not complete extraction of every bibliographic fact. [Current status](status.md) records that distinction and the remaining acceptance work. [[production-readiness]] describes the ratified contract, [[testing]] the reach of the evidence.

The deliverable subject comprises data, vocabulary, software, static interface, provenance and validation artifacts. A new Klawiter publication is not part of the repository mandate. The Klawiter blog post is written outside the repository, and its claim check against the repository is kept as evidence in `knowledge/evaluations/`. External live write-backs and institutional work decisions remain later options. The wiki/print merge is worked on since October 2026 as a strand outside the production run ([Merged bibliography](print-wiki-merge.md)); print addresses and evidenced claims join the production run as a frozen file without print text (decided on 2026-10-24 under the operator's delegation), and whether print values are delivered depends on the open decisions on rights in the print volumes and on admitting print as a source of values.

## Consortium and Design

The interface is connected with Stefan Zweig Digital and uses the established colour and typography language of the research consortium. The technical holdings stay independently deployable. Details are held in [[frontend]].

## How the bibliography is cited

A literature and trade sweep of 2026-10-24 read research texts, editions, reviews, dealer and auction catalogues and the data of Stefan Zweig Digital for the way they cite Klawiter. Most research cites the bibliography without a locator, as an entry in the reference list or a footnote such as "vgl. Klawiter 1991". Where a text locates a statement, it uses the print, by page (Stefan-Zweig-Handbuch, 2018), by print address (Meissenburg, 2010, "sub F 28") or by both, as the edition of the letters published by S. Fischer does ("S. 64 [D 156]"). The trade cites print addresses systematically, often beside the running number of the bibliography of 1965 ("Klawiter 136. Klawiter² I, F 46."), and research up to the 1980s and recent local history cite the 1965 numbers as well (Durzak, 1974). A bare "Klawiter" with a number is therefore ambiguous without its edition. Addendum I is cited by page, and no citation of an Addendum I address was found. The wiki is cited rarely and only as a website, once with page URLs of the Fredonia instance and no access date (de Brito, 2016). Those URLs now redirect to klawiter.stefanzweig.digital, where the main page answered 404 on 2026-10-24. Stefan Zweig Digital cites no Klawiter numbers, and no Zweig institution has published a citation recommendation.

The one contemporary review that describes the structure praises the system of references between sections and dates the coverage to the end of 1990 (Prater, 1991), against the publisher's "to 1988". No accessible review explains the asterisk convention, the informant sigla or the abbreviations, which therefore remain to be read from the volumes themselves.

This suggests that the print addresses of the main volume already work as identifiers in research and trade and belong in the merged bibliography as citable, resolvable aliases with volume, section and number, together with the 1965 number where a concordance supplies it. They cannot be the primary identifier, because they cover the print holdings only, were not continued in the addenda and the wiki, and relate to wiki pages in a relation of unknown type ([Print volumes](print-volumes.md), Print and wiki). The project has to set its own citation recommendation ([Merged bibliography](print-wiki-merge.md), Open questions).

## Licenses and Citation

The code is licensed under MIT. Documentation and the structured data are licensed under CC BY 4.0. Permission to publish the compiled bibliography under CC BY 4.0 exists, as the operator confirmed on 2026-09-23. `CITATION.cff` contains the machine-readable citation details; the bibliographic source must be credited expressly on reuse.
