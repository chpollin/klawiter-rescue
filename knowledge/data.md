---
title: Data and Model
status: maintained
language: en
updated: 2026-09-05
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

Language is category-derived under the existing selection precedence. Its human label is retained separately from its registered BCP-47 subtag. The historical source label “Serbo-Croatian” uses the registered macrolanguage `sh`; it is not silently narrowed to Serbian or Croatian. See the [IANA registry](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry). Publication- or contribution-specific language still needs scoped modelling.

`pageCount` / `schema:numberOfPages` means numbered extent. A citation locator such as “References: p. 425” is not a 425-page book. Translator name transcription and the association of that translator with a publication are separate assertions. Missing, not applicable, not yet extracted and ambiguous values are not yet represented as distinct states throughout the flat layer.

Redirect targets preserve their source title. Stage 05 resolves literal aliases and redirect chains with cycle protection. An unresolved `seeAlso` is a diagnostic: it may reflect whitespace, link syntax or source absence, and must not automatically be described as a genuine red link.

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
