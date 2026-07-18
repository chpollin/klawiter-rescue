---
title: Data
aliases: [data model, entity types]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
method:
  name: Promptotyping
  url: https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin
template:
  name: Vorlage Datengrundlage
  version: 0.1
  url: https://dhcraft.org/Promptotyping/promptotyping-document/data
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-data
status: complete
language: en
version: 0.3
tags: [data, quality]
created: 2026-03-29
updated: 2026-07-18
authors: [Christopher Pollin]
topics: ["[[Data Modelling]]", "[[Normdata]]", "[[Controlled Vocabularies]]"]
knowledge-sources:
  institutions:
    Stefan Zweig Centre Salzburg: https://www.stefanzweig.digital/
  standards:
    Schema.org: https://schema.org/
    Dublin Core Metadata Terms: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
    Wikidata: https://www.wikidata.org/
  vocabularies:
    klawiter namespace: https://chpollin.github.io/klawiter-rescue/vocab/
related: [about, pipeline, testing, production-readiness]
---

# Data

The Klawiter bibliography dataset: its model, entity types, field coverage, and known quality issues. Live coverage figures, distribution counts, and per-field provenance totals are reported in `data/output/quality-report.json`, the `_meta` block of `docs/data/klawiter.json`, and `.github/baseline-metrics.json`, which are the sources of truth this document does not duplicate.

## Data Model

Domain-specific JSON-LD vocabulary under the `klawiter:` namespace (`https://chpollin.github.io/klawiter-rescue/vocab/`), documented at `docs/vocab/index.html`.

### Vocabulary blend

The model blends Schema.org (standard bibliographic fields such as name, datePublished, publisher), Dublin Core (`bibliographicCitation` for the original entry text), and a custom `klawiter:` namespace for the entity types and fields without a Schema.org equivalent (for example "Dramatic Reading", "Symposium"). Each entry gets a `@type` array combining a Schema.org type with a `klawiter:` type, for example `["schema:Book", "klawiter:FictionEntry"]`. BIBFRAME (FRBR-based Work/Instance/Item) would be correct but overengineered for this dataset as a serialization, since it carries no official JSON-LD context; the conceptual Work/Edition split it expresses is realized where needed through `schema:workExample`/`exampleOfWork`, see [[production-readiness#zielmodell-werkausgabe-trennung]]. The trade-off of the blend is that the output is not directly machine-readable for library systems. The vocabulary is implemented in `pipeline/lib/vocabulary.py`.

### Example Entry

```json
{
  "@context": { "klawiter": "https://chpollin.github.io/klawiter-rescue/vocab/" },
  "@type": "klawiter:FictionEntry",
  "@id": "klawiter:entry/3",
  "klawiter:title": "Amok. Novellen einer Leidenschaft",
  "klawiter:entryType": "fiction",
  "klawiter:year": 1922,
  "klawiter:timePeriod": "lifetime",
  "klawiter:publisher": "Insel-Verlag",
  "klawiter:location": "Leipzig",
  "klawiter:language": "German",
  "klawiter:languageCode": "de",
  "klawiter:categories": ["Collected and Selected Works", "Fiction / Volumes (German)"],
  "klawiter:mainCategory": "Collected and Selected Works",
  "klawiter:contentItems": ["Der Amokläufer, pp. (9)-86", "..."],
  "klawiter:fullBibliographicEntry": "...",
  "klawiter:sourcePageId": 3,
  "klawiter:sourceTextId": 835,
  "klawiter:sourceBlobId": 0
}
```

### Fields

#### Core
| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Work title (cleaned) |
| `originalTitle` | string | Original title for translations |
| `entryType` | enum | One of 16 entity types (see below) |
| `year` | integer | Publication year |
| `timePeriod` | enum | `pre-zweig`, `lifetime`, `post-wwii`, `late-20c`, `contemporary` |

#### Publication
| Field | Type | Description |
|-------|------|-------------|
| `publisher` | string | Publisher name |
| `location` | string | Publication location |
| `locationSameAs` | IRI | Wikidata URI of the primary location (e.g. `http://www.wikidata.org/entity/Q90`); present when the location is reconciled |
| `language` | string | Language (English name, e.g. "German") |
| `languageCode` | string | ISO 639-1 (e.g. "de") |
| `pageCount` | integer | Page count |
| `translator` | string | Translator name |

#### Classification
| Field | Type | Description |
|-------|------|-------------|
| `categories` | string[] | MediaWiki categories |
| `mainCategory` | string | Primary category |

#### Relationships
| Field | Type | Description |
|-------|------|-------------|
| `seeAlso` | string[] | Cross-references |
| `reprints` | string[] | Reprint entries |
| `translations` | string[] | Translation entries |
| `contentItems` | string[] | Table of contents (for collected works) |

#### Provenance
| Field | Type | Description |
|-------|------|-------------|
| `sourcePageId` | integer | MediaWiki page_id |
| `sourceTextId` | integer | Text ID in BLOB |
| `sourceBlobId` | integer | BLOB file (0–7) |

### Provenance Metadata (`_provenance`)

Per-field extraction source tracking, injected by `inject_provenance.py`:
- `publisher`: "regex" | "llm" | "missing"
- `location`: "regex" | "llm" | "missing"
- `translator`: "regex" | "llm" | "missing"
- `pageCount`: "regex" | "llm" | "missing"

Coverage: 49.6% regex, 11.7% LLM, 38.8% missing (across 4 fields x 5,179 entries)

### Redirects

Redirects are stored as a map in the frontend: `{ "Old Page Name": target_page_id }`. In the full JSON-LD dataset, redirects have `klawiter:isRedirect: true` and `klawiter:redirectTarget`.

---

## Entity Types

16 classified types, derived from MediaWiki categories. Each maps to a Schema.org type paired with its `klawiter:` type, see [[#vocabulary-blend]].

### Distribution

| Type | Count | Share | Description |
|------|-------|-------|-------------|
| `redirect` | 1,545 | 24.5% | Redirect to another entry |
| `secondary-literature` | 1,406 | 22.3% | Criticism, studies, biographies about Zweig |
| `fiction` | 1,118 | 17.8% | Novels, novellas, short stories |
| `essay` | 905 | 14.4% | Essays, articles, reviews |
| `historical-study` | 535 | 8.5% | Dissertations, monographs |
| `poetry` | 275 | 4.4% | Individual poems, collections |
| `collected-works` | 114 | 1.8% | Collected/selected works, anthologies |
| `correspondence` | 109 | 1.7% | Letters, postcards |
| `film` | 92 | 1.5% | Film adaptations, operas, performances |
| `translation` | 56 | 0.9% | Zweig's translations of other authors |
| `drama` | 43 | 0.7% | Plays, libretti |
| `symposium` | 39 | 0.6% | Conferences, exhibitions |
| `foreword` | 36 | 0.6% | Forewords, afterwords, editorial contributions |
| `dramatic-reading` | 18 | 0.3% | Dramatic readings |
| `other` | 4 | 0.1% | Unclassifiable |
| `newspaper` | 1 | 0.0% | Newspaper article |

Counts above are `entry_type` classifications (from `.github/baseline-metrics.json`). The 1,545 `redirect` type count differs by one from the 1,546 records carrying the `isRedirect` flag (one redirect page is classified under another type); of those 1,546 redirects, 1,210 resolve to an existing entry in the frontend map (see [[pipeline#redirects-as-map-instead-of-resolved-entries]]).

### Classification Logic

1. **Redirects**: Entry begins with `#REDIRECT` → `redirect`
2. **Category mapping**: `main_category` → type (e.g. "Fiction" → `fiction`, "Secondary Literature" → `secondary-literature`)
3. **Content fallback**: Keywords in content (e.g. "novel" → `fiction`, "essay" → `essay`)
4. **Default**: `other`

### Time Periods

Each dated entry receives a time period:

| Period | Range | Count |
|--------|-------|-------|
| `pre-zweig` | before 1881 | 61 |
| `lifetime` | 1881–1942 | 1,124 |
| `post-wwii` | 1943–1980 | 867 |
| `late-20c` | 1981–2000 | 1,050 |
| `contemporary` | 2001+ | 1,327 |

### Language Distribution (Top 10)

| Language | Entries |
|----------|---------|
| German | ~1,050 |
| Chinese | ~510 |
| French | ~350 |
| English | ~270 |
| Spanish | ~260 |
| Arabic | ~210 |
| Russian | ~80 |
| Portuguese | ~70 |
| Italian | ~60 |
| Hindi | ~40 |

---

## Data Quality

All numbers refer to non-redirect entries (n=4,751) unless stated otherwise.

### Field Coverage

After regex extraction (step 03) + LLM enrichment (step 03b, Gemini 3.1 Flash Lite):

| Field | Coverage | Regex only | Improvement | Notes |
|-------|----------|------------|-------------|-------|
| title | 100.0% | 100.0% | — | 33 remaining bracket titles without page_title fallback |
| categories | 99.8% | 99.8% | — | 11 entries without category |
| fullBibliographicEntry | 99.3% | 99.3% | — | 32 entries with only category tag, no content |
| year | 93.2% | 93.2% | — | First match only, no range detection |
| language | 89.4% | 89.4% | — | Derived from category names (e.g. "(German)") |
| location | 87.5% | 67.8% | **+19.7pp** | LLM reads non-standard city names |
| pageCount | 53.3% | 51.0% | +2.3pp | Previously 81.6%, corrected after `pp. N-M` FPs (Session 11) + 12 outlier rejections (Session 15) |
| publisher | 52.2% | 34.5% | **+17.7pp** | LLM reads publishers; Session 15 normalization rejected 160 garbage entries |
| translator | 41.9% | 35.1% | +6.8pp | LLM reads abbreviations and non-English patterns |

**Precision**: All fields ≥99% real precision. Regex extractions have 100% precision. LLM extractions have 0 hallucinations (verified on 20-entry stratified sample + full-run FP analysis).

### Encoding

**Before**: 61.1% of entries had Mojibake — UTF-8 bytes misinterpreted as Latin-1. See [[pipeline#encoding-fix]] for details.

**After**: 0% known Mojibake — no entries match the `Ã[\x80-\xbf]|Â[\xa0-\xff]` detection regex. This verifies that the specific UTF-8-as-Latin-1 pattern is fully resolved. It does **not** guarantee all encoding is correct: other corruption types (double encoding, truncated multibyte chars, non-Mojibake misinterpretation, fix destroying intentional characters) are not checked.

**Honesty check**: The first encoding fix claimed "0%" but only tested 7 common patterns. Actually 9.1% (574 entries, 21 patterns) were still affected. The revised fix uses line-wise `encode('latin-1').decode('utf-8')` and is complete for the known Mojibake pattern.

### Known Problems

**Publisher extraction (52.2%)**: Regex covers 34.5% (3 pattern families), LLM adds +17.7pp net; Session 15 normalization then rejected 160 garbage values (raw regex+LLM coverage was 55.6%). The ~48% gap breaks down: 15-20% (~350 entries) legitimately missing (anthology poems, journal articles, see-also references — no publisher in source text). 80-85% (~1,750 entries) structural extraction failures (publisher present in implicit formats like `[[Collection]] [City, Year]` that regex doesn't match). Only 1.7% of entries without publisher contain publisher keywords. Poetry/Individual Poems: 80.7% gap — anthology entries structurally lack standalone publishers.

**Translator extraction (41.9%)**: Regex covers 35.1% with 0% false positives. LLM adds +6.8pp. Remaining ~58% are mostly German originals (no translator) or entries that don't name the translator. A newline-leaking bug in the translator regex (`\s` matching `\n`) was fixed — 34 translator fields previously contained trailing wiki markup from subsequent sections.

**Title precision**: verify.py previously reported 81.5% precision (880 false positives). Investigation showed these are page_title fallbacks — titles sourced from wiki metadata, correctly absent from raw content. verify.py now classifies these as `correct_fallback`. Actual title precision is ~95%+. Title extraction improved: `[year]:` patterns now search for second bold block as real title before falling back to page_title.

### Wikidata Reconciliation

382 geocoded locations in `docs/data/locations.json` are reconciled against Wikidata via the Reconciliation API (en + de endpoints) + SPARQL metadata. Coverage: 360/382 (94.2%) with Q-IDs. Script: `pipeline/reconcile_locations.py`. Log: `docs/data/locations_reconciliation_log.json`.

Fields added per location: `wikidataId` (Q-number), `wikidataLabel` (English name), `wikidataScore` (match confidence), `countryQid` (country Q-number from Wikidata). Ground truth fixture: `tests/wikidata_ground_truth.json` (20 entries). 6 deterministic tests in `tests/test_wikidata_locations.py`.

22 locations unmatched (encoding variants, composite slash-locations, obscure villages). 3 low-score matches flagged for manual review.

**Per-entry linking (`locationSameAs`)**: Step 05 maps each entry's primary location to its Wikidata URI and writes it as `klawiter:locationSameAs` (`@type: @id`) into both the JSON-LD and frontend JSON. Coverage: 4,013 of 4,162 located non-redirect entries (~96%); the gap is locations without a reconciled Q-ID. Only the primary `location` is linked, not `allLocations`.

**Bracket titles**: Collected-works entries with format `'''[1922]: Insel-Verlag, Leipzig'''` as bold line. Originally 33 without page_title fallback, reduced to ~15 after `remove_wiki_markup()` improvements (section header stripping, unpaired bold marker removal, magic word removal).

**originalTitle false positives (fixed)**: The `extract_original_title()` regex previously matched bare years in brackets (e.g. `[1931]`) as original titles, producing 272 false positives. Fixed by rejecting candidates that match `^\d{4}$`.

**1 stub entry**: page_id 2979 ("A unidade espiritual do mundo") — text_id 18046 not in any BLOB. Present in output as stub (sourcePageId + entryType only, no title/content). Root cause established by revision-history trace: the page has exactly three revisions (2014-06-24), and the latest one (rev 18324, the one `page_latest` points to) has `rev_len = 0` — the page was **blanked** three minutes after creation. The only non-empty revisions (18322, 18323) carry just a category tag (`[[Category:Essays / Individual Essays (Portuguese)]]`). No bibliographic content for this entry was ever preserved in the dump; this is source-side loss, not a pipeline parsing miss. The title "A unidade espiritual do mundo" survives in the `zweig_page` table. The editor decided (Forschungsleitstelle order 2026-06-21) to show it with the title rather than as a nameless stub. The fix is now in `03_parse_entries.py` (the empty-content early-return branch falls back to the cleaned `page_title`) and is locked by `tests/test_parse_entries.py`; it becomes visible in the output on the next full pipeline run, where it is regenerated together with the location and mojibake fixes. The census identity is unaffected: 2979 stays one displayed entry, now titled rather than nameless. See [[#record-census]].

**0 titles with markup residue** (Session 14): Fixed — orphaned `]]`/`[[`/`'''` cleanup in `remove_wiki_markup()`. 14 `__TOC__` titles fixed in Session 11.

**0 section-header titles** (Session 14): Fixed — "Contents:", "Volumes:", "German:", "See:", "Note:" etc. rejected with page_title fallback. Was 1,368 entries. 345 titles have encoding artifacts in page_title (Arabic/Cyrillic transliterations where the page_title has mojibake). 43 titles are >200 chars (encoding-guard cases — long extracted title preferred over mojibake page_title).

**111 German entries with translator** (found by test_consistency.py, Session 11): Regex false positives where author names, editors, or location text was extracted as translator (e.g. `translator: "Stefan Zweig. Leipzig"`).

**727 broken seeAlso references** (Session 14, was 1,140 in Session 11): Reduced because title fix resolved 1,210 redirects (was 430). Remaining 727 broken due to language suffixes like "/ Spanish" or formatting mismatches.

**427 multi-edition pages** (Session 14): 6.8% of wiki pages contain multiple publications. Publisher, pageCount, year extracted from first match — may come from wrong edition. See [[pipeline#known-limitations--multi-edition-pages]].

### Record Census

Where `verify.py` checks field *values* (false positives/negatives) and the quality report measures dataset completeness, `census.py` answers the completeness-of-records question the data rescue rests on: does every record reach the frontend from the SQL source, with nothing silently lost and nothing invented? It reconciles three layers — `01_extracted.csv` (source), `klawiter.jsonld` (Linked Data), `klawiter.json` (frontend) — and asserts the identities below (output: `data/output/census-report.json`, all five currently pass):

- **JSON-LD is 1:1 with the source**: 6,725 source pages, 6,725 JSON-LD entries, every `sourcePageId` present exactly once. No record lost, none invented, no duplicates.
- **Frontend = JSON-LD minus redirects**: 5,179 = 6,725 − 1,546. Redirects are correctly excluded from the frontend; 0 redirects leak into it.
- **Source ns0 reconciles**: 6,296 = 4,751 displayed entries + 1,545 ns0 redirects.
- **Empty-content pages are isolated and explained**: 4 source pages have no BLOB text row, of which exactly 1 is bibliographic (ns0 page 2979, the blanked stub above); the other 3 are non-bibliographic system pages (a `MediaWiki:Print.css`, an empty Armenian category, an image-description page). The census asserts that the set of empty bibliographic pages equals the set of unnamed displayed entries — currently the single page 2979.

The census is the systematic proof behind the headline "every entry safely and correctly from SQL into the frontend": the path is lossless and invention-free, and the only anomaly is one source-blanked page, fully characterized. The "unverifiable" surface that the [[frontend#eil-curation-interface|EIL editing interface]] targets is exactly what `verify.py` and the provenance metadata flag; the census guarantees the editor is working over a complete record set, not a leaky one.

### Quality Report

Automatically generated by `06_validate.py` → `data/output/quality-report.json`:
- 442 entries with info-level issues (missing fullBibliographicEntry)
- 4 warnings (residual encoding suspects)
- 0 errors

### Correction Protocol (Planned)

The EIL interface logs every editor action as a correction episode; the accumulated log is the correction protocol. It is documentation input for the qualitative DIA-XAI evaluation, not a metric. The measurable part of that evaluation is separate, the expert-verified gold standard against which extraction quality per field is described. Each logged episode records:

- **Action, field, provenance** — an Accept, Correct, or Add on a named field, tagged with the provenance the value carried before the edit (regex / llm / missing).
- **Entry type** — the record type the correction happened on (fiction, secondary literature, symposium, and so on).
- **Machine original and new value** — the pre-edit value and what the editor put in its place, preserved as a before/after pair.

The protocol supports two documentation uses. Qualitatively, systematic correction patterns are workshop findings, when editors repeatedly correct the same field on the same entry type, that is a signal to the developer that the pipeline has a fixable weakness there. As reference-building, the human-confirmed entries accumulate into the gold standard against which extraction quality per field is described. The protocol falls out as a byproduct of curation, every Accept/Correct/Add is logged with field, provenance, and entry type; no controlled experiment or time tracking is involved, and the log is not read as an effectiveness metric of the workflow. See [[about#dia-xai-connection]] for the evaluation frame.
