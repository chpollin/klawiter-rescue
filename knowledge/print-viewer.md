---
title: "Print viewer: views, content hierarchy and interaction"
status: draft
language: en
created: 2026-10-24
updated: 2026-10-24
related: [print-volumes, print-wiki-merge]
---

# Print viewer: views, content hierarchy and interaction

The print viewer (`pipeline/print_volumes/viewer/`, served locally with the data of `p12_jsonld.py`) has two tasks: a person decides whether the values read from the print volumes are right in their context, and anyone working on the strand looks up a record with its provenance. The first task limits the throughput of the strand, because correctness is measured only from these decisions ([Print volumes](print-volumes.md), Structured objects), so the viewer is designed around it. The visual identity follows the production frontend (palette and type stacks of `docs/css`), since the project has no design document of its own.

The operator rejected the first version on 2026-10-24: standing explanatory prose in the header and the review box, code paths as field names, the values to decide below the first screen, a reviewer name field on every object, a correction hidden behind a second button, and about one click per value with no way to finish a correct object quickly. The hierarchy below replaces it. Kept from the first version: every value with its passage and chain, the decision kinds of `_review.py`, read-only mode without the server, apparatus records without review controls.

## Review of an object

Task
: Decide for every value of one object whether it is right in its entry, then mark the object complete and go to the next open object of the sample.

First screen
: One line naming the object (volume, part, address, PDF page, its position among the objects of its entry) and its review state. The entry text with the object's passage emphasised and scrolled into view, beside the values grouped as the bibliography reads (title block, persons, imprints, extent, edition notes, series, periodicals, host, contents, references, relation, inherited values), each with a readable label, its value and its decision. The decision count and the two finishing actions stay reachable at the bottom of the screen.

On demand
: The provenance chain and decision history of the selected value, the producer where it is not a rule, the rule name, the internal identifier. A missing value and a wrong object boundary are secondary actions after the values.

Interaction
: Selecting or focusing a value marks its passage in the entry text. Right, wrong and unsure are one key or click each; wrong opens the correction in place, taken from the text the reviewer selects in the entry, with "should not exist" as the alternative. "Remaining right" confirms every undecided value, "Complete and next" closes the object and opens the next open one, so an object without errors takes two actions. The reviewer's name is asked once per browser and can be changed in the header. Keys: arrow keys or J and K move between values, R, W and U decide, A marks the remaining values right, C completes and moves on, M adds a missing value, B flags the boundary, N skips, Escape cancels a form.

Narrow screens
: The entry text comes first in a scrolling box of limited height, the values follow as blocks, the finishing actions stay at the bottom.

## Browsing

Task
: Find a record by address, title or text and open it.

First screen
: The state of the review with the way to continue it, the filters (search, volume, kind of record, review state) and a table of records with address, volume, part, page, title and kind, one line each. A record without a read title shows the start of its text, marked as such. Readable kind names replace the codes of the schema.

## Questions

Task
: Record a data-cleaning question once, with the objects it concerns, sort it by the kind of problem and by who can settle it, and answer it with a resolution.

Why a layer of its own
: A review decision says whether one value is right. Many problems are larger: a printed convention whose meaning is unknown, a reading class that recurs across entries, a case the data model cannot hold, a gap only a printed copy can close. Such a question gathers its cases instead of being repeated as notes on single decisions.

First screen
: The list of questions with their kind, who can answer, the number of cases, the state (open or the resolution) and who asked, filtered by state, kind and answerer. One question shows its text, kind and answerer as editable fields, a proposed answer where a rule or agent made one (headed as not decided), the answer or the answer form, the cases as links into the object view with title and value, and the history.

Interaction
: Q on any object, print object or apparatus item, opens a dialog that asks a new question or adds the object, with its selected value, as a case to an open question. Categorising, answering and reopening are events in an append-only log (`_questions.py`, `data/print/review/questions.jsonl`), validated and stamped by `review_server.py`, which also folds the log into the state the page shows. Only a person answers; the browser always speaks for a person. Rules and LLM agents seed questions from the shell (`questions_seed.py`, from the open questions of the knowledge base and probes over the records), each with a stable key and marked with its producer.

Kinds and answerers
: Kinds are reading, boundary, notation, source, data model, vocabulary, print and wiki, other; answerers are the operator, a domain expert, data analysis and a printed copy. Resolutions are change the rule, change the data model, keep as read, error in the print, needs an expert, out of scope. The definitions stand on the help page.

## Help

A page of its own explains what a decision means and what the sample measures, lists the keys, and states that the view is local because the rights to the print volumes are unresolved. No other view repeats this.

## Acceptance

Checked on real data at a wide and a narrow width with read screenshots, the decision flow run by keyboard and pointer against a review server with a trial log, `check_render.mjs` for complete chains and readable labels of every value, and an independent read-only review given the tasks above. The operator's own review of the sample is the acceptance.
