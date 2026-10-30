---
title: "TEI profile: the delivery format for Stefan Zweig Digital"
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
status: draft
language: en
created: 2026-10-30
updated: 2026-10-30
template:
  name: Vorlage Specification
  version: 0.3
  url: https://dhcraft.org/Promptotyping/promptotyping-document/specification
related: [print-wiki-merge, data, governance, plan]
---

# TEI profile: the delivery format for Stefan Zweig Digital

The operator decided on 2026-10-30, as the side of Stefan Zweig Digital, that the bibliography is delivered as TEI, so that it stands in the data repository of Stefan Zweig Digital beside its other holdings and its pages can be rendered there. This settles the first of the two delivery routes of [Merged bibliography](print-wiki-merge.md), Merged bibliography and delivery. The TEI is a projection: `pipeline/export_tei.py` builds it from the canonical data on every run, and nothing is curated in it. The schema is `docs/schema/klawiter-tei.rng`, a RELAX NG grammar of the subset the profile uses, chosen over an ODD by the operator for compactness; `tests/test_tei_export.py` validates the export against it and resolves every internal pointer, which RELAX NG cannot. The profile is a draft until it has been reviewed and agreed on a sample object.

## Delivery decisions

The operator decided on 2026-10-30:

- The bibliography is one GAMS object, `o:szd.klawiter`, like the other holdings of Stefan Zweig Digital.
- It is rendered by a stylesheet of its own, `szd-klawiter.xsl`, in the design of Stefan Zweig Digital, because the existing stylesheets select `biblFull` and show no provenance; the RDF stylesheet of Stefan Zweig Digital needs a branch for the object as well.
- Unreviewed data may be ingested into GAMS Staging, which is a test instance outside the GAMS infrastructure, to check ingest and rendering before the human round; the production instance receives the bibliography after the round.

## What the profile takes from Stefan Zweig Digital

Stefan Zweig Digital has no schema; its encoding patterns are described from its data in the data repository (`SZD/knowledge/DATA_MODEL.md`, `COLLECTIONS.md`). The profile follows them where they apply:

- the header pattern, with the publisher, licence and an object PID `o:szd.klawiter` in `publicationStmt`;
- one `listBibl` in the body;
- identifiers after the pattern `{COLLECTION_CODE}.{NUMBER}`, here `SZDKLA`, never reassigned once given;
- machine-readable dates in attributes beside the text of the source;
- `@ref` for authority identifiers once a link is confirmed.

## Where it departs, and why

- A record is a `biblStruct`, not the `biblFull` with `msDesc` of the holdings of Stefan Zweig Digital, because Klawiter describes publications, not items an archive holds.
- Every value carries `@resp` (its producer, pointing to an `application` in `appInfo`), `@source` (its passage, pointing to a `seg` of Klawiter's entry in `sourceDesc`) and `@ana` (its statement state, pointing to a category of the state taxonomy in `classDecl`). Stefan Zweig Digital records uncertainty only as `@cert` on dates, which would drop what this project is about.
- Klawiter's entries stand in `standOff/listBibl[@type='sources']`, with page and revision, the page title and categories, the print addresses the entry cites, and the entry text unaltered with one `seg` per passage a value points to; passages nest, and a passage crossing another is addressed by a `string-range()` pointer. The entries stay out of the header because the Dublin Core mapping of GAMS reads the header's first title; `sourceDesc` names the wiki and its dump only. Text no value was read from stays unmarked, so it can be told from what was read.
- A value keeps the spelling of the source (Ştiinţifică with cedillas as Klawiter wrote it); normalised forms are not yet part of the profile.
- Statements between a source and a publication are `relation` elements in `standOff`, with producer and state, so a proposed identity of a print record and a wiki page is never encoded as structure.
- User-facing text is not bilingual, because Klawiter's text is English and the values are its words; only the header titles follow the bilingual pattern.

## Print records

Print records enter only as identifier and checksum in the source list, linked to the wiki entry by their proposed claim (`relation[@name='samePublicationAs']` with `@mutual`), never with print text, because the rights to the print volumes are unresolved ([Project](project.md)). An export with print records is written under `data/print/derived/tei/` and stays local; the versioned export under `data/output/tei/` holds wiki data only.

## State of the export

The export covers every content page. A page classified as an edition page gives one `biblStruct` per publication of its publication layer, or one from its flat record when it has none; pages of other kinds give none yet. Which field reaches which element, which waits for a later milestone and which is excluded is declared in `FIELDS` of `pipeline/export_tei.py`. `pipeline/acceptance.py` checks the export over all pages against tei_all and against values it recomputes from the canonical data, and the acceptance view shows the result ([Plan](plan.md), Program). The faults the first export had (altered source text, fixed states, collapsed publications, monographs from author pages, lost passages, print records in `sourceDesc`) are closed by these checks; the profile schema and a mutation suite that shows the checks reject wrong documents are the open part of D1.

## Open

- The identifier scheme: `SZDKLA.<page>.<n>` is provisional until the operator decides how a publication is identified independently of the page it stands on ([Plan](plan.md), M2 Identifiers).
- Pages of other kinds whose entry yields publications (page 54), and author pages as persons with contributions (page 1605): decisions E8 and E3 of the acceptance view.
- Proposed and confirmed authority links (place, person, work), as `relation` while proposed and `@ref` once confirmed, and the link to the work index of Stefan Zweig Digital.
- Normalised forms beside the source spelling (`choice` with `orig` and `reg`).
- `szd-klawiter.xsl` and the RDF branch for `o:szd.klawiter` in the data repository of Stefan Zweig Digital.
- The sample object on which the profile is agreed; page 212 is the first, page 54 the one [Merged bibliography](print-wiki-merge.md) named.
