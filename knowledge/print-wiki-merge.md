---
title: "Merged Klawiter bibliography: model and plan"
status: draft
language: en
created: 2026-10-23
updated: 2026-10-23
related: [print-volumes, data, about, production-readiness]
---

# Merged Klawiter bibliography: model and plan

The compiler carried the Stefan Zweig bibliography through several states: the main volume of 1991, Addendum I of 1999, the unpublished working file of Addendum II, and the wiki begun in December 2008 as the latest state. The first bibliography of 1965 is not available to the project. Which statements exist only in print, only in the wiki or in both is unknown. This strand reconstructs the print volumes as structured research data, relates them to the wiki records and derives from both a merged Klawiter bibliography in which every statement keeps its source and the revision states stay visible, for delivery as TEI to Stefan Zweig Digital. The result is a curated bibliographic dataset. It is no scholarly edition, since its object is the bibliographic information, not the compiler's text and its transmission. How the print volumes are built is recorded in [Print volumes](print-volumes.md); this document holds the model, the way results are checked and the plan.

## Principles

- The sources stay as they are. Every record is bound to exactly one source (a print volume or the wiki) and keeps its location and raw text. Records are never merged.
- What belongs together is stated as a claim between records, with evidence, producer and status, using the states `proposed`, `confirmed` and `contested` of the reconciliation layer ([Data](data.md)).
- An LLM proposes claims. A claim is confirmed only by an exact deterministic rule or by a person. Contested claims stay visible in the data and in the merged bibliography.
- The curated work index of Stefan Zweig Digital is linked, never extended. Klawiter becomes an object of its own there.

## Record model

Entry
: A place in a print volume as the compiler set it, with volume, page, address where one exists, and unaltered text. The entry is the evidence every later statement points back to.

Object
: A publication, printing, article, letter holding or event that an entry describes. An entry describes none, one or several objects (a collected edition with its printings, a reprint list, the reviews of a review entry), and each object belongs to exactly one entry. Numbered sub-items such as "[5]." and volume lines such as "Vol. 2." are objects inside their entry.

Context
: Some objects inherit data from outside their entry, the imprint from a collection header or the host volume from an address ("in Romans et Nouvelles [BA1 5]"). The object keeps a link to that source and may carry the inherited value, marked as inherited.

Reference
: A cross-reference entry ("**** … See A 167") is an entry without an object. Its addresses, like every address inside an entry, become edges of the reference network.

The wiki side keeps its existing records, flat pages and the work/edition graph ([Data](data.md)). A print object and a wiki publication are the units a concordance relates.

## Claims

Claims connect records and come in three classes, which the merged bibliography keeps apart.

| Class | Producer | Examples |
|---|---|---|
| Compiler | the compiler's own notation, applied by rule | `[Correction to L 77]`, `[Cont. H 367]`, `Rep:`, the errata of Addendum I |
| Editorial | rule, LLM proposal, person | print object and wiki publication describe the same publication; an essay is about a work; an entry refers to a work of the curated index |
| External | sources outside the compiler's work | a match in a national library catalogue, labelled as such |

A cited print address in the wiki is a relation of unknown type and counts as evidence for identity only after typing ([Print volumes](print-volumes.md), Print and wiki). Groups of records that describe the same publication are derived from confirmed identity claims only and are never stored as records of their own.

## Merged bibliography and delivery

The merged bibliography is a projection from confirmed claims and documented editorial rules, rebuilt on every run. It follows the compiler's section order, records for each statement the state in which it arose, its corrections, the deviations between sources and the open claims, and can be produced in several readings, from the compiler's text alone to a version with labelled external additions. It is exported as TEI under a profile of its own, since Stefan Zweig Digital has no TEI schema and no construct for claims, and as JSON-LD for the frontend. The title matches between wiki and work index that Stefan Zweig Digital already holds enter as proposed claims.

## How results are checked

Self-consistency checks (number sequences, contents ranges, reference resolution) confirm the numbering and find references into gaps; they cannot show that boundaries between existing entries are right. Correctness is measured against a gold standard: pages annotated blind, without access to rules or results, by two annotators, with a person deciding their disagreements and a control sample of their agreements. Rules are developed on other pages than those they are measured on, and a sample is frozen before its results are inspected. An independent skeptical review checks method, code and claims of this document before each milestone closes.

## Plan

| Step | Result | Accepted when |
|---|---|---|
| 1 Model | this document | the operator confirms the record model |
| 2 Segmentation | every print entry and its objects as records, with stable identifiers | boundary and object scores on a fresh benchmark, residue listed for review |
| 3 Fields | title, persons with roles, imprint, extent, date and language per object, context resolved | field accuracy on the benchmark |
| 4 Compiler claims | references, corrections, continuations and errata as claims | every address resolved or listed as open |
| 5 Wiki anchor | print addresses mined from the wiki revision history, typed | anchors with their relation type |
| 6 Concordance | identity candidates between print and wiki and within print | candidates with evidence and producer, report of what exists only in print, only in the wiki or in both |
| 7 Review tool | inspect, verify and create claims, view the chain of evidence | a person can follow a claim from evidence to decision |
| 8 Merged bibliography | TEI and JSON-LD projection with notes on states, corrections and deviations | deterministic rebuild, every statement traceable to claims |
| 9 Delivery | TEI profile, object of its own in Stefan Zweig Digital | staging ingest, subject to rights and agreement with Stefan Zweig Digital |

The claim schema of the reconciliation layer serves two entity types today and exists in two forms. A shared schema keyed by claim, with subject, predicate, object, typed producer and the state `proposed`, precedes step 4.

## Next milestone: segmentation measured

The milestone closes step 2 for the three volumes.

- Rules for numbered sub-items and volume lines on lines of their own, and for wrapped continuation lines, built on development pages, which include the first benchmark pages.
- Objects read from sub-items and printings instead of counted by citation patterns.
- A second benchmark sample, drawn before the rules are evaluated, stratified by volume and section, oversampling hard cases with recorded weights, larger in Addendum II, disjoint from the development pages.
- Two blind annotations of that sample and a list of disagreements between annotators and between method and annotators for a human decision.
- An independent review of rules, scores and this document.

The milestone is reached when boundary and object scores on the second sample are reported per volume against both annotators, the annotators' agreement is reported beside them, and the disagreement list is ready for a human decision. The scores are reported as measured; no threshold is set in advance.

## Open decisions

- Confirmation of the record model above.
- Whether print becomes a second admitted source of bibliographic values; claims between records do not require it, a merged view that shows print values beside or instead of wiki values does.
- Whether and under which label external additions enter.
- Rights in the print volumes and in data derived from them, before any publication.
- Profile, object and the treatment of open claims, agreed with Stefan Zweig Digital.
