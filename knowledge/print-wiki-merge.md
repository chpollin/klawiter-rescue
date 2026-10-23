---
title: "Merged Klawiter bibliography: model and plan"
status: draft
language: en
created: 2026-10-23
updated: 2026-10-23
related: [print-volumes, data, about, production-readiness]
---

# Merged Klawiter bibliography: model and plan

The compiler carried the Stefan Zweig bibliography through several states: the main volume of 1991, Addendum I of 1999, the unpublished working file of Addendum II, and the wiki begun in December 2008 as the latest state. The first bibliography of 1965 is not available to the project. Which statements exist only in print, only in the wiki or in both is unknown. This strand reconstructs the print volumes as structured research data, relates them to the wiki records and derives from both a merged Klawiter bibliography in which every statement keeps its source, for delivery as TEI to Stefan Zweig Digital. The result is a curated bibliographic dataset. It is no scholarly edition, since its object is the bibliographic information, not the compiler's text and its transmission. How the print volumes are built is recorded in [Print volumes](print-volumes.md); this document holds the model, the way results are checked, the plan and the open questions. Its plan was revised on 2026-10-23 after three independent agent reviews (constructive, critical, user and infrastructure needs), whose findings on code and documents the main agent checked.

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

Group
: The records of different sources that describe one publication, derived from confirmed identity claims. A group is what users, citations and Stefan Zweig Digital point to, so it receives a stable identifier that is never reused, with a recorded history when groups split or join. The member records stay unmerged; a group holds no values of its own beyond the identifier and its membership.

The wiki side keeps its existing records, flat pages and the work/edition graph ([Data](data.md)). A print object and a wiki publication are the units a concordance relates.

## Claims

Every claim names its producer, and the producer's class keeps three kinds of statement apart: the compiler's own notation applied by rule (`[Correction to L 77]`, `[Cont. H 367]`, `Rep:`, the errata of Addendum I), editorial decisions by rule, LLM proposal or person (identity of a print object and a wiki publication, an essay about a work, a link to a work of the curated index), and external sources, which wait for an operator decision before they are used. A cited print address in the wiki is a relation of unknown type and counts as evidence for identity only after typing ([Print volumes](print-volumes.md), Print and wiki).

The claim schema of the reconciliation layer serves two entity types today and exists in two forms. A shared schema keyed by claim, with subject, predicate, object, evidence selector and hash, typed producer, the state `proposed` and the decision chain, precedes the first claims between records.

## Merged bibliography and delivery

The merged bibliography is a projection from claims and documented rules, rebuilt on every run. It shows each group with its member records and the source of every value, the deviations between sources side by side, and the open claims as open. One reading with filters by source and state serves the known uses. For statements of the main volume the state in which they arose cannot always be told, because its file is a working state after 1991 with insertions and partly applied errata; such statements carry the volume without a finer state.

The delivery shape is agreed with Stefan Zweig Digital on one sample object (an entry, three sources, a claim, a group) before a TEI profile is written, because Stefan Zweig Digital has no TEI schema, ingests through its own content model and renders RDF through per-object stylesheets. The title matches between wiki and work index that Stefan Zweig Digital already holds are untyped and partly wrong; they enter as proposed claims and their file is superseded. The namespace of the Klawiter vocabulary differs between the two repositories and is unified before delivery.

## How results are checked

Self-consistency checks (number sequences, contents ranges, reference resolution) confirm the numbering and find references into gaps; they cannot show that boundaries between existing entries are right. A content check, comparing the title cited before an address with the opening of the target entry, tests those boundaries. Correctness of segmentation and fields is measured against a gold standard: pages annotated blind by two annotators, with a person deciding their disagreements and a control sample of their agreements. Agent annotators measure agreement, not correctness, until a person has decided. A person who decides with a proposal in view tends to adopt it, so at least part of the human control sample is annotated blind, from the source page alone, before the person sees any annotation or method output; only that part measures correctness, the rest measures how often the person accepts proposals. Rules are developed on other pages than those they are measured on, and a sample is frozen before its results are inspected. Automatic confirmation rules are admitted only with a precision measured on a sample. Before delivery, the merged bibliography is tried on real research tasks. An independent skeptical review checks method, code and this document before each milestone closes.

## Plan

The steps are ordered by dependency. Step 0 runs alongside the others and blocks only publication; step 3 decides how much of steps 5 to 7 is needed.

| Step | Result | Accepted when | Depends on |
|---|---|---|---|
| 0 Frame | decisions on rights in the volumes and in derived data, admission of print as a source of values, delivery shape with Stefan Zweig Digital, publishing institution, vocabulary namespace | recorded in [Production readiness](production-readiness.md) | operator, Stefan Zweig Digital, rights holder |
| 1 Model and claim schema | this record model confirmed, shared claim schema with group identifiers | existing gate artifacts rebuild under the shared schema, identical or with a reasoned difference | operator |
| 2 Segmentation | print entries and their objects as records with stable identifiers | boundary and object scores on the frozen second sample, disagreements decided by a person | 1 |
| 3 Overlap experiments | how far early wiki revisions carry print text, how large the overlap of print and wiki is, which relation types cited addresses have | each question answered on a small counted sample | 2 |
| 4 Resolution tables | abbreviations, informant, periodical and repository sigla, section codes, each with its source location | every siglum used is resolved or listed as open | p01 |
| 5 Fields | title, persons with roles, date, imprint and language per object first, further fields as the delivery needs them, inherited values marked | field accuracy on the benchmark | 2, 4 |
| 6 Compiler claims | references typed, errata of Addendum I and Addendum II title references parsed | every address and erratum resolved or listed as open | 1, 2 |
| 7 Concordance | identity candidates print and wiki and within print, rule classes for automatic confirmation with measured precision, report of what exists only in print, only in the wiki or in both | report reproducible, a sample checked by a person | 3, 5, 6 |
| 8 Work and person links | links to the curated work index and to persons of Stefan Zweig Digital or the GND, existing title matches superseded | each link with evidence and state | 7 |
| 9 Adjudication | the existing curation interface and patch store extended to claims between records, with the chain from claim to print line or wiki revision | a person can follow a claim from evidence to decision and decide it | 1, 7 |
| 10 Projection and delivery | sample object agreed, TEI profile with ODD, projection, staging ingest, trial on research tasks | deterministic rebuild, every statement traceable to claims, staging ingest succeeds | 0, 8, 9 |

## Milestones

The first milestone, segmentation measured, closed step 2 on 2026-10-23: boundary and object scores on the frozen second sample are reported per volume against two blind agent annotators, with the scorer faults found by an independent review corrected, and the disagreement list exists. Its human decision is open and waits for the person who carries the subject checks (Frame).

The next milestone, concordance measured, carries steps 5 to 7 far enough to judge the merge on all data.

- Fields that the concordance depends on are read better, first year and title (an author name before the title, a year inside the title, imprints in brackets), and inherited imprints count as a second field.
- The two routes of step 7 run over all records: alignment with every wiki revision, and title, year and a second field against the latest text and page titles, with field matches mapped to the wiki publication whose source slice holds them.
- Silver pairs, print entries that stood near-verbatim in some revision, measure the loss of the field route per volume; each field change is measured on them before it is kept.
- A report states what exists only in print, only in the wiki or in both, per volume and kind of publication.
- The errata of Addendum I are read as compiler claims.
- The matches are visible in the lab view of the AI operator from a local file that is never published ([Coordination](coordination.md)).
- A person with domain expertise annotates a small sample of print entries blind against the wiki, which gives the precision of both routes; an independent review checks method, code and this document.

The milestone is reached when recall on silver pairs and precision on the human sample are reported per route and volume and the overlap report exists. No threshold is set in advance; the figures decide which rule classes may confirm automatically.

## Open questions

Frame and delivery
- May structure and values derived from the print volumes be published, including the unpublished Addendum II, and does the existing CC BY permission for the compiled wiki content cover them? Answered by the operator with the rights holder; a no limits delivery to wiki values, addresses and claims.
- Does print become a second admitted source of values? Answered by the operator; a no keeps print values internal and makes the merged bibliography a concordance.
- What does Stefan Zweig Digital accept as an object, does it want open claims in it, and which stylesheet renders it? Answered by Stefan Zweig Digital on the sample object; the answer decides between claims in TEI and a separate data stream.
- Which institution publishes the merged bibliography, given that the project documents name the Literaturarchiv Salzburg and the delivery targets Stefan Zweig Digital in GAMS? Answered by the operator.
- How much human review time exists for adjudication? Answered by the operator; it decides how much automatic confirmation the concordance needs.

Model
- Is one group identifier per publication the right unit for citation and linking, and how are the compiler's addresses carried in it? Answered by the operator with a domain expert.
- Do unnumbered units such as collection headers and commentary paragraphs become entries of their own or context of the following entries? Answered by data analysis and the operator.

Data
- The three overlap experiments of step 3 have a first answer on small agent-judged samples ([Print volumes](print-volumes.md), Print and wiki). Addendum II can be aligned with the early wiki revisions character by character, the main volume and Addendum I only through fields. The overlap is partial: book editions mostly overlap, periodical items mostly exist in print only. A cited address is never evidence for identity. The concordance of step 7 therefore takes two routes, alignment for Addendum II and title-and-year blocking with a second agreeing field for the other volumes, and it matches print entries also against the contents lines of the wiki, not only its publications. Does the first answer hold on a larger sample checked by a person? Answered by the human control of step 7.
- Does the open-access bibliography of 1965 resolve sigla of the main volume? Answered by comparing its abbreviations.
- What do `G 379*` and the end of section D at 223 against 227 in the contents mean? Answered by a domain expert or further print evidence.

Use
- With which keys does Zweig research cite the bibliography, print addresses, wiki pages or both? Answered by a domain expert; it decides whether addresses are part of the identifiers.
- Which research tasks must the merged bibliography support, now that the owner's own research case was withdrawn? Answered by the operator and Stefan Zweig Digital; the tasks become the trial before delivery.
- Should authors and translators link to the person index of Stefan Zweig Digital? Answered by Stefan Zweig Digital.
