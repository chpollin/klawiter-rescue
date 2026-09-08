---
title: Data and Model
status: maintained
language: en
updated: 2026-09-08
related: [about, pipeline, frontend, testing, production-readiness, status]
---

# Data and model

## Source scope

The rescue selects `page_latest`, preserving every current MediaWiki page ID. It does not extract every historical bibliographic statement into an entity. The delivered dump also contains earlier revisions and archived material; historical revision recovery and the triage of archived main-namespace titles absent from the current table remain separately scoped work. The archive's revision rows, distinct namespace/title pairs and absent bibliography titles are different populations; do not call all of them “deleted pages”. The [completion review](project-review-2026-09-05.md) documents their census.

Four current pages lack a delivered text body. Only page `2979`, *A unidade espiritual do mundo*, is bibliographic; its named stub preserves the source identity. Uploaded image metadata does not imply that the image bytes were delivered. Raw originals remain unchanged. A separately reviewed public source package is still required; an archival directory is not a publication allowlist.

## Data levels and ownership

| Level | Location | Contract |
|---|---|---|
| Archival source | `data/raw/` | preserve original bytes |
| Frozen external/model evidence | `data/provenance/` | versioned inputs; live refresh is separate |
| Reviewed decisions | `data/reconciliation/`, `data/corrections/` | explicit evidence, action and history |
| Intermediate stages | `data/intermediate/` | regenerable CSVs, not canonical decisions |
| Flat canonical graph | `data/output/klawiter.jsonld` | one record per current wiki page, including redirects |
| Structured graphs | `data/output/editions/`, `data/output/reconciliation/` | selected edition structures and authority claims |
| Interface projection | `docs/data/` | non-redirect records, evidence, review and curation views |

The current census and coverage are in [Status](status.md). The exact source/canonical ID multisets agree; the frontend contains the canonical non-redirect IDs. Structural namespaces remain in its dataset but outside the bibliography views. This establishes record preservation, not field recall.

## Flat compatibility model

The flat record uses Schema.org, Dublin Core and `klawiter:` terms. It retains title, year, publisher, place, language, translator, extent, categories, cross-references and source identifiers. A populated field can belong to a different publication block from another field on the same page. A first match is a compatibility choice, not a universal scholarly rule.

Language is category-derived under the existing selection precedence. Its human label is retained separately from its registered BCP-47 subtag. The historical source label “Serbo-Croatian” uses the registered macrolanguage `sh`; it is not silently narrowed to Serbian or Croatian. See the [IANA registry](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry). Publication-scoped language lives in the publication layer described below.

`pageCount` / `schema:numberOfPages` means numbered extent. A citation locator such as “References: p. 425” is not a 425-page book. Translator name transcription and the association of that translator with a publication are separate assertions. Missing, not applicable, not yet extracted and ambiguous values are not yet represented as distinct states throughout the flat layer.

Redirect targets preserve their source title. Stage 05 resolves literal aliases and redirect chains with cycle protection. An unresolved `seeAlso` is a diagnostic: it may reflect whitespace, link syntax or source absence, and must not automatically be described as a genuine red link.

## Publication and contribution scope

A source page can describe several publications. The flat record answers with one value per field, so it can join one publication's imprint to another publication's language and describe a publication the source never documents. Page 4445 showed this in the interface, where the year, place, publisher and extent of a German book from 2000 appeared beside the language of an Arabic article from 2015. The frontend record therefore carries a second layer in which every fact belongs to the publication it was written under. The flat fields keep their meaning and their values, so search, facets and exports continue to work on them.

Stage 05 builds the layer from the page's source text through `lib/publications.py`, which segments with `lib.editions.segment_page`, the same function Gate 1 uses. Publication identifiers, source slices and extents therefore agree with the edition graph wherever both cover a page; `klawiter:publication/{page}-{year}-{suffix}` corresponds to `klawiter:edition/{page}-{year}-{suffix}`. A page whose source carries no publication header receives no layer, because absence of a header is the honest statement about such a page.

The records live in one file per source page under `docs/data/publications/`, named by page id and reached through the template in `_meta.publicationCoverage.pathTemplate`. The main dataset keeps the page-level summary, so search and facets work without loading any of them, and the interface fetches a page's file when it shows that page. The canonical Work/Edition graph stays the authority for multi-edition pages, and the flat `klawiter.jsonld` is unchanged by this projection. Carrying the layer into the canonical RDF needs a vocabulary extension and remains open work.

### Page-level fields

| Field | Meaning |
|---|---|
| `pageKind` | `author-page` where a source category path carries the segment Authors, otherwise `edition-page` for several publications and `single-publication` for one |
| `publicationCount` | number of publications documented on the page |
| `publicationYears`, `publicationPlaces`, `publicationLanguages` | union over all publications, so a facet finds the page under every publication's value instead of under the value of one of them |
| `reviewFlags` | field-scoped hints on flat values, currently the encoding repair of an enrichment value, each naming its `field` |

The side file of a page carries `sourcePageId`, its `publications` in source order and its `nameVariants`, where a name variant is a spelling that differs slightly from a credited name, held with the source line it stands in and `status: unresolved`.

`publicationPlaces` covers the imprint places of every publication together with the place of an article's container, because an article carries its place in the container statement.

### Publication fields

| Field | Meaning |
|---|---|
| `id`, `sourceSlice` | identifier, and the exact start, end and SHA-256 of the source block the record was read from; `textStart` and `textEnd` name the same passage inside the delivered `fullBibliographicEntry`, and are absent where no single passage matches |
| `year`, `yearRaw` | publication year, and the header notation including an approximate `ca.` form |
| `title` | the italic or quoted title of the block, whichever notation comes first |
| `imprint` | the header statement in its source wording |
| `publisher`, `places` | publisher, and every place of publication in source wording |
| `language`, `languageCode` | language of this publication and its BCP-47 subtag |
| `editionStatement` | an edition statement such as `2nd revised edition` |
| `extent` | `raw` holds the source notation such as `444/(3)p.`, `numbered` and `unnumbered` hold its components |
| `series`, `seriesVolume` | series statement and the volume number it ends with |
| `note` | source prose that follows the series statement, such as a thesis origin |
| `credits` | `role`, `name` and the literal `creditLabel` of the source |
| `contributions` | contents entries with `title`, `note`, `pages`, `pageStart`, `pageEnd` and their own `credits` |
| `container` | `title`, `place`, `issue` and `pages` of a journal an article appeared in |
| `online` | `url` and the qualification the source gives it, such as a shortened preview version |
| `reviewFlags` | `code` and readable `detail` of a case the rules cannot decide |
| `provenance` | the provenance class of every reported field of this publication |

A field stays absent where the source carries no value for it. Roles use the closed vocabulary `translator`, `editor`, `illustrator` and `contributor`, and a credit is read only where the label names a contribution role; a label such as "Cover design by" stays unread rather than entering as an untyped contributor. The scalar `translator` of the flat record is one credit under the compatibility rule, so an interface must read `credits` and `contributions[].credits` before it says anything about the translators of a publication.

### Effect on the flat fields

The flat publisher takes the imprint of the first publication whose header also names a place, split exactly as the publication layer splits it, so the two layers never disagree. The body patterns keep the entries that never carried a header, and a candidate stating who translated, edited or illustrated a work is refused, because a contribution credit is no imprint. A header without a place is left alone, since its single segment can equally be a publisher, a place or a country.

Enrichment values reach the record through a repair. A value that arrived as a Latin-1 or CP1252 misreading of UTF-8 bytes is restored by the byte round-trip and carries the review hint `encoding-repaired` under its field; a value whose bytes were already lost when the cache was frozen empties the field, because an empty field is a smaller claim than a corrupt one. The repaired value keeps its provenance class `llm`, the origin of the value being unchanged by the repair. The class of every reported field is stated, for title, year, language and categories as well as the four fields the enrichment can fill.

### What the layer does not assert

The publications listed on one page share that source page, and on an author page they share the author. No translation, edition or work relation between them is asserted here, because the source establishes none. A relation of that kind needs review evidence and belongs in the reconciliation layer.

Every value of the layer is rule-extracted from the source slice it is reported with, so `provenance` currently reports `regex` for each field. Model values and editor values do not enter it. A released field patch can later set `editor` on a single field, and the per-field map is shaped for that.

Three review flags mark what the rules leave open. `imprint-segments-unresolved` marks a header with more than two comma segments whose publisher and place boundary the string does not settle; the split into several places is made only where the frozen location stock of `docs/data/locations.json` attests a trailing run of at least two places. `contents-pagination-exceeds-extent` marks contents that run past the stated numbered extent, as on page 1891, where the contents end at 445 and the extent states 444. `missing-location` marks a publication header without a place.

`nameVariants` records a bracket spelling that has the same token count and the same final token as a credited name and a similarity of at least 0.85, as with the foreword spelling Hymme Weiss beside the credited translator Hymne Weiss on page 4209. Both spellings stay in the record and no identity between them is asserted.

## Work/edition model

The ratified Gate 1 corpus consists of main-namespace pages with at least two supported bold publication headers containing a four-digit or approximate year. This grammar selects a bounded corpus; compound pages outside it remain unresolved by this graph.

| Entity | Identity and meaning |
|---|---|
| `schema:CreativeWork` | `klawiter:work/{page_id}`, work of the source page |
| `schema:Book` | `klawiter:edition/{page_id}-{year}-{suffix}`, segmented publication block |
| `oa:Annotation` | edition's exact source block, start/end selector and SHA-256 |
| `schema:PublicationVolume` | source-documented carrier occurrence; no global collected-volume identity inferred |

Source order stabilizes edition suffixes and selectors. The graph improves segmentation and evidence; it does not yet model every translator, language, contribution, imprint and pagination relation for every publication. The flat interface does not yet offer full edition navigation. Those are acceptance gaps, not reasons to reapprove the already ratified separation.

## Statement states

- `proposed`: deterministic, unreviewed statement.
- `confirmed`: source-bound reviewed statement.
- `contested`: open statement with competing interpretations and review history.

A `klawiter:ContestedClaim` has a stable ID, subject/predicate, source evidence, interpretations, review actions, `claimStatus = contested` and `decisionStatus = open`. It remains in the final graph while the disputed relation is withheld.

The adaptation `klawiter:edition/4916-2016-b` remains preserved. Claim `klawiter:claim/work-binding/4916-2016-b` distinguishes an edition of *Schachnovelle* from an independent graphic-novel work. It publishes no confirmed `schema:exampleOfWork` while the work identity is open.

## Reconciliation

Gate 2 separates candidates, decisions, claims and `publishable-links.json`. Location candidates, the SZD work index, and translator/publisher candidates are frozen inputs. The agent candidate stock uses a minimum occurrence threshold; absence from that stock is not evidence of absence from the bibliography.

Only `confirm` and `correct` publish authority links. `reject` retains the negative decision. `unresolved` retains alternatives as an open claim. Superseding decisions preserve their predecessor. Stage 05 consumes the publishable layer, never promotes a candidate itself.

Occurrence evidence includes page/text IDs, source lines and hashes. Multi-part place matches retain component information. Agent occurrences are tied to entries carrying that field; a `sourceMatchMode: field-value` fallback or a spelled-out null finding is weaker than a literal line match and remains distinguishable. RDF contexts preserve nested page-summary and contested source-evidence fields; the RDF tests assert literal preservation, beyond JSON object presence.

## Provenance and review scope

The frontend field layer uses `regex`, `llm`, `missing` and `editor`. Its provenance injection and patch overlay currently happen after canonical JSON-LD export. They are not fully propagated into the flat canonical graph, edition graph and all quality reports. Browser exports and playground projections also have distinct scopes; see [Frontend](frontend.md).

Gate artifacts carry input/code hashes, PROV activities and EARL/validation results. Occurrence matching establishes that a string is present, not that it belongs to the intended publication.

The frontend `review` object carries status, reviewer, time where present, and per-field actions. Current entry-level precedence is `approved` over `agent_verified` over `contested`. Therefore a badge does not certify all fields or remove an open claim on another field. Field-scoped review meaning needs clearer publication and interface treatment.

## Correction Protocol

The browser saves a local session and exports decisions; it does not write into this repository. Released field patches replay into the frontend and preserve `edit_history`; released reconciliation patches enter the Gate 2 rebuild and preserve `supersedes`.

Field replay validates positive integer IDs, timezone-aware timestamps, actions and permitted fields. Invalid patches or unknown targets abort the batch before frontend persistence. A differing `oldValue` currently produces a warning; it does not veto the authoritative patch. Exact examples and maintenance instructions belong in the [patch-store contract](../data/corrections/README.md).

## Canonical evidence

[Status](status.md) links current counts and open work; [Testing](testing.md) defines what the evidence proves. Quality population, source occurrence, semantic correctness, complete modelling and user acceptance are separate measurements. A selected sample gives no corpus-wide accuracy estimate.
