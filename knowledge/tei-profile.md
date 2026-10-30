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
- Klawiter's entries stand in `sourceDesc/listBibl` as the sources of the file, with page and revision, the page title and categories, and the entry text with one `seg` per located passage. Text no value was read from stays unmarked, so it can be told from what was read.
- A value keeps the spelling of the source (Ştiinţifică with cedillas as Klawiter wrote it); normalised forms are not yet part of the profile.
- Statements between a source and a publication are `relation` elements in `standOff`, with producer and state, so a proposed identity of a print record and a wiki page is never encoded as structure.
- User-facing text is not bilingual, because Klawiter's text is English and the values are its words; only the header titles follow the bilingual pattern.

## Print records

Print records enter only as identifier and checksum, linked by their proposed claim, never with print text, because the rights to the print volumes are unresolved ([Project](project.md)). An export with print records is written under `data/print/derived/tei/` and stays local; the versioned export under `data/output/tei/` holds wiki data only.

## State of the first export

The first export (ebe5ae3) is a sample, not a delivery. An independent TEI review and an audit over all main-namespace pages on 2026-10-30 found it valid against the profile schema but neither conformant nor faithful yet ([Journal](journal.md), entry of that day):

- one conformance error against tei_all (a timestamp in `application/@version`), and an empty `imprint` that the profile schema admits and TEI does not;
- the serialisation indents the mixed content of `quote` and so changes the source text wherever a gap between passages is whitespace only;
- review states of values are not carried (`@ana` is fixed), the publication layer is ignored, so a page with several publications becomes one `biblStruct`, and author pages and work hubs become monographs;
- many fields of the record have no trace in the TEI, among them original titles, contents, translations, See references, print citations and review flags;
- a passage swallowed by a wider span of an unexported field loses `@source`; repeated and non-verbatim occurrences and values normalised by rule are not represented; a value from a category points to the first category;
- print records stand in `sourceDesc`, which reads as "derived from", and the identity relation joins a description to a publication;
- the profile schema and the five tests accept most wrong documents a reviewer constructed, because they check page 212 only.

These faults are the work list of [Plan](plan.md), Delivery, which replaces the sampling tests by invariants over all records.

## Open

- The identifier scheme: `SZDKLA.<page>.<n>` is provisional until the operator decides how a publication is identified independently of the page it stands on ([Plan](plan.md), M2 Identifiers).
- Pages with a publication layer, which export one `biblStruct` per publication from the per-page files.
- Proposed and confirmed authority links (place, person, work), as `relation` while proposed and `@ref` once confirmed, and the link to the work index of Stefan Zweig Digital.
- Normalised forms beside the source spelling (`choice` with `orig` and `reg`).
- `szd-klawiter.xsl` and the RDF branch for `o:szd.klawiter` in the data repository of Stefan Zweig Digital.
- The sample object on which the profile is agreed; page 212 is the first, page 54 the one [Merged bibliography](print-wiki-merge.md) named.
