# Klawiter Bibliography — v2 Pipeline

Vollständige Extraktion und Strukturierung der Stefan-Zweig-Bibliographie (Klawiter) als JSON-LD.

## Status

| Metrik | Wert |
|--------|------|
| Extrahierte Einträge | 6.295 / 6.296 (99,99%) |
| Mojibake behoben | 61,1% → 0% |
| Entitätstypen | 16 klassifiziert, 0,1% "other" |
| Titel korrekt | ~97% (33 verbleibende Bracket-Titel) |
| Translator korrekt | 100% der extrahierten (35% Coverage) |
| JSON-LD | Strukturell valide, domänenspezifisches Vokabular |
| Frontend | Noch nicht implementiert (nur HTML-Skeleton) |

## Pipeline

```
working/zt_00–07 + zweig_part_01.sql
  ↓ 01_extract.py     — SQL-Dump + BLOB-Parsing ohne MySQL
  ↓ 02_fix_encoding.py — Mojibake-Reparatur (latin-1 → utf-8, zeilenweise)
  ↓ 03_parse_entries.py — Wiki-Markup → strukturierte Felder
  ↓ 04_classify.py     — Entitätstyp + Zeitperiode
  ↓ 05_to_jsonld.py    — JSON-LD Konversion (Gesamt + Einzeldateien)
  ↓ 06_validate.py     — Qualitätsreport
```

### Ausführen

```bash
# Vollständige Pipeline
python pipeline/run_pipeline.py

# Ab Schritt 3 (wenn Extraktion + Encoding schon gelaufen)
python pipeline/run_pipeline.py 3

# Schritte 2 bis 4
python pipeline/run_pipeline.py 2 4
```

### Voraussetzungen

- Python 3.10+
- Keine externen Abhängigkeiten (nur Standardbibliothek)
- Die Quelldateien in `../working/` (zt_00–07, zweig_part_01.sql)
- Kein MySQL nötig

## Output

| Datei | Beschreibung |
|-------|-------------|
| `data/output/klawiter.jsonld` | Gesamtdatensatz (6.296 Einträge, ~8 MB) |
| `data/output/entries/*.jsonld` | Einzeldateien pro Eintrag |
| `data/output/quality-report.json` | Validierungsergebnis |
| `frontend/data/klawiter.json` | Frontend-optimiertes JSON (4.751 Non-Redirects) |

## Datenmodell

Domänenspezifisches JSON-LD-Vokabular unter `klawiter:` Namespace.
Mapping zu Schema.org/Dublin Core/BibFrame ist als späterer Schritt vorgesehen.

### Entitätstypen

| Typ | Anzahl | Anteil |
|-----|--------|--------|
| redirect | 1.545 | 24,5% |
| secondary-literature | 1.406 | 22,3% |
| fiction | 1.118 | 17,8% |
| essay | 905 | 14,4% |
| historical-study | 535 | 8,5% |
| poetry | 275 | 4,4% |
| collected-works | 114 | 1,8% |
| correspondence | 109 | 1,7% |
| film | 92 | 1,5% |
| translation | 56 | 0,9% |
| drama | 43 | 0,7% |
| symposium | 39 | 0,6% |
| foreword | 36 | 0,6% |
| dramatic-reading | 18 | 0,3% |
| other | 4 | 0,1% |
| newspaper | 1 | 0,0% |

### Feldabdeckung (Non-Redirects, n=4.751)

| Feld | Coverage |
|------|----------|
| title | 100% |
| categories | 99,8% |
| fullBibliographicEntry | 99,3% |
| year | 93,2% |
| language | 89,4% |
| pageCount | 78,4% |
| location | 67,8% |
| translator | 35,1% |
| publisher | 34,5% |
| contentItems | 19,7% |
| seeAlso | 14,4% |
| reprints | 8,8% |
| translations | 3,7% |

## Bekannte Limitierungen

### Solide
- Extraktion: 99,99% — nur 1 von 6.296 Seiten fehlt
- Mojibake: 0% nach Fix (verifiziert mit Regex-Scan)
- Klassifikation: Regelbasiert, nur 4 Einträge unklassifiziert
- Pipeline ist idempotent (deterministische Schritte, keine Zufälligkeit)

### Ehrlich fragil
- **Publisher-Extraktion (35%)**: Nur 3 Regex-Muster, viele Verlage werden nicht erkannt
- **33 Bracket-Titel** bleiben, wo kein page_title als Fallback vorhanden ist
- **JSON-LD-Namespace** (`klawiter-rescue.github.io/vocab/`) existiert nicht als auflösbare URL
- **Nicht gegen JSON-LD-Processor validiert** (nur strukturelle JSON-Prüfung)
- **Frontend existiert noch nicht** — nur HTML-Datei ohne JavaScript

### Nicht im Scope
- Kein Ontologie-Mapping (Schema.org, BibFrame) — bewusst domänenspezifisch
- Kein serverseitiges Backend — alles Client-Side
- Keine MySQL-Abhängigkeit — direkte Datei-Extraktion
