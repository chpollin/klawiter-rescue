---
title: Design
aliases: [design, design system, visual identity]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: draft
language: en
created: 2026-10-24
updated: 2026-10-28
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Opus 5.5)
template:
  name: Vorlage Design
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/design
topics: ["[[Information Visualisation]]", "[[Scholar-Centered Design]]"]
related: [specification, frontend-architecture, design, governance, print-wiki-merge, plan, data]
---

# Design

The interface of the Klawiter bibliography is a reading and review instrument for one rescued reference work, laid out like a card catalogue on a desk, where the evidence of every value stands beside it and a machine proposal never looks stronger than a person's decision. It belongs to the visual family of Stefan Zweig Digital, shares that family's burgundy and gold and its `--sz-*` token names with the ontology site of the same family (`SZD/docs/css/szd-ontology.css`), and sets itself apart by accent emphasis, since gold carries the section headings here where the ontology site heads its sections in burgundy. The values live in two stylesheets, `docs/css/styles.css` for the published reader and `pipeline/print_volumes/viewer/cards.css` for the local card workbench. Routes, keys and behaviour stand in [Frontend architecture](frontend-architecture.md) and [Card workbench](#card-workbench), and the tasks the design serves in [Specification](specification.md).

## Design stance

The bibliography speaks through its own structure, so a count opens the records it counts and no figure stands for its own sake. Cream is the page and white is data. Record cards, the reading pane and the start-page data block stand on white, while reading pages and the Explore panels sit on cream. Order comes from whitespace, small headings and hairlines between rows, and a card carries one outline with nothing framed inside it. Reading pages carry their anchor navigation without a rule under it, and tables structure themselves through a hairline between rows under a single header rule, without an outer frame. Colour on a record is reserved for a state a reader has to act on, a gap in the completeness matrix, a contested claim or the triage hint of edit mode, and for the hue of a producer sign, which repeats its shape and never stands alone (State and producer marks), so entry type and review status read as plain subdued text in both card layouts. Every such state is also a word, and gaps and open claims stay visible as the holding has them.

## Rule hierarchy

When two design rules compete, the one higher in this order prevails. The order derives from the operator principles in [Governance](governance.md#operator-principles) ("A gap before a wrong value", "Who confirms", "An interface people like working in") and from the Goal of [Merged bibliography](print-wiki-merge.md#goal), and it is a revisable proposal of this design.

1. A value stands with the passage it was read from and in the wording of the source, and a gap reads as a gap, with "not read" kept apart from "not given".
2. What has been decided, by whom and with what scope is visible at equal weight beside the value, the producer as a sign explained once per card and the decision in words, and a proposal of a Large Language Model (LLM) agent never takes the form of a confirmed relation.
3. A value is shown at the level it holds for. A page-level row carries only what holds for every publication of the page, a publication block what holds for that publication, a contribution its own credits.
4. The first screen of a view carries what the reader's next decision needs, and everything else opens on request.
5. Each fact appears once, a slip has two lines, lists are preferred to cards, and space separates groups where a drawn rule would otherwise stand.
6. Tokens and the family resemblance with Stefan Zweig Digital yield to the five rules above.

## Surfaces

The published reader stays as it is while development is local ([Governance](governance.md#operator-principles)). Locally the operator's decision of 2026-10-24 reduces the sitemap to three destinations, and [Plan](plan.md#m1-ready-for-review) builds them in the increments of the record desk. A departure of the published reader from the rules below is closed in the local surface that succeeds it.

Overview
: The first screen holds title, one sentence on what the bibliography is, the search field and the way into Records on one line, and below them the white data block with the model table and the section table of the compiler's sections A to R against the sources. Every count is a link, a thin gold bar under it shows its share of the largest count in its column, and the explanation of the model opens behind an (i). Below 40rem each section becomes a block with the sources as labelled values. The committed start page has this form, and its local successor is increment 1.

Records
: The record desk, described below, holds the print objects and the wiki records in one card design and replaces the wiki catalogue locally. Explore becomes an arrangement of the records the desk has filtered, and data quality becomes a set of filters and a review mode of the desk (increments 2 to 5).

Documentation
: Data and About join one reading page on cream with an anchor row, a letterspaced view title, section headings in gold-dark serif and subsections in burgundy serif, tables with one header rule and hairlines between rows, and reading text held below 80 characters per line. The JSON-LD playground keeps its dark code surface with its own syntax palette (increment 1).

Help and imprint
: Help opens as a dialog from every surface, after the model of the one help dialog of the workbench, and the imprint stands in the footer (increment 1).

Page check tool
: A local tool for one PDF page at a time, described below (increment 1).

## Record desk

The record desk follows the [card workbench requirements](specification.md#card-workbench-requirements) the operator set and extends them to wiki records. Records are the slips of a card catalogue, several lie side by side, and a person reads and decides several of them without opening a page for each. Print and wiki records share one anatomy, so a person compares them by position rather than by reading two layouts. The committed workbench has this design for print objects, with the wiki shown as candidates in a drawer, and the wiki cards and the shared design are increment 2.

### Slip at rest

A slip has two lines. The first carries the title and the record's identifier, the print address with its volume or the wiki page identifier. The second carries a short overview quoted from the record's own passages, which tells records of the same title apart (`snippet` in `_viewer_data.py` for print). Beside these two lines stand three marks, each as a word or a short sign with its word in reach.

- The source sign, the print volume with its PDF page or the wiki page, as an icon with its name.
- The relation to the other source, a candidate with its route, no candidate, or wiki only, each `proposed` until a person decides.
- The review state of the record and its producer, such as open, complete or flagged and the reviewer or "no person", and the word "contested" where an open claim concerns the record.

Nothing else stands on a slip. Values, decision controls, long contents lists and the provenance chain wait for the open card.

### Open card

The open card is the card in focus, and exactly one card is in focus. Its head names the identifier, the source location and, for a print object, its position in the entry, and it carries the title and the type with their decisions. Its body sets each group of values on one line close to the line of the source it was read from (imprint, extent, persons, contents, references, notes, inherited values for print, and for a wiki record the page-level rows followed by one block per publication in source order). Every value stands once, with its decision sign and its state and producer word beside it. The source text, the print entry or the Klawiter source of the wiki page, stands beside the values with the record's passages marked, and a click on a mark selects its value.

The card is dense by the rules of [Value row](#value-row) and keeps a value and its passage on one screen at wide widths. Below the three-column width the active card comes first, a compact slip pager stands directly above it and the decision bar stays in view while the card is active.

### Facts on demand

The provenance chain of a value opens on demand at the value, with its five links `Value`, `Passage`, `Record`, `Source file` and `Producer`, each as visible and operable text, and so does its decision history. The chain opens without leaving the card and closes back to the value. A disclosure counts only when a reader perceives it, so no hidden element stands in for it. The workbench opens the chain on the active print card, and the reader card does not yet, which the exit condition of the record desk closes ([Plan](plan.md#m1-ready-for-review)).

### State and producer

State and producer stay visible at rest and in focus. A slip carries the record's state and producer, an open card the state and producer of every value, and colour only adds to the word. A person's decision on a wiki value becomes a patch that confirms the value with the producer person (increment 3), and the card then shows "confirmed" with "person" in the same subdued words as a proposal shows "proposed" with its producer, so the two are told apart by reading and never by weight.

### Arrangements and modes

Sections, Source lanes and Card grid arrange the same slips ([Card workbench](#workbench-desk)). Explore is a further arrangement of the filtered records, the decade histogram, the language and type rankings and the map drawn over the current filter, and a selection in it filters the desk (increment 4). Data quality is a set of filters, each class with its count, and a review mode that steps through the filtered cards with the decision keys (increment 5).

### Decisions for increment 2

The research coordinator took these decisions on 2026-10-24 under the operator principles, after a design and an adversarial review of it. They are revisable until the operator accepts the desk.

- Records is one view of the reader, and one card component renders both sources. The card workbench keeps its decision bar and guards for the running review but draws its cards through the same component, so there is one design and one builder. Increment 3 moves the decisions into Records, and the workbench then forwards to it.
- On the desk every value row names its producer in words, because a decision is read there. The result list keeps the default stated once behind the (i), as in [Value row](#value-row). The words themselves stay the operator's decision (Open design decisions), and until then the desk uses the committed ones.
- Every value opens its own chain, so a row with several values, such as credits, places or contents, opens one chain per value.
- A value's passage comes from the offsets the parser held when it read the value, carried through by the pipeline. Where no offset exists the chain names the gap in words, such as "passage not located", and a gap the binding rule made reads "gap by rule" with its rule, apart from a gap in the source. The card never shows a first match as the passage.
- The place and publisher rows of a publication keep their authority links, contested marks and curation controls, and a verbatim imprint row joins them.
- The record identifier is the permalink, and the type stays the one type badge of the head, so each fact stands once.
- Records shows the wiki records on every host. It loads print records only when the review server answers with the print index, and without it the page makes no request for print data and names none. Category pages whose text remains after their category links get a card, infrastructure pages do not.
- A push of `docs/` publishes Records. On 2026-10-25 the operator instructed to merge all work on main and push it, so the public site carries the desk in its state of work; acceptance stays a separate decision.

## Card workbench

The card workbench is the local review surface of the print strand. In it a person decides whether the values read from the print volumes are right in their context, compares a print record with the wiki, and finds any record with its provenance. Field correctness is measured only from these decisions ([Print pipeline](print-pipeline.md), Structured objects), and the review happens through work in the workbench rather than through a planned budget of hours ([Governance](governance.md), Operator principles). The workbench is therefore judged by the cost of a decision, by whether the evidence stands beside each value, and by whether a key ever acts on something not in view.

The code lies in `pipeline/print_volumes/viewer/`: `cards.html`, `cards.js`, `cards.css` and the pure module `render.js`, which holds every helper that does not touch the page. `review_server.py` serves the code from that folder and the data p12 writes (`index.json`, `vocab.json`, `wiki_concordance.json`) from `data/print/derived/viewer/` only, records decisions, and opens the PDF page of a record (`/print/I.pdf#page=790`, with single byte ranges, so a PDF viewer loads the page and not the volume). A `.gitignore` in the code folder keeps every data file out of the versioned tree. `index.html` forwards to `cards.html` and keeps old links to an object, the review and the help working. Palette and type stacks mirror the production frontend in a stylesheet of their own, whose unification with it [Unification of the two stylesheets](#unification-of-the-two-stylesheets) plans.

### Workbench desk

The desk filters by volume, section, kind of record, review state and source combination, sorts in printed order, by address, by title or by the first year in the text, and has three arrangements of the same cards.

Sections
: Three columns of different granularity. The compiler's sections A to R named as in the contents of 1991 with their counts, then the slips of the chosen section, then the full card of the selected slip with its comparison to the wiki. A person can move slips by hand, and that order is a working arrangement, not data.

Source lanes
: Print, shared and wiki side by side.

Card grid
: The cards of the current page as a grid.

The pills above the desk select by source combination: records with a text candidate, a field candidate or a title-year candidate, records with none, and wiki pages no claim names. A wiki page that no claim names is unlinked, which does not make it absent from print. "Review sample" restricts the desk to the frozen review sample of `review_sample.py`, open, complete or all.

### Workbench card

The head names address, volume, part, PDF page and the position of the object in its entry, and holds title and type with their decisions. Each group of values (imprint, extent, persons, contents, references, notes, inherited values) stands on one line close to the printed line, every value shown exactly once with its decision sign, beside the entry text with the object's passages marked. A click on a mark selects its value. Address targets stand at the value with links, and an address that resolves nowhere reads as unresolved. The provenance chain of a value and its decision history open on demand.

The wiki side reads the projection of the p07 claims and the p08 conflicts. Every link is a candidate with its route (text alignment, field agreement, title and year) and its state, which is `proposed`, with the claim identifiers in its tooltip rather than in the running text. The drawer says that the concordance proposed it and nobody confirmed it, a claim whose record has changed since p07 says so, and where more candidates exist than are shown the card says how many. A field conflict shows the print and the wiki fields side by side, with "not read" and "not given" kept apart.

### Workbench decisions

Exactly one card is active, the one that holds the focus and is in view. The active slip and card carry `aria-current` besides their colour, and a card with a value marked wrong or unsure, or with a missing value or boundary flagged, says "flagged". Keys act on the active card alone. A key pressed while the next card loads acts on nothing, and the status line says why a key did nothing. Every message about a decision names the object it concerns ("Saved on F 61, title right."), so a message standing beside the next card never reads as one about it. A form closes whenever its card is rebuilt, and Escape cancels it only from inside the card.

- R, W and U mark the selected value right, wrong or unsure.
- Wrong takes the correction from a typed passage, which the workbench finds inside the object nearest the value, or from a selection in the entry text, with "should not exist" as the alternative.
- A marks every undecided value of the card right, but only values that lie inside the viewport and every scrolling column around them. It refuses while an undecided value is out of view and stops as soon as the card leaves the screen.
- C completes the card and opens the next open one. M adds a missing value, B flags a wrong object boundary, N jumps to the next open card of the sample from anywhere outside a text field.
- J and K or the arrow keys move between values and stop at the edge of the card. Escape cancels a form or returns from the card to its slip.
- The reviewer's name is asked once per browser and can be changed in the header. The workbench loads only that reviewer's decisions (`GET /review/decisions?reviewer=`, filtered again in the page), and while recording it hides the review state of the export, so a second reviewer decides blind to the first. A server that cannot read its decision log says so in a banner, and the cards stay read only.
- Help and keys stand in one dialog. A skip button, the first tab stop, leads into the active card, and only the active slip's move buttons are tab stops.

`_review.check` enforces the rules every caller shares, the server included. A correction keeps the field and the type of its value, a flag is corrected as the boolean true and a flag that does not hold should not exist, and an inherited value can only be marked as one that should not exist.

Index entries and other apparatus records show with their resolved and unresolved addresses but without review controls, because the review layer covers the print objects of the sections A to R. Whether index entries enter a measurement is open. A single value cannot be addressed by a link, only its card.

## Page check tool

The page check tool shows one PDF page of a print volume beside everything read from it. The page stands on one side at a readable size, and on the other side stand the lines read from it in reading order, each with its line position and the address of its record, and under each line the values read from it with their fields. A line no record covers and a value without a line stand out by a word. Selecting a line or a value marks the other side. The tool runs only on the local review server over `data/print/`, and nothing it shows reaches a versioned file. While the blind sheets are incomplete, it withholds the readings of their pages ([Specification](specification.md), T19). The tool is increment 1 of the record desk, and this layout is a proposal.

## Design system

### Tokens

The token values live in the `:root` block of `styles.css` and the `@layer tokens` block of `cards.css`. Production also mirrors chart colours in `docs/js/constants.js`, and the categorical colours of languages, types and periods are literal values in `docs/js/explore.js` and `docs/js/explore-geography.js`. The roles below are the design, and U1 moves both surfaces onto one token file.

| Role | Production | Workbench |
|---|---|---|
| Brand, links, titles | `--sz-burgundy` | `--burgundy` |
| Hover, pressed | `--sz-burgundy-dark` | `--burgundy-dark` |
| Chart category only | `--sz-burgundy-light` | none |
| Decoration, rules, marks on burgundy | `--sz-gold` | `--gold` |
| Hover fill, count bars | `--sz-gold-light` | none |
| Gold that carries text | `--sz-gold-dark` | `--gold-dark`, also `--unsure` |
| Page ground | `--sz-cream` | `--cream` |
| Data surface | `--sz-white` | `--paper` |
| Body text | `--sz-text` | `--text` |
| Secondary text | `--sz-text-light` | `--text-light`, `--text-faint` |
| Outline of card and pane | `--sz-border` | `--border` |
| Hairline, start-page data block outline | `--sz-border-light` | `--hairline` |
| Control edge | none | `--border-strong` |
| Confirmed, right | none | `--ok` |
| Wrong, conflict | none | `--bad` |
| Wiki candidate, wiki-only record | none | `--wiki`, `--wiki-only` |
| Passage highlight | `mark` with a literal gold tint | `--mark`, `--mark-strong` |
| Contested block | literal tint and heading colour | none |

### Contrast

Text reaches 4.5:1 against its ground, and focus indicators, field boundaries and meaningful graphics reach 3:1, measured as Web Content Accessibility Guidelines (WCAG) 2.x relative luminance. Gold carries text only as the gold-dark token. Cream on burgundy carries the header and the primary button, and gold on burgundy the focus ring and the active underline of the header. Body text and burgundy are too close to tell a link from text by colour, so links in running text are underlined (U10). The pairs the committed code misses are listed under [Departures](#departures-of-the-committed-code).

### Type

Source Serif 4 and Source Sans 3 are shipped locally through `docs/fonts/fonts.css`, the serif at 400 and 600 with an italic, the sans from 300 to 600 with an italic. No weight above 600 is used, because no shipped face carries it. The reader sets running text in serif and uses sans for navigation, controls, counts and bibliographic values. The workbench sets its base in sans and uses serif for titles, values and the entry text. Sizes are tokens of the two stylesheets.

| Role | Face | Colour |
|---|---|---|
| View title | serif, uppercase with tracking | burgundy |
| Start title | serif 600, no capitals | burgundy |
| Result heading | serif | burgundy |
| Section heading | serif 600 | gold-dark |
| Card title, larger in the reading pane | serif 600 | burgundy |
| Publication heading | serif 600 | gold-dark |
| Field label | serif in the reader, sans 600 in the workbench | burgundy in the reader, secondary in the workbench |
| Field value | sans in the reader, serif in the workbench | body text |
| Secondary line, state and producer words | small sans | secondary |
| Facet and queue heading | small sans, uppercase with tracking | gold-dark |

Letterspaced capitals mark the view title, and the small heading of facets and queues is the one accepted exception. The start title drops them deliberately.

### Spacing, shape and layout

Spacing follows one scale of rem steps, which the workbench names `--space-1` to `--space-5` and the reader still writes as literal values (U15). Cards, panes, inputs and buttons take a small radius, marks a smaller one, and filter chips a pill.

The reader holds its layout to a maximum width with a facet sidebar, an Explore sidebar of its own width and reading pages narrower than wide pages. From the reading-pane width (`App.PANE_QUERY` in `app.js`) list and card stand side by side, below a medium width the facets move into a drawer and Explore stacks, and on narrow screens the start tables become blocks. A container query lets the field labels of a card share one column once the card is wide enough. The workbench main area runs wider, the entry text keeps a measure of 72 characters (`--reading`), and the columns stack at one width with the active card first. U17 sets one rem set of thresholds for both.

### Components

#### Card

A card is one outline on white with a small radius, and nothing inside it is framed. A result in the list has neither outline nor surface, so only the opened card and the pane carry them. Publications are separated by one hairline, and the source block carries a start rule. The workbench card adds a start edge whose colour states completion, flag or wiki-only, an outline and a shadow on the active card, and a tinted ground for guide records. Wherever the edge carries a state, a word stands beside it, "flagged" or the progress figure.

#### Value row

A value row is one label and one value. A short value stays on the label's line and a long one wraps under it. Additions to a value, a language subtag or the numbered extent, stand in subdued sans after it, and a list value keeps a space between its title and its page reference. A missing field reads "Not recorded" without a mark. Every row renders text, and an object or array is never written out as code.

#### Publication block

A block is headed by its year and its distinguishing statement in gold-dark serif, carries the edition state as a word and two citation exports as text links in its heading row, and ends with one tinted review line where the extraction rules leave something open. On a page with the publication layer a value that belongs to one publication stands in its block, and a flat value no publication carries stands as a first match labelled as such.

#### Provenance disclosure

The default provenance, extraction by rule and not reviewed, is stated once behind the (i) beside the result heading. A field carries a word only where it deviates (LLM-enriched, expert-curated) or where a decision exists for it. The complete source entry closes the card, and where a publication reports text offsets its passage is marked by a gold start rule with its name. On the record desk every value opens its chain as described under [Facts on demand](#facts-on-demand).

#### State and producer marks

Review status and edition state are plain subdued words in small sans. The producer of a value is a sign of equal weight with its own shape and hue per kind of evidence: rule, derived, language model, person and test fixture (operator, 2026-10-30, replacing the producer word on every row). The word stays the accessible name of the sign and stands once in a legend per card, and no kind is drawn stronger than another, so an LLM proposal never looks weightier than a person's decision. Shape tells the kinds apart, so colour never carries the meaning alone. The workbench marks decisions by a sign and an underline per outcome (right, wrong, unsure) and the wiki state by an icon with its name. The committed vocabulary differs between surfaces, and U12 gives the target.

#### Contested block

An open claim is a tinted section without a frame, headed in serif 600 by what is contested. Its competing readings stand one per line under their authority identifier with a description that tells them apart, followed by the source evidence with its checksum abbreviated to the ends, every evidence page as a link to its record, and the review history in plain words. The block stays open, and the claim identifier sits in the heading's tooltip. A contested value carries the word "contested" beside it as a link to the block. A decided claim keeps its block under a "decided" heading with each reading's status.

#### Buttons, text links and tabs

There are two button styles, filled burgundy with cream text for the action a view exists for and outlined for every other action. Inside a card an action is borderless text with a leading icon, because the card already has its one outline. A control that only navigates or downloads is a text link with its icon. Views over one surface, such as the Explore modes and the playground views, are text tabs whose active member carries the burgundy underline of the main navigation, with a gold underline on hover. Compact in-row controls (facet items, legend entries, per-field edit controls) keep their in-place form, and the round floating filter button is accepted as the drawer opener of narrow screens. A disabled control keeps readable text and states its state by form as well as by colour, as the workbench does with a dashed edge (U9). A control without function in the running environment is not rendered.

#### Counts

A count is a link to the list it counts, its unit is named wherever a neighbouring figure counts something else, and the list it opens holds the number it states.

#### Candidate drawer

The wiki drawer of a print card lists candidates with their route and the state `proposed`. One wiki page appears once with its routes under one head, candidates are ordered by route strength, and a candidate shows which fields agreed with which values. The section column lists the compiler's sections A to R first and apparatus parts under a heading of their own.

## Interaction patterns

The interaction logic stands in [Frontend architecture](frontend-architecture.md#research-views) and [Card workbench](#workbench-decisions). Its visual consequences are these.

- Exactly one object is active on a surface and carries `aria-current` besides its colour.
- A selection made in one view survives the step into the next, from Explore to the desk, from the list to the card and from a filter to the matching publication, which is brought into view.
- A message about a decision names its object and stands where the decision was made.
- A permalink arrives with its heading and its (i) disclosure clear of the sticky header.

## Visualisation logic

The Explore overview counts source pages, one per value they carry, and says so in its units. The decade histogram is neutral grey with the selected range in burgundy, and every populated decade is a labelled, keyboard-operable button with its count. Rankings are bars with their counts and `aria-pressed`. Missing language and missing year stay visible as groups of their own and open their records. The map reports unlocated records separately. Every coloured mark carries its label or count in text. Whether reception research needs counts in publications rather than pages is open in [Specification](specification.md#open-questions), so the page unit stays and is labelled.

## Accessibility minima

These minima bind every surface.

- Contrast as under [Contrast](#contrast).
- Semantic HTML, labelled forms and ARIA labels for iconic controls.
- A visible focus ring on every link, button and field, 3px gold-dark at 2px offset on light grounds and gold on the bar (U6).
- After a view change `showView` moves focus to the heading of the view or to `#main-content`, so hash navigation reaches screen readers, while a change that follows from typing in the search field leaves the focus there. That focus is a starting point rather than a keyboard position and draws no ring.
- Keyboard paths for every pointer action, with shortcuts that bail out under Control, Meta or Alt.
- `prefers-reduced-motion` drops animation and smooth scrolling on every surface.
- A state is never conveyed by colour alone, and a reason needed on touch never lives only in a `title` attribute.
- Targets of at least 24 by 24 CSS pixels or the spacing exception.
- No horizontal page scroll at 320 CSS pixels or at 200 % zoom. Mobile layouts keep search, filters and detail information, and wide matrices such as the completeness matrix scroll in their own container.
- Input text of at least 16px, so mobile Safari does not zoom on focus.
- Reading text below 80 characters per line.

## Unification of the two stylesheets

The workbench comment in `cards.css` says that its tokens follow the production frontend. The two share the hues, while names, the secondary grey, the sans stack, the base face and the loaded fonts differ, and the workbench page links no font file. Print and wiki cards in one design (increment 2) need the targets below.

| ID | Aspect | Target |
|---|---|---|
| U1 | Token source | one `docs/css/tokens.css` with the `--sz-*` names, linked from both pages, which the review server already serves at `/css/tokens.css` because it serves `docs/` at its root |
| U2 | Secondary grey | the production value everywhere as the family value |
| U3 | Fonts | the workbench links `/fonts/fonts.css` |
| U4 | Base type | each surface keeps its base face and size and shares the role table |
| U5 | Source text face | serif with the 72-character measure on both surfaces |
| U6 | Focus ring | 3px gold-dark at 2px offset on light grounds, gold on the bar |
| U7 | Outlined button | burgundy text, field boundaries in a `--sz-border-control` that reaches 3:1 on white, the grey the histogram already uses |
| U8 | Primary button text | cream |
| U9 | Disabled | the workbench rule, a dashed edge and readable faint text without fading |
| U10 | Links | underlined in running text, value rows and the footer, not in navigation, tabs and list titles |
| U11 | State colours | the workbench set as `--sz-state-*`, contested and open in the unsure family, wrong in bad, confirmed in ok, replacing the literal contested colours and the alert colours of edit mode and triage |
| U12 | Producer words | one vocabulary of subdued words, rule as the default stated once in the result list and named on every row of the desk, LLM proposal, person and test fixture, with the deciding agent role in the disclosure |
| U13 | Word "contested" | kept for an open claim, while the workbench class for a card the reviewer flagged becomes `.is-flagged` |
| U14 | Highlight | the workbench tokens, replacing the literal gold tints of the reader |
| U15 | Spacing | the scale in the shared tokens |
| U16 | Monospace | one `--font-mono` |
| U17 | Breakpoints | one rem set of 30, 40, 50, 64 and 75rem, with the workbench stacking at 64rem |
| U18 | Header | 3.5rem and one shared header rule set |
| U19 | Cascade | `@layer` and logical properties as in the workbench for new rules |
| U20 | Name "workbench" | the data-quality page is called "Data quality" in the interface |

## Departures of the committed code

The published reader stays as it is while development is local, so each departure is closed in the local surface that succeeds the view, in the increment of the record desk that [Plan](plan.md#m1-ready-for-review) names. Rows without an increment belong to the browser review that the exit condition of the record desk requires, and to Interface acceptance in [M2](plan.md#m2-merged-and-accepted).

| ID | Rule | Departure | Increment |
|---|---|---|---|
| D1 | A disclosure counts only when perceived | `detail.js` emits empty hidden `data-key` and `data-provenance-for` markers for a fixed key list, and the record coverage test counts them | exit condition |
| D2 | The chain opens at the value | the "Source slice" row shows character offsets as plain text and leads to no passage, and no value discloses its producer from `pub.provenance` | 2 |
| D3 | A proposal never reads as a decision | the About and Data pages say that authority links were decided by LLM agents under delegation (`AUTHORITY_DECISION_NOTE` in `pages.js`) | 1 |
| D4 | A selection survives into the card | a filtered list opens the card at its top, far above the first matching publication | 2 |
| D5 | A value is shown at the level it holds for | `_pageRows` renders a flat translator or contents list no publication carries as a page-level row without a first-match note | 2 |
| D6 | Readings are told apart in the block | two readings can carry identical labels, and evidence pages are plain text | 2 |
| D7 | Every row renders text | the page-classification row passes `wikiPageKindEvidence`, an array of objects, through `esc()` and shows "[object Object]" | 2 |
| D8 | A count names its unit | a start-page print count of entries opens a workbench view that counts print objects | 1 |
| D9 | A count names its unit | the data-quality queue of open authority claims counts entries under a label that reads as claims | 5 |
| D10 | No control without function | on localhost the "Print cards" navigation item and the print address links appear whether or not the review server serves the workbench | 1 |
| D11 | No horizontal page scroll | the start-page model table overflows at 200 % zoom, and the stacked section table leaves the merged wiki cell of sections A and B unnamed in the second row | 1 |
| D12 | A permalink arrives clear of the header | view headings carry no scroll margin, so the heading and the (i) of a permalink sit under the sticky header | 2 |
| D13 | A list value keeps its spacing | page-level contents rows lack the space between title and page reference that contributions have | 2 |
| D14 | Reading text below 80 characters | `.page-content` and the Data page body run wider | 1 |
| D15 | The decision bar stays in reach | below the three-column width of the workbench the decision bar lies below the whole card and the filter strip takes the first screen | 2 |
| D16 | Candidates grouped by page | the drawer lists routes of one wiki page apart and does not show which fields agreed | 2 |
| D17 | Sections before apparatus | the section column mixes apparatus parts into the sections | 2 |
| D18 | Text contrast | the header search placeholder and `.subject-reach` stay below 4.5:1 | |
| D19 | Boundary and focus contrast | `--sz-border` as a field edge and the workbench control edge stay below 3:1, gold focus outlines on light grounds stay below 3:1, and `.editable-field` removes its outline | |
| D20 | Graphic contrast | the chart categories "Not recorded", gold and "Other" stay below 3:1 against white | |
| D21 | Links are underlined | links outside reading pages carry no underline, and burgundy also colours labels that are not links | |
| D22 | Shipped weights and 16px inputs | several rules of both stylesheets request weight 700, and both header searches, the sort select, the playground search and the workbench decision form set input text below 16px | |
| D23 | Capitals for the view title | further small labels (`.badge`, `.ov-title`, `.contested-claim h4`, `.sort-label` among them) are uppercase and tracked | |
| D24 | Two button styles | `.edit-save-btn` is gold-filled, `.geo-toggle` has a filled active state and `.queue-btn` is white-filled | |
| D25 | Targets of 24 pixels | `.card-nav-btn`, the chip close button, `.results-actions .action-btn` and `button.slip-move` are smaller by an estimate from the CSS | |
| D26 | Reduced motion everywhere | the workbench smooth-scrolls the active card into view below its stacking width without checking `prefers-reduced-motion` (`cards.js`) | 2 |
| D27 | Colours come from tokens | the contested block, the edit-mode marks and several highlights use literal colours outside `:root` | 2 |

## Open design decisions

The swap of faces in the value row changes the published card, so it waits for the operator. The proposal is a subdued sans label and a serif value on both surfaces, which leaves burgundy for links and titles and sets the value and its source passage in the same reading face in which review compares them.

The producer words differ between code and knowledge. The committed reader writes "LLM agent", "person" and "rule" beside state words, "… by LLM agent, no person" on proposals and "LLM agent review (…), no person" on publication headings, the field badges read "LLM-enriched" and "expert-curated", and the workbench tags a value "LLM proposal" in semibold red. [Frontend architecture](frontend-architecture.md#rendering-of-contested-statements) still documents "LLM agent, delegated", which the code no longer writes. Since every decision of an LLM agent is a proposal ([Data and model](data.md#statement-states)), U12 proposes "LLM proposal" as the one word for it, in subdued type, with the deciding agent role inside the disclosure. The wording is the operator's decision, and [Frontend architecture](frontend-architecture.md) follows it.
