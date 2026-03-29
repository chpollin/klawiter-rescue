# Ontology

Semantic modeling strategy for the Klawiter bibliography. Current state: custom `klawiter:` namespace. Target: Schema.org where possible, domain-specific extensions where needed.

## Current State

### Namespace

`klawiter:` → `https://klawiter-rescue.github.io/vocab/`

This URL does not currently resolve. The namespace is used in all JSON-LD output but has no published vocabulary document. See [[plan#m4-ontology--data-model]] for the resolution plan.

### @context

```json
{
  "@context": {
    "klawiter": "https://klawiter-rescue.github.io/vocab/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "klawiter:year": { "@type": "xsd:integer" },
    "klawiter:pageCount": { "@type": "xsd:integer" },
    "klawiter:sourcePageId": { "@type": "xsd:integer" },
    "klawiter:sourceTextId": { "@type": "xsd:integer" },
    "klawiter:sourceBlobId": { "@type": "xsd:integer" },
    "klawiter:translationOf": { "@type": "@id" },
    "klawiter:reprintOf": { "@type": "@id" },
    "klawiter:seeAlso": { "@type": "@id", "@container": "@set" },
    "klawiter:categories": { "@container": "@set" },
    "klawiter:contentItems": { "@container": "@list" }
  }
}
```

### Why Custom Namespace

See [[architecture#1-domain-specific-vocabulary-instead-of-schemaorg]]. Key reasons:
- Entity types like "Dramatic Reading" and "Symposium" have no Schema.org equivalent
- BibFrame is overengineering for this dataset
- Dublin Core is too flat

---

## Schema.org Mapping

Planned mapping from `klawiter:` to `schema:` properties:

### Entry Types

| klawiter type | Schema.org type | Notes |
|---------------|----------------|-------|
| `fiction` | `schema:Book` | |
| `essay` | `schema:Article` | |
| `poetry` | `schema:Book` | Or `schema:CreativeWork` |
| `drama` | `schema:Play` | |
| `film` | `schema:Movie` | |
| `correspondence` | `schema:Message` | |
| `collected-works` | `schema:Collection` | |
| `secondary-literature` | `schema:ScholarlyArticle` | |
| `historical-study` | `schema:ScholarlyArticle` | |
| `translation` | `schema:Book` | With `schema:translationOfWork` |
| `foreword` | `schema:CreativeWork` | No specific type |
| `symposium` | `schema:Event` | Not a publication |
| `dramatic-reading` | `schema:CreativeWork` | **No Schema.org equivalent** |
| `newspaper` | `schema:NewsArticle` | |

### Fields

| klawiter field | Schema.org property | Notes |
|---------------|-------------------|-------|
| `title` | `schema:name` | |
| `year` | `schema:datePublished` | |
| `publisher` | `schema:publisher` | |
| `location` | `schema:locationCreated` | Or `schema:publisher.location` |
| `language` | `schema:inLanguage` | |
| `pageCount` | `schema:numberOfPages` | |
| `translator` | `schema:translator` | |
| `originalTitle` | `schema:translationOfWork.name` | |
| `seeAlso` | `schema:isRelatedTo` | |
| `entryType` | — | **Domain-specific, keep as `klawiter:`** |
| `timePeriod` | — | **Domain-specific, keep as `klawiter:`** |
| `contentItems` | `schema:hasPart` | Ordered list |
| `categories` | — | **MediaWiki-specific, keep as `klawiter:`** |
| `fullBibliographicEntry` | `schema:description` | Or `dcterms:bibliographicCitation` |
| `sourcePageId` | `dcterms:identifier` | Provenance |

---

## Target @context Design

The redesigned context will use multiple vocabularies:

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
    "klawiter": "https://klawiter-rescue.github.io/vocab/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "name": "schema:name",
    "datePublished": { "@id": "schema:datePublished", "@type": "xsd:gYear" },
    "publisher": "schema:publisher",
    "inLanguage": "schema:inLanguage",
    "numberOfPages": { "@id": "schema:numberOfPages", "@type": "xsd:integer" },
    "translator": "schema:translator",
    "sameAs": { "@id": "schema:sameAs", "@type": "@id" }
  }
}
```

This allows entries to be both `klawiter:FictionEntry` and `schema:Book` simultaneously via `@type` arrays.

---

## Namespace Resolution

The `klawiter:` namespace URL must resolve to a human-readable vocabulary document:

- **Location**: `docs/vocab/index.html`
- **Content**: List of all terms with definitions, types, and Schema.org equivalents
- **Format**: HTML (human-readable) — JSON-LD context document could be served separately

This makes the bibliography proper Linked Data: any consumer can follow the namespace URL to understand the vocabulary.

---

## Open Questions

- Should `@id` URIs use page_id or a slug? E.g. `klawiter:entry/3` vs `klawiter:entry/amok-novellen`
- Should redirects have their own `@id` or only exist as aliases?
- How to handle entries that are both `schema:Book` and `klawiter:FictionEntry`? Multiple `@type` values?
- Should authority data URIs (Wikidata, GND) go into the `@context` or only as `schema:sameAs` values?
