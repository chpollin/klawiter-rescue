---
title: Lab frontend for the rescued wiki data
aliases: [lab, lab frontend, scholar-centred prototypes]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: proposal
language: en
tags: [frontend, lab, user-stories, evaluation, provenance]
created: 2026-10-23
updated: 2026-10-23
related: [frontend, data, coordination, print-wiki-merge]
---

# Lab frontend for the rescued wiki data

The lab develops, prototypes and evaluates a scholar-centred way of showing the rescued wiki data. It answers an assignment the operator gave the AI operator session on 2026-10-23 and runs beside the production frontend described in [Interface and Curation](frontend.md), which it leaves untouched. Its prototypes live under `docs/lab/`, data preparation under `pipeline/lab/`, and the division of paths follows [Coordination](coordination.md). The epics and user stories below are derived from documents and literature and await the operator's review before the prototypes are built.

## Assignment

The lab serves one goal the operator set on 2026-10-23, to show that research data from an agentically built workflow can state its epistemic status honestly, for every value how it came about, whether it was checked and by whom. Two related deliverables pursue the same goal, the blog post on the rescue and the DIA-XAI follow-up proposal, which cites the lab as dated evidence of agentic engineering. Their milestones are listed under Plan.

The operator fixed three points of the assignment.

- The output is a lab with a concept, two or three comparable prototypes on real data and an evaluation report. Whether anything moves into the production frontend is a later operator decision.
- The primary research task is finding, judging and citing. Zweig researchers look for the editions and translations of a work, judge where each value comes from and who confirmed it, and cite a record reliably.
- The innovation lies in showing that agentic engineering can carry research data workflows. The lab therefore documents its own production, which decisions were human, which were delegated to agents and how each result was checked, and evaluates that process alongside the prototypes.

Four working assumptions follow from coordination with the research coordinator. The published lab shows wiki data only. In a local run it can show proposed print matches at page level from a file the print strand produces, and the matching moves to edition level once the print strand supplies publication identifiers ([Merged bibliography](print-wiki-merge.md)). Statements keep the three states of the data model, `proposed`, `confirmed` and `contested`, and the producer stands beside the state. Evaluations by language model agents are labelled as simulated and never stand in for acceptance by a person.

## Users and their tasks

The primary users are researchers working on Stefan Zweig's works and their reception. No observation of these users exists for this project. The stories are therefore derived from three kinds of evidence, each named at the story. The first is the material itself and its documented defects. The second is the operator's vault knowledge on scholar-centred design, chiefly the interface contract EIL-01 to EIL-10 and the pattern of evidence-faithful counting. The third is published research on scholarly information work and bibliographic displays.

The closest study of the target group found that literary scholars treat bibliographies and footnotes as their most trusted tools, chain backwards through citations, weigh an item more when several independent sources attest it, and rely on knowing a bibliography's coverage (Brockman et al. 2001). A scholar in that study preferred the card catalogue for authors with a vast corpus because its subheadings allowed browsing an author's works. These findings shape the epics on finding, citing and coverage.

## Design principles

Each principle names its grounding. Where the grounding is a transfer from another domain, the sentence says so.

Source beside value
: Every bibliographic value can be traced to its passage in the wiki text, and the passage is shown, not only linked. This follows EIL-01 and EIL-02 of the vault's interface contract and the field-to-source marking already built in the sibling repository klawiter-compare-lab. Explanations that lower the cost of checking reduced overreliance on machine output in controlled studies (Vasconcelos et al. 2023), while persuasive model-written rationales raised acceptance regardless of correctness (Bansal et al. 2021). The lab therefore shows the source passage and no model rationale.

State, producer and origin kept apart
: Origin (`regex`, `llm`, `missing`, `editor`) describes how a value came about and appears as neutral text. State (`proposed`, `confirmed`, `contested`) appears as a word with its producer and names the object it applies to, for example "Wikidata link Q1085: confirmed by LLM agents under operator delegation, no person, for the name 'Praha', not for this publication". Colour marks only a contested statement, always together with a word. Gaps, confirmed and proposed states and the warnings of the boundary check and of the automatic verification appear as words, the warnings with a marker symbol, so that frequent states do not outweigh the few that need attention. Absent values are the majority state for several fields, so colouring them would colour most records. In an experiment with news images, participants read the colour of a provenance indicator as a verdict on the content (Feng et al. 2023). Transferring this finding to bibliographic fields is an inference the lab will test in its evaluation.

Gaps named where they occur
: A value that is not documented in the source appears as a labelled state inside the normal layout, and overviews carry an explicit group for undated or unlocated records. Leaving missing values out produced the lowest perceived credibility in charts with missing data (Song and Szafir 2019), and a review of digital humanities visualisation documents dedicated unknown values and visible buckets for missing places as scholarly practice (Panagiotidou et al. 2023). The vault's pattern of evidence-faithful counting adds that every count names its denominator and opens the list of exactly the records it counts.

Work at the centre, relations by their evidence
: A work appears with the compiler's German work page at the top and the pages of its translations grouped by language beneath it, as an indented list. In card-sorting and concept-mapping tasks, lay participants placed the original expression together with the work and translations one level lower (Pisanski and Žumer 2010). Visual displays of bibliographic families outperformed a traditional catalogue in user studies whose abstracts report that the indented tree and the sunburst did best (Merčun, Žumer and Aalberg 2017). The indented list is chosen because titles are long and it reads linearly with a keyboard and a screen reader. Membership follows the vault's rule that a group rests on a reference and never on a name form. Pages the compiler linked count as members. Pages that merely cite the original title in brackets form a separate, separately counted list, because that is a statement about the source text and no identity decision.

Search and lists stay first-class
: Overviews complement search and never replace it. Novel visual components did not by themselves raise engagement with generous collection interfaces (Speakman, Hall and Walsh 2018), and in a project mapping translated literature the faceted search outlived the map as the research instrument (Skogmo et al. 2025). The operator's standing rule that the landing page is a category portal points the same way.

Coverage and editorial scope visible
: The interface states which states of the bibliography it holds, which time span the wiki covers and which modelling limits apply. Scholars in the study cited above relied on knowing a tool's scope and criticised online resources that hide it (Brockman et al. 2001).

Exceptions before defaults
: A state that holds for most values of a page, such as "rule" as origin or "no decision recorded", is stated once per page, and each value shows only what deviates from it. The first review of the running prototypes counted hundreds of repeated state lines on a single work page, which buried the few warnings. Internal names (decider strings, file paths, gate names, wiki markup) are translated into the reader's terms or left out.

No confidence values
: The interface shows no model confidence, no aggregate reliability score and no model-written explanation. This follows the vault's verification vocabulary and the SZD-HTR decision not to compute an aggregate value that would hide who checked a result.

The lab keeps the `--sz-*` design tokens of the production frontend, including `--sz-gold-dark` for text. Its novelty lies in evidence paths, states and gaps. The vault names the cream, serif and muted accent of the genre as a default to avoid, so the lab treats the palette as the brand frame and adds no decorative elements beyond it.

## Epics and user stories

Stories are written for the primary user unless they name another. Acceptance criteria are the yardstick of the evaluation. Each story names its grounding as material, vault or literature, and stories without such grounding are hypotheses. The stories were revised on 2026-10-23 after an independent critical review of the first specification. Its findings are summarised under Process record.

### E1 Find a work and its editions

S1.1 Find a work under any title form
: As a Zweig researcher I want to find a work by its German title, a translated title or a transliteration, so that I reach its editions from one place. Acceptance: search folds diacritics and umlauts, matches substrings in page titles, publication titles and bracketed original titles, and lists works before single pages. Grounding: material (titles in many scripts and transliterations).

S1.2 See the editions of a work by language and year
: As a Zweig researcher I want a work to show the compiler's German work page first and the pages of its translations grouped by language, each group ordered by year, so that I can see the reception of the work. Acceptance: an indented list with three separately counted parts, pages the compiler linked to the work page, translations the work page lists as text, and pages that cite the original title in brackets, the last marked as found by a lab rule; every count names its unit and opens exactly those records; a page in more than one part is marked in each and counted once in a union total beside the part counts; publications without a recorded language and without a year form their own groups; where no German work page exists the view says so; appearances inside anthologies and collected volumes are not covered, and the scope panel says so. Grounding: literature (Pisanski and Žumer 2010; Merčun, Žumer and Aalberg 2017), vault (grouping by reference, evidence-faithful counting).

S1.3 Know what the work view leaves out
: As a Zweig researcher I want to see which pages of Zweig's own works no work view reaches, so that I do not mistake the work view for the whole bibliography. Acceptance: the denominator is the set of namespace-0 pages whose entry type belongs to `ZWEIG_AUTHOR_TYPES` in `docs/js/constants.js` (fiction, essay, poetry, drama, correspondence, historical study, collected works); the view states how many of these any work view reaches and lists the uncovered pages by kind. Grounding: material.

S1.4 Browse by language
: As a Zweig researcher I want to list all pages and publications in one language across works, so that I can study the reception in that language. Acceptance: a language facet on the start view, with a group for publications whose language is not recorded. Grounding: material (language is recorded per publication), literature (Brockman et al. 2001 on browsing). Chaining through cross-references and contents lines, which the same study describes, is out of scope for this round and named as such on the scope panel.

### E2 Judge a value

S2.1 See where a value comes from
: As a Zweig researcher I want to select a publisher, place, translator or page count and see the passage it was taken from, so that I can judge it without leaving the record. Acceptance: matching respects word boundaries and matches each part of a comma-separated value; an occurrence inside the publication's own passage is marked first; where no exact occurrence exists the interface says "no exact occurrence, the value may be normalised". Grounding: vault (EIL-01, EIL-02), sibling precedent (klawiter-compare-lab), literature (Vasconcelos et al. 2023).

S2.2 Notice a page-level value that belongs to another publication
: As a Zweig researcher I want to be warned when a value of the page-level record occurs only in the passage of a publication other than the one that supplies the record's year, so that I recognise values mixed between the publications of one page. Acceptance: the check runs on pages that have a publication breakdown, is deterministic and names the publication whose passage holds the value; where several publications share the record's year, a value found in any of them passes; where no publication has the record's year, the check does not run and the record says that its year matches no publication; on pages without a breakdown that carry more than one year, the record states that its values may come from different publications. Grounding: material (the flat record of a page combines publications, documented in [Data](data.md); reference cases are selected by the preparation script from the regenerated data).

S2.3 See the state of a place link and who produced it
: As a Zweig researcher I want each place link to show its state and its producer, so that I can tell a person's confirmation from a rule's or an agent's, and a fixture's proposal from a confirmation. Acceptance: labels follow the provisional mapping below and name the object, "Wikidata link Q1085"; every agent producer names LLM agents and "no person"; the scope sentence "for the name '<place>', not for this publication" stands in the visible state line; the state of each publication's edition assignment appears at the publication heading; no state relies on colour. Grounding: material and [Data](data.md).

S2.4 See where the automatic verification disagrees
: As a Zweig researcher I want to see when the pipeline's verification stage could not find a page-level value in the raw text, so that I treat that value with care. Acceptance: a value of publisher, place, translator or page count whose verification status is a false positive carries the note "the automatic check did not find this value in the raw text"; the note states that the check covers page-level values only; the status name is not shown. Grounding: material.

S2.5 See competing readings of a contested statement
: As a Zweig researcher I want a contested place to show all recorded readings with their evidence, so that I can decide myself which one my work relies on. Acceptance: readings appear side by side with their evidence lines and review history; none is shown as the value; evidence from other pages names its page. Grounding: [Data](data.md) (contested claims stay visible), literature (Panagiotidou et al. 2023; Windhager et al. 2019).

S2.6 Follow the provenance chain of one value
: As a Zweig researcher I want to open, for any value, the chain of steps it passed, so that I can see whether it comes from the wiki, from the print volumes or from an LLM, and who checked what. Acceptance: a "Provenance" control beside each value opens one ordered list with the steps the data hold, each with its producer: source (wiki page, text id, restored revision where applicable), extraction (rule, LLM gap fill or editor), checks (exact occurrence in the own passage, the boundary check, the pipeline's verification note), decision (for place links: state, LLM or person, scope sentence), print correspondence (S6.2). A step the data do not hold is named as missing, for example "no per-record prompt stored". An exact occurrence is stated as evidence that the value exists in the source, not that it is relevant or complete. Grounding: the operator's requirement of 2026-10-23 that every data point shows whether it comes from the wiki, the print volumes or an LLM.

### E3 Cite and reuse

S3.1 Cite a record with its data state
: As a Zweig researcher I want a citation for a work, an edition or a page that identifies the data state, so that a reader can find what I relied on. Acceptance: the citation names the identifier, the Git commit of the data the lab was built from, a short content hash of its inputs and the access date; work groups carry an identifier derived from the anchor page and are labelled as lab-derived; the interface state is addressable by URL. Grounding: vault (a citable view needs a determinable data state), material (the version field of the published data has not changed across regenerations).

S3.2 Export with state and producer
: As a Zweig researcher I want exported records to keep state, producer and origin of their values, so that my reference manager does not turn a proposal into a fact. Acceptance: BibTeX and RIS exports carry state, producer and origin in a note field; the JSON export carries them as fields. Grounding: vault (EIL-10).

### E4 Trace the history of a record

S4.1 Follow a record through the workflow
: As a reader of the project's blog post or a Zweig researcher I want to step through the stages that produced a record, from the wiki text to its linked place, so that I understand which step was rule, LLM, fixture, agent or person. Acceptance: one card per stage with the record's state after it; where the regeneration after the October pipeline fixes changed a value, the card shows both states with their commits; states the artefacts do not hold are named precisely, for example "per-record prompt and raw response not stored, prompt template hash recorded". Grounding: the blog handover and the reconstruction check of 2026-10-23.

### E5 Coverage and scope

S5.1 See coverage per field with its denominator
: As a Zweig researcher I want to see for each field how many pages carry a value, how many carry none and how many values are LLM gap fills, so that I can judge what a filter result omits. Acceptance: an absent value reads "no value recorded, a gap in the source and a value not extracted are not yet distinguished"; the verification stage's count of values it found in the raw text but the record lacks is shown separately; every count names its unit and denominator and opens exactly the counted records. Grounding: vault (evidence-faithful counting), [Data](data.md) (absent, not applicable and not extracted are not yet distinct states).

S5.2 Know what the bibliography holds
: As a Zweig researcher I want a short statement of the bibliography's states and the known modelling limits, so that I know what a search can and cannot find. Acceptance: a scope panel reachable from every view that names the printed states (1965, not available to the project, 1991, 1999, the unpublished Addendum II), the wiki's editing period and the latest publication years it records, what the lab shows, the work grouping rules with their exclusions, and the modelling limits from [Data](data.md). Grounding: literature (Brockman et al. 2001).

### E6 Print volumes

S6.1 See whether the print volumes have been compared
: As a Zweig researcher I want to know whether a record rests on the wiki alone, so that I do not assume a comparison that has not happened. Acceptance: the scope panel states once that the published lab shows wiki data only. In a local run, `pipeline/lab/split_print_links.py` splits the print strand's matches into one ignored file per page under `docs/lab/local/print/` with an index. Where the index exists and a page has no file, the page reads "compared locally, no match found"; only without the index does it read "not compared". Every match reads "proposed" with its route as producer and never "confirmed". Field matches that name candidate publications appear under each of them as "candidate for this edition", with "one of N candidate editions" where they name several. Remaining field matches stay expanded up to five per page and are otherwise collapsed behind their count with "not reviewed, often unrelated on work and collection pages", a provisional threshold set by the research coordinator until a human sample measures one. The pane says that the print text is shown as extracted, with its encoding not corrected. Each match gives volume, address or PDF page and route. Alignment matches with at least 0.9 of the print entry's distinctive word 5-grams in some revision read "near-verbatim in a wiki revision of <first seen>", those between 0.8 and 0.9 read "largely the same wording in a wiki revision of <first seen>", and no score is shown. The raw print text stands in its own pane beside the wiki text, a persistent notice states that the print data is local and unpublished because the rights are unresolved, and matches by title and year alone stay behind a collapsed count marked as noisy. The labels for alignment matches are read from the file when it provides them, so that thresholds stay with the print strand, and a test in `pipeline/lab/` fails if any file under `docs/lab/local/` is tracked by Git. Grounding: [Merged bibliography](print-wiki-merge.md) and the operator's wish of 2026-10-23 to see print data in the lab.

S6.2 See where wiki and print agree on a value
: As a Zweig researcher I want to see when a wiki value also stands in the print entry matched to its edition, so that I know which values two sources support and which rest on the wiki alone. Acceptance: for each value of a publication with at least one candidate print entry, the preparation script checks deterministically whether the value occurs in that entry's text, with the occurrence rules of S2.1. A hit reads "also in print, Volume <v>, <address> (proposed, field match)"; a value absent from every candidate entry reads "not in the matched print entry"; a value without a candidate entry shows nothing. With several candidate editions the line names that the print entry is one of N candidates. No agreement raises a state, merges a value or reads "confirmed", because the print data are matches, not parsed fields, and no person has reviewed them; the scope panel says so. Wiki and print are states of one compiler's work, and the supplementary volume was aligned with early wiki revisions, so an agreement shows consistency between them, not independent support; the line says so. A value not found in the print text reads as not found, which can be an extraction error in the print text, and never as a disagreement. Alignment matches are attached to the publication whose passage they cover, so that they take part in the comparison. No agreement line appears on a Wikidata link, because print never supports an identity. Grounding: the operator's requirement of 2026-10-23 that a data point supported by both wiki and print shows this along its provenance chain, and [Merged bibliography](print-wiki-merge.md), where merging is a later step.

### Cross-cutting acceptance

Every prototype works with the keyboard alone, shows a visible focus, conveys no state by colour alone, reflows at 320 px width and 200 % zoom without hiding the source text behind a disclosure, uses English interface text and loads no library or font from a network. These criteria follow the house frontend rules and the accessibility minima in [Interface and Curation](frontend.md).

## Provisional producer labels

The mapping derives producer labels from the decider strings until the shared claim schema provides a typed producer class. It is provisional and follows [Data](data.md).

| Stored decision | Decider and basis | State shown | Producer shown |
|---|---|---|---|
| `confirm` or `correct` | `independent-verification-agent`, agent review file with source occurrence | confirmed | independent LLM agents against source and Wikidata, adjudicated by the main LLM agent under operator delegation, no person |
| `confirm` or `correct` | `independent-verification-agent`, low-score review without source occurrence | confirmed, with the warning "no source occurrence" | LLM agent review, no source occurrence, no person |
| `confirm` | `main-instance` | confirmed | main LLM agent under operator delegation, no person |
| `reject` | any | no link | candidate rejected, with the decider's label |
| `unresolved` | any | contested | open, readings listed |

Every place decision stored today was made by LLM agents. Whether such decisions may carry the state word `confirmed` is an open operator decision about the operator's delegation. Until it is taken, the research coordinator's ruling of 2026-10-23 applies: every agent producer names LLM agents and "no person", "no source occurrence" never appears beside `confirmed` without a visible warning, and the scope sentence "for the name '<place>', not for this publication" stands in the visible state line. A data contract test in `pipeline/lab/` fails if an agent producer lacks "LLM" or a confirmed state carries a non-person decider without saying so.

Until 2026-10-23 a test fixture of twenty places produced decisions labelled `agent_verified` without a source occurrence. The operator demoted them that day, and since then these places carry no decision. The record history shows the earlier link with this producer.

## Prototypes

Three prototypes cover the epics with different emphasis, so that the evaluation can compare them on the same tasks. The production frontend serves as the baseline on the same tasks, because it already shows publication blocks, marked source passages, contested readings and per-publication citations.

1. Judge a value covers E2, S3.2 and E6. It is the record view rebuilt around the source passage, the page-level boundary check, state with producer, the provenance chain of each value and the print correspondence.
2. Find and cite a work covers E1, E3 and E5. It is a work-centred entry with a language facet, the indented list and the scope panel.
3. Record history covers E4 and serves the blog explainer. A static snapshot for the blog is generated from the same data with a text equivalent.

A comparison of context depth is deferred until the three prototypes have passed their review, at the operator's priority of 2026-10-23. If it runs, prototype 1 is built twice under each of two context conditions. Under the first, the building agent receives the epics and stories only. Under the second, it also receives this document, the vault's interface knowledge and the house frontend rules. Two runs per condition reduce the chance of reading run-to-run variation as an effect. The comparison remains a documented observation on one case and supports no general claim about context depth.

## Interface specification

The specification describes each prototype on real records, so that a reviewer can check it against the stories before anything is built. Values shown in angle brackets are filled from the data by the preparation script and are never typed into the interface. Wireframes show the wide layout. Below 48rem every layout becomes one column in the order given under each wireframe.

### What a work is in this data

A wiki page usually holds one work in one language. Page 448 lists four Czech editions of "Netrpělivost srdce". For many works the compiler keeps a German work page marked VIST, which according to the compiler's note on page 7460 stands for volumes, individual stories and translations, for example "Ungeduld des Herzens (VIST)" and "Schachnovelle (VIST)". Such a page carries a see-also list of related pages and a section headed "Translations" written as text. German editions may sit on the VIST page itself or on separate German pages of the same title, as "Schachnovelle" holds German editions while "Schachnovelle (VIST)" holds the links. Translated pages usually cite the German original title in square brackets after their own title, "Netrpělivost srdce [Ungeduld des Herzens]".

The anchor of a work is its VIST page together with the German pages of Zweig's own works that the VIST page links or that carry the same title after removing suffixes such as "(VIST)", "(IS)" or "/ Volume". Where no VIST page exists, a German page of Zweig's own works becomes an anchor if other pages link it or cite its title in brackets. Maria Stuart, page 35, with many inbound links and no VIST page, is such a case. The lab distinguishes three relations by their evidence.

1. Linked by the compiler. Pages named in an anchor page's see-also list or naming an anchor page in theirs. They are counted and grouped by kind, translations by language, adaptations and readings, secondary literature and other, because the compiler's see-also list mixes them.
2. Listed by the compiler as text. The "Translations" section of the anchor page, parsed from the page text by the preparation script and shown as the compiler wrote it, by language. The published `translations` field cannot serve, because it holds only the first language of the list. Lines of that section that list German reprints are shown under the German editions.
3. Citing the title in brackets. Pages whose first bracket after the page title holds the anchor's title, both sides normalised by Unicode compatibility form, straight apostrophes, case folding and removal of suffixes and genre words such as "Roman" or "Novelle". They form a separate list grouped by entry type, with its own count, labelled "cites the original title in brackets, found by a lab rule, not reviewed". Brackets holding a year, a number, a place, an English gloss or several titles are excluded and listed by kind with counts. Variant forms such as "Der Brief einer Unbekannten" are shown as possibly the same title and never merged. A page also linked by the compiler is marked "also linked by the compiler".

All counts come from the preparation script. A second review pass checked the bracket rule on the three reference works by category and title and judged it precise for translated pages, while it misses appearances in anthologies by design. The script repeats this check and reports it. With anchors limited to VIST pages the work view would reach about a quarter of the pages of Zweig's own works and no essays, so the extended anchor rule above is required, and the coverage statement of S1.3 shows what remains outside.

### Prototype 1, Judge a value

The record view of one wiki page. The left column shows the page's publications, the right column the source text. Selecting a value marks its occurrence in the text.

```
+--------------------------------------------------------------------------+
| Klawiter Bibliography LAB   Search [____________________]   Scope  Help  |
+--------------------------------------------------------------------------+
| Netrpělivost srdce                       Work: Ungeduld des Herzens       |
| Czech, <n> publications <years>, page 448   (cites the title in brackets, |
|                                              lab rule, not reviewed)     |
+-------------------------------------+------------------------------------+
| PUBLICATIONS                        | SOURCE TEXT                         |
|                                     | plain text derived from wiki page   |
| 1968  Svoboda, Praha                | 448, revision <id>                  |
|   edition assignment: proposed      |                                    |
|   Publisher  Svoboda        rule    | [1968]: Svoboda, Praha [Prague]    |
|   Place      Praha          rule    | Netrpělivost srdce [Ungeduld des   |
|     Wikidata link: <state> by       | Herzens]. Translated by Božena     |
|     <producer>, for the name        | Koseková. ‖326/(2)p.‖              |
|     'Praha', not this publication   |                                    |
|     [Provenance]                    | [1976]: Práce, Praha [Prague] ...  |
|   Translator <value or "no value    |                                    |
|              recorded ...">         |  ‖ ‖ marks the selected value with  |
|   Extent     ▸326/(2)p.◂    rule    |  an outline and the label           |
|                                     |  "selected value"                   |
| 1976  Práce, Praha  2nd edition     |                                    |
|   ...                               |                                    |
+-------------------------------------+------------------------------------+
| PAGE-LEVEL RECORD (one record for the whole page, used by search and     |
| exports; it can combine values of different publications)                 |
|   Year <value>          rule                                              |
|   Page count <value>    rule   <if found only in another publication:     |
|                                "occurs only in the passage of the 1976   |
|                                publication">                              |
|   Translator <value>    <origin>  <if flagged: "the automatic check did   |
|                                not find this value in the raw text">     |
+--------------------------------------------------------------------------+
| Cite page ▾   Export ▾          Data: commit <hash>, inputs <hash>        |
+--------------------------------------------------------------------------+
```

Narrow order: header, publications, page-level record, footer. On narrow screens a selected value shows its marked passage directly beneath it, so the source is never behind a disclosure.

Behaviour

- Each value is a button. Activating it marks its occurrences in the source text with an outline and a text label, the occurrence in the publication's own passage first, and scrolls the text pane to it without moving focus. Esc clears the mark.
- The source text pane names what it shows, the plain text the pipeline derived from the wiki page and the revision it comes from. Where the source revision was restored, the pane says so.
- The boundary check of S2.2 runs on the page-level record only. A value whose occurrences all lie in the passage of a publication other than the year-supplying one carries the warning with that publication's year.
- Origin stands as a plain word (rule, LLM gap fill, editor) in muted text. A recorded gap reads "no value recorded" in plain text. "Contested" is the only coloured state. The two warnings carry a marker symbol and their sentence. The state of a decision names its object and producer in one sentence. "Decision record" opens the decider, basis, evidence lines and "no date recorded" inline below the value.
- A contested place shows "Wikidata link: contested" and lists every reading with its evidence lines and their pages, including the reading "no assignment". No reading is styled as the value.
- On a page without a publication breakdown, the publications column is replaced by the source text in full width and the page-level record, with the note of S2.2 where the page carries more than one year.
- Cite offers the page or a publication with identifier, data commit, input hash and access date. Export offers BibTeX, RIS and JSON, each carrying state, producer and origin.
- In a local run with print matches, a third pane "Print volumes, local only" lists the page's matches below the source text.

Reference records are selected by the preparation script from three classes: a page with a breakdown where the boundary check fires, a page without a breakdown carrying several years, and a page with a contested place whose value is rule-extracted.

### Prototype 2, Find and cite a work

A work-centred entry. The start view offers search, a language facet and a list of works anchored on the compiler's German work pages. Selecting a work opens the work view.

```
+--------------------------------------------------------------------------+
| Klawiter Bibliography LAB   Search [____________________]   Scope         |
| Language [any ▾]   Years from [____] to [____]                            |
+--------------------------------------------------------------------------+
| Ungeduld des Herzens                                                      |
| Anchor: "Ungeduld des Herzens (VIST)" (page 54) and German pages of the  |
| same title.  <n> German publications.  <n> pages in all parts (union)     |
+--------------------------------------------------------------------------+
| LINKED BY THE COMPILER              <n> pages                             |
|   ▸ Translations   <n> pages, by language                                 |
|   ▸ Adaptations and readings   <n> pages                                  |
|   ▸ Secondary literature and other   <n> pages                            |
+--------------------------------------------------------------------------+
| LISTED ON THE WORK PAGE AS TEXT     <n> languages                         |
|   ▸ Albanian  "Padurimi i zemrës. Roman [Tiranë/Tirana, 1997 / 2014] ..." |
+--------------------------------------------------------------------------+
| CITING THE TITLE IN BRACKETS  found by a lab rule, not reviewed           |
| <n> pages, <n> publications;  <n> also linked by the compiler             |
|   ▸ Fiction   Czech <n> pages, ...                                        |
|       <year> <imprint>   page <id>   Open record                          |
|   ▸ Language not recorded  <n> publications                               |
|   ▸ Year not recorded      <n> publications                               |
|   Excluded brackets: <n> with a year, <n> glosses, <n> several titles     |
|   Possibly the same title: "Der Brief ..." (separate list)                |
+--------------------------------------------------------------------------+
| Cite work ▾   Export ▾          Data: commit <hash>, inputs <hash>        |
+--------------------------------------------------------------------------+
```

Narrow order: title block, the three parts, footer. Filters sit above the list and stay visible.

Behaviour

- Search folds diacritics and umlauts, matches substrings and lists work anchors, then pages.
- The three parts are nested disclosure lists of buttons and links, which avoids interactive elements inside tree items. Group headings name their unit. Activating a count lists exactly the counted rows.
- The year filter uses two number fields. Filtering announces the remaining number through a status region and never changes the counts in the part headings, which state "of <n>" while a filter is active.
- Work anchors without linked pages show the first part as "no pages linked by the compiler".
- The coverage view of S5.1 and the scope panel of S5.2 open from "Scope" as a page of their own. Coverage counts are links to the counted lists.

```
+--------------------------------------------------------------------------+
| Coverage of <n> pages of Zweig's own works (data commit <hash>)           |
| Field       value recorded   no value recorded*   of these LLM gap fills  |
| Publisher   <n> (<p>%)        <n>                  <n>                    |
| Place       ...                                                           |
| * a gap in the source and a value not extracted are not yet distinguished.|
|   The verification stage found <n> publisher values in the raw text that  |
|   the record lacks.                                                       |
| Work views reach <n> of <n> pages. Not reached, by kind: essays <n>, ...  |
+--------------------------------------------------------------------------+
```
- The URL holds work, filters and opened groups, and the footer names the data commit, so a view is citable.

Reference works are Ungeduld des Herzens, Schachnovelle, and Brief einer Unbekannten with Der Brief einer Unbekannten.

### Prototype 3, Record history

A step-through of how one record came about, for the blog explainer and for readers who want to understand the workflow.

```
+--------------------------------------------------------------------------+
| How a record comes about                       Record [page 448 ▾]        |
| Every core value shows where it comes from. Step through the stages.      |
+--------------------------------------------------------------------------+
| Stages: 1 Wiki text  2 Repair  3 Parse  4 Fill gaps  5 Link places        |
|         6 Published record                                                |
+--------------------------------------------------------------------------+
| 4 Fill gaps          Actor: LLM gemini-3.1-flash-lite-preview, answers   |
|                      frozen on 2026-08-21, prompt template hash recorded  |
|  Translator was empty after stage 3 because the name rule did not accept |
|  names beginning with Ž. The LLM filled:                                  |
|     Božena Koseková, Božena Koseková, Božena Koselová                     |
|  The verification stage did not find this value in the raw text.         |
|  After the fix of <date> (commit <hash>) the rule extracts the name, and  |
|  the LLM value no longer applies.                                         |
|  Not stored: the per-record prompt and raw response.                      |
|                                                  Previous   Next          |
+--------------------------------------------------------------------------+
| Where a person can intervene today: field corrections and place           |
| decisions in the local edit mode of the production app.                   |
+--------------------------------------------------------------------------+
```

Narrow order: title, stage list as vertical steps, current card.

Behaviour

- The start state shows the finished record with its origins and states, so a reader who does not step through still gets the message of the title sentence.
- Each stage card states the record's values after that stage, the actor and what the artefacts do not hold. A stage that changed nothing says "no change on this record".
- The stage list is a tab list with arrow-key navigation, and Previous and Next repeat it as buttons.
- The record switcher offers the reference records of prototype 1 and page 448 as the case changed by the October fixes.
- The blog snapshot is one image per record with a text equivalent of every card.

## Data basis

A script under `pipeline/lab/` reads the published data under `docs/data/`, the tracked reconciliation decisions and the verification report, and writes prepared JSON to `docs/lab/data/`. It runs after the research coordinator's regeneration of the published data and never during a pipeline run. It records the Git commit of its inputs and a content hash in every output file, selects the reference records, and reports the precision of the bracket rule on the three reference works. It derives the producer labels above, the publication text ranges for the boundary check of S2.2 and the record histories for E4. The source slice hash of a publication is computed over raw text that the site does not publish, so a browser cannot verify it. The lab states this where it shows the hash.

## Evaluation

The evaluation separates three levels of claim, what the code demonstrably does, which stories the prototypes pass, and what only a person with domain expertise can judge. A survey of evaluations at the intersection of visualisation and the humanities found that designs relying on an author's walkthrough or an expert checklist alone show the lowest rigour and recommends triangulating methods and reporting participants transparently (Benito-Santos et al. 2026). The protocol therefore combines the following components, and the production frontend runs the same tasks as a baseline.

1. Task walkthroughs on six tasks, mapped to the stories: look up a work and its editions (S1.2), decide whether a value is documented in the source (S2.1, S2.2), explain a contested link (S2.5), characterise the reception of a work (S1.2), decide whether a gap is a source gap (S5.1) and obtain a citation (S3.1).
2. A heuristic pass by the AI operator with the value-driven heuristics of ICE-T (Wall et al. 2019), reported descriptively, because the published power analysis recommends five raters, and with project heuristics for provenance, state and gaps, labelled as the project's own derivation.
3. Simulated inspection by language model agents that interact with the running prototypes in a browser, two or three independent runs per prototype, each finding citing the view, the task step and the heuristic. Agent findings are triaged into confirmed, false positive and duplicate before they count. Studies comparing LLM inspection with human experts report large shares of duplicates and false positives and weak recall of expert findings (Guerino et al. 2025), and LLM-generated research data lacked the diversity of human data (Hämäläinen, Tavast and Kunnari 2023). The report therefore names model, date, prompt and runs and treats these findings as candidate issues only.
4. An accessibility check with an automated tool on each view and a manual pass covering keyboard completion of the tasks, a screen reader spot check and the critical heuristics of Chartability (Elavsky, Bennett and Moritz 2022).
5. A session with one or two Zweig specialists, if the operator can arrange it, with a think-aloud on the tasks, an open exploration and a critique interview that asks explicitly for what is wrong or missing, because positive expert feedback is prone to demand effects (Isenberg et al. 2013).

Each task carries its type, which decides who checks it. A deterministic task is checked by a rule without a person. A simple task needs care but no domain knowledge and can be checked by any careful person. A complex task needs Zweig expertise, and specialist time goes to these alone, on few cases and partly blind. Of the six tasks, the lookup of a work, the gap decision and obtaining a citation are simple, explaining a contested link and characterising a work's reception are complex, and deciding whether a value is documented in the source is simple where an exact occurrence exists and complex where it does not. This sorting follows the operator's guidance of 2026-10-23.

An exact occurrence in the source proves that a value exists there, not that it is the relevant value or complete. The first prototype review found occurrences for fragments such as "I wish to express" as a publisher, so the evaluation reports occurrence as evidence of existence only.

The process level asks how long a prototype took to reach its stories, which defects the project knowledge prevented or failed to prevent, which corrections needed a person, and, if the deferred comparison runs, how the two context conditions differed.

## Plan

The lab is complete when its three prototypes run on real data, keep origin and review state apart, have passed a critical review against the user stories, are evaluated, and their production is documented in the process record.

| Milestone | Content | Depends on |
|---|---|---|
| L1 Concept | assignment, principles, epics and stories in this document | operator review of the stories |
| L2 Interface specification | wireframes and behaviour per prototype, independent critical review against stories and data, revision | L1 |
| L3 Data preparation | `pipeline/lab/` script writing `docs/lab/data/`, print split into the ignored local folder | the research coordinator's stable data state after the pipeline fixes |
| L4 Prototypes | three prototypes under `docs/lab/` | L2, L3 |
| L5 Prototype review | independent review of the running prototypes against the stories in a browser, fixes | L4 |
| L6 Evaluation | tasks, heuristics, triaged simulated inspection, accessibility, optional expert session, report | L5, availability of Zweig specialists |
| L7 Handover | process record completed, report to the research coordinator, commit | L6 |

The related deliverables run on their own tracks. Their shared blocker, the meaning of `confirmed` for the twenty fixture-based place decisions, was resolved by the operator's decision of 2026-10-23 to demote them to `proposed`.

| Milestone | Content | Depends on |
|---|---|---|
| B1 Blog wording of review states | "bestätigt" used only where the data support it | regeneration implementing the fixture decision; operator decision on agent-adjudicated place decisions |
| B2 Blog figures | figures re-read from the regenerated artefacts | regeneration commit |
| B3 Blog explainer | static snapshot from prototype 3 | L4 |
| B4 Blog claim check | every statement checked against the artefacts, naming and editorship settled | B1 to B3, operator decisions on editorship |
| A1 Proposal version | settled on 2026-10-23: the operator's team draft "Grounds for Use" (after v1.5, with questions to named team members) is the basis; the agent drafts v1.3 and v1.4 supply material only; changes go to the team draft as proposals, never as edits without the operator's go-ahead | operator |
| A2 Proposal terms and literature | terms aligned with the vault decision of 2026-10-03, literature updated, gap claims checked | A1 |
| A3 Proposal evidence | dated cases from this repository and from the vault inserted | A1, B1 for the fixture case |
| A4 Proposal formalities | contractor role of DHCraft, disclosure of AI use in writing, CV decision, cost justification | operator |

## Process record

The record lists the human decisions, the agent briefs with their guardrails, the checks performed on agent results and the errors observed. Entries so far, all from 2026-10-23:

- The operator fixed output, research task and innovation axis by answering three questions.
- The research coordinator corrected a proposed fourth state, `checked`, against the statement states of the data model and replaced it with producer labels. The correction came from model knowledge the AI operator session lacked.
- A verification agent found that the blog handover described four of its five example pages inaccurately and discovered five pipeline defects. The AI operator checked the central counts and the translator name class against the files, and the research coordinator had them verified independently before fixing them.
- An independent review of the first interface specification found four blocking defects. The boundary check had no data on its own reference case and targeted the wrong layer, the grouping by bracketed title could not place the German original and grouped by name form against the vault's pattern of evidence-faithful counting, gaps were labelled with reasons the data does not hold, and the citation had no determinable data state. It also showed that the specification's reference values would change with the pending pipeline fixes. The specification was revised on the same day.
- A literature agent put the operator's e-mail address into a request to a bibliographic web service once, against its brief, and reported this itself. Later briefs name the prohibition explicitly.
- A second independent review of the revised specification found further defects, among them example values in the wireframes that the AI operator session had invented rather than read from the data, and a claim that a reference work had no linked pages, which came from measuring the German page of the same title instead of its VIST page. Wireframes now carry placeholders, and every figure in this document was re-read from the data.
- Measuring the work model against the data showed that the compiler encodes it in the pages themselves (VIST page, see-also list, "Translations" section, bracketed original title), and that the published `translations` field keeps only the first language of that section. The lab therefore keeps the three relations apart by their evidence, and the truncation went to the research coordinator as a production defect.
- The working rule that emerged for prompting interfaces is to measure each user story against the real data before writing any interface code, and to have the specification reviewed independently against stories and data. Both reviews of 2026-10-23 found blocking defects at a point where fixing them cost a text edit.
- The first running build passed two independent reviews on real data without invented values, and both found the same central gap. Agent decisions read "confirmed" without naming LLM agents, and the interface repeated default states so often that the warnings disappeared. The research coordinator ruled on the agent labels pending the operator's decision on delegation, and the operator required on 2026-10-23 that every data point shows whether it comes from the wiki, the print volumes or an LLM, and where wiki and print agree. Stories S2.6 and S6.2 and the principle of exceptions before defaults were added the same day.

## Sources


Bansal, G., et al. 2021. "Does the Whole Exceed Its Parts? The Effect of AI Explanations on Complementary Team Performance." CHI '21. https://doi.org/10.1145/3411764.3445717

Benito-Santos, A., et al. 2026. "Chasing Meaning and/or Insight? A Survey on Evaluation Practices at the Intersection of Visualization and the Humanities." arXiv 2601.20464, accepted to CHI '26. https://arxiv.org/abs/2601.20464

Brockman, W. S., L. Neumann, C. L. Palmer, and T. J. Tidline. 2001. Scholarly Work in the Humanities and the Evolving Information Environment. CLIR pub104. https://www.clir.org/pubs/reports/pub104/

Elavsky, F., C. Bennett, and D. Moritz. 2022. "How Accessible Is My Visualization? Evaluating Visualization Accessibility with Chartability." Computer Graphics Forum 41 (3). https://www.frank.computer/papers/2022-eurovis-chartability.pdf

Feng, K. J. K., et al. 2023. "Examining the Impact of Provenance-Enabled Media on Trust and Accuracy Perceptions." PACM HCI 7 (CSCW2), Art. 270. https://doi.org/10.1145/3610061

Guerino, G., et al. 2025. "Can GPT-4o Evaluate Usability Like Human Experts?" INTERACT 2025. https://arxiv.org/abs/2506.16345

Hämäläinen, P., M. Tavast, and A. Kunnari. 2023. "Evaluating Large Language Models in Generating Synthetic HCI Research Data: A Case Study." CHI '23. https://doi.org/10.1145/3544548.3580688

Isenberg, T., P. Isenberg, J. Chen, M. Sedlmair, and T. Möller. 2013. "A Systematic Review on the Practice of Evaluating Visualization." IEEE TVCG 19 (12): 2818–2827. https://doi.org/10.1109/TVCG.2013.126

Merčun, T., M. Žumer, and T. Aalberg. 2017. "Presenting Bibliographic Families Using Information Visualization." JASIST 68 (2): 392–411. https://doi.org/10.1002/asi.23659

Panagiotidou, G., et al. 2023. "Communicating Uncertainty in Digital Humanities Visualization Research." IEEE TVCG 29 (1). https://doi.org/10.1109/TVCG.2022.3209436

Pisanski, J., and M. Žumer. 2010. "Intuitiveness of FRBR: A Study in a Broader Context." Information Research 15 (4), paper colis725. https://informationr.net/ir/15-4/colis725.html

Skogmo, O., et al. 2025. "Oversatt litteratur på kartet." NTOT 1 (2): 51–70. https://doi.org/10.5324/ntot.v1i2.6496

Song, H., and D. A. Szafir. 2019. "Where's My Data? Evaluating Visualizations with Missing Data." IEEE TVCG 25 (1). https://doi.org/10.1109/TVCG.2018.2864914

Speakman, R., M. M. Hall, and D. Walsh. 2018. "User Engagement with Generous Interfaces for Digital Cultural Heritage." TPDL 2018, LNCS, 186–191. https://doi.org/10.1007/978-3-030-00066-0_16

Vasconcelos, H., et al. 2023. "Explanations Can Reduce Overreliance on AI Systems During Decision-Making." PACM HCI 7 (CSCW1), Art. 129. https://doi.org/10.1145/3579605

Wall, E., et al. 2019. "A Heuristic Approach to Value-Driven Evaluation of Visualizations." IEEE TVCG. https://doi.org/10.1109/TVCG.2018.2865146

Windhager, F., et al. 2019. "Visualization of Cultural Heritage Collection Data: State of the Art and Future Challenges." IEEE TVCG 25 (6): 2311–2330. https://doi.org/10.1109/TVCG.2018.2830759

Research agents of the AI operator session read the full texts of these sources on 2026-10-23, with two exceptions whose abstracts alone were accessible, Merčun, Žumer and Aalberg (2017) and the journal articles of Pisanski and Žumer, which are cited here through their open conference version. Several long sources were read in their methods, findings and limitations sections only. The AI operator session itself checked the agents' reports for consistency, not the full texts.
