# Data

The Klawiter bibliography dataset: its model, entity types, field coverage, and known quality issues.

## Data Model

Domain-specific JSON-LD vocabulary under the `klawiter:` namespace (`https://klawiter-rescue.github.io/vocab/`). See [[architecture]] for the rationale behind a custom namespace vs Schema.org. See [[ontology]] for the planned mapping to established vocabularies.

### Example Entry

```json
{
  "@context": { "klawiter": "https://klawiter-rescue.github.io/vocab/" },
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

| Field | Coverage | Notes |
|-------|----------|-------|
| title | 100.0% | 33 remaining bracket titles without page_title fallback |
| categories | 99.8% | 11 entries without category |
| fullBibliographicEntry | 99.3% | 32 entries with only category tag, no content |
| year | 93.2% | First match only, no range detection |
| language | 89.4% | Derived from category names (e.g. "(German)") |
| pageCount | 78.4% | Pattern: `\d+ p.` and variants |
| location | 67.8% | Matched against list of ~100 known cities |
| translator | 35.1% | Only explicit "Translated by Name" patterns |
| publisher | 34.5% | Weakest field — only 3 regex families |

### Encoding

**Before**: 61.1% of entries had Mojibake — UTF-8 bytes misinterpreted as Latin-1. See [[pipeline#encoding-fix]] for details.

**After**: 0% residual Mojibake (verified via `Ã[\x80-\xbf]` regex scan across all entries).

**Honesty check**: The first encoding fix claimed "0%" but only tested 7 common patterns. Actually 9.1% (574 entries, 21 patterns) were still affected. The revised fix uses line-wise `encode('latin-1').decode('utf-8')` and is complete.

### Known Problems

**Publisher extraction (34.5%)**: Only 3 regex families: `Verlag|Publisher|Press`, `published by`, and name patterns. Many international publishers are not recognized. Improvement needs more patterns or Named Entity Recognition.

**Translator extraction (35.1%)**: Deliberate trade-off: the old extraction had 69% coverage but 46% false positives. The current one has 0% false positives at 35% coverage. Missing patterns: non-Latin scripts, unusual phrasings.

**33 bracket titles**: Collected-works entries with format `'''[1922]: Insel-Verlag, Leipzig'''` as bold line. For 33 of these, no usable page_title exists as fallback.

**1 missing entry**: 1 of 6,296 pages could not be found in any of the 8 BLOBs.

### Quality Report

Automatically generated by `06_validate.py` → `data/output/quality-report.json`:
- 32 entries with info-level issues (missing fullBibliographicEntry)
- 1 warning (residual encoding suspect)
- 0 errors
