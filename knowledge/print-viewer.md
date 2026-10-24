---
title: "Print viewer: card workbench for the review of the print readings"
status: draft
language: en
created: 2026-10-24
updated: 2026-10-24
related: [print-volumes, print-wiki-merge, frontend]
---

# Print viewer: card workbench for the review of the print readings

The print viewer is a card workbench. In it a person decides whether the values read from the print volumes are right in their context, compares a print record with the wiki, and finds any record with its provenance. Field correctness is measured only from these decisions ([Print volumes](print-volumes.md), Structured objects), and the review happens through work in the workbench rather than through a planned budget of hours ([Production readiness](production-readiness.md), Operator principles). The workbench is therefore judged by the cost of a decision, by whether the evidence stands beside each value, and by whether a key ever acts on something not in view.

The code lies in `pipeline/print_volumes/viewer/`: `cards.html`, `cards.js`, `cards.css` and the pure module `render.js`, which holds every helper that does not touch the page. `review_server.py` serves the code from that folder and the data p12 writes (`index.json`, `vocab.json`, `wiki_concordance.json`) from `data/print/derived/viewer/` only, records decisions, and opens the PDF page of a record (`/print/I.pdf#page=790`, with single byte ranges, so a PDF viewer loads the page and not the volume). A `.gitignore` in the code folder keeps every data file out of the versioned tree. `index.html` forwards to `cards.html` and keeps old links to an object, the review and the help working. Palette and type stacks follow the production frontend.

## Requirements

The operator set these requirements while the workbench was built, and they stay binding.

- Records are the slips of a card catalogue. Many lie side by side as on a desk, and a person reads and decides several of them without opening each on a page of its own.
- A card at rest shows what identifies it and what tells it apart. The decision controls of single values, the provenance chain and long contents lists appear only on the card in focus.
- Every card names its source, the print volume with its PDF page or the wiki page, and its relation to the other source, so that a person sees where print and wiki overlap and where they do not before deciding how they merge.
- Each fact appears once. The title stands in the head and is not repeated among the values, the source location is a short sign with an icon and a tooltip, and groups are set apart by space, not by drawn rules or nested boxes.
- A slip has two lines, the title with the record's identifier, and below it a short overview quoted from the record's own passages that tells records of the same title apart (the `snippet` of `_viewer_data.py`).
- The workbench is the viewer's only view. Browsing, comparison with the wiki and the review of values happen in it.
- Every record leads to where it stands, a print record to its PDF page and a wiki page to its permalink.

## Desk

The desk filters by volume, section, kind of record, review state and source combination, sorts in printed order, by address, by title or by the first year in the text, and has three arrangements of the same cards.

Sections
: Three columns of different granularity. The compiler's sections A to R named as in the contents of 1991 with their counts, then the slips of the chosen section, then the full card of the selected slip with its comparison to the wiki. A person can move slips by hand, and that order is a working arrangement, not data.

Source lanes
: Print, shared and wiki side by side.

Card grid
: The cards of the current page as a grid.

The pills above the desk select by source combination: records with a text candidate, a field candidate or a title-year candidate, records with none, and wiki pages no claim names. A wiki page that no claim names is unlinked, which does not make it absent from print. "Review sample" restricts the desk to the frozen review sample of `review_sample.py`, open, complete or all.

## Card

The head names address, volume, part, PDF page and the position of the object in its entry, and holds title and type with their decisions. Each group of values (imprint, extent, persons, contents, references, notes, inherited values) stands on one line close to the printed line, every value shown exactly once with its decision sign, beside the entry text with the object's passages marked. A click on a mark selects its value. Address targets stand at the value with links, and an address that resolves nowhere reads as unresolved. The provenance chain of a value and its decision history open on demand.

The wiki side reads the projection of the p07 claims and the p08 conflicts. Every link is a candidate with its route (text alignment, field match, title-year), its claim identifier and its state, which is `proposed`. The drawer says that the concordance proposed it and nobody confirmed it, a claim whose record has changed since p07 says so, and where more candidates exist than are shown the card says how many. A field conflict shows the print and the wiki fields side by side, with "not read" and "not given" kept apart.

## Decisions

Exactly one card is active, the one that holds the focus and is in view, and keys act on it alone. A key pressed while the next card loads acts on nothing, and the status line says why a key did nothing.

- R, W and U mark the selected value right, wrong or unsure.
- Wrong takes the correction from a typed passage, which the workbench finds inside the object nearest the value, or from a selection in the entry text, with "should not exist" as the alternative.
- A marks every undecided value of the card right, but only values the card displays, and it refuses while an undecided value is not displayed.
- C completes the card and opens the next open one. M adds a missing value, B flags a wrong object boundary, N jumps to the next open card of the sample from anywhere outside a text field.
- J and K or the arrow keys move between values and stop at the edge of the card. Escape cancels a form or returns from the card to its slip.
- The reviewer's name is asked once per browser and can be changed in the header. Help and keys stand in one dialog.

`_review.check` enforces the rules every caller shares, the server included. A correction keeps the field and the type of its value, a flag is corrected as the boolean true and a flag that does not hold should not exist, and an inherited value can only be marked as one that should not exist.

Index entries and other apparatus records show with their resolved and unresolved addresses but without review controls, because the review layer covers the print objects of the sections A to R. Whether index entries enter a measurement is open. A single value cannot be addressed by a link, only its card.

## Acceptance

- `check_render.mjs` confirms over all objects that every value is shown once with its chain and PDF page and that every wiki link is a proposed candidate.
- `check_review.mjs` confirms the key and confirmation rules, and mutations of `render.js` are caught.
- The pytest cases of `_review.check` fail against a review layer without these rules.
- A browser run against a trial review server with its own log (`--log`) exercises the decision flow by keyboard and pointer at a wide and a narrow width with read screenshots.
- The review of 2026-10-24 ([review record](evaluations/2026-10-24/print-viewer-review.md)) has every finding that endangered the measurement closed. The review of index entries and the neighbouring line of an index entry stay open.
- Not yet checked are Firefox and Safari, a screen reader, and drag and drop by pointer. No independent reviewer has read the rebuilt code.

The operator's own review of the sample is the acceptance.
