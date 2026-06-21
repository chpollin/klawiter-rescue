---
title: Field-Level Validation
aliases: [validation, spot-check, M3.8, field fidelity]
tags: [validation, quality, eil]
created: 2026-06-21
updated: 2026-06-21
---

# Field-Level Validation

Findings from a field-level fidelity check of the live frontend against the source text shown per entry, Session 17 (2026-06-21). This is the manual-validation work package M3.8. Record-level completeness is already proven separately (no entry lost or invented, see [[data#record-census]]); this document checks the complementary question, whether the structured field values match the raw wiki source. The check uses the frontend itself, because each entry displays its full bibliographic source text directly beneath the extracted fields, so the source is the evidence on the same screen.

## Summary

The pipeline is correct on the common case, a single-edition page, and the extracted fields then match the source. The errors concentrate in four classes, three of them systematic and one a single unrecoverable record. The dominant field-level failure is the multi-edition page, where one wiki page holds several publications and the flat extraction pulls each field from a different part. A second systematic class is a location extracted from chapter titles rather than the publication line. The provenance badges (regex / llm / missing) and the per-entry source text make every one of these visible without leaving the detail view, which is the uncertainty surface the editing tool builds on.

## Provenance distribution (snapshot)

Across the 4,751 real bibliographic records (namespace 0), how each tracked field was produced:

| Field | regex | llm | missing |
|---|---|---|---|
| publisher | 1478 | 1001 | 2272 |
| location | 3221 | 937 | 593 |
| translator | 1665 | 325 | 2761 |
| pageCount | 2350 | 180 | 2221 |

Publisher is regex-extracted for under a third of records and missing for nearly half; translator is missing for most. This is the field-level uncertainty the record-level completeness proof does not touch, and it is what the expert curation addresses.

## Error class 1: location from chapter titles ("Weimar")

48 records carry location "Weimar", almost all non-German editions (Russian 16, Chinese 6, Spanish 4, Croatian 3, Bulgarian 3, and others). A Chinese or Russian Zweig edition is not published in Weimar. Root cause, visible in entry 804: the location extractor matches a city name anywhere in the text, including inside a chapter title. "Sternstunden der Menschheit" contains the chapter "Die Marienbader Elegie. Goethe zwischen Karlsbad und Weimar", and that word "Weimar" appears in the contents of every translation of the work, which is why the affected records are overwhelmingly Sternstunden translations.

- Entry 804 (Armenian): location "Weimar", source publication line says Yerevan.
- Entry 87 (Chinese): location "Weimar, New York", source publication line says Taiyuan/Xi'an.

The error propagates into the LOD layer, because the Wikidata reconciliation then links "Weimar" to its entity. Scoped Strand-1 fix: constrain location extraction to the publication-line position rather than the whole entry text, then re-run and diff. This is a fidelity-restoration fix, not an editorial change.

## Error class 2: multi-edition flattening

A wiki page can be a container for several publications (the German edition, the original edition, excerpts, reprints, and translations into several languages). The pipeline treats each page as one flat record and draws each field from a different part of the page. Entry 11 ("Collected Works:") is the worst case observed: every structured field is wrong while the full source text below is complete and correct.

- Title: "Collected Works:" (a section header, not a title).
- Publisher: "Company and London: Constable and Company" (a fragment of the English translation's publisher line).
- Location: ten cities stacked (Frankfurt am Main, Leipzig, Berlin, Wien, München, Stuttgart, Darmstadt, New York, London, Paris).
- pageCount: 274 (the English translation's page count, not the German edition's 323).
- Translator: "Stefan Zweig. Leipzig" (Zweig is the author, not the translator).

This is the known multi-edition limitation (427 pages, 6.8%, see [[pipeline#known-limitations--multi-edition-pages]] and [[testing#f-semantic--is-the-value-correct]]). It is the dominant field-level error class and the main open question for the editing tool, because per-hand correction, flag-and-defer, and a separate decomposition project are genuinely different scopes.

## Error class 3: surviving title mojibake

Encoding repair removed the gross mojibake at the field level (no replacement characters remain in title, publisher, location, translator), but transliterated titles still carry double-encoded artifacts. Entry 804's title reads "Mardkutâyan asteghayin zhamerÄ", where the â is a double-encoded transliteration apostrophe and the Ä a double-encoded diacritic. The full source text of such entries shows the same artifacts throughout. This matches the roughly 345 titles with encoding artifacts that the heuristic tests already bound ([[testing#f-semantic--is-the-value-correct]]). These are fidelity errors the pipeline introduced, in scope for restoration, but the title is not currently an editable field.

## Error class 4: the blanked stub (2979)

Entry 2979 surfaces as an "Untitled" record in the "Other" category with no fields. Its source page was blanked at the source (rev_len 0), so there is nothing to extract, the census already isolates it as the single anomaly, and it is unrecoverable from the dump (see [[data#record-census]]). It is not an extraction error, it is a faithful representation of an empty source page.

## What works (positive control)

The pipeline is correct on single-edition pages, which are the majority. Entry 3 ("Amok. Novellen einer Leidenschaft") is a clean Insel-Verlag first edition whose fields match the source. Entry 804, despite its title mojibake and wrong location, has a correct LLM-inferred translator (Levon Hakhverdian, matching "with an afterword by Levon Hakhverdian" in the source), which shows the enrichment step working. The validation surfaces the errors, it does not suggest the extraction is broadly wrong.

## Implications for the editing tool

The four currently editable fields (publisher, location, translator, pageCount) do not cover the observed Strand-1 errors. Title repair (classes 2 and 3) requires the title to be editable, and the multi-edition class requires a decision on scope before the tool invests in it. The systematic classes also feed the triage signal, because a record whose location is "Weimar" or whose title is a section header is a high-attention case the surface can rank automatically (see [[eil-editing#the-uncertainty-surface]]).

## Method and limits

This is a targeted, not exhaustive, pass: it confirms the error classes and their mechanisms against named example entries, and quantifies the Weimar class fully. It does not yet measure a per-field error rate across a stratified sample, which is the remaining part of M3.8 and the calibration input the triage signal needs.

## Related

- [[data#record-census]] — the record-level completeness proof this complements
- [[testing#f-semantic--is-the-value-correct]] — the heuristic and ground-truth layers that bound these classes
- [[pipeline#known-limitations--multi-edition-pages]] — the multi-edition limitation
- [[eil-editing]] — the editing surface these findings shape
