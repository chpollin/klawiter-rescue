---
title: Data and Model
status: maintained
language: en
updated: 2026-09-23
related: [about, pipeline, frontend, testing, production-readiness, status]
---

# Data and model

## Source scope

The rescue selects `page_latest`, preserving every current MediaWiki page ID. It does not extract every historical bibliographic statement into an entity. The delivered dump also contains earlier revisions and archived material; historical revision recovery and the triage of archived main-namespace titles absent from the current table remain separately scoped work. Version 1.0 excludes those titles explicitly ([release scope](production-readiness.md#release-scope)). The archive's revision rows, distinct namespace/title pairs and absent bibliography titles are different populations; do not call all of them “deleted pages”. The [completion review](project-review-2026-09-05.md) documents their census.

Four current pages lack a delivered text body. Only page `2979`, *A unidade espiritual do mundo*, is bibliographic; its named stub preserves the source identity. Uploaded image metadata does not imply that the image bytes were delivered. Raw originals remain unchanged. Their SHA-256 inventory is `data/provenance/source-dump.json`, checked by `tests/test_source_inventory.py`. The dump also holds account data, edit metadata with IP addresses and an archived private message, so `.gitattributes` keeps `data/raw` out of every release archive. An archival directory is not a publication allowlist.

### Pages overwritten by the Redirect fixer

The wiki ran an automatic account named "Redirect fixer" that rewrote double redirects after page moves. In some cases it overwrote a content page with an unrelated redirect. Page 35 "Maria Stuart", the German original work page of the biography with its editions and its list of translations, became a redirect to the reviewer page 4113 in revision 33773 on 2017-10-08, after the unrelated move of that reviewer page. The 26 translation pages whose "See also" names Maria Stuart therefore pointed to a review of *Castellio gegen Calvin*.

Where the revision the fixer overwrote is a delivered human text that is no redirect, the edition publishes that last human revision, and the fixer redirect is not resolved as a relation (decided by the main instance after delegation by the operator on 2026-09-23, revisable). This applies to pages 35, 279, 793, 2816, 2817, 4248, 4428 and 5839. Where that revision is absent from the dump, as for ten pages overwritten in 2010 and 2011, the redirect is withheld and an open claim of the type `source-revision` records the case. `data/reconciliation/source-revision-decisions.json` holds every decision with the fixer revisions, the restored revision and its text hash. Stage 01 re-detects the cases from the revision tables on every run and fails when detection and decisions disagree. A restored frontend record carries the decision as `sourceRevision`. This is the only place where the edition departs from `page_latest`.

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

Redirect targets preserve their source title. Stage 05 resolves literal aliases and redirect chains with cycle protection. A link target is split at its pipe and has its whitespace runs collapsed before the lookup, as MediaWiki does. An unresolved `seeAlso` is a diagnostic and must not automatically be described as a genuine red link. The two that remain, on pages 679 and 7232, name titles no current page carries.

## Publication and contribution scope

A source page can describe several publications. The flat record answers with one value per field, so it can join one publication's imprint to another publication's language and describe a publication the source never documents. Page 4445 showed this in the interface, where the year, place, publisher and extent of a German book from 2000 appeared beside the language of an Arabic article from 2015. The frontend record therefore carries a second layer in which every fact belongs to the publication it was written under. The flat fields keep their meaning and their values, so search, facets and exports continue to work on them.

Stage 05 builds the layer from the page's source text through `lib/publications.py`, which segments with `lib.editions.segment_page`, the same function Gate 1 uses. Publication identifiers, source slices and extents therefore agree with the edition graph wherever both cover a page; `klawiter:publication/{page}-{year}-{suffix}` corresponds to `klawiter:edition/{page}-{year}-{suffix}`. A page whose source carries no publication header receives no layer, because absence of a header is the honest statement about such a page.

The records live in one file per source page under `docs/data/publications/`, named by page id and reached through the template in `_meta.publicationCoverage.pathTemplate`. The main dataset keeps the page-level summary, so search and facets work without loading any of them, and the interface fetches a page's file when it shows that page. The canonical Work/Edition graph stays the reference structure for multi-edition pages, and the flat `klawiter.jsonld` does not carry the layer. Carrying the layer into the canonical RDF needs a vocabulary extension and remains open work.

### Page-level fields

| Field | Meaning |
|---|---|
| `pageKind` | `author-page` where a source category path carries the segment Authors, otherwise `edition-page` for several publications and `single-publication` for one |
| `publicationCount` | number of publications documented on the page |
| `publicationYears`, `publicationPlaces`, `publicationLanguages` | union over all publications, so a facet finds the page under every publication's value instead of under the value of one of them |
| `reviewFlags` | field-scoped hints on flat values, currently the encoding repair of an enrichment value, each naming its `field` |
| `publicationReviewFlags` | the distinct review flag codes of the page's publications, so a facet can find pages with open cases without loading their side files |
| `sourceRevision` | on a page restored from before a Redirect fixer overwrite, the decision, the restored revision and the fixer revisions |

The side file of a page carries `sourcePageId`, its `publications` in source order and its `nameVariants`, where a name variant is a spelling that differs slightly from a credited name, held with the source line it stands in and `status: unresolved`.

`publicationPlaces` covers the imprint places of every publication together with the place of an article's container, because an article carries its place in the container statement.

### Publication fields

| Field | Meaning |
|---|---|
| `id`, `sourceSlice` | identifier, and the exact start, end and SHA-256 of the source block the record was read from; `textStart` and `textEnd` name the same passage inside the delivered `fullBibliographicEntry`, and are absent where no single passage matches |
| `year`, `yearRaw` | publication year, and the header notation including an approximate `ca.` form |
| `title` | the italic or quoted title of the block, whichever notation comes first |
| `editionId`, `reviewStatus` | the Gate 1 edition node the publication corresponds to, and its state `proposed` or `confirmed`. A publication outside the Gate 1 corpus is `proposed` and has no `editionId` |
| `imprint` | the header statement in its source wording |
| `imprints` | the publisher/place pairs of a co-imprint, one pair per imprinting house |
| `publisher`, `places` | publisher, and every place of publication in source wording, a qualifier such as `UT` or `Switzerland` kept with its place |
| `language`, `languageCode` | language of this publication and its BCP-47 subtag |
| `editionStatement` | an edition statement such as `2nd revised edition` |
| `extent` | `raw` holds the source notation such as `444/(3)p.`, `numbered` and `unnumbered` hold its components |
| `series`, `seriesVolume`, `seriesGloss` | series statement, its volume number as a separate value, and an English gloss the source gives in brackets, as on page 5039 with "Tvorba národov" and the gloss "The Formation of Nations"; a "See" cross-reference is no series statement, except where it names a multi-volume set followed by a volume number |
| `note` | source prose that follows the series statement, such as a thesis origin |
| `credits` | `role`, `name` and the literal `creditLabel` of the source |
| `contributions` | contents entries with `title`, `note`, `pages`, `pageStart`, `pageEnd` and their own `credits` |
| `container` | `title`, `place`, `issue` and `pages` of a journal an article appeared in |
| `online` | `url` and the qualification the source gives it, such as a shortened preview version |
| `reviewFlags` | `code` and readable `detail` of a case the rules cannot decide |
| `provenance` | the provenance class of every reported field of this publication |

A field stays absent where the source carries no value for it. Roles use the closed vocabulary `author`, `translator`, `editor`, `illustrator` and `contributor`, and a credit is read only where the label names a contribution role. The role `author` is read only from a label that credits the publication itself to a person, which in the corpus is "A graphic novel by" on pages 4916 and 5110, and "adapted into <language> by" counts as a translation credit. A label such as "Cover design by" stays unread rather than entering as an untyped contributor. The scalar `translator` of the flat record is one credit under the compatibility rule, so an interface must read `credits` and `contributions[].credits` before it says anything about the translators of a publication.

### Effect on the flat fields

The flat publisher takes the imprint of the first publication whose header also names a place, split exactly as the publication layer splits it, so the two layers never disagree. The body patterns keep the entries that never carried a header, and a candidate stating who translated, edited or illustrated a work is refused, because a contribution credit is no imprint. A header without a place is left alone, since its single segment can equally be a publisher, a place or a country.

Enrichment values reach the record through a repair. A value that arrived as a Latin-1 or CP1252 misreading of UTF-8 bytes is restored by the byte round-trip and carries the review hint `encoding-repaired` under its field; a value whose bytes were already lost when the cache was frozen empties the field, because an empty field is a smaller claim than a corrupt one. The repaired value keeps its provenance class `llm`, the origin of the value being unchanged by the repair. The class of every reported field is stated, for title, year, language and categories as well as the four fields the enrichment can fill.

### What the layer does not assert

The publications listed on one page share that source page, and on an author page they share the author. No translation, edition or work relation between them is asserted here, because the source establishes none. A relation of that kind needs review evidence and belongs in the reconciliation layer.

Every value of the layer is rule-extracted from the source slice it is reported with, so `provenance` currently reports `regex` for each field. Model values and editor values do not enter it. A released field patch can later set `editor` on a single field, and the per-field map is shaped for that.

Three review flags mark what the rules leave open. The rules behind them were revised on 2026-09-23 after an audit found most flags to be parser artifacts rather than conflicts in the source.

- `imprint-segments-unresolved` marks a header whose publisher and place boundary the string does not settle, such as "Reed Library, State University College, Fredonia, New York". The split keeps a trailing qualifier with its place. The qualifier lists are cited in `lib/patterns.py` (USPS state codes and names, Canada Post codes, Brazilian state codes, the Natural Earth country names vendored under `docs/vendor/`, and regions attested with their page). A legal-form suffix stays with the publisher. A co-imprint joined by " / ", " // ", "; " or an "and" between two complete statements yields several publisher/place pairs. Commas inside brackets or quotation marks never split, and "[s.n.]" and "[s.l.]" are absences.
- `contents-pagination-exceeds-extent` marks contents that run past the extent the notation declares, numbered and unnumbered pages together, and each volume of a set against its own extent. Page 1891 (`444/(3)p.`, contents ending at (445)) is therefore no longer flagged, while pages such as 204 and 4554 keep a genuine overrun.
- `missing-location` marks a publication header without a place. An imprint set after the closing bold, a single place attested by the location stock, and the "Place: Publisher, YEAR" statement on the first body line of a date-only header with the same year are read as places before the flag applies.

A contribution's pages are its first page statement outside brackets. The contents line stops at a "See" or "(First/Re)printed in" reference, and a contents list ends at a wiki heading or a bold label such as "Reprinted in:". A year header followed only by a page locator, as on page 3757, is no publication. Page 1875 still merges its six volumes into one publication, because splitting it would change the Gate 1 segmentation.

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

A `klawiter:ContestedClaim` has a stable ID, subject/predicate, source evidence, interpretations, review actions, `claimStatus = contested` and `decisionStatus = open`. It remains in the final graph while the disputed relation is withheld. A recorded decision closes it without removing it. The claim then carries `claimStatus = resolved`, `decisionStatus = decided`, one `accepted` and the other interpretations `rejected`, the decision as a further review action with its date, and `klawiter:reviewNote` for what the decision leaves open. Only the accepted reading becomes a relation. The decision lives in `data/reconciliation/edition-modeling-decisions.json` as the `resolution` of the claim, so removing it restores the open claim.

Gate 2 keeps authority claims the same way. `docs/data/reconciliation.json` lists open claims under `contestedClaims` and decided ones under `decidedClaims`, the latter with accepted and rejected readings, the basis of the decision and its review notes. The compound place subjects "Sofija, Varna", "Varna, Sofija" and "Bloemfontein, Kaapstad" are decided as two places each. Their single-identity readings are rejected and the components are confirmed on their own (Varna Q6506, Bloemfontein Q37701, Kaapstad (Capetown) Q5465, Sofija Q472), decided by the main instance after delegation by the operator on 2026-09-23, revisable. Tyresö and Saint-Aignan stay open, because the source settles neither the municipality or district of the first nor whether the second means Mont-Saint-Aignan. Open claims of the type `source-revision` record the withheld Redirect fixer cases described under source scope. In the flat `klawiter.jsonld` a place, person or publisher node under an open claim references it through `klawiter:hasContestedClaim`.

The graphic novel `klawiter:edition/4916-2016-b` was the one open work binding. Claim `klawiter:claim/work-binding/4916-2016-b` is resolved with the adaptation reading, decided by the main instance after delegation by the operator on 2026-09-22, revisable. The candidate `klawiter:work-candidate/4916-2016-b-adaptation` keeps its identifier and is now a `schema:CreativeWork` without a source page of its own, `schema:isBasedOn` the Schachnovelle work `klawiter:work/4916`, with the illustrator as `schema:creator`, and derived from the claim. The German edition of 2016 is its `schema:workExample` and leaves the editions of `klawiter:work/4916`; its `schema:translationOfWork` points to the French graphic novel of 2015 on pages 675 and 5110 (`klawiter:edition/675-2015-a`, `klawiter:edition/5110-2015-a`). The source pages give the German edition 120p. (page 4916) and 128p. (page 5110). The difference is held as the review flag `extent-differs-across-source-pages` and as a review note, and it is not resolved. The French edition on page 675 and both occurrences on the author page 5110 keep their page bindings, because the decision covers the German edition on page 4916 only.

## Reconciliation

Gate 2 separates candidates, decisions, claims and `publishable-links.json`. Location candidates, the SZD work index, and translator/publisher candidates are frozen inputs. The agent candidate stock uses a minimum occurrence threshold; absence from that stock is not evidence of absence from the bibliography.

Only `confirm` and `correct` publish authority links. `reject` retains the negative decision. `unresolved` retains alternatives as an open claim. Superseding decisions preserve their predecessor. Stage 05 consumes the publishable layer, never promotes a candidate itself.

Occurrence evidence includes page/text IDs, source lines and hashes. Multi-part place matches retain component information, and a component match counts only where one imprint, a bold edition header or a bracket, contains every component as a whole word. Before this rule the claims on "Sofija, Varna" took evidence from ten pages on which the two cities stand in citations of different publications. Agent occurrences are tied to entries carrying that field; a `sourceMatchMode: field-value` fallback or a spelled-out null finding is weaker than a literal line match and remains distinguishable. RDF contexts preserve nested page-summary and contested source-evidence fields; the RDF tests assert literal preservation, beyond JSON object presence.

## Provenance and review scope

The frontend field layer uses `regex`, `llm`, `missing` and `editor`. Its provenance injection and patch overlay currently happen after canonical JSON-LD export. They are not fully propagated into the flat canonical graph, edition graph and all quality reports. Browser exports and playground projections also have distinct scopes; see [Frontend](frontend.md).

Gate artifacts carry input/code hashes, PROV activities and EARL/validation results. Occurrence matching establishes that a string is present, not that it belongs to the intended publication.

The frontend `review` object carries status, reviewer, time where present, per-field actions and `scope`, the list of fields the decisions cover. For most reviewed entries that scope is the place alone. A `reject` yields the status `reviewed`, which records a decision and no verification. The interface names the scope in its review label, so a badge does not suggest that the whole entry was checked, and an open claim on a value stays visible beside it.

## Correction Protocol

The browser saves a local session and exports decisions; it does not write into this repository. Released field patches replay into the frontend and preserve `edit_history`; released reconciliation patches enter the Gate 2 rebuild and preserve `supersedes`.

Field replay validates positive integer IDs, timezone-aware timestamps, actions and permitted fields. Invalid patches or unknown targets abort the batch before frontend persistence. A differing `oldValue` currently produces a warning; it does not veto the authoritative patch. Exact examples and maintenance instructions belong in the [patch-store contract](../data/corrections/README.md).

## Canonical evidence

[Status](status.md) links current counts and open work; [Testing](testing.md) defines what the evidence proves. Quality population, source occurrence, semantic correctness, complete modelling and user acceptance are separate measurements. A selected sample gives no corpus-wide accuracy estimate.
