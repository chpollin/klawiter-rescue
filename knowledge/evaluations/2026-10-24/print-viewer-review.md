---
title: "Print viewer and card board: independent review of 2026-10-24"
status: historical
language: en
created: 2026-10-24
related: [print-viewer, print-volumes]
---

# Print viewer and card board: independent review of 2026-10-24

A read-only review by an LLM agent (fresh context, explicit model override) exercised the review view, the index-entry view, Browse and the card board in a browser at 1500, 1280 and 390 px against a trial review server, and read the code. Line references point at the state of 16:00; the card board has been rewritten since, so each finding has to be checked against the current files before it is acted on. The review is simulated and no acceptance.

## Findings that endanger the measurement

These put decisions on values nobody looked at, which the review sample would then count.

- A key pressed while the next object loads acts on the previous one: "right" was recorded on the object that had just been completed while the address already showed the next. Keys must be blocked and the object on screen cleared while an object loads, and a post must check that the object it names is the one shown.
- The card board confirmed values it did not show: parts of the extent and reference kinds were hidden on the card and confirmed together with a visible sibling and by "all right". No value may be confirmed that is not displayed.
- Card board keys acted on a card outside the viewport (the first card was active by default). Keys may act only on the one object that is visible and visibly focused.
- Corrections of flag values (circa, year in brackets) were sent as strings where the review layer requires a boolean, so the server refused them; and the server does not enforce that an inherited value can only be marked as one that should not exist. Both belong in `_review.check`, which every caller passes.

## Findings that block review tasks

- Index entries cannot be reviewed anywhere: the review layer admits only object identifiers of the parts A to R and reads only the entry records.
- Unresolved index addresses are not shown at the value; a boundary error of an index entry cannot be seen, because the export does not carry the record's line pieces (page, line, column), so no neighbouring line can be shown.
- A correction needs a mouse selection on the card board; there is no keyboard path.

## What the card board does well

One line per group (imprint, references, index addresses) close to the printed line; many objects side by side, which makes a recurring misreading visible; title, subtitle and type decided in the card head; a click on a mark in the text selects its value; and a tray that stays in place.

## Structure

The review view and the card board duplicated about thirty functions, and the copies had already drifted (provenance wording, the wiki filter, note limits, the inherited rule). One shared store and pure render module, with the board's three good ideas in one review route and exactly one focused visible object, was the recommended target.

## Data outside the pipeline

The wiki concordance the card board reads (`pipeline/print_volumes/viewer/wiki_concordance.json`) is produced by no pipeline stage, carries no provenance, sits in a versioned folder without an ignore rule, and holds print-derived fields. It presents title-and-year candidates as matches. Print and wiki matching (Gate 3) is outside the production run.
