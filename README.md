# Klawiter Bibliography

Extraktion und Strukturierung der Stefan-Zweig-Bibliographie (Dr. Randolph J. Klawiter, University of Notre Dame) aus einer stillgelegten MediaWiki-Datenbank als JSON-LD mit statischer Web-Oberfläche.

## Status

| Metrik | Wert |
|--------|------|
| Extrahierte Einträge | 6.295 / 6.296 (99,99%) |
| Mojibake behoben | 61,1% → 0% |
| Entitätstypen | 16 klassifiziert, 0,1% "other" |
| Feldabdeckung Titel | 100% |
| JSON-LD | Strukturell valide, `klawiter:` Namespace |
| Frontend | Statische Webseite (GitHub Pages) |

## Projektstruktur

```
pipeline/               Python-Pipeline (6 Stufen, keine externen Abhängigkeiten)
docs/                   Frontend (GitHub Pages) — statisches HTML/JS/CSS
data/
  raw/                  MediaWiki SQL-Dump + 8 BLOB-Dateien (363 MB)
  intermediate/         Pipeline-Zwischenschritte (CSV, gitignored)
  output/               JSON-LD Gesamtdatensatz + Einzeldateien
knowledge/              Projektdokumentation (Obsidian Vault)
```

## Pipeline

```
data/raw/zt_00–07 + zweig_part_01.sql
  ↓ 01_extract.py      SQL-Dump + BLOB-Parsing ohne MySQL
  ↓ 02_fix_encoding.py  Mojibake-Reparatur (Latin-1 → UTF-8)
  ↓ 03_parse_entries.py  Wiki-Markup → strukturierte Felder
  ↓ 04_classify.py      Entitätstyp + Zeitperiode
  ↓ 05_to_jsonld.py     JSON-LD Konversion
  ↓ 06_validate.py      Qualitätsreport
```

### Ausführen

```bash
# Vollständige Pipeline
python pipeline/run_pipeline.py

# Ab Schritt 3
python pipeline/run_pipeline.py 3

# Schritte 2 bis 4
python pipeline/run_pipeline.py 2 4
```

### Voraussetzungen

- Python 3.10+
- Keine externen Abhängigkeiten (nur Standardbibliothek)
- Quelldateien in `data/raw/` (zt_00–07, zweig_part_01.sql)

## Output

| Datei | Beschreibung |
|-------|-------------|
| `data/output/klawiter.jsonld` | Gesamtdatensatz (6.296 Einträge, ~8 MB) |
| `data/output/entries/*.jsonld` | Einzeldateien pro Eintrag |
| `data/output/quality-report.json` | Validierungsergebnis |
| `docs/data/klawiter.json` | Frontend-optimiertes JSON (4.751 Non-Redirects) |

## Frontend

Statische Webseite unter `docs/` (GitHub Pages):
- Volltextsuche (FlexSearch)
- Facettierung: Typ, Sprache, Zeitraum, Ort
- Dashboard mit Statistiken und Charts
- Deep-Linking pro Eintrag
- JSON-LD Export
- Kein Framework, kein Build-Step

## Dokumentation

Der `knowledge/`-Ordner bildet einen Obsidian Vault mit der gesamten Projektdokumentation:
Datenmodell, Pipeline, Encoding-Problem, Architekturentscheidungen, Ontologie, Reconciliation-Strategie u.a.

## Credits

Die Bibliographie wurde von **Dr. Randolph J. Klawiter** (University of Notre Dame) über Jahrzehnte kompiliert. Sie umfasst 6.296 Einträge zu Stefan Zweigs Werk — Erstausgaben, Übersetzungen, Sekundärliteratur, Verfilmungen, Korrespondenz — in über 40 Sprachen.

## Lizenz

*Noch zu klären — Rechte an den bibliographischen Daten müssen mit der University of Notre Dame abgestimmt werden.*
