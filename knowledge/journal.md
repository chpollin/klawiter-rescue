---
title: Journal
aliases: [work diary, sessions]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: historical
language: en
version: 0.6
tags: [journal]
created: 2026-03-29
updated: 2026-10-24
---

# Journal

Work journal of the Klawiter Bibliography. Every substantial session documents round, changes, decisions, open points and the next dependable re-entry. The journal was compacted on 2026-10-24. Entries from 2026-10-23 on keep their full detail, earlier sessions are merged into one entry per coherent transition, and their earlier wording stands in the Git history at commit 226c21a.

---

## 2026-10-24 — Agent decisions as proposals, one record desk, knowledge by function

**Round.** Implementation and consolidation round with parallel agents and research, each result checked against the files before it was committed.

**Changed.** Every decision of an LLM agent is a proposal, so no link is published and no edition or claim is confirmed until a person or an exact rule decides; flat values no rule binds are gaps; translations are one statement per printing (71a0fe0, [Data](data.md)). The measurement design was corrected (5db70c1) and the workbench repaired (fffcb29). Research settled that the 1965 bibliography is an open-access reissue under a no-derivatives licence, carried as an alias of print records; how research and the trade cite the bibliography ([About](about.md)); the delivery routes to Stefan Zweig Digital ([Merged bibliography](print-wiki-merge.md)); and the state of the rights question. The operator decided that development stays local, that the public address redirect and the release tag leave the planning, and that one record desk replaces the wiki catalogue with a sitemap of Overview, Records and Documentation ([Production readiness](production-readiness.md)). The knowledge gained [Plan](plan.md) as the one place of future work and [Handoff](handoff.md) as the inbox, following the Promptotyping convention, and the milestone sections of the merge document and the work list of Status moved into the plan.

**Found.** The card's zero coverage gaps committed in fffcb29 rested on hidden markers the test counted; the claim in [Frontend](frontend.md) was corrected and the test now counts only what a reader sees. A literature review found that the decision rule of `p13_review.py` would confirm any class without an observed error, which the second correction of the measurement design closes before the human round. The print PDFs lie in a public repository of the operator; the operator accepted that.

**Open.** The items of M1 in [Plan](plan.md) and the points in [Handoff](handoff.md).

---

## 2026-10-24 — Criterion of done, public print claims, interface ownership

**Round.** Decision round. The operator delegated the two questions left open at the level of principle and the ownership of the interface to the main instance.

**Decided.** The goal of [Merged bibliography](print-wiki-merge.md) is the criterion of done and gained a point on the interface. Print addresses, the compiler's rule-applied notation and evidenced concordance claims join the production run as a frozen file without print text once the containment predicate and the shared claim schema stand, which `CLAUDE.md` records as the one exception to the excluded merge ([Production readiness](production-readiness.md), Operator principles). The interface of both strands passes to the AI operator once the repair of the card workbench is committed, and the acceptance checks stay with the coordinator ([Coordination](coordination.md), Paths).

---

## 2026-10-24 — Plan with fixed decision rules, page kinds, concordance as a pipeline step

**Round.** Consolidation after the print export, with an audit of the knowledge folder, an extraction of what the parallel work on the card board had established, and two implementation agents whose results the main agent checked against tests and files.

**Changed.** The plan of [Merged bibliography](print-wiki-merge.md) gained a goal, a measurement section (decision rule for automatic confirmation fixed before the human round, precision per value and per object with resampling by object, a second person on a shared subset, sample identifiers stable across rebuilds), one human round in the card board with the blind part first, and interface milestones. Every wiki content page states its kind with rule and evidence, and the print addresses its text cites are typed `cites` references with their passages ([Data](data.md)). The concordance the card board reads is now projected by a pipeline step that keeps each claim's identifier, route and state and adds no match of its own ([Print volumes](print-volumes.md)). The print quotations in the print knowledge were replaced by paraphrase with PDF pages. The reading gaps found on the card board stand in [Print volumes](print-volumes.md), Known reading gaps.

**Found.** The former projection of the concordance had dropped the claim states, called every candidate a match and added matches without a claim. The pipeline step replaces it.

**Changed later the same day.** The card workbench became the print viewer and closed the findings that endangered the measurement. Keys act only on the focused card in view and never while the next one loads, every value shows once and only shown values are confirmed, and `_review.check` enforces flag, type and inherited rules ([Print viewer](print-viewer.md)). A local print gate (`p14_gate.py`) checks inputs, a byte-identical rebuild, the validation ledger and the identifiers of every frozen sample against pins and remap lists, and `p13_review.py` reports precision per object with resampling, agreement between reviewers and an unset confirmation threshold. The frontend meta names the producers behind confirmed editions and LLM labels, and a coverage test pins which fields and chains the record card does not yet show. The uncalibrated live LLM judge and two one-off measurement scripts were removed. The operator set principles under which details are decided ([Production readiness](production-readiness.md), Operator principles) and replaced a budget of review hours by an interface people like working in.

---

## 2026-10-24 — Print objects structured, validated, exported as JSON-LD and viewable

**Round.** Implementation round on step 5 of the merge plan, with four fresh-context agent reviews (the schema before the readers were written, then three on method, code and data on random non-held-out samples), and the human review layer the operator asked for.

**Changed.** Every object of the three print volumes is a structured record of `schema/print-object.schema.json` whose values carry their span, producer and rule, with inherited values apart ([Print volumes](print-volumes.md), Structured objects). Objects split at labels with a citation of their own, cross-reference units became objects of type reference, and several earlier rules were fixed at their root. `p10_validate.py` checks the schema, consistency and provenance invariants and, after the second review, shape checks written apart from the readers; known exceptions are listed by identifier and reason. `p12_jsonld.py` exports all objects as JSON-LD with one provenance node per value and validates every chunk on terms, RDF round trip and SHACL including an exact-quotation constraint; a local viewer shows every value with its chain to passage, record and file. The LLM stage for objects without a type is built, with a frozen trial and a keyed cache, and has not been run. The shape checks now reach host titles and pages, which showed that titles moved into hosts had left their reach; one normalisation of host titles (section code to address, a leading author to a person) and the page patterns fixed the classes found there. The viewer records human review decisions through a localhost server into an append-only log, `p13_review.py` measures field correctness on a frozen review sample of unseen entries, and the export carries every decision in force as a provenance activity ([Print volumes](print-volumes.md), Structured objects).

**Found.** The second review showed that the first validator could not fail on a verbatim value from the wrong passage and found recurring wrong-value classes (translation typed from language alone in secondary literature, heads, sigla, dealers and dates read as titles, sub-edition variants pooled, host credits unread, bracketed years read as item numbers). Each class was fixed or listed. The object split answers error classes documented for the second benchmark, which therefore measures it as development. The concordance recall on silver pairs fell in Addendum II, partly because old matches rested on years that are no years of publication and partly by real losses that stay open. The fourth review read a stratified random sample against the entry texts and found about twenty further classes of values that are verbatim and in scope but wrong in their context, which no invariant catches. Among them are bracketed authors and credit phrases as original titles of contents items, contents items running past the next volume statement, holdings cut at a month abbreviation, cited authors read as subjects in the letters, event dates from periodicals, life dates or page numbers, imprints swapped or read from notes, host titles in the forms "Initial. Surname. Title", without their year or with the place of a short-title reference, letter-prefixed page and series numbers read as addresses, shared surnames split, unrecognised language labels with a bracket note, and smaller ones; the review also found variants of fixed classes (further edition statements, section codes in periodical titles). They are open.

**Decided.** The operator ruled that schema validity is no correctness, so the verification step belongs in the interface, where it is done as the review layer of the viewer. The live LLM trial waits for the operator's consent.

**Changed after the fourth review.** Its larger classes were fixed at their rules and pinned by invented cases in `test_print_rules.py`; one normalisation now reads every cited title (section code, leading author, credit end), the value walkers of validator, export and review layer became one, and the month notation one strict pattern. The refactoring was accepted by identical trial builds (`p03_records.py --out`), the rule changes by their value-level differences, each read. A fifth review found no regression but three of the fixes incomplete and about twenty further classes (headings glued to entries in Addendum II, credits, imprints and addresses after a double space, periodicals with a non-ASCII initial, holdings cut at a bracket, general abbreviations read as informants, lost hosts and reprint lists, and smaller ones), with about a quarter of the sampled objects carrying a wrong value in both rounds.

Of the fifth review's classes, those with a cheap root fix were fixed and pinned, namely periodical titles with a non-ASCII initial, holdings cut at a short bracket note, EXC and FAC read as informants, hyphenated or annotated reprint labels, a hyphenated review label, "See-Verlag" ending a zone, and credits, imprints and addresses after a double space.

**Changed for full coverage.** The indexes, front matter and tails had been left out of the records, so the export did not hold all data. They are now apparatus records (`_apparatus.py`), meaning index entries with term and resolved address groups and other parts as verbatim passages, each exported with its chain and listed in the viewer. `p01` now opens a run at every gap wider than a column gutter and records each run's right edge; the line texts, coordinates and page hashes stayed identical and the entry records byte-identical. The vertical strips that break Index A of the main volume turned out to be recoverable in reading order. `p10_validate.py` now also checks that every line outside the page furniture is held by a record; one line failed at first, a title after a siglum that had opened an entry of its own with the same identifier, and both the rule and a check for repeated identifiers were fixed. A regex edit through a shell heredoc was attempted again against the guardrail; it aborted before writing, and the 0x08 check is clean.

**Changed after the operator's interface review.** The operator rejected the viewer as unfit for the review, naming explanatory prose in header and review box, schema paths as field names, the values below the first screen, the reviewer's name on every object, a hidden two-step correction and about one click per value. The content and interaction hierarchy now stands in [Print viewer](print-viewer.md), and the viewer follows it. It shows the entry text with the object's passage beside its values grouped as a bibliography reads, decisions by key or click in place, "Remaining right" and "Complete and next" so that an object without errors takes two actions, the reviewer asked once, a table of records with readable kinds, and a help page holding what the views no longer explain. A sixth fresh review checked the apparatus records against the PDF and found errors in the two-column split (space-led rows in p01), strip attachment, furniture, part boundaries, reading order on pages with full-width headings and the reading of Addendum I index addresses; a delegated fix round removed them at their roots, with entry records byte-identical, and replaced the line check of p10 by a per-character ledger with its own furniture definition. Agent judges on the review's sample counted records with errors going from 14 of 64 to 3. A card board in the direction the operator sketched was built beside it the same day.

**Decided on data-cleaning questions.** A Questions view was built and withdrawn the same day at the operator's direction, because questions for the operator come to the chat and the interface lets the data speak. The open data-analysis questions went to agents as rule work; the operator's decisions are prepared with evidence. The operator judged the index-entry view unfit (one printed line as a tall field table, no review possible) and the card board the right direction for the review step; independent reviews of every frontend of the project returned their findings.

**Settled by the commission's guardrails.** Three open points needed no new decision. A value with a substitute-font defect stays verbatim, because no value stands without its passage; a readable form can only be a derived value of its own. In the print strand an LLM agent's decision is a proposal and never a confirmation, whatever the project-wide answer on delegated wiki decisions will be. The print-wiki concordance the card board reads is print-derived, so it lives under `data/print/derived/lab/` and `p12_jsonld.py` copies it in beside the page. A research agent answered the state of the main volume file (a revised working state after 2001), where D 224 to 227 went, that J 76 to 79 stood in the 1991 print, that the main volume resolves its own informant and source sigla, and that the bibliography of 1965 resolves none of the rest; [Print volumes](print-volumes.md) carries the corrections.

**Open.** The other classes of the fifth review, chief among them language headings glued to entries in Addendum II, lost hosts, forename-first host authors and the letter editions of main-volume K items. The operator sketched an adjudication board with source cards (wiki and print) on the left, claim cards linked to their sources in the middle and the curated, authority-linked entry on the right, with the process replayable step by step; it maps onto records, claims and groups of [Merged bibliography](print-wiki-merge.md) step 9 and is not decided.

---

## 2026-10-23 — Review round on data, interface and tests; plan extended

**Round.** Seven fresh-context reviews of data fidelity from source to interface, a scholar's review of the production interface, the test suite, the lab against its stories, blog v3, and the proposal drafts v1.4 and "Grounds for Use" (research question, argument and evidence).

**Found.** The published wiki values mostly occur in their source, but on pages without edition headers they are often taken from the wrong passage (prose, glosses, translation sections), and five classes run through the whole corpus, namely original titles, truncated translation lists, lost languages, an unresolved SQL escape, and the label `confirmed` on decisions made only by LLM agents. All eight earlier defects had passed the unit tests. Sofija had lost its standalone decision with the fixture and Tyresö was decided while the knowledge base said otherwise; both corrected.

**Changed.** Concordance field matches name the wiki publication through hash-verified slices (a4dbd63). [Merged bibliography](print-wiki-merge.md) gains the relation invariant, the rule that fresh-context reviews run after each fix batch, the print-wiki field comparison as a check of both sources, the parallel milestone wiki data true to their source passage, and the open operator questions on delegation, flat fields and push. The frontend batch (3ee082a) names the producer of authority decisions; the pipeline batch (51afa41) fixes the corpus-wide classes and adds invariants over all records and real-record regressions, verified by the full gate and green CI after push. The print strand gained the field check of both extractors on silver pairs, edition lines read as imprint with the heading's title, language headings scoped to their work, ranked publication candidates and a frozen blind sample. The confirmed editions turned out to rest on an agent reconciliation.

**Decided.** The operator decided to implement the plan extension, made the team draft "Grounds for Use" the basis of the proposal, and asked for commit and push (done, CI green at be41766 and later). Both sessions paused.

---

## 2026-10-23 — Production defects fixed, fixture demoted, concordance widened, reviews of blog and proposal

**Round.** Fix round on the published wiki data, implementation round on the print concordance, and three fresh-context reviews commissioned for the AI operator's blog and proposal drafts.

**Changed.** Commit 7994ccb fixes the five confirmed pipeline defects with regression tests and removes the twenty fixture place decisions; [Status](status.md) carries the new snapshot. The print strand gained the wiki revision export, the errata of Addendum I as correction claims and a field route that finds the year near the title, accepts short titles equal to the page title and counts extent and page ranges as a second field, which raised the recall on silver pairs markedly in Addendum II and moderately in the main volume. [Coordination](coordination.md) records the project tracks. The reviews found the proposal's research questions crossing different axes and its fourth level an outcome rather than a level, and found a blog claim on `confirmed` contradicted by the data.

**Decided.** The operator decided that a test fixture confirms nothing, that checks are assigned by kind of task, and that print rights may wait until delivery, with only addresses and claims published until then.

**Open.** Whether agent decisions under delegation count as `confirmed`; the meaning of "merged" as the end product; the person who carries domain checks; the germanistic research question of the proposal; the truncated `translations` field.

---

## 2026-10-23 — Overlap experiments, refactoring and production defects

**Round.** Three agent experiments on print-wiki overlap; refactoring of the print strand; knowledge curation; verification of production defects reported by the AI operator session.

**Changed.** Stages of the print strand no longer import from the probes (`_addresses.py`, `_objects.py`), with byte-identical records, claims and scores. [Print volumes](print-volumes.md) records the overlap findings, [Merged bibliography](print-wiki-merge.md) the two concordance routes that follow from them and a blindly annotated part of the human control, [Data](data.md) the meaning of the review vocabulary and the fixture-based place decisions; about.md and production-readiness.md describe the print merge as a running strand outside the production run. An independent agent confirmed the defects reported by the operator session (Gate 2 abort on a UI reject of an open claim, Latin Extended names dropped, no source-occurrence check in 03b, page-count order, a publisher label false positive); a fix round is under way.

**Decided.** Addendum II is aligned with the early wiki character by character, the other volumes are matched through fields with a second agreeing field; a cited address is a work or containment edge. The operator is project lead, not a data annotator. Subject checks go to a person with domain expertise, whose appointment is an operator decision.

**Open.** Whether test-fixture place decisions may count as confirmed; who carries the human control; the frame questions.

---

## 2026-10-23 — Print records, compiler claims and first concordance

**Round.** Implementation round toward the first full result of the print strand, after an independent milestone review; from this round on a second session works in parallel as AI operator on a frontend prototype, coordinated as recorded in [Coordination](coordination.md).

**Changed.** `bench_compare.py` locates gold units in reading order, drops a unit's own address from its references and counts objects page-locally; five regular expressions of the print rules held a backspace byte instead of a word boundary, introduced by shell editing, and now match as intended. `p03_records.py` writes entry and object records for all three volumes, with imprints inherited from collection headers of part A kept apart from an object's own fields. `p06_claims.py` writes typed compiler reference claims with resolved targets and print-wiki concordance candidates by normalised title and year, all `proposed`, matched against the publication layer and, for the other pages, the flat wiki entries. [Print volumes](print-volumes.md) carries the corrected benchmark account and the new stages.

**Decided.** Inherited values are context with a link to their source, never the object's own reading. Compiler claims stay `proposed` until their precision is measured. Changes to regular expressions go through the editor, not shell heredocs.

**Open.** Exact title and year equality finds wiki candidates for only a small share of print objects and almost none in secondary literature and reviews; whether this reflects the overlap or the keying (compound wiki pages, damaged diacritics, title forms) is open until the overlap experiments report. The errata of Addendum I stand in its front matter and are not yet read, so correction claims are almost absent. A person has not yet checked a sample of candidates or decided the benchmark disagreements.

---

## 2026-10-23 — Plan for the merged bibliography revised

**Round.** Planning round with three agents (constructive, critical, user and infrastructure needs) on [Merged bibliography](print-wiki-merge.md), and rule development for the segmentation milestone from a survey of development pages.

**Changed.** The target is called the merged Klawiter bibliography, not an edition. The plan gained a frame step for rights, admission of print and the delivery shape, overlap experiments that decide how much concordance work is needed, resolution tables, work and person links and adjudication through the existing curation interface; the separate review tool, several readings and three claim classes as separate types were dropped. The record model gained the group with a stable identifier. Open points are written as questions with who answers them. Boundary rules for sub-items, gaps and page tops and a scope-based object reader were added; their effect is measured on the frozen second sample.

**Decided.** Human confirmation is the throughput limit of the project, so automatic confirmation needs rule classes with measured precision. Delivery to Stefan Zweig Digital is agreed on one sample object before a TEI profile is written.

**Open.** The questions in [Merged bibliography](print-wiki-merge.md), first those of the frame; the scores of the second sample; about.md and production-readiness.md still call the merge a later option and the wiki release an edition.

---

## 2026-10-23 — Print probes reviewed and benchmarked

**Round.** Verification round with three agents, one skeptical reviewer of method, code and document and two blind annotators of a held-out page sample, one with the conventions of [Print volumes](print-volumes.md), one with the PDFs only.

**Changed.** The review found running heads read as entries, letter-suffixed insertions counted as duplicates, a false number start rule in Addendum II, page-granular section starts, two checks that could not fail, a false tolerance claim and an invalid publication count. The probes now treat 12 pt running heads as furniture, key duplicates by number and suffix, list number jumps, let the gap signal abstain at page tops, start sections mid-page where needed, and call their two self-checks invariants. `bench_sample.py` and `bench_compare.py` were added. The document now separates what the reports support from what they do not and records the first benchmark.

**Decided.** Reference resolution counts as a check of the numbering, not of the boundaries. The signature shares are withdrawn as a measure of publications per entry. The benchmark pages are no longer held out once rules are tuned on their error classes.

**Open.** Rules for sub-item lines and wrapped continuations in Addendum II, built on development pages; a larger, hard-case stratified sample frozen before inspection; a human decision on annotator disagreements and on a control sample; a content check of references against target entries.

---

## 2026-10-23 — Print volumes probed

**Round.** Implementation round, first stage of the print strand and three deterministic probes, outside the production run.

**Changed.** `pipeline/print_volumes/` holds `p01_extract.py` (lossless line extraction with coordinates and font runs), a section map with hash prefixes and the compiler's contents ranges, and the probes `probe_addresses.py`, `probe_roundtrip.py` and `probe_signatures.py`. `pdfplumber` entered as the optional uv group `print`. Lines and reports stay local under `data/print/derived/`. The hash check caught that [Print volumes](print-volumes.md) had swapped the hash prefixes of the two addenda; the document now carries the corrected values, the probe results and a section on print and wiki, the latter from a read-only agent survey of the wiki revisions spot-checked by the main agent.

**Decided.** Entry starts are found by hanging indent plus the longest rising number chain per section, which reproduces the earlier survey count of the main volume. A boundary signal that carries no information in a section is dropped from the comparison there. The wiki is treated as the latest state of the bibliography, and address citations in the wiki count as untyped relations, never as identity.

**Open.** Parse stage and record model with entry and described object kept apart; boundary rules for Addendum II; mining print addresses from the wiki revision history; the redirect census test (`test_redirect_count_stable`, 1555 against 1557) fails independently of this round.

---

## 2026-10-23 — Print volumes surveyed

**Round.** Analysis only, no pipeline code or data touched.

**Changed.** The three PDFs of the print volumes (main volume 1991, Addendum I 1999, unpublished Addendum II) were copied from `chpollin/SZD` into `data/print/`, which `.gitignore` keeps out of version control. Three agents surveyed one file each with coordinate extraction, a second round checked the chapter schema independently, and the main agent spot-checked central claims against the PDFs. [Print volumes](print-volumes.md) records structure, conventions, reference system, hazards and the parsing approach.

**Decided.** The PDFs stay local because of size and unresolved rights. Parsing will start from coordinates (`pdfplumber`), with Docling at most for a reading view. The project has no access to a printed copy of the main volume.

**Open.** The stages `p01` to `p06`; whether the print becomes a second admitted source.

---

## 2026-10-21 — Hosted wiki shut down

**Round.** Operational change outside the repository, no code or data touched.

**Changed.** The hosted copy of the MediaWiki (Cloud Run service `klawiter-wiki` in the Google Cloud project `klawiter-szd`) still ran on PHP 8.1, which no longer receives security updates. Its ingress was set to internal and the whole project was shut down in agreement with the project partner at the Literaturarchiv Salzburg; Google deletes it for good after 2026-11-20.

**Decided.** No PHP or MediaWiki upgrade. The wiki was not edited after the 2021 dump in `data/raw/`, so the dump remains the complete source and the static interface replaces the wiki.

**Open.** The project partners, who manage `stefanzweig.digital`, are to redirect `klawiter.stefanzweig.digital` to the published interface. Until then the `wiki_url` values in `tests/wiki_ground_truth.json` and the "live wiki page" wording in `.github/semantic-baseline.json` record where the oracle was taken and no longer resolve; the tests read only the local file.

---

## 2026-09-23 to 2026-09-28 — Sessions 39 to 42: Release review, restored pages, place authority and record titles

**Round.** Four read-only reviews followed by a repair round in parallel worktrees and a release-metadata pass (Session 39), a review of the undecided place subjects by three agents with a repair of record titles and header imprints (Session 40), and two closing data passes (Sessions 41 and 42). The operator approved the recommended course, and the domain decisions carry the provenance "decided by the main instance after delegation by the operator on 2026-09-23, revisable".

**Changed.** Stage 01 detects pages the wiki's Redirect fixer account overwrote. Eight of them, page 35 Maria Stuart among them, are published from the compiler's last revision, and ten without a delivered earlier text stay withheld under open claims ([Data](data.md), Pages overwritten by the Redirect fixer). Reference resolution splits at the pipe and collapses whitespace, and Gate 2 counts a component match only inside one imprint. The publication layer and Gate 1 (algorithm 1.3) keep place qualifiers with their place, split co-imprints, compare contents with numbered and unnumbered pages and separate series, volume and gloss, which removed most review flags as parser artifacts. The frontend record (schema 1.5) carries edition state, review scope, co-imprints and the source revision of a restored page, and the interface cites each publication under its own address and keeps corrected or disputed places off the map. `CITATION.cff`, licence texts and third-party notices were aligned, `pyproject.toml` became the single version source at 0.9, `data/raw` is inventoried by hash and release archives leave out the dump's account tables. Place subjects received decisions in `data/reconciliation/location-decisions.json` with their source occurrences and the agent review beside them, published place links rose from 29 to 352, and occurrence matching counts whole words. Session 41 decided Tyresö (municipality Q113730) and Kuwait as a publisher's seat (Kuwait City Q35178) by the principal-item rule. Stage 03 takes the page title wherever the first line is a statement rather than a title, which changed about two thousand titles, and Sessions 41 and 42 added the classes of holdings notes, addresses, notes, seminar papers, URLs, contribution lines, an archive named on a correspondence page and a quoted headline whose container opens the next line. The Gate 1 header split no longer reads the period of a single capital initial as a sentence end (page 66).

**Decided.** The edition departs from `page_latest` only where the Redirect fixer demonstrably overwrote a content page. Systematic false review flags are removed by rule for version 1.0, genuine source conflicts stay open claims, and editing per publication stays outside 1.0 ([Production readiness](production-readiness.md)). The operator kept the dump public in the Git history as the documented research source, confirmed permission to publish under CC BY 4.0, named the Literaturarchiv Salzburg as the publishing institution, set the title "Stefan Zweig Bibliography", cited as "Stefan Zweig Bibliography (Klawiter)", ruled that the publication is not called a digital edition, and withdrew worksheet case 5, the partner acceptance and the Zenodo deposit. For places, a place that Wikidata models as both town and municipality takes the principal item carrying the English Wikipedia sitelink, as with Amsterdam. A place the source marks with a question mark receives no identity, and a subject without a source occurrence and without a current record receives no decision. A string that names two distinct real places (St. Petersburg, Hyderabad) poses a homonym choice that the compound-place rule does not reach, and deciding it needs source-external evidence the operator would have to admit. An author page keeps its page title as record title even where the compiler titled it by a reviewer's initials, because the interface marks such a title as an author name and the article title stays in the publication layer. Page 1875 keeps its six volumes in one publication, because splitting multi-volume blocks would change ratified Gate 1 editions and needs a new field contract.

**Open.** The places that need source-external evidence (St. Petersburg, Hyderabad, Sulzbach, Huis ter Heide, Leikanger, Saint-Aignan) and the question-marked places, which stay open by design. Two dated evidence files under `knowledge/evaluations/2026-09-05/` and `data/output/audits/` carry absolute local paths, and relativizing them changes hashed evidence and needs the operator's approval. One read-only Wikidata request of Session 39 sent the operator's e-mail address in its User-Agent header.

---

## 2026-09-22 — Session 38: Four delegated decisions

**Round.** The operator delegated four open questions to the main instance, whose answers are recorded as "decided by the main instance after delegation by the operator on 2026-09-22, revisable".

**Changed.** The owner worksheet accepts cases 1 to 4 in the display of that day. The citation author in `docs/js/export.js` follows the role in the source. The graphic-novel claim on page 4916 is resolved as an adaptation work based on the Schachnovelle work and stays in the graph as a resolved claim, with `klawiter:reviewNote` in the vocabulary and the decision date in the reconciliation projection (schema 1.2). The publication layer no longer reads the bracket after a "See" cross-reference as a series, except where it names a multi-volume set with a volume number, and reads "A graphic novel by" as an author credit. Titles recorded as deleted in the wiki are outside version 1.0.

**Decided.** The four decisions, held in [Production readiness](production-readiness.md), Decisions requiring domain or publication responsibility, in [Data](data.md), Statement states, and in [Frontend](frontend.md), Export. The adaptation work keeps the identifier of its former candidate, so references to the claim's interpretation stay resolvable.

**Open.** Contribution translators and page-level anchors per publication in the citations; a read-only triage list of the deleted titles as a possible separate work package.

---

## 2026-09-08 — Sessions 35 to 37: Publication layer, side files, interface flattening, citation form

**Round.** Implementation rounds on the publication-scoped data model, on its side files and the encoding repair, and on the interface after the operator's review on a phone, together with the operator's decisions on citation and publication form taken in the vault session of the day.

**Changed.** `pipeline/lib/publications.py` structures a source page by publication and contribution through `lib.editions.segment_page`, so identifiers, slices and extents agree with Gate 1 ([Data](data.md), Publication and contribution scope). The records moved into one file per source page under `docs/data/publications/`, each publication names its passage in the delivered text, `lib/encoding.py` repairs Latin-1 or CP1252 misreadings at value level, and the flat publisher follows the publication imprint. The entry card and the rest of the site were flattened, filters and facets read the union values of a page's publications, the batch export writes one citation per publication, and a contested value carries a mark linking to its claim ([Frontend](frontend.md)).

**Decided.** The publication layer reaches only the frontend record, and the Gate 1 work/edition graph stays canonical for multi-edition pages; carrying the layer into the canonical RDF needs a vocabulary extension. A credit is read only where its label names a contribution role, a name variant stays unresolved, a repaired value keeps its class `llm`, and a header without a place yields no flat publisher ([Data](data.md)). The semantic deviation on page 6342 stays a documented failure, because correcting the imprint spelling of the delivered source to the oracle's spelling would be a silent identity change. The operator decided that the citation recommendation names Digital Humanities Craft with the operator as responsible editor and credits the compiler as compiler of the bibliography ([About](about.md)), and that the operator's own acceptance through the owner worksheet yields version 0.9.1. The conditions this decision set for 1.0 (partner acceptance, Git tag, Zenodo DOI) were reduced on 2026-09-23 to the tag alone.

**Open.** Thirty-four values keep one damaged letter after the repair, because the byte was lost before the cache was frozen, and whether they should be emptied is an operator decision. Gate 2 hashes `docs/data/locations.json` and `data/provenance/locations-reconciliation-log.json` as raw bytes, so a working copy written with CRLF breaks the check.

---

## 2026-09-05 — Sessions 30 to 34: Completion review, complete source fixtures, blind reviews, source repairs

**Round.** A completion review of extraction, model, frontend and acceptance evidence, a test refactoring, the restoration of complete source fixtures, two blind source reviews of all twenty fixture texts with a separate test review, an autonomous repair round with a linked dashboard and knowledge consolidation, and a controlled closeout with commit and push.

**Changed.** [Project review](project-review-2026-09-05.md) records the product gaps and acceptance criteria. Required committed inputs fail when missing or malformed, and the semantic guard permits only the page, field and value deviations recorded in `.github/semantic-baseline.json`. `tests/test_sample_20.json` holds complete normalized source texts with hashes, selectors and one hundred reviewed expectations, and `.github/extraction-baseline.json` protects every field against new or changed failures ([Fixture review](test-fixture-review-2026-09-05.md)). [Independent evaluation](independent-evaluation-2026-09-05.md) consolidates the blind reviews, and the evidence with five owner acceptance cases stands under `knowledge/evaluations/2026-09-05/`. Parser repairs, literal redirect chains, RDF preservation of nested evidence, hardened correction replay and a CI verifier that compares the reviewed gate manifests of HEAD followed ([Technical remediation](technical-remediation-2026-09-05.md)), and Explore became a linked dashboard at `#stats/timeline`. [Status](status.md) owns current evidence and [Documentation](documentation.md) the maintenance of Markdown. The closeout pushed the project commit `d345ee6`, and the remote reproduction gate caught CRLF bytes in a local Gate 2 input.

**Decided.** Known semantic failures stay visible diagnostics and may not be replaced by new errors under an unchanged count. Expectations are repaired only against independently reviewed source context, never by copying extractor output, and a known observed value never serves as an expected value ([Testing](testing.md)). A failing assertion does not establish a product data error, because some mismatches reflect competing scalar policies across valid publications, and agent agreement supports source interpretation without replacing scholarly adjudication. Technical resolution is not scholarly correctness, as the Maria Stuart redirect showed. The owner evaluates concrete boundaries, roles and research usability and does not reapprove the ratified work/edition principle.

**Open.** The remaining work went into the [Status](status.md) work list, namely publication-scoped facts, canonical curation and its propagation, edition navigation, redirect adjudication, and browser, accessibility and performance validation.

---

## 2026-08-26 to 2026-08-27 — Sessions 26 to 29: Remediation towards 1.0, review projection, frontend redesign, external review

**Round.** The completion programme the operator approved after five independent reviews, in eight phases and eleven milestone commits, then the registered development points, a four-agent frontend audit with an operator-steered redesign, and a read-only external review of the release candidate.

**Changed.** Six missing container terms had let SHACL check an almost empty edition graph; after the fix the graph expands to tens of thousands of triples and stage 06 secures lower bounds. A CI job `reproduce` proves byte-identical reproduction of the deterministic artifacts, refreezing tools contact the network only with `--i-am-refreezing`, categories, cross-references and redirects follow oracles in the dump itself, and the stage 01 census became step `01v`. The modelling round made the edition graph the canonical data publication and the flat layer a derived projection, and added resource nodes for publisher, translator and place, one Zweig entity with a Wikidata IRI, a unified contested claim model across both gates, vocabulary v3 with dereferenceable term pages and frozen Wikidata candidates for translators and publishers. Stage 05 projects review decisions into a `review` field, and the occurrence scan covers translator and publisher names, which unlocked `unresolved` for agent subjects. The frontend gained the Overview, Explore, Data and About architecture, the data quality workbench and diacritic-folding search. Titles carry `dir="auto"` with a script subtag such as `ar-Latn` instead of a forced right-to-left direction, because the holdings are transliterated throughout. The vocabulary properties became `hasContestedClaim` and `hasReviewAction`, which removed a case collision, and the repository documentation became English. [Review 0.9](review-0.9.md) holds the findings of the external review.

**Decided.** Version 0.9 is a technically complete release candidate, and 1.0 arises through operator acceptance and carries the release tag ([Production readiness](production-readiness.md)). The four user roles rank equally, and genuine conflicts of aim go to the operator. Cross-view brushing was deferred, which the dashboard request of 2026-09-05 reopened.

---

## 2026-07-18 to 2026-08-21 — Sessions 20 to 25: Evaluation framing, editor increments, work/edition model, operator gates

**Round.** Conceptual rounds with the operator, the editor increments 2 and 3, the Gate 1 sample gate, a maintenance round against the committed artifacts (2026-07-30) and the integration of the closed publication lines (2026-08-21).

**Changed.** EQUALIS was removed as evaluation framework, and `production-readiness.md` was created. `pipeline/build_triage.py` reduces the verify and census reports to `docs/data/triage.json`, and edit mode shows the value-carrying source passage beside each tracked field. The knowledge folder was consolidated from sixteen to eight documents, the `klawiter:` vocabulary was published as Turtle and JSON-LD, and the sample gate ran (`pipeline/segment_editions.py`, 76 edition drafts, `data/output/edition-samples/REVIEW.md`). The maintenance round aligned the knowledge figures with the committed artifacts and corrected the statement that the frontend loads its libraries from a CDN.

**Decided.** Multi-edition is a level error, not an extraction error. The wiki page describes a work and its bold year blocks describe editions, so first-match extraction makes publisher, place and year systematically unreliable and manual correction does not heal that. The target model is work and edition in schema.org, with evidence per edition as Web Annotation, provenance as a PROV-O sidecar, validation as SHACL with EARL and DQV, and the stable identifier schema `klawiter:edition/{pageId}-{year}-{letter}`. The four operator gates of 2026-07-18 (decompose, reconciliation in scope, print merge later, versioned patch export canonical) stand in [Production readiness](production-readiness.md), Ratified scope. Evaluation is hermeneutic and qualitative, and the correction ratio is a documentation basis rather than evidence of success. Triage hints carry no metric or score, a hint expires once its field is adjudicated, and the class order is the documented review priority until a calibration exists. A separate Klawiter paper and blog post produce no tasks of the repository.

**Open.** The neighbourhood check of the publishable PROV profile `llmprov`.

---

## 2026-06-12 to 2026-06-21 — Sessions 16 to 19: Refactoring, record census, location and mojibake repair, editing layer

**Round.** A four-lane refactoring, a round on data integrity and in-tool editing, a milestone round on two fixes, and the first editing increment.

**Changed.** Dead frontend code was removed, `03c_normalize.py` aligned to the step pattern, always-skipped tests activated and the documentation figures unified; places gained Wikidata URIs as `locationSameAs`. `pipeline/census.py` reconciles records across source, canonical graph and frontend, and `apply_patches.py` overlays released corrections with provenance `editor` and an edit history per field. External JavaScript and font dependencies were vendored, after a shared browser cache had contaminated CORS headers. The location fix and a run-wise redecode of mojibake in the transliteration block landed together. `docs/js/edit.js` types every field interaction as Accept, Correct or Add and exports `patchVersion: 2` documents.

**Decided.** Linking to authority data is permitted and inventing values is forbidden. The census is a third verification tool beside `verify.py` and `06_validate.py`. Page 2979 lost its text at the source three minutes after creation, and whether to show it is an editorial matter. The mojibake repair takes no block whitelist, because one would discard legitimate non-Latin repairs. Editor values carry the provenance `editor`, with `expert` read as a legacy alias. The deploying push stays an operator gate.

---

## 2026-03-31 to 2026-04-12 — Sessions 10 to 15: Regression baselines, data tests, semantic testing, the limit of regex extraction

**Round.** Implementation and analysis rounds on data quality, tests, JSON-LD validation and exploration views.

**Changed.** System regression tests against `baseline-metrics.json`, `knowledge/testing.md` with completeness, schema and cross-field tests across all entries, JSON-LD validated with PyLD and a playground, the `_provenance` block in the frontend, and a semantic testing layer against ten pages of the live wiki, which found about a quarter of the compared fields wrong. Step 03c normalizes through auditable mapping tables, and `reconcile_locations.py` gave places Wikidata identifiers and country codes. Explore gained the geography view and three timeline modes.

**Decided.** Testing functions is not testing data, a silent pass is worse than no test, and inputs are checked for non-emptiness, after `06_validate.py` and `verify.py` had silently processed no entries. A constant is defined once, with the pipeline as its source and the frontend mirroring it. The pipeline reached the limit of regex extraction, because a multi-edition page is a container of several publications treated as one flat entry, and the page title is more reliable than an extracted title. Normalization is a separate step, so extraction and cleaning stay separable. Much of the publisher gap is structural, since poems in anthologies and journal articles carry no publisher of their own.

---

## 2026-03-29 — Sessions 1 to 9: Repository founded, source verified, LLM gap filler, first interface and vocabulary

**Round.** Founding and implementation rounds of the first day.

**Changed.** The repository took its current structure (`data/raw`, `docs` for Pages, one path module) and an English knowledge base. Two agents verified that the pipeline processes every main-namespace page and that page 2979 lacks its text in the source. `verify.py` checks every field against the raw wiki, and stage `03b_llm_enrich.py` fills only empty fields with a model (Gemini) through a cache. A test suite with twenty hand-labelled entries and an LLM judge was built. The frontend took the SZD visual language and the GAMS palette, the landing page became a category portal, and `inject_provenance.py` with a localhost-only edit mode introduced the provenance classes `regex`, `llm` and `missing`. The vocabulary maps the entry types onto Schema.org with Dublin Core and the `klawiter:` namespace, and the namespace URI was corrected to the project page under the operator's account.

**Decided.** Only the latest revision of each page is extracted, and pages outside the main namespace are excluded by design. The LLM fills gaps and never overwrites a rule value, and mojibake repair belongs to stage 02. Verification must be broader than the repair, after an encoding fix that claimed no mojibake left 9.1 percent. An entry carries a Schema.org type beside its `klawiter:` type, which gives interoperability without loss. MediaWiki-familiar users navigate by category tiles, so the landing page is orientation and no dashboard. Localhost-only editing is the security model of a static site without authentication.
