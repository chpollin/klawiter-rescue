---
title: "Merged Klawiter bibliography: model and plan"
status: maintained
language: en
created: 2026-10-23
updated: 2026-10-24
related: [print-volumes, data, about, production-readiness]
---

# Merged Klawiter bibliography: model and plan

The compiler carried the Stefan Zweig bibliography through several states: the main volume of 1991, Addendum I of 1999, the unpublished working file of Addendum II, and the wiki begun in December 2008 as the latest state. The first bibliography of 1965 is available as an open-access reissue of 2020 under a non-commercial, no-derivatives licence and is held locally beside the print volumes; it is not yet used. Which statements exist only in print, only in the wiki or in both is unknown. This strand reconstructs the print volumes as structured research data, relates them to the wiki records and derives from both a merged Klawiter bibliography in which every statement keeps its source, for delivery to Stefan Zweig Digital. The result is a curated bibliographic dataset. It is no scholarly edition, since its object is the bibliographic information, not the compiler's text and its transmission. How the print volumes are built is recorded in [Print volumes](print-volumes.md); this document holds the model, the way results are checked, the plan and the open questions.

## Principles

- The sources stay as they are. Every record is bound to exactly one source (a print volume or the wiki) and keeps its location and raw text. Records are never merged.
- What belongs together is stated as a claim between records, with evidence, producer and status, using the states `proposed`, `confirmed` and `contested` of the reconciliation layer ([Data](data.md)).
- An LLM proposes claims. A claim is confirmed only by an exact deterministic rule or by a person. Contested claims stay visible in the data and in the merged bibliography.
- The curated work index of Stefan Zweig Digital is linked, never extended. Klawiter becomes an object of its own there.
- The interface is built so that people like working with the data in it. Review decisions arise from that work, and no budget of review hours is planned or measured (operator, 2026-10-24). What the interface can be judged by is the cost of a decision: how many actions a value takes, whether the evidence stands beside it, and whether a key ever acts on something not in view.

## Record model

The units of the sources (entry, heading and reference unit, wiki page, described object, publication, work, value) are defined once in [Data](data.md), one model across print and wiki. The terms below add what the merge needs.

Entry
: A place in a print volume as the compiler set it, with volume, page, address where one exists, and unaltered text. The entry is the evidence every later statement points back to.

Object
: A publication, printing, article, letter holding or event that an entry describes. An entry describes none, one or several objects (a collected edition with its printings, a reprint list, the reviews of a review entry), and each object belongs to exactly one entry. Numbered sub-items such as "[5]." and volume lines such as "Vol. 2." are objects inside their entry, and so is a further printing a label introduces ("FIE: 266p. 1950"). An object records how it relates to the object it follows (reprint, excerpt, translation, edition, revised version, review, item). Its fields follow the schema described in [Print volumes](print-volumes.md), Structured objects.

Context
: Some objects inherit data from outside their entry, the imprint from a collection header or the host volume from an address ("in Romans et Nouvelles [BA1 5]"). The object keeps a link to that source and may carry the inherited value, marked as inherited.

Reference
: A reference unit ("**** … See A 167") describes no publication. Since 2026-10-24 it is held as one object of type reference, so that every unit except a heading has a structured record; the concordance skips it. Its addresses, like every address inside an entry, become edges of the reference network.

Group
: The records of different sources that describe one publication, derived from confirmed identity claims. A group is what users, citations and Stefan Zweig Digital point to, so it receives a stable identifier that is never reused, with a recorded history when groups split or join. The member records stay unmerged; a group holds no values of its own beyond the identifier and its membership.

The wiki side keeps its existing records, flat pages and the work/edition graph ([Data](data.md)). A print object and a wiki publication are the units a concordance relates.

## Claims

Every claim names its producer, and the producer's class keeps three kinds of statement apart: the compiler's own notation applied by rule (`[Correction to L 77]`, `[Cont. H 367]`, `Rep:`, the errata of Addendum I), editorial decisions by rule, LLM proposal or person (identity of a print object and a wiki publication, an essay about a work, a link to a work of the curated index), and external sources, which wait for an operator decision before they are used. A cited print address in the wiki is a relation of unknown type and counts as evidence for identity only after typing ([Print volumes](print-volumes.md), Print and wiki).

The claim schema of the reconciliation layer serves two entity types today and exists in two forms. A shared schema keyed by claim, with subject, predicate, object, evidence selector and hash, typed producer, the state `proposed` and the decision chain, precedes the first claims between records.

## Merged bibliography and delivery

The merged bibliography is a projection from claims and documented rules, rebuilt on every run. It shows each group with its member records and the source of every value, the deviations between sources side by side, and the open claims as open. One reading with filters by source and state serves the known uses. For statements of the main volume the state in which they arose cannot always be told, because its file is a working state after 1991 with insertions and partly applied errata; such statements carry the volume without a finer state.

The delivery shape is agreed with Stefan Zweig Digital on one sample object (an entry, three sources, a claim, a group) before a TEI profile is written, because Stefan Zweig Digital has no TEI schema and ingests TEI through its own content model (`cirilo:TEI.szd`), renders each object's TEI through its own stylesheet and derives RDF at ingest only for search. Neither Stefan Zweig Digital nor GAMS models claims, contested statements or statement provenance; uncertainty exists only as `@cert` on dates and does not reach the RDF. Two delivery routes follow from a survey of 2026-10-24: a TEI profile with an ODD, a new RDF branch and a page stylesheet on the side of Stefan Zweig Digital, or the validated JSON-LD with provenance kept as the canonical delivery and either converted to RDF/XML for a `cirilo:Ontology` object or kept external with stable group URIs that the work index links to. The second is smaller and loses nothing, and Stefan Zweig Digital decides between them on the sample object, for which page 54 with its wiki publication, two print records and their proposed claims is the candidate. The title matches between wiki and work index that Stefan Zweig Digital already holds are untyped and partly wrong; they enter as proposed claims and their file is superseded. The namespace of the Klawiter vocabulary differs between the two repositories: the Stefan Zweig Digital repository keeps the host used before 2026-03-29, which no longer resolves, and maps terms the vocabulary no longer has. It is unified once, on the namespace where the instance URIs will live permanently, before delivery.

## How results are checked

Self-consistency checks (number sequences, contents ranges, reference resolution) confirm the numbering and find references into gaps; they cannot show that boundaries between existing entries are right. A content check, comparing the title cited before an address with the opening of the target entry, tests those boundaries. Correctness of segmentation and fields is measured against a gold standard: pages annotated blind by two annotators, with a person deciding their disagreements and a control sample of their agreements. Agent annotators measure agreement, not correctness, until a person has decided. Checks are assigned by the kind of task (operator guidance of 2026-10-23). A deterministic check, such as near-verbatim alignment or the resolution of an address, needs no person. A simple check, such as an entry boundary or whether title, year and publisher agree between two lines, needs care but no domain knowledge. A complex check, such as edition against later printing, which translation is meant or what counts as an object, needs Zweig expertise, and only these cases go to specialists. A person who decides with a proposal in view tends to adopt it, so at least part of the human control sample is annotated blind, from the source page alone, before the person sees any annotation or method output; only that part measures correctness, the rest measures how often the person accepts proposals. Rules are developed on other pages than those they are measured on, and a sample is frozen before its results are inspected. Automatic confirmation rules are admitted only with a precision measured on a sample. Before delivery, the merged bibliography is tried on real research tasks. An independent skeptical review checks method, code and this document before each milestone closes.

Two kinds of invariant hold over all records, not only over test pages. A presence invariant asks whether a value occurs in its source; a relation invariant asks whether it occurs where the publication it describes is written. The review round of 2026-10-23 found eight defects in the published wiki data that every unit test had passed, each a value present in the source but taken from the wrong passage, or a whole class that a per-page fixture could not show. Each defect class therefore receives an invariant over all records, with known exceptions listed by identifier and reason so that a new case fails and a repaired one must leave the list. Fresh-context reviews of data fidelity, interface and tests run before each milestone and after each fix batch, and their findings count only after a check against code and data.

Print and wiki check each other's extraction. Where a print entry stood near-verbatim in a wiki revision and year and title agree, the print strand and the production pipeline have read related text independently, so comparing their remaining fields checks both extractors by rule, without a human gold standard (`p08_field_check`). Because that wiki text descends from the compiler's print file, agreement shows consistency of the two readings, not correctness against the book; a disagreement shows that at least one reading is wrong. The check carries for Addendum II, whose text reached the early wiki; for the main volume and Addendum I the aligned text is mostly translation or review lists pasted into work pages, and the pairs that survive the title gate are too few to measure.

## Goal

The merged Klawiter bibliography is reached when all of the following hold, checked against the files and not against reports:

- Every record of the four sources stands with a stable identifier and leads to where it stands, a print record to its PDF page and line, a wiki page to its permalink.
- Every value carries its passage, its producer and its state.
- Field correctness and the precision of the concordance are measured by persons on frozen samples under decision rules fixed before the measurement, and the agreement of two persons is reported on a shared subset.
- The merged reading shows each group with its member records, the source of every value, the deviations between sources side by side and the open claims as open.
- Wiki and print rebuild deterministically under their gates.
- What is published contains only what the rights decision of step 0 admits.
- The interface carries reading, review and citation, and the operator has accepted it on real tasks.

This list is the criterion of done since 2026-10-24, decided by the main instance under the operator's explicit delegation ([Production readiness](production-readiness.md), Operator principles).

## Steps

The steps of the merge are ordered by dependency, and [Plan](plan.md) sequences them into milestones. Step 0 runs alongside the others and blocks only publication. Step 3 decided that the concordance takes two routes.

| Step | Result | Accepted when | Depends on |
|---|---|---|---|
| 0 Frame | decisions on rights in the volumes and in derived data, admission of print as a source of values, delivery shape with Stefan Zweig Digital, publishing institution, vocabulary namespace | recorded in [Production readiness](production-readiness.md) | operator, Stefan Zweig Digital, rights holder |
| 1 Model and claim schema | the shared terms of [Data](data.md) (one model across print and wiki) and a shared claim schema with group identifiers. The concordance claims of step 7 were written before this schema and migrate into it. | existing gate artifacts and the concordance rebuild under the shared schema, identical or with a reasoned difference | operator |
| 2 Segmentation | print entries and their objects as records with stable identifiers | boundary and object scores on the frozen second sample, disagreements decided by a person | 1 |
| 3 Overlap experiments | how far early wiki revisions carry print text, how large the overlap is, which relation types cited addresses have | each question answered on a small counted sample | 2 |
| 4 Resolution tables | abbreviations, informant, periodical and repository sigla, section codes, each with its source location | every siglum used is resolved or listed as open | p01 |
| 5 Fields | every object a span-bound record with typed producer, inherited values marked | precision and misses per field and volume from the human round, under the rule fixed before it | 2, 4 |
| 6 Compiler claims | references typed, errata of Addendum I and Addendum II title references parsed, index addresses resolved | every address and erratum resolved or listed as open | 1, 2 |
| 7 Concordance | a pipeline stage that keeps every candidate `proposed`, rule classes for automatic confirmation, a report of what exists only in print, only in the wiki or in both | report reproducible, precision per route and volume from the human round, recall on silver pairs | 3, 5, 6 |
| 8 Work and person links | links to the curated work index and to persons of Stefan Zweig Digital or the GND, through the existing reconciliation layer (`pipeline/lib/reconciliation.py`) with its candidates, decisions and open claims; existing title matches superseded | each link with evidence and state | 7 |
| 9 Adjudication | one local interface and one append-only decision log for values and for claims between records, with the chain from claim to print line or wiki revision. The card workbench of the [Print viewer](print-viewer.md) carries it; the edit mode of the production frontend keeps the field corrections of the wiki under its patch contract. | a person can follow a claim from evidence to decision and decide it | 1, 7 |
| 10 Projection and delivery | sample object agreed, projection, staging ingest, trial on research tasks. A TEI profile with ODD only if the agreed delivery shape needs TEI; otherwise the validated JSON-LD with provenance per value is the delivery. | deterministic rebuild, every statement traceable to claims, staging ingest succeeds | 0, 8, 9 |

## Measurement

Every human measurement follows rules fixed before its sample is opened, and under the operator's decision of 2026-10-24 nothing confirms automatically in this phase, so every confirmation is a person's.

Decision rule
: `confirmation_rule.json` holds two rules, one for the rule classes of the fields and one for the routes of the concordance. A class is bound to one volume and confirms only there. Only classes fixed as admissible before any decision may confirm, those with at least forty judged values or claims expected in the sample (`p13_review.py --fix-rule`, which refuses once the log or a blind sheet holds anything). The rule records the code it was fixed on, and a change of that code invalidates it until the classes are fixed again. A class would confirm when the lower bound of its object-resampled interval, at the level Holm's correction over the admissible classes assigns, exceeds the threshold. Both thresholds are null.

Reviewers
: Precision comes from the first reviewer of each object. A second person decides a subset of forty objects marked in advance without seeing the first person's decisions and measures agreement only, as raw agreement, Cohen's kappa per kind of decision and the positive specific agreement on corrections. A third person or the operator settles each disagreement by an adjudication that names both decisions and the one that stands. Reports give reviewer 1, reviewer 2 and the adjudicated state, and the export follows the adjudicated state. Until a second person exists, the field figure is acceptance by one reviewer after inspection. Agent annotators never replace the second person.

Estimates
: Values of one object are not independent, so precision is reported per value and per object with intervals from resampling objects. Beside it stand precision with open values counted as wrong and recall over complete objects. Because the review sample draws a few objects from parts of very different size, a Horvitz-Thompson estimate weighted by part size stands beside the unweighted figures. Entries the sample excluded as hard form a stratum of their own, reported apart and joined in one population estimate. An object marked with a wrong boundary leaves the field figures and enters a boundary rate.

Concordance
: The blind answers are compared with the proposals the current claims make at measurement time, and each entry is weighed by its inclusion probability in both blind samples. A second, non-blind phase decides the claims of those entries one by one, and only it gives claim precision per route and volume. The supplement brings the title-year route to forty claims per volume, while the field route falls short in every volume and is therefore not admissible. Near-verbatim alignment is a deterministic check and has no route rule. Silver pairs are a development metric.

Stability
: Identifiers of a frozen sample stay valid across rebuilds. A moved identifier needs a remap entry with its reason, and a changed fingerprint (the entry hash, and for an object its span) needs a rehash entry with its reason. Every report names the commit and the gate result it ran on.

The human round runs in the card workbench in this order, so that the blind part stays blind:

1. Both blind sheets of `p09_human_sample`, from the print entry alone.
2. The claim sheet of p09, which is written only once both blind sheets are complete.
3. The review sample and its stratum of hard entries, value by value, with the second person on the marked subset.
4. The disagreements of the segmentation benchmark.

## Milestones

The milestones of the merge, their entry and exit conditions and their state live in [Plan](plan.md).

## Open questions

Frame and delivery
- May structure and values derived from the print volumes be published, including the unpublished Addendum II, and does the existing CC BY permission for the compiled wiki content cover them? Answered by the operator with the rights holder; a no limits delivery to wiki values, addresses and claims.
- Does print become a second admitted source of values? Answered by the operator; a no keeps print values internal and makes the merged bibliography a concordance.
- What does Stefan Zweig Digital accept as an object, does it want open claims in it, and which stylesheet renders it? Answered by Stefan Zweig Digital on the sample object; the answer decides between claims in TEI and a separate data stream.
- Which institution publishes the merged bibliography, given that the project documents name the Literaturarchiv Salzburg and the delivery targets Stefan Zweig Digital in GAMS? Answered by the operator.

Model
- Is one group identifier per publication the right unit for citation and linking? Answered by the operator with a domain expert.
- Do unnumbered units such as collection headers and commentary paragraphs become entries of their own or context of the following entries? Answered by data analysis and the operator.

Data
- The three overlap experiments of step 3 have a first answer on small agent-judged samples ([Print volumes](print-volumes.md), Print and wiki). Addendum II can be aligned with the early wiki revisions character by character, the main volume and Addendum I only through fields. The overlap is partial: book editions mostly overlap, periodical items mostly exist in print only. A cited address is never evidence for identity. The concordance of step 7 therefore takes two routes, alignment for Addendum II and title-and-year blocking with a second agreeing field for the other volumes, and it matches print entries also against the contents lines of the wiki, not only its publications. Does the first answer hold on a larger sample checked by a person? Answered by the human control of step 7.
- The bibliography of 1965 has one running numbering with insertions marked by a letter suffix and an addenda block, Roman sections that map onto the 1991 sections only approximately, its own shorter periodical sigla, and an OCR text layer whose figures are unreliable. Neither the 1991 volumes nor the 1965 volume cite the other's numbers, so a concordance from print addresses to 1965 numbers has to be built by matching title, year and imprint, with typed relations (same publication, other edition, contains) as `proposed` claims, beginning with the primary works. Its sigla do not resolve the 1991 sigla by identity, though its full titles may suggest readings as proposals. How far does such a concordance reach, measured on a sample? Answered after the OCR route is chosen (fresh OCR or digit correction).
- What do `G 379*` and the end of section D at 223 against 227 in the contents mean? Answered by a domain expert or further print evidence.

Use
- Research cites the bibliography mostly without a locator, and where it locates, by page, by print address or by both; the trade cites print addresses systematically, and the wiki is cited as a website only ([About](about.md), How the bibliography is cited). Should the group identifier carry the print address and the 1965 number as citable aliases? Answered by the operator with a domain expert.
- Which research tasks must the merged bibliography support, now that the owner's own research case was withdrawn? Answered by the operator and Stefan Zweig Digital; the tasks become the trial before delivery.
- Should authors and translators link to the person index of Stefan Zweig Digital? Answered by Stefan Zweig Digital.
