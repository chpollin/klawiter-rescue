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
- Klawiter's entries stand in `sourceDesc/listBibl` as the sources of the file, with page and revision, the page title and categories, and the entry text with one `seg` per located passage. Text no value was read from stays unmarked, so it can be told from what was read.
- A value keeps the spelling of the source (Ştiinţifică with cedillas as Klawiter wrote it); normalised forms are not yet part of the profile.
- Statements between a source and a publication are `relation` elements in `standOff`, with producer and state, so a proposed identity of a print record and a wiki page is never encoded as structure.
- User-facing text is not bilingual, because Klawiter's text is English and the values are its words; only the header titles follow the bilingual pattern.

## Print records

Print records enter only as identifier and checksum, linked by their proposed claim, never with print text, because the rights to the print volumes are unresolved ([Project](project.md)). An export with print records is written under `data/print/derived/tei/` and stays local; the versioned export under `data/output/tei/` holds wiki data only.

## Open

- The identifier scheme: `SZDKLA.<page>.<n>` is provisional until the operator decides how a publication is identified independently of the page it stands on ([Plan](plan.md), M2 Identifiers).
- Pages with a publication layer, which export one `biblStruct` per publication from the per-page files.
- Proposed and confirmed authority links (place, person, work), as `relation` while proposed and `@ref` once confirmed, and the link to the work index of Stefan Zweig Digital.
- Normalised forms beside the source spelling (`choice` with `orig` and `reg`).
- The rendering on the side of Stefan Zweig Digital, which its stylesheet needs for the departures above.
- The sample object on which the profile is agreed; page 212 is the first, page 54 the one [Merged bibliography](print-wiki-merge.md) named.
