# Data

The Klawiter bibliography dataset: its model, entity types, field coverage, and known quality issues.

## Data Model

Domain-specific JSON-LD vocabulary under the `klawiter:` namespace (`https://chpollin.github.io/klawiter-rescue/vocab/`). See [[architecture]] for the rationale behind a custom namespace vs Schema.org. See [[ontology]] for the planned mapping to established vocabularies.

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

16 classified types, derived from MediaWiki categories. See [[ontology]] for Schema.org mapping.

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
| pageCount | 54.1% | 51.0% | +3.1pp | Previously 81.6%, corrected after `pp. N-M` page range FPs removed (Session 11) |
| publisher | 55.6% | 34.5% | **+21.1pp** | LLM reads publishers without "Verlag/Press" markers |
| translator | 41.9% | 35.1% | +6.8pp | LLM reads abbreviations and non-English patterns |

**Precision**: All fields ≥99% real precision. Regex extractions have 100% precision. LLM extractions have 0 hallucinations (verified on 20-entry stratified sample + full-run FP analysis).

### Encoding

**Before**: 61.1% of entries had Mojibake — UTF-8 bytes misinterpreted as Latin-1. See [[pipeline#encoding-fix]] for details.

**After**: 0% known Mojibake — no entries match the `Ã[\x80-\xbf]|Â[\xa0-\xff]` detection regex. This verifies that the specific UTF-8-as-Latin-1 pattern is fully resolved. It does **not** guarantee all encoding is correct: other corruption types (double encoding, truncated multibyte chars, non-Mojibake misinterpretation, fix destroying intentional characters) are not checked.

**Honesty check**: The first encoding fix claimed "0%" but only tested 7 common patterns. Actually 9.1% (574 entries, 21 patterns) were still affected. The revised fix uses line-wise `encode('latin-1').decode('utf-8')` and is complete for the known Mojibake pattern.

### Known Problems

**Publisher extraction (55.6%)**: Regex covers 34.5% (3 pattern families), LLM adds +21.1pp. The ~44% gap breaks down: 15-20% (~350 entries) legitimately missing (anthology poems, journal articles, see-also references — no publisher in source text). 80-85% (~1,750 entries) structural extraction failures (publisher present in implicit formats like `[[Collection]] [City, Year]` that regex doesn't match). Only 1.7% of entries without publisher contain publisher keywords. Poetry/Individual Poems: 80.7% gap — anthology entries structurally lack standalone publishers.

**Translator extraction (41.9%)**: Regex covers 35.1% with 0% false positives. LLM adds +6.8pp. Remaining ~58% are mostly German originals (no translator) or entries that don't name the translator. A newline-leaking bug in the translator regex (`\s` matching `\n`) was fixed — 34 translator fields previously contained trailing wiki markup from subsequent sections.

**Title precision**: verify.py previously reported 81.5% precision (880 false positives). Investigation showed these are page_title fallbacks — titles sourced from wiki metadata, correctly absent from raw content. verify.py now classifies these as `correct_fallback`. Actual title precision is ~95%+. Title extraction improved: `[year]:` patterns now search for second bold block as real title before falling back to page_title.

**Bracket titles**: Collected-works entries with format `'''[1922]: Insel-Verlag, Leipzig'''` as bold line. Originally 33 without page_title fallback, reduced to ~15 after `remove_wiki_markup()` improvements (section header stripping, unpaired bold marker removal, magic word removal).

**originalTitle false positives (fixed)**: The `extract_original_title()` regex previously matched bare years in brackets (e.g. `[1931]`) as original titles, producing 272 false positives. Fixed by rejecting candidates that match `^\d{4}$`.

**1 stub entry**: page_id 2979 ("A unidade espiritual do mundo") — text_id 18046 not in any BLOB. Present in output as stub (sourcePageId + entryType only, no title/content).

**20 titles with markup residue** (found by test_schema.py, Session 11): 14 entries have `__TOC__` as their title (title extraction fell through to magic word), 6 entries have unclosed `]]` or `[[` wiki links in titles. Pipeline bug in `extract_title()`.

**111 German entries with translator** (found by test_consistency.py, Session 11): Regex false positives where author names, editors, or location text was extracted as translator (e.g. `translator: "Stefan Zweig. Leipzig"`).

**717 broken seeAlso references** (found by test_consistency.py, Session 11): 717 of 1,213 cross-references don't match any entry title or redirect target. Partially a matching problem — reference strings include language suffixes like "/ Spanish" or formatting that doesn't match clean titles.

### Quality Report

Automatically generated by `06_validate.py` → `data/output/quality-report.json`:
- 32 entries with info-level issues (missing fullBibliographicEntry)
- 1 warning (residual encoding suspect)
- 0 errors
