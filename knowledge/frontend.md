---
title: Interface and Curation
aliases: [frontend, interface, EIL, curation tool]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: en
version: 1.5
tags: [frontend, eil, accessibility, export]
created: 2026-03-29
updated: 2026-08-27
authors: [Christopher Pollin]
related: [data, pipeline, testing, production-readiness]
---

# Interface and Curation

## Purpose

The static application under `docs/` makes the rescued holding searchable and provides a local Expert-in-the-Loop curation surface. It needs no build step and no server process beyond a static localhost server for edit mode.

The public application supports search, facets, a timeline, language and place analysis, reference rankings, detail cards, a data-quality workbench and citation exports. The local curation layer adds source evidence, provenance, triage, subject-level authority decisions and a versioned patch export. The interface language is English throughout, edit mode included.

## Architecture

`docs/index.html` loads classic scripts (no module system, one shared global namespace) and locally vendored dependencies (`docs/vendor/`: FlexSearch, D3 v7, topojson-client, d3-sankey, `countries-110m.json` with a provenance note). FlexSearch is loaded with `defer` because every visit needs the search index. The three visualization bundles are fetched by `App.ensureExploreLibs` on the first switch to `#stats`, in a fixed order and behind a single promise gate; if that fetch fails, the Explore view shows an error with a retry while search and the result list keep working. The application contacts no external host at runtime.

| Module | Task |
|---|---|
| `app.js` | data loading, state, hash routing, result list, cards, edit-mode switch |
| `constants.js` | type and period labels, colour constants, chart dimensions |
| `utils.js` | escaping, highlighting, counting and download helpers |
| `home.js` | start view with figures and entry points; one plain row per category |
| `facets.js` | facet sidebar of the result view |
| `detail.js` | entry detail in two layouts, a compact reading view and an adjudication table in edit mode |
| `edit.js` | local field and reconciliation curation, triage hints, source evidence, patch export |
| `curate.js` | data-quality workbench (`#data/quality`): completeness matrix, work queues, candidate queue |
| `export.js` | BibTeX, RIS, single-entry and full export, permalink |
| `pages.js` | the two static pages About and Data, figures taken from `_meta` |
| `jsonld-playground.js` | interactive JSON-LD view with escaped syntax highlighting, rendered as a section of the Data page; addressable through `#data/playground/<pageId>`, suggestion list as a `listbox` with arrow and Enter operation and its own empty state, view buttons carrying `aria-pressed`, document listener registered once, entry types read from `constants.js` |
| `explore.js` | Explore frame: modes, the shared filter set, URL state, detail panel |
| `explore-timeline.js` | timeline with language, type and provenance layers |
| `explore-geography.js` | globe and map view from the vendored geometry |
| `explore-network.js` | reference ranking (most-referenced entries) and translator Sankey |

The application loads `docs/data/klawiter.json` blocking and checks `resp.ok`. If that load fails, a full-page error state replaces the start view, names the cause and offers a retry; navigation and the search field are visibly disabled meanwhile, because without the holding neither resolves anything. `reconciliation.json` is loaded where its data first becomes visible (expanded card, edit mode, workbench) through a shared load promise, and a card that is already open is refreshed once the data arrives. `triage.json` is fetched only on entering edit mode. The search index is built after first paint through `requestIdleCallback`, with a `setTimeout` fallback and a lazy build on the first search as the last resort. Data verification (`verifyData`) runs on `localhost` only, because it is a development instrument and costs several full passes over the holding. Missing reconciliation data produces no invented links; the affected areas stay empty.

## Navigation, Routes and Page Layout

The header navigation carries four destinations, Overview, Explore, Data and About. There is no dropdown and no research-network bar above the header; what those held has moved into the two text pages or into the footer. The footer carries two blocks, credits on the left with compiler, publishing context, the Promptotyping attribution, the producer credit and the licence line, and the link column on the right, which runs in two columns over About, Data, Data Quality, Stefan Zweig Digital, Ontology & Data and GitHub. The imprint is reachable from the credits text and carries no link of its own, because it is a section of About.

| Route | Content |
|---|---|
| `#` | start page with search, browse entry point and the category groups as cards |
| `#stats`, `#stats/<mode>` | Explore with timeline, map and connections view |
| `#data`, `#data/<section>` | data model, specification and vocabulary, downloads, JSON-LD playground, pointer to the workbench |
| `#data/playground/<pageId>` | playground with a preloaded entry; the action bar of an entry card links there as "View as JSON-LD" |
| `#data/quality` | data-quality workbench, a sub-page of Data |
| `#about`, `#about/<section>` | project, methodology, help and imprint as sections of one page with anchor navigation |
| `#browse`, `#q=…`, `#entry=…`, facet parameters | result list |

User-triggered state changes (choosing a facet, removing a chip, submitting a search, changing the sort) write a real history entry; `replaceState` is reserved for normalizations that only catch the URL up with a state it already carries. The back path therefore leads through the research steps instead of leaving the application after the first interaction. The router ignores the fragment `#main-content` of the skip link, because it addresses an element rather than a route.

An `#entry=` permalink labels the result line after render as "Permalink — 1 entry". If the identifier does not resolve, a state of its own appears that points at a possible redirect and offers a way to the start page; a `#title=` without a hit in the redirect map and the title index leads to the same state instead of silently falling through to the start page. The static pages and the workbench reset query, filters and the search field the way the Explore branch does.

A static page addresses its sections through a suffix in the hash (`#about/imprint`); the router renders the page and then scrolls to `sec-<section>`. The published deep links of the earlier page layout stay valid and are rewritten in the router to their section, `#methodology` and `#help` and `#imprint` to `#about/…`, `#jsonld` to `#data/playground`, and `#quality` to `#data/quality`. The workbench hash takes the same rewrite path, so it never reaches the branch that would render it under its former address. The document title is set in `App._updateTitle` alone, with the base title "Klawiter — Stefan Zweig Bibliography" as shipped in the HTML.

The About page takes the figures of the holding dynamically from `_meta` (holding size, languages, year span, field coverage, number of types), so prose and data state cannot drift apart. The Data page names the files shipped under `docs/data/` with their role and marks the canonical graphs under `data/output/` as reachable through the repository only. The full export is called "Download dataset (JSON)", because it delivers the flat projection in frontend key names and carries no `@context`.

## Design and Accessibility Contract

The interface uses the established Stefan Zweig Digital palette, Source Serif 4 for reading text and Source Sans 3 for navigation and controls. CSS variables are the only source for colours and spacing. Libraries and fonts are local.

The visual language is deliberately narrow. Letterspaced capitals mark the title of a view and nothing below it, so section headings are plain serif in the dark gold token or in burgundy. Reading pages sit on a white card with a quiet edge on the cream ground, and the anchor navigation of a page carries no rule under it. Tables structure themselves through row striping under a single header rule. The entry-type badge on a result card is monochrome, because colour on a card is reserved for a state that needs attention, meaning review status, a gap in the completeness matrix and a contested claim. There are two button styles, filled burgundy for the action a view exists for and outlined for every other action; compact controls inside lists and rows (facet items, legend entries, the per-field controls of edit mode) are not buttons in this sense and keep their in-place form.

Semantic HTML, visible keyboard focus, labelled forms, ARIA labels for iconic controls and sufficient contrast form the basis. Gold that carries text uses the darkened token that clears 4.5:1 against white and cream. After a view change `showView` moves focus to the heading of the view or to `#main-content`, so hash navigation reaches screen readers; a change that follows from typing in the search field leaves the focus there. All keyboard shortcuts bail out when Control, Meta or Alt is held. `prefers-reduced-motion` is respected globally (animations and smooth scrolling are dropped). A state is never conveyed by colour alone. Mobile layouts preserve search, filters and detail information without horizontal scrolling; the completeness matrix scrolls in its own container.

## Research Views

- The overview shows extent, temporal distribution, languages, types and places. A category is one row that opens the filtered list; the former expandable subcategories assumed a "format and language" structure most categories do not have.
- The result list combines full-text search, facets and sorting. The card shows type, title, year, language, place, publisher and page count; the source excerpt is dropped, because the expanded card carries the full entry. The card header carries `aria-expanded` and `aria-controls` pointing at the detail id.
- The search index folds diacritics (`charset: 'latin:advanced'`), so the transliterations of the holding are findable in plain spelling as well. A search runs from two characters on. The hit count is capped at 5,000, and the result label says so once the cap is reached. The header field and the start-page field share one handler, the start-page field is prefilled with the current query on render, and focus moves into the header field on the switch to the result view. Highlighting marks the raw text and escapes segment by segment, so an apostrophe, ampersand or quotation mark in the query matches and no entity is torn apart.
- Facet counters follow the standard drilldown, so every facet counts against the set that all other filters select and the alternatives of a chosen facet stay selectable. Language and place show the most frequent values and expand per group to the full holding. Chips carry labelled closers and, from two active filters on, a "Clear all" chip; the empty state offers the same action.
- The mobile drawer moves the sidebar into the overlay by DOM move and back on close instead of cloning its markup. Focus jumps to the close button on open, stays cyclic inside the panel, Escape closes, a selection closes, and focus returns to the opener. The mobile filter button appears on the result view only.
- The expanded reading view adds only what the card header does not carry (original title, translator, categories, Wikidata place link), renders the contents as a structured list with page references and holds the complete original Klawiter entry as a collapsed source. If an entry carries nothing beyond the full entry, the source is rendered open, because an expansion consisting of one collapsed line reads as empty. Contested claims stay visible in the reading view, as does the review-status chip, which stands in both layouts. A category link filters on the category itself (`#category=`); a contents item whose title has an entry of its own becomes an `#entry=` link.
- Redirects do not appear as search hits of their own; the redirect map (including the page-title aliases from stage 05) leads queries and cross-references to the canonical entry.

## Explore

Explore is one frame for three visualizations. The mode choice sits above the frame as a group of buttons carrying `aria-pressed`; `#stats` opens the mode last used in the session and the first one otherwise, because there is no overview layer above the visualizations. A persistent sidebar on the left carries the filters, and the drawing surface takes the whole remaining width. On a narrow viewport the sidebar stacks above the surface rather than disappearing, because it holds the only filter path of that view.

One filter set serves all three modes. The sidebar offers language, type and decade as facet groups, counted against every other active filter the way the result sidebar counts, so a group does not collapse to its own selection. Below the groups the active filters stand as chips, and a filter set from inside a view (the timeline brush, the decade playback of the map) redraws chips and facet lists through the same entry point, so the two stay in step. A decade and a brushed year range address the same axis, so choosing one clears the other.

What a view cannot draw is stated once in the sidebar instead of on the drawing surface. The timeline names the undated entries, the map names the entries without a mapped place and the place names that the geocoding could not resolve, each as a control that opens the affected records as a result list. Pointer instructions for the globe live in its tooltip and in the SVG description rather than as a caption. The selection detail sits under the filters in the same sidebar.

Timeline, map and connections view derive their data from the same filtered record set. Missing language reads as "Not recorded" in all three views and stays separate from "Other languages", which means a recorded language outside the top ranks. The connections view is a ranking of the most-referenced pages with expandable reference lists; the former global community graph is gone, because its largest node was the residual aggregation and it answered no bibliographic question. The translator Sankey stays; multiple mentions are split at conjunctions, truncated values are excluded, and the smallest nodes are bundled into "Other translators". The provenance overlay is a strip of its own under the timeline axis. Legends are real filtering buttons and serve as the keyboard path, the SVGs carry `role="group"`, and `prefers-reduced-motion` zeroes every d3 transition duration. Click paths hand their filters over to the result route in full, which for that purpose also knows `publisher`, `translator` and year ranges; only the country filter of the map stays bound to the session, because the result route does not load `locations.json`.

## Data Quality Workbench (`#data/quality`)

The workbench answers the curation question whether all data is cleanly processed, out of the published artifacts themselves:

- A status panel with three figures that direct the work, open authority candidates, contested claims and pending decisions of the current session. Everything the panel used to count as well stands in the matrix and the queues below, where it is also clickable.
- A completeness matrix of field against entry type; every cell with gaps opens the affected entries as a result list.
- Work queues as clickable lists over census anomalies, values not evidenced in the source text, detectable but unextracted values, LLM-derived fields, unresolvable cross-references (with a list of the most frequent red-link targets) and contested authority claims.
- A subject-level candidate queue for translator and publisher names, sorting open cases by reach (number of occurrences) first. It is publicly readable, and deciding is possible in local edit mode only.

The queue is a `listbox` with a roving tabindex, so it is a single tab stop that lands on the row where the work begins (the subject last worked on, otherwise the first open case). On the keyboard in edit mode, arrows and j/k move, y confirms the top candidate, n rejects, u holds open, z and Backspace take back the last decision, and Enter opens the affected entries. All queue keys bail out when Control, Meta or Alt is held. The way back from the result list finds the subject last worked on by its identifier, scrolls to it and sets focus. Every row shows the top candidate and holds the others in an expandable block with a confirm button per candidate, so a decision is not forced onto the highest score. A redraw of the queue rewrites the status panel above it, because its counters for the running session would otherwise contradict the save counter.

If `triage.json` or `reconciliation.json` fails to load, the module records that in its load state, and the affected counters and blocks mark themselves as "not available (failed to load)". A load failure is thereby distinguishable from a clean holding.

The workbench lists are session views without a hash address of their own, because they derive from artifacts rather than from filter state. The document title then takes the list label, and above the list stands a visible way back to the view it was opened from (workbench or Explore).

## EIL Curation Interface

Edit mode is active on `localhost` only; the switch checks `isLocal` in the setter, and the published site cannot enter the mode even through the console. The switch in the header is additionally view-dependent and appears only where editing actually applies, on the start page, the result list and the workbench; on the text pages and in Explore it is hidden. The mode state itself survives a view change. Publisher, place of publication, translator and page count are editable. Every field action is typed:

- `accept` confirms an existing value;
- `correct` replaces a value and preserves its predecessor;
- `add` fills a previously empty value.

For every action the interface shows the evidencing passage or the complete source text. Triage hints prioritize round-trip deviations, missing or model-supported provenance and census anomalies; a provenance legend explains the R/L/E badges. In edit mode j/k walk the result list card by card, and the sort "Needs review first" orders by the most urgent data signal.

A field with an open correction shows the corrected value; the replaced dataset value stands struck through beside it, so a re-render does not appear to take back what was just typed. An empty field carries a labelled add button beside the placeholder area that focuses it. In a `contenteditable` field Enter completes the input (line break suppressed, field left) and Escape discards it back to the rendered state; every field carries `role="textbox"` and an `aria-label` with the field name. All controls of a card run through event delegation with data attributes, in the action bar as well as in the candidate blocks; place and agent candidates share one renderer parameterized by the kind of subject.

Running changes stay in `localStorage` until export, together with the timestamp of the last write; the save counter in the header shows the unsecured state and, for a state restored from an earlier sitting, the note "resumed from <date>". If a reload brings back open decisions without edit mode being on, a note beside the counter says the mode has to be switched on to continue. After the patch download the interface asks whether the session is cleared or continues with the open decisions, because the download alone says nothing about what happens to the session.

Session state is separate from the data state. An unsecured field action makes the entry "edited (unsaved)"; "approved" is reserved for the `review` projection of the dataset, which the pipeline writes after an applied patch.

Place reconciliation offers `confirm`, `reject` and `unresolved`; `unresolved` records competing readings as an open claim. Translator and publisher candidates offer the same actions, and since Gate 2 the source occurrences per agent subject are collected from the classified source and published under `sourceOccurrences` in `docs/data/reconciliation.json`, so an unresolved agent decision is evidenced against the source. Both kinds of candidate are subject-level; the interface states the reach ("applies to N entries"). Candidates stay proposals; nothing is published without a decision. The combined export uses `patchVersion: 2` and `reconciliationPatchVersion: 1`.

The review-status chip reads the `review` field of the entry, whose semantics are in [[data]]. An entry without that field stays unchecked, and an unsecured edit of the running session remains a state of the interface.

## Rendering of Contested Statements

Confirmed relations and contested statements are rendered separately. An open authority claim shows the source value, the candidates, the decision history and the open status. The adaptation case on page 4916 shows both work readings, the source identifier and the reviews.

The interface does not turn a contested candidate into a clickable confirmed authority link. Figures count publishable relations only. The number of open claims is reported separately.

## Data Page and JSON-LD Playground

The Data page describes the model, the shipped files and the vocabulary without repeating figures that the vocabulary itself publishes. The `klawiter:` namespace resolves to the vocabulary documentation, and the page points there instead of naming a term count that ages with the next vocabulary round. The prefix and namespace table is gone, because the `@context` block in the playground states the same bindings against a live record.

The playground shows one entry in three views, compact, expanded and as triples. In the compact view the `@context` sits in a collapsed disclosure above the record, because it is identical for every entry and long. The record itself shows only keys the `@context` defines. A key without a term definition carries no IRI and would be dropped by a conformant processor, so showing it would suggest a term the vocabulary does not publish; this is what removes `_provenance`, `review` and `locationSameAs` from the view.

## Export

- BibTeX and RIS serve citation transfer of the flat records. Both read the same type rule and include the permalink (`url` and `UR` respectively); the recorded extent stands in `pagetotal`, because `pages` means the page range inside a container. A run on `localhost` or over `file://` cites the published address, so the link resolves for the recipient.
- The batch export of the result list labels itself with the hit count and asks back above a thousand entries.
- Copying the permalink catches a denied clipboard and then offers the address in a selectable field.
- The single-entry JSON-LD export adds existing edition claims as graph nodes of their own, under the properties `klawiter:hasContestedClaim` and `klawiter:hasReviewAction` of the current vocabulary; the class names `ContestedClaim` and `ReviewAction` are unchanged.
- The full export carries contested edition and authority claims alongside the confirmed relations.
- The canonical complete graphs remain `data/output/editions/work-editions.jsonld` and the Gate 2 artifacts under `data/output/reconciliation/`.

A claim with the predicate `schema:exampleOfWork` is exported without setting the corresponding confirmed relation on the edition node at the same time.

## Validation

Node tests cover source-evidence logic, triage order, reconciliation lookup, a stable patch export, the separation of contested claims, the routing guard including the edit-mode gate, the redirects of the published deep links, the section suffix of static pages, the visibility rule of the edit switch and the order of the candidate queue. The workbench route is asserted in both directions, as a redirect of `#quality` and as the one page route on which the edit switch appears. `tests/edit_session.test.js` holds the session state, meaning the rendered correction value with its struck-through predecessor, the add control on an empty field, "edited" instead of "approved", the index over contested claims, the category link, the review-status chip and the opened source in the reading view, and the playground route. Added to that are the search guarantees in `tests/search_logic.test.js` (diacritic folding of the index, highlighting against escaping, minimum query length, facet drilldown, label resolution and the cap notice) and the history guarantee and error routes in `tests/routing_guard.test.js`. `node --check` validates every module syntactically. The Python suite checks the generated data contracts (including the frontend projection contract) and calls the Node tests through the shared test bridge.

A local smoke test runs with a static server over `docs/`:

```bash
python -m http.server 8000 --directory docs
```

The application is then reachable at `http://localhost:8000/`; the curation surface is active only there.

## Deployment and Limits

GitHub Pages publishes the content of `docs/`. The application performs no live write-back. Exports are downloaded locally and then integrated as reviewed repository patches.

The flat detail page cannot fully separate edition-specific fields on multi-edition pages. The edition graph and its queue stay authoritative for those cases. Title editing and institutional work decisions are outside the current local editor.
