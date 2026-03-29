# Ontology

Semantic modeling for the Klawiter bibliography. Uses a blend of Schema.org (standard bibliographic), Dublin Core (citation/provenance), and klawiter: (domain-specific extensions).

## Vocabulary Blend

### Schema.org (`schema:`)
Standard bibliographic properties with universal web interoperability:

| Short Key | Maps To | Usage |
|-----------|---------|-------|
| `name` | `schema:name` | Entry title |
| `author` | `schema:author` | Author (Stefan Zweig with Wikidata `sameAs`) |
| `datePublished` | `schema:datePublished` | Publication year |
| `publisher` | `schema:publisher` | Publisher name |
| `locationCreated` | `schema:locationCreated` | Place of publication |
| `inLanguage` | `schema:inLanguage` | Language of the work |
| `numberOfPages` | `schema:numberOfPages` | Page count (xsd:integer) |
| `translator` | `schema:translator` | Translator name |
| `isRelatedTo` | `schema:isRelatedTo` | Cross-references ("see also") |
| `workTranslation` | `schema:workTranslation` | Translation references |
| `hasPart` | `schema:hasPart` | Table of contents / constituent works |
| `sameAs` | `schema:sameAs` | Authority URIs (Wikidata, GND, VIAF) |

### Dublin Core (`dcterms:`)
Citation and provenance:

| Short Key | Maps To | Usage |
|-----------|---------|-------|
| `bibliographicCitation` | `dcterms:bibliographicCitation` | Full original bibliographic entry text |

### Domain-Specific (`klawiter:`)
Properties with no Schema.org or DC equivalent:

| Short Key | Full IRI | Usage |
|-----------|----------|-------|
| `entryType` | `klawiter:entryType` | Classification key (fiction, essay, drama, etc.) |
| `timePeriod` | `klawiter:timePeriod` | Historical period (pre-zweig, lifetime, etc.) |
| `categories` | `klawiter:categories` | MediaWiki categories (@set) |
| `mainCategory` | `klawiter:mainCategory` | Primary category for classification |
| `originalTitle` | `klawiter:originalTitle` | Original-language title |
| `languageCode` | `klawiter:languageCode` | ISO 639-1 language code |
| `allYears` | `klawiter:allYears` | All years in multi-edition entries |
| `allLocations` | `klawiter:allLocations` | All publication locations |
| `reprints` | `klawiter:reprints` | Reprint references (@set) |
| `contentItems` | `klawiter:contentItems` | ToC for collected works (@list) |
| `sourcePageId` | `klawiter:sourcePageId` | MediaWiki page ID (xsd:integer) |
| `sourceTextId` | `klawiter:sourceTextId` | MediaWiki text revision ID |
| `sourceBlobId` | `klawiter:sourceBlobId` | BLOB file number (0-7) |
| `pageNamespace` | `klawiter:pageNamespace` | MediaWiki namespace |
| `isRedirect` | `klawiter:isRedirect` | Redirect flag |
| `redirectTarget` | `klawiter:redirectTarget` | Redirect target title |

---

## Namespace

`klawiter:` resolves to `https://klawiter-rescue.github.io/vocab/`

This URL serves a human-readable vocabulary document at `docs/vocab/index.html` listing all domain-specific terms with definitions, types, and Schema.org equivalents.

---

## @context

Defined in `pipeline/lib/vocabulary.py`:

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
    "klawiter": "https://klawiter-rescue.github.io/vocab/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "name": "schema:name",
    "datePublished": "schema:datePublished",
    "publisher": "schema:publisher",
    "inLanguage": "schema:inLanguage",
    "numberOfPages": { "@id": "schema:numberOfPages", "@type": "xsd:integer" },
    "translator": "schema:translator",
    "locationCreated": "schema:locationCreated",
    "sameAs": { "@id": "schema:sameAs", "@type": "@id" },
    "isRelatedTo": { "@id": "schema:isRelatedTo", "@container": "@set" },
    "workTranslation": { "@id": "schema:workTranslation", "@container": "@set" },
    "hasPart": { "@id": "schema:hasPart", "@container": "@list" },
    "author": { "@id": "schema:author", "@type": "@id" },
    "bibliographicCitation": "dcterms:bibliographicCitation",
    "entryType": "klawiter:entryType",
    "timePeriod": "klawiter:timePeriod",
    "categories": { "@id": "klawiter:categories", "@container": "@set" },
    "contentItems": { "@id": "klawiter:contentItems", "@container": "@list" },
    "mainCategory": "klawiter:mainCategory",
    "originalTitle": "klawiter:originalTitle",
    "languageCode": "klawiter:languageCode",
    "allYears": "klawiter:allYears",
    "allLocations": "klawiter:allLocations",
    "reprints": { "@id": "klawiter:reprints", "@container": "@set" },
    "sourcePageId": { "@id": "klawiter:sourcePageId", "@type": "xsd:integer" },
    "sourceTextId": { "@id": "klawiter:sourceTextId", "@type": "xsd:integer" },
    "sourceBlobId": { "@id": "klawiter:sourceBlobId", "@type": "xsd:integer" },
    "pageNamespace": "klawiter:pageNamespace",
    "isRedirect": "klawiter:isRedirect",
    "redirectTarget": "klawiter:redirectTarget"
  }
}
```

---

## Entry Types & @type Mapping

Each entry gets a `@type` array combining Schema.org and klawiter: types:

| Entry Type Key | @type Array | Description |
|----------------|-------------|-------------|
| `fiction` | `[schema:Book, klawiter:FictionEntry]` | Novels, novellas, stories |
| `essay` | `[schema:Article, klawiter:EssayEntry]` | Essays, articles, reviews |
| `poetry` | `[schema:CreativeWork, klawiter:PoetryEntry]` | Poems, collections |
| `drama` | `[schema:Play, klawiter:DramaEntry]` | Plays, libretti |
| `film` | `[schema:Movie, klawiter:FilmEntry]` | Film adaptations |
| `correspondence` | `[schema:Message, klawiter:CorrespondenceEntry]` | Letters |
| `collected-works` | `[schema:Collection, klawiter:CollectedWorksEntry]` | Anthologies |
| `secondary-literature` | `[schema:ScholarlyArticle, klawiter:SecondaryLiteratureEntry]` | Scholarship about Zweig |
| `historical-study` | `[schema:ScholarlyArticle, klawiter:HistoricalStudyEntry]` | Academic studies |
| `translation` | `[schema:Book, klawiter:TranslationEntry]` | Zweig translating others |
| `foreword` | `[schema:CreativeWork, klawiter:ForewordEntry]` | Forewords, afterwords |
| `symposium` | `[schema:Event, klawiter:SymposiumEntry]` | Conferences, exhibitions |
| `dramatic-reading` | `[schema:CreativeWork, klawiter:DramaticReadingEntry]` | Performance readings |
| `newspaper` | `[schema:NewsArticle, klawiter:NewspaperEntry]` | News articles |
| `redirect` | `[klawiter:RedirectEntry]` | MediaWiki redirect |
| `other` | `[schema:CreativeWork, klawiter:OtherEntry]` | Unclassified |

---

## Author Modeling

Primary works include Stefan Zweig as structured author with Wikidata link:

```json
{
  "author": {
    "@type": "schema:Person",
    "name": "Stefan Zweig",
    "sameAs": "https://www.wikidata.org/entity/Q78491"
  }
}
```

Secondary literature, historical studies, and symposia omit the author field (Zweig is the subject, not the author).

---

## Design Rationale

### Why Schema.org + klawiter: (not BIBFRAME or CIDOC-CRM)?

- **BIBFRAME**: No official JSON-LD context from Library of Congress (showstopper for JSON-LD-first project). Work/Instance/Item hierarchy adds complexity without benefit for a publication bibliography.
- **CIDOC-CRM / LRMoo**: LRMoo v1.0 (April 2024) has no production-ready JSON-LD tooling. Event-centric modeling is conceptual overkill for bibliographic records.
- **Schema.org**: Official JSON-LD context, search engine visibility, covers ~80% of fields natively (`workTranslation`, `hasPart`, `translator`, `numberOfPages`).
- **klawiter:**: Clean extension point for domain-specific types (dramatic-reading, symposium) and MediaWiki provenance.

### Future Alignment

- **Stefan Zweig Digital** (Uni Graz): Uses CIDOC-CRM. A separate research project is planned to develop a Nachlass ontology that bridges both projects. The current `@type` arrays and `sameAs` links provide extension points for CIDOC-CRM alignment without restructuring.
- **Wikidata**: Reconciliation of works (P50=Q78491), persons (translators), places, and publishers is planned (see [[reconciliation]]). Authority URIs will be added as `schema:sameAs` values.

---

## Frontend JSON Mapping

The frontend (`docs/data/klawiter.json`) uses short keys for efficiency. `make_frontend_entry()` in step 05 maps semantic keys back to frontend keys:

| JSON-LD Key | Frontend Key |
|-------------|-------------|
| `name` | `title` |
| `datePublished` | `year` (as integer) |
| `locationCreated` | `location` |
| `inLanguage` | `language` |
| `numberOfPages` | `pageCount` |
| `bibliographicCitation` | `fullBibliographicEntry` |
| `isRelatedTo` | `seeAlso` |
| `workTranslation` | `translations` |
| `hasPart` | `contentItems` |

All other keys pass through unchanged.
