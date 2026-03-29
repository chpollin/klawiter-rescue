# Reconciliation

Strategy for linking Klawiter bibliography entities to authority data: Wikidata, GND, VIAF, GeoNames. See [[plan#m5-semantic-enrichment--reconciliation]] for implementation tasks.

## Goal

Transform the bibliography from an isolated dataset into connected Linked Data by adding `schema:sameAs` links to established authority systems. This enables:
- Disambiguation (which "Fischer Verlag"? which "Leipzig"?)
- Cross-referencing with library catalogs, research databases, and other DH projects
- Integration with [[ui-design|Stefan Zweig Digital]] and the broader Zweig research ecosystem

## Target Authority Systems

| System | URI pattern | Covers | Access |
|--------|-----------|--------|--------|
| **Wikidata** | `wikidata.org/entity/Q...` | Works, persons, places, publishers | SPARQL, API |
| **GND** | `d-nb.info/gnd/...` | Persons, works, publishers (German-speaking) | lobid.org API |
| **VIAF** | `viaf.org/viaf/...` | Persons (international) | API, SPARQL |
| **GeoNames** | `geonames.org/...` | Places | API |

## Entities to Reconcile

### Works (highest priority)

Stefan Zweig's works have Wikidata entries (P50 = Q78491). Matching strategy:
- Extract unique work titles from the dataset
- Query Wikidata for all works by Zweig (via SPARQL)
- Fuzzy match extracted titles against Wikidata labels and aliases (multi-language)
- Manual review for ambiguous cases

**Expected coverage**: High for major works (Schachnovelle, Ungeduld des Herzens, etc.), lower for obscure editions and secondary literature.

### Persons

| Person type | Count | Authority | Strategy |
|-------------|-------|-----------|----------|
| Stefan Zweig | 1 | GND 118637479, Wikidata Q78491 | Hardcoded |
| Translators | ~500 unique names | GND, VIAF | Batch reconciliation |
| Authors of secondary lit | Unknown | GND, VIAF | Lower priority |

Translator names are extracted as plain strings. Challenges:
- Name variants (initials, married names)
- Non-Latin scripts (translators for Arabic, Chinese, Hindi editions)
- Ambiguity (common names)

### Places (~100 unique cities)

Publication locations are already extracted. Reconciliation is straightforward:
- Match against Wikidata (instance of Q515 = city)
- Most cities are well-known (Wien, Berlin, Paris, New York, Tokyo)
- Add Wikidata URI and optionally GeoNames ID

**Expected coverage**: 95%+ — the city list is mostly major cities.

### Publishers

Publisher names are the weakest field (34.5% extracted). Reconciliation:
- Match against GND corporate body records or Wikidata (instance of Q2085381 = publisher)
- Challenge: historical publishers may have been renamed, merged, or dissolved
- Focus on high-frequency publishers first (Insel-Verlag, S. Fischer, Bermann-Fischer)

**Expected coverage**: Moderate for major publishers, low for obscure ones.

## Tooling Options

### Option A: OpenRefine Reconciliation
- Mature tool with Wikidata reconciliation service built in
- Good for semi-automated matching with manual review
- Not easily scriptable in a pipeline

### Option B: Custom Python Script
- Full control, integrates into existing pipeline as step `07_enrich.py`
- Use Wikidata SPARQL endpoint + GND lobid.org API
- Store results as JSON mapping files (`data/mappings/works.json`, `data/mappings/persons.json`, etc.)
- Rerunnable and deterministic

### Option C: Hybrid
- Use OpenRefine for initial high-quality matching with manual review
- Export mappings as JSON
- Pipeline step reads mappings and applies them to JSON-LD output

**Recommended**: Option C — manual review is essential for quality, but the pipeline integration should be automated.

## Data Model Integration

Reconciled entities will be added to the JSON-LD output as `schema:sameAs`:

```json
{
  "@type": ["klawiter:FictionEntry", "schema:Book"],
  "klawiter:title": "Schachnovelle",
  "schema:sameAs": "http://www.wikidata.org/entity/Q213434",
  "klawiter:publisher": {
    "@type": "schema:Organization",
    "schema:name": "Bermann-Fischer Verlag",
    "schema:sameAs": "http://www.wikidata.org/entity/Q..."
  },
  "klawiter:location": {
    "@type": "schema:Place",
    "schema:name": "Stockholm",
    "schema:sameAs": "http://www.wikidata.org/entity/Q1754"
  }
}
```

This enriches flat strings into structured Linked Data objects.
