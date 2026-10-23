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

Four working assumptions follow from coordination with the research coordinator. The lab shows wiki data only. Each edition carries an empty slot for the print volumes, placed at edition level so that a later group of records from several sources can fill it ([Merged bibliography](print-wiki-merge.md)). Statements keep the three states of the data model, `proposed`, `confirmed` and `contested`, and the producer stands beside the state. Evaluations by language model agents are labelled as simulated and never stand in for acceptance by a person.

## Users and their tasks

The primary users are researchers working on Stefan Zweig's works and their reception. No observation of these users exists for this project. The stories are therefore derived from three kinds of evidence, each named at the story. The first is the material itself and its documented defects. The second is the operator's vault knowledge on scholar-centred design, chiefly the interface contract EIL-01 to EIL-10 and the pattern of evidence-faithful counting. The third is published research on scholarly information work and bibliographic displays.

The closest study of the target group found that literary scholars treat bibliographies and footnotes as their most trusted tools, chain backwards through citations, weigh an item more when several independent sources attest it, and rely on knowing a bibliography's coverage (Brockman et al. 2001). A scholar in that study preferred the card catalogue for authors with a vast corpus because its subheadings allowed browsing an author's works. These findings shape the epics on finding, citing and coverage.

## Design principles

Each principle names its grounding. Where the grounding is a transfer from another domain, the sentence says so.

Source beside value
: Every bibliographic value can be traced to its passage in the wiki text, and the passage is shown, not only linked. This follows EIL-01 and EIL-02 of the vault's interface contract and the field-to-source marking already built in the sibling repository klawiter-compare-lab. Explanations that lower the cost of checking reduced overreliance on machine output in controlled studies (Vasconcelos et al. 2023), while persuasive model-written rationales raised acceptance regardless of correctness (Bansal et al. 2021). The lab therefore shows the source passage and no model rationale.

State, producer and origin kept apart
: Origin (`regex`, `llm`, `missing`, `editor`) describes how a value came about and appears as neutral text. State (`proposed`, `confirmed`, `contested`) is the reader's primary signal and is the only element that carries colour, always together with a word. In an experiment with news images, participants read the colour of a provenance indicator as a verdict on the content (Feng et al. 2023). An unexplained label for AI involvement lowered trust even in true headlines, and the effect disappeared when the label explained the limited role of the model (Altay and Gilardi 2024). Transferring both findings to bibliographic fields is an inference the lab will test in its evaluation.

Gaps named where they occur
: A value that is not documented in the source appears as a labelled state inside the normal layout, and overviews carry an explicit group for undated or unlocated records. Leaving missing values out produced the lowest perceived credibility in charts with missing data (Song and Szafir 2019), and a review of digital humanities visualisation documents dedicated unknown values and visible buckets for missing places as scholarly practice (Panagiotidou et al. 2023). The vault's pattern of evidence-faithful counting adds that every count names its denominator and opens the list of exactly the records it counts.

Work at the centre, original with the work
: A work appears with its original German publication at work level and its translations grouped by language beneath it, as an indented tree. In card-sorting and concept-mapping tasks, lay participants placed the original expression together with the work and translations one level lower (Pisanski and Žumer 2010). Visual displays of bibliographic families outperformed a traditional catalogue in user studies whose abstracts report that the indented tree and the sunburst did best (Merčun, Žumer and Aalberg 2017). The indented tree is chosen over the sunburst because titles are long and the tree reads linearly with a keyboard and a screen reader.

Search and lists stay first-class
: Overviews complement search and never replace it. Novel visual components did not by themselves raise engagement with generous collection interfaces (Speakman, Hall and Walsh 2018), and in a project mapping translated literature the faceted search outlived the map as the research instrument (Skogmo et al. 2025). The operator's standing rule that the landing page is a category portal points the same way.

Coverage and editorial scope visible
: The interface states which states of the bibliography it holds, which time span the wiki covers and which modelling limits apply. Scholars in the study cited above relied on knowing a tool's scope and criticised online resources that hide it (Brockman et al. 2001).

No confidence values
: The interface shows no model confidence, no aggregate reliability score and no model-written explanation. This follows the vault's verification vocabulary and the SZD-HTR decision not to compute an aggregate value that would hide who checked a result.

The lab keeps the `--sz-*` design tokens of the production frontend, including `--sz-gold-dark` for text. Its novelty lies in evidence paths, states and gaps. The vault names the cream, serif and muted accent of the genre as a default to avoid, so the lab treats the palette as the brand frame and adds no decorative elements beyond it.

## Epics and user stories

Stories are written for the primary user unless they name another. Acceptance criteria are the yardstick of the evaluation. Each story names its grounding as material, vault or literature, and stories without such grounding are hypotheses.

### E1 Find a work and its editions

S1.1 Find a work under any title form
: As a Zweig researcher I want to find a work by its German title, a translated title or a transliteration, so that I reach all its editions from one place. Acceptance: search folds diacritics and umlauts, matches substrings and shows the work with its number of attached publications. Grounding: material (titles in many scripts and transliterations).

S1.2 See the editions of a work by language and year
: As a Zweig researcher I want the editions of a work grouped with the original first and translations by language, each group ordered by year, so that I can see the reception of the work at a glance. Acceptance: an indented tree; every group count names its unit and opens exactly those records; undated publications form their own group. Grounding: literature (Pisanski and Žumer 2010; Merčun, Žumer and Aalberg 2017) and vault (evidence-faithful counting).

S1.3 Know which records the work view does not cover
: As a Zweig researcher I want to see which pages are not yet part of the work and edition graph, so that I do not mistake the work view for the whole bibliography. Acceptance: the work view states its coverage against the number of pages and links to the uncovered records. Grounding: material (the graph covers the ratified header-selected corpus).

### E2 Judge a value

S2.1 See where a value comes from
: As a Zweig researcher I want to select a publisher, place, translator or page count and see the passage it was taken from, so that I can judge it without leaving the record. Acceptance: the passage is marked in the shown wiki text; if no occurrence is found, the interface says so. Grounding: vault (EIL-01, EIL-02), sibling precedent (klawiter-compare-lab), literature (Vasconcelos et al. 2023).

S2.2 Notice a value that belongs to another publication
: As a Zweig researcher I want to be warned when a value of a publication occurs in the wiki text outside that publication's passage, so that I recognise values mixed between publications of one page. Acceptance: the check is deterministic, compares the occurrence with the publication's text range and names the publication the value occurs in. Grounding: material. On page 5021 an LLM-filled publisher and a page count belong to a 1965 book while the record's year belongs to a 2012 article, and the existing check against the source line passes because the words occur on the page.

S2.3 See the state of a statement and who produced it
: As a Zweig researcher I want each place link to show its state and its producer, so that I can tell a person's confirmation from a rule's or an agent's. Acceptance: labels follow the provisional mapping below; the twenty fixture-based place decisions read "confirmed by test fixture, no source occurrence"; state is never conveyed by colour alone. Grounding: material and [Data](data.md), which documents the decider strings.

S2.4 See where an automatic check disagrees
: As a Zweig researcher I want to see when the pipeline's verification stage flags a value as not found in the raw text, so that I treat that value with care. Acceptance: a flagged value carries a short note naming the check; unflagged values carry nothing. Grounding: material (the verification report flags LLM translator values, among them page 448, and no gate uses the flag).

S2.5 See competing readings of a contested statement
: As a Zweig researcher I want a contested place to show all recorded readings with their evidence, so that I can decide myself which one my work relies on. Acceptance: readings appear side by side with source references and review history; none is shown as the value. Grounding: [Data](data.md) (contested claims stay visible), literature (Panagiotidou et al. 2023; Windhager et al. 2019).

### E3 Cite and reuse

S3.1 Cite a record with its data state
: As a Zweig researcher I want a citation for a work, an edition or a page that names the data version, so that a reader can find the state I relied on. Acceptance: a citation string with the stable identifier, version and access date; the interface state is addressable by URL. Grounding: vault (a citable view needs a determinable data state), literature (Brockman et al. 2001 on chaining).

S3.2 Export with state and producer
: As a Zweig researcher I want exported records to keep state, producer and origin of their values, so that my reference manager does not turn a proposal into a fact. Acceptance: BibTeX and RIS exports carry state and origin in a note field; the JSON export carries them as fields. Grounding: vault (EIL-10).

### E4 Trace the history of a record

S4.1 Follow a record through the workflow
: As a reader of the project's blog post or a Zweig researcher I want to step through the stages that produced a record, from the wiki line to its linked place, so that I understand which step was rule, LLM, agent or person. Acceptance: one card per stage with the record's state after it; rejected or absent states appear as such; states the artefacts do not record read "not recorded". First records are pages 448 and 5021. Grounding: the blog handover of 2026-10-23 and the reconstruction check of the same day, which found that roughly half of a record's states are recoverable from published or tracked artefacts.

### E5 Coverage and scope

S5.1 See coverage per field with its denominator
: As a Zweig researcher I want to see for each field how many records carry a value, how many lack one in the source and how many values are LLM-filled, so that I can judge what a filter result omits. Acceptance: counts name their unit and denominator and open exactly the counted records; the numbers come from the published data at build time. Grounding: vault (evidence-faithful counting), literature (Panagiotidou et al. 2023).

S5.2 Know what the bibliography holds
: As a Zweig researcher I want a short statement of the bibliography's states, the wiki's time span and the known modelling limits, so that I know what a search can and cannot find. Acceptance: a scope panel reachable from every view, drawing its facts from [About](about.md) and [Data](data.md). Grounding: literature (Brockman et al. 2001).

### E6 Print volumes slot

S6.1 See where the print volumes will appear
: As a Zweig researcher I want each edition to show whether the printed volumes have been compared, so that I know the record rests on the wiki alone. Acceptance: an edition-level slot reading "print volumes not yet compared"; no print data is shown. Grounding: [Merged bibliography](print-wiki-merge.md).

### Cross-cutting acceptance

Every prototype works with the keyboard alone, shows a visible focus, conveys no state by colour alone, reflows at 320 px width and 200 % zoom, uses English interface text and loads no library or font from a network. These criteria follow the house frontend rules and the accessibility minima in [Interface and Curation](frontend.md).

## Provisional producer labels

The mapping derives producer labels from the decider strings until the shared claim schema provides a typed producer class. It is provisional and documented in [Data](data.md).

| Stored decision | Decider | State shown | Producer shown |
|---|---|---|---|
| `confirm` or `correct` | `independent-verification-agent` with source occurrence | confirmed | agent review against source and Wikidata |
| `confirm` or `correct` | `independent-verification-agent` without source occurrence | confirmed | agent review, no source occurrence |
| `confirm` | `repository-ground-truth-fixture` | confirmed | test fixture, no source occurrence |
| `confirm` | `main-instance` | confirmed | main agent under operator delegation |
| `reject` | any | no link | candidate rejected by the named decider |
| `unresolved` | any | contested | open, readings listed |

Whether the fixture decisions remain `confirmed` is an open operator decision. The lab shows them as stored and names their basis.

## Prototypes

Three prototypes cover the epics with different emphasis, so that the evaluation can compare them on the same tasks.

1. Judge a value covers E2 with S3.2 and S5.1. It is the record view rebuilt around the source passage, the publication boundary check and state with producer.
2. Find and cite a work covers E1, E3, S5.2 and E6. It is a work-centred entry with the indented edition tree.
3. Record history covers E4 and serves the blog explainer. A static snapshot for the blog is generated from the same data.

A comparison of context depth is deferred until the three prototypes have passed their review, at the operator's priority of 2026-10-23. If it runs, prototype 1 is built twice under each of two context conditions. Under the first, the building agent receives the epics and stories only. Under the second, it also receives this document, the vault's interface knowledge and the house frontend rules. Two runs per condition reduce the chance of reading run-to-run variation as an effect. The comparison remains a documented observation on one case and supports no general claim about context depth.

## Interface specification

The specification describes each prototype on real records, so that a reviewer can check it against the stories before anything is built. Wireframes show the wide layout. Below 48rem every layout becomes one column in the order given under each wireframe.

### What a work is in this data

A wiki page usually holds one work in one language. Page 448 lists four Czech editions of "Netrpělivost srdce" from 1968 to 2006. The compiler marks the German original title in square brackets after the translated title, as in "Netrpělivost srdce [Ungeduld des Herzens]". The lab groups pages into a work by this bracketed title. The grouping is a deterministic proposal derived from the compiler's notation and is labelled as such wherever it appears. Variant forms of the same original title, such as "Brief einer Unbekannten" and "Der Brief einer Unbekannten", stay separate groups and are listed under each other as possibly the same work, because merging them would be an identity decision. Brackets that hold a place name or an English gloss are excluded by the preparation script, and its exclusion rules are listed on the scope panel. Pages without a bracketed title remain reachable by search and appear in the coverage statement of S1.3.

### Prototype 1, Judge a value

The record view of one wiki page. The left column shows the page's publications as rows, the right column the wiki text. Selecting a value marks its occurrence in the text.

```
+--------------------------------------------------------------------------+
| Klawiter Bibliography LAB    Search [Ungeduld____________]   Scope  Help  |
+--------------------------------------------------------------------------+
| Netrpělivost srdce                                    Work: Ungeduld des  |
| Czech, 4 publications 1968-2006, wiki page 448     Herzens (37 pages,|
|                                                          compiler's title)|
+-------------------------------------+------------------------------------+
| PUBLICATIONS                        | WIKI TEXT  (page 448, latest rev.)  |
|                                     |                                    |
| 1968  Svoboda, Praha                | [1968]: Svoboda, Praha [Prague]    |
|   Publisher  Svoboda        rule    | Netrpělivost srdce [Ungeduld des   |
|   Place      Praha          rule    | Herzens]. Translated by Božena     |
|              confirmed by test      | Koseková. ‖326/(2)p.‖              |
|              fixture, no source     |                                    |
|              occurrence   [details] | [1976]: Práce, Praha [Prague] ...  |
|   Translator not extracted  gap     |                                    |
|              (name not recognised   |  ‖ ‖ = occurrence of the selected  |
|              by the rule)           |        value, outline + label      |
|   Extent     ▸326/(2)p.◂    rule    |                                    |
|                                     |                                    |
| 1976  Práce, Praha  2nd edition     |                                    |
|   ...                               |                                    |
+-------------------------------------+------------------------------------+
| PAGE-LEVEL VALUES (flat record, mixes publications)                       |
|   Translator  Božena Koseková, Božena Koseková, Božena Koselová   LLM gap |
|               fill, automatic check: not found in raw text as given      |
|   Page count  348   rule, belongs to the 1976 publication, page year 1968|
+--------------------------------------------------------------------------+
| Print volumes: not yet compared (per publication)    Cite  Export ▾      |
+--------------------------------------------------------------------------+
```

Narrow order: header, publications, wiki text collapsed behind "Show wiki text", page-level values, footer.

Behaviour

- Each value is a button. Activating it marks every exact occurrence in the wiki text with an outline and a text label "selected value", scrolls the text pane to the first occurrence and moves no focus. Esc clears the mark.
- If no occurrence exists, the value row says "not found in the wiki text" in words.
- For publication values the boundary check of S2.2 compares each occurrence with the publication's text range. An occurrence outside the range adds the line "occurs in the passage of the 1965 publication" to the value. Page 5021 is the reference case.
- Origin stands as a plain word (rule, LLM gap fill, missing, editor) in muted text. State appears only where a decision exists, as a word in a bordered pill with the producer sentence beneath it. "Details" opens the decision record (decider, basis, evidence, date or "no date recorded") inline below the value.
- A contested place shows "contested" and lists every recorded reading with its evidence lines, including the reading "no assignment". No reading is styled as the value.
- The page-level block explains in one sentence that the flat record combines publications and shows its values with the same origin, state and check notes. It exists because readers of the production app and of exports meet these values.
- Cite copies a citation for the page or the selected publication with identifier, data version and access date. Export offers BibTeX, RIS and JSON, each carrying origin and state.

Reference records: page 448 (four publications, LLM translator, verification flag), page 5021 (values from another publication, contested place), page 3183 (clean contested place).

### Prototype 2, Find and cite a work

A work-centred entry. The start view is a search field above a browsable list of works grouped by original title, with a scope panel. Selecting a work opens the work view.

```
+--------------------------------------------------------------------------+
| Klawiter Bibliography LAB    Search [______________________]   Scope     |
+--------------------------------------------------------------------------+
| Ungeduld des Herzens                                                      |
| Grouped from 37 wiki pages by the compiler's bracketed original title     |
| (rule, not reviewed). <n> pages carry no bracketed title  [what is not    |
| included]                                                                 |
+--------------------------------------------------------------------------+
| Languages  [All ▾]   Years  [1939 ──────── 2020]   ☐ only dated           |
+--------------------------------------------------------------------------+
| ▾ German (original)                         3 publications on 2 pages     |
|     <year> <imprint from data>          page <id>   ▸ record              |
|     ...                                                                   |
| ▾ Czech                                     4 publications on 1 page      |
|     1968  Svoboda, Praha                page 448    ▸ record              |
|     1976  Práce, Praha   2nd ed.        page 448                          |
|     ...                                                                   |
| ▸ English                                   n publications on n pages     |
| ▸ Undated (any language)                    n publications                |
+--------------------------------------------------------------------------+
| Possibly the same work: "Ungeduld des Herzens. Roman" (2 pages)           |
| Print volumes: not yet compared                     Cite work  Export ▾   |
+--------------------------------------------------------------------------+
```

Narrow order: title block, filters behind a "Filter" button, tree, related titles, footer.

Behaviour

- Search folds diacritics and umlauts, matches substrings across original titles, page titles and publication titles, and lists works first, then pages without a work group.
- The tree is a WAI-ARIA tree with arrow-key navigation. Group headings name their unit ("publications on pages"). A count opens exactly the listed rows. Pages that carry no publication layer appear as one row labelled "page without publication breakdown".
- The original group comes first and holds German-language pages. If none exists, the group reads "no German-language page under this title".
- Filters reduce the tree and announce the remaining number through a status region. Selecting a row never changes a denominator.
- The scope panel states the bibliography's states (printed 1965, 1991, 1999, unpublished Addendum II, wiki 2008-2020), what the lab shows (wiki data only), the grouping rule with its exclusions and the modelling limits from [Data](data.md).
- The URL holds work, filters and expanded groups, so a view is citable together with the data version shown in the footer.

Reference works: Ungeduld des Herzens, Schachnovelle, Brief einer Unbekannten with Der Brief einer Unbekannten.

### Prototype 3, Record history

A step-through of how one record came about, for the blog explainer and for readers who want to understand the workflow.

```
+--------------------------------------------------------------------------+
| How a record comes about                         Record: page 448  [▾]    |
| Every core value shows where it comes from. Step through the stages.      |
+--------------------------------------------------------------------------+
|  ① Wiki   ② Repair   ③ Parse   ④ Fill gaps   ⑤ Link places   ⑥ Publish   |
|  source   encoding   fields    LLM           agents/fixture  result      |
|  ●────────●──────────●─────────◉─────────────○───────────────○           |
+--------------------------------------------------------------------------+
| ④ Fill gaps                           Actor: LLM (Gemini 3.1 Flash-Lite), |
|                                       answer frozen in a cache            |
|  Translator was empty after ③ because the rule did not recognise the     |
|  name "Božena". The LLM filled it:                                        |
|     Božena Koseková, Božena Koseková, Božena Koselová                     |
|  Later check (verify stage): not found in the raw text as given.          |
|  Not recorded: the LLM's input and raw answer, rejected values.           |
|                                                   ‹ Previous   Next ›    |
+--------------------------------------------------------------------------+
| Where a person can intervene: field corrections and place decisions in    |
| the local edit mode (available), release into all exports (planned)      |
+--------------------------------------------------------------------------+
```

Narrow order: title, stage list as vertical steps, current card.

Behaviour

- The start state already shows the finished record with its origins, so a reader who does not step through still gets the message of the title sentence.
- Each stage card shows the record's state after that stage, the actor and what is not recorded. Stages without a change say "no change on this record".
- Arrow keys and the Previous and Next buttons move between stages, and the stage list is a tab list.
- A record switcher offers pages 448 and 5021.
- A static snapshot for the blog is rendered from the same data as one image per record.

## Data basis

A script under `pipeline/lab/` reads the published data under `docs/data/`, the tracked reconciliation decisions and the verification report, and writes prepared JSON to `docs/lab/data/`. It runs after the research coordinator's regeneration of the published data and never during a pipeline run. It derives the producer labels above, the publication text ranges for the boundary check of S2.2 and the record histories for E4. The source slice hash of a publication is computed over raw text that the site does not publish, so a browser cannot verify it. The lab states this where it shows the hash.

## Evaluation

The evaluation separates three levels of claim, what the code demonstrably does, which stories the prototypes pass, and what only a person with domain expertise can judge. A survey of evaluations at the intersection of visualisation and the humanities found that designs relying on an author's walkthrough or an expert checklist alone show the lowest rigour and recommends triangulating methods and reporting participants transparently (Benito-Santos et al. 2026). The protocol therefore combines the following components.

1. Task walkthroughs on six tasks, mapped to the stories: look up a work and its editions (S1.2), decide whether a value is documented in the source (S2.1, S2.2), explain a contested link (S2.5), characterise the reception of a work (S1.2), decide whether a gap is a source gap (S5.1) and obtain a citation (S3.1).
2. A heuristic pass by the AI operator with the value-driven heuristics of ICE-T (Wall et al. 2019), reported descriptively, because the published power analysis recommends five raters, and with project heuristics for provenance, state and gaps, labelled as the project's own derivation.
3. Simulated inspection by language model agents that interact with the running prototypes in a browser, two or three independent runs per prototype, each finding citing the view, the task step and the heuristic. Agent findings are triaged into confirmed, false positive and duplicate before they count. Studies comparing LLM inspection with human experts report large shares of duplicates and false positives and weak recall of expert findings (Guerino et al. 2025), and LLM-generated research data lacked the diversity of human data (Hämäläinen, Tavast and Kunnari 2023). The report therefore names model, date, prompt and runs and treats these findings as candidate issues only.
4. An accessibility check with an automated tool on each view and a manual pass covering keyboard completion of the tasks, a screen reader spot check and the critical heuristics of Chartability (Elavsky, Bennett and Moritz 2022).
5. A session with one or two Zweig specialists, if the operator can arrange it, with a think-aloud on the tasks, an open exploration and a critique interview that asks explicitly for what is wrong or missing, because positive expert feedback is prone to demand effects (Isenberg et al. 2013).

The process level asks how long a prototype took to reach its stories, which defects the project knowledge prevented or failed to prevent, which corrections needed a person, and how the two context conditions differed.

## Plan

The lab is complete when its three prototypes run on real data, keep origin and review state apart, have passed a critical review against the user stories, are evaluated, and their production is documented in the process record.

| Milestone | Content | Depends on |
|---|---|---|
| L1 Concept | assignment, principles, epics and stories in this document | operator review of the stories |
| L2 Interface specification | wireframes and behaviour per prototype, independent critical review against stories and data, revision | L1 |
| L3 Data preparation | `pipeline/lab/` script writing `docs/lab/data/` | the research coordinator's regeneration commit after the pipeline fixes |
| L4 Prototypes | three prototypes under `docs/lab/` | L2, L3 |
| L5 Prototype review | independent review of the running prototypes against the stories in a browser, fixes | L4 |
| L6 Evaluation | tasks, heuristics, triaged simulated inspection, accessibility, optional expert session, report | L5, availability of Zweig specialists |
| L7 Handover | process record completed, report to the research coordinator, commit | L6 |

The related deliverables run on their own tracks and share one blocker, the operator's decision whether the twenty fixture-based place decisions remain `confirmed`. The lab does not wait for it, because it shows those decisions as stored with their basis.

| Milestone | Content | Depends on |
|---|---|---|
| B1 Blog wording of review states | "bestätigt" used only where the data support it | fixture decision |
| B2 Blog figures | figures re-read from the regenerated artefacts | regeneration commit |
| B3 Blog explainer | static snapshot from prototype 3 | L4 |
| B4 Blog claim check | every statement checked against the artefacts, naming and editorship settled | B1 to B3, operator decisions on editorship |
| A1 Proposal version | choice of the working tab and of the role of Promptotyping as instrument or object of study | operator |
| A2 Proposal terms and literature | terms aligned with the vault decision of 2026-10-03, literature updated, gap claims checked | A1 |
| A3 Proposal evidence | dated cases from this repository and from the vault inserted | A1, B1 for the fixture case |
| A4 Proposal formalities | contractor role of DHCraft, disclosure of AI use in writing, CV decision, cost justification | operator |

## Process record

The record lists the human decisions, the agent briefs with their guardrails, the checks performed on agent results and the errors observed. Entries so far, all from 2026-10-23:

- The operator fixed output, research task and innovation axis by answering three questions.
- The research coordinator corrected a proposed fourth state, `checked`, against the statement states of the data model and replaced it with producer labels. The correction came from model knowledge the AI operator session lacked.
- A verification agent found that the blog handover described four of its five example pages inaccurately and discovered five pipeline defects. The AI operator checked the central counts and the translator name class against the files, and the research coordinator had them verified independently before fixing them.
- A literature agent put the operator's e-mail address into a request to a bibliographic web service once, against its brief, and reported this itself. Later briefs name the prohibition explicitly.

## Sources

Altay, S., and F. Gilardi. 2024. "People Are Skeptical of Headlines Labeled as AI-Generated, Even If True or Human-Made, Because They Assume Full AI Automation." PNAS Nexus 3 (10): pgae403. https://doi.org/10.1093/pnasnexus/pgae403

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
