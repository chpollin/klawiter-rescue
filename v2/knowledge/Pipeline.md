# Pipeline

Die Extraktions-Pipeline überführt die Rohdaten aus der [[MediaWiki-Datenbank]] in [[JSON-LD]]. Sie besteht aus 6 Stufen, läuft ohne MySQL und ist idempotent.

## Ablauf

```
working/zt_00–07 + zweig_part_01.sql
  ↓ 01_extract.py
  ↓ 02_fix_encoding.py
  ↓ 03_parse_entries.py
  ↓ 04_classify.py
  ↓ 05_to_jsonld.py
  ↓ 06_validate.py
```

## Stufen im Detail

### 01_extract.py — Extraktion

Parst den SQL-Dump (`zweig_part_01.sql`) und die 8 Binärdateien (`zt_00`–`zt_07`) direkt in Python. Kein MySQL nötig.

**Verknüpfungskette**: `zweig_page` → `page_latest` → `zweig_slots` → `slot_content_id` → `zweig_content` → `tt:XXXXX` → BLOB-Suche

**Ergebnis**: 6.295 von 6.296 Einträgen (99,99%)

### 02_fix_encoding.py — Encoding

Behebt das [[Encoding-Problem]] (Mojibake). Erkennt `Ã[\x80-\xbf]`-Sequenzen per Regex und repariert zeilenweise via `encode('latin-1').decode('utf-8')`.

**Ergebnis**: Von 61,1% betroffenen Einträgen auf 0%

### 03_parse_entries.py — Parsing

Extrahiert strukturierte Felder aus dem Wiki-Markup:
- Titel (aus `'''bold'''` oder page_title als Fallback)
- Jahr, Verlag, Ort, Seitenzahl, Übersetzer (via [[Regex-Patterns]])
- Kategorien, See-Also-Referenzen, Nachdrucke, Übersetzungen
- Sprache (aus Kategorie-Namen, z.B. "Poetry / Individual Poems (German)")

### 04_classify.py — Klassifikation

Ordnet jedem Eintrag einen der 16 [[Entitaetstypen]] zu (primär kategorie-basiert, mit Content-Fallback) und eine Zeitperiode.

### 05_to_jsonld.py — JSON-LD

Konvertiert die klassifizierten Einträge in das [[Datenmodell]]:
- `klawiter.jsonld` — Gesamtdatensatz
- `entries/*.jsonld` — Einzeldateien
- `klawiter.json` — Frontend-optimiert (ohne Redirects, kurze Keys)

### 06_validate.py — Validierung

Prüft JSON-LD-Struktur, Feldabdeckung, residuales Mojibake. Generiert `quality-report.json`.

## Ausführung

```bash
python pipeline/run_pipeline.py       # Alles
python pipeline/run_pipeline.py 3 6   # Ab Schritt 3
```

## Abhängigkeiten

Keine externen Pakete — nur Python 3.10+ Standardbibliothek.

## Laufzeit

~35 Sekunden (27s BLOB-Parsing, 8s Rest)
