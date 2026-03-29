# Datenmodell

Domänenspezifisches JSON-LD-Vokabular unter dem Namespace `klawiter:` (`https://klawiter-rescue.github.io/vocab/`).

Bewusste Entscheidung gegen Schema.org/BibFrame als Primärvokabular — siehe [[Architekturentscheidungen]]. Mapping zu etablierten Ontologien ist als späterer Schritt vorgesehen.

## Beispiel-Eintrag

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

## Felder

### Kern
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `title` | string | Werktitel (bereinigt) |
| `originalTitle` | string | Originaltitel bei Übersetzungen |
| `entryType` | enum | Einer der 16 [[Entitaetstypen]] |
| `year` | integer | Publikationsjahr |
| `timePeriod` | enum | `pre-zweig`, `lifetime`, `post-wwii`, `late-20c`, `contemporary` |

### Publikation
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `publisher` | string | Verlagsname |
| `location` | string | Publikationsort |
| `language` | string | Sprache (Englisch, z.B. "German") |
| `languageCode` | string | ISO 639-1 (z.B. "de") |
| `pageCount` | integer | Seitenzahl |
| `translator` | string | Übersetzer/in |

### Klassifikation
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `categories` | string[] | MediaWiki-Kategorien |
| `mainCategory` | string | Oberkategorie |

### Beziehungen
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `seeAlso` | string[] | Querverweise |
| `reprints` | string[] | Nachdrucke |
| `translations` | string[] | Übersetzungen |
| `contentItems` | string[] | Inhaltsverzeichnis (bei Sammelwerken) |

### Provenienz
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `sourcePageId` | integer | MediaWiki page_id |
| `sourceTextId` | integer | Text-ID im BLOB |
| `sourceBlobId` | integer | BLOB-Datei (0–7) |

## Redirects

Redirects werden im Frontend als Map gespeichert: `{ "Alter Seitenname": target_page_id }`. Im JSON-LD-Gesamtdatensatz haben Redirects `klawiter:isRedirect: true` und `klawiter:redirectTarget`.

## Offenes Mapping

Mögliche Zuordnung zu Schema.org:

| klawiter | Schema.org |
|----------|-----------|
| `FictionEntry` | `schema:Book` |
| `EssayEntry` | `schema:Article` |
| `FilmEntry` | `schema:Movie` |
| `CorrespondenceEntry` | `schema:Message` |
| `title` | `schema:name` |
| `year` | `schema:datePublished` |
| `publisher` | `schema:publisher` |
| `language` | `schema:inLanguage` |
