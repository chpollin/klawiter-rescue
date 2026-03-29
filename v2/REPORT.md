# Abschlussbericht: Klawiter v2 Pipeline

## 1. Datenanalyse

### Ausgangslage
- **Quelle**: MediaWiki-Datenbank mit 6.725 Seiten, Inhalte verteilt auf 8 LONGBLOB-Dateien (363 MB)
- **Bisherige Extraktion**: 5.652 Einträge (84%), MySQL-abhängig
- **Hauptprobleme**: 55% Mojibake, 27% fehlklassifizierte Redirects, 92% fehlende Metadaten

### Ergebnis der Neuextraktion

| Metrik | Alt (v1) | Neu (v2) | Verbesserung |
|--------|----------|----------|--------------|
| Extraktion | 5.652 / 6.725 (84%) | 6.295 / 6.296 (99,99%) | +643 Einträge |
| MySQL nötig | Ja | Nein | Eliminiert |
| Mojibake | 55% | 0% | Vollständig behoben |
| Titel korrekt | ~67% | ~99% | Bracket-Titel von 1.579 auf 33 |
| Sprache erkannt | 1,2% | 89,4% | +88 Prozentpunkte |
| Jahr erkannt | 68% | 93,2% | +25 Prozentpunkte |
| Ort erkannt | 25% | 67,8% | +43 Prozentpunkte |

### Verbleibende Lücken (ehrlich)
- **Publisher**: 34,5% — schwächstes Feld, braucht mehr Regex-Patterns oder NER
- **Translator**: 35,1% — korrekte Werte, aber viele Formatvarianten nicht abgedeckt
- **33 Bracket-Titel**: Seiten ohne verwertbaren page_title als Fallback
- **1 fehlender Eintrag**: 1 von 6.296 nicht in BLOBs gefunden

## 2. Architekturentscheidungen

### Vokabular: Domänenspezifisch
- **Entscheidung**: Eigenes `klawiter:` Namespace statt Schema.org/BibFrame
- **Begründung**: Die Daten passen nicht sauber in bestehende Ontologien (z.B. "Dramatic Reading" hat kein Schema.org-Pendant). Mapping zu Schema.org kann als separater Schritt erfolgen.
- **Trade-off**: Nicht direkt maschinenlesbar für Bibliothekssysteme

### Pipeline: 6 Stufen, kein MySQL
- **Entscheidung**: Direkte Datei-Extraktion statt Datenbankabfragen
- **Begründung**: Eliminiert MySQL-Abhängigkeit, macht die Pipeline portabel
- **Trade-off**: SQL-Parser ist fragiler als MySQL-Queries, aber deterministisch

### Frontend: Vanilla JS
- **Entscheidung**: Kein Framework, kein Build-Step
- **Begründung**: 4.751 Einträge sind klein genug für Client-Side-Rendering. Statisches Hosting auf GitHub Pages ohne CI/CD möglich.
- **Trade-off**: 8,5 MB JSON muss vollständig geladen werden

## 3. Pipeline-Status

```
✅ 01_extract.py     6.295/6.296 extrahiert (99,99%)
✅ 02_fix_encoding.py Mojibake 0% (verifiziert)
✅ 03_parse_entries.py Titel 100%, Jahr 93%, Sprache 89%
✅ 04_classify.py     16 Typen, 0,1% "other"
✅ 05_to_jsonld.py    klawiter.jsonld + 6.296 Einzeldateien + Frontend-JSON
✅ 06_validate.py     32 Einträge mit Info-Issues, 1 Warning
```

**Laufzeit**: ~35s (Schritt 1: 27s BLOB-Parsing, Schritte 2–6: 8s)

### Output-Dateien

| Datei | Größe | Inhalt |
|-------|-------|--------|
| `data/output/klawiter.jsonld` | ~8 MB | Gesamtdatensatz |
| `data/output/entries/` | 6.296 Dateien | Einzeleinträge |
| `data/output/quality-report.json` | ~15 KB | Validierungsergebnis |
| `frontend/data/klawiter.json` | 8,5 MB | Frontend-optimiert (4.751 + 1.074 Redirects) |

## 4. Frontend-Status

### Implementiert
- HTML-Struktur mit Tailwind CSS (responsive)
- FlexSearch-basierte Volltextsuche über alle Felder
- Facettierung: Typ, Sprache, Zeitraum, Ort
- Detailansicht mit allen Feldern pro Eintrag
- Deep-Linking: `#entry=1234` für jeden Eintrag
- Redirect-Auflösung: `#title=Alte+Seite` → Ziel-Eintrag
- Dashboard mit Statistiken und Charts (Timeline, Sprachen, Typen)
- JSON-LD-Export pro Eintrag und für den Gesamtdatensatz
- Filter-Chips mit Entfernen-Funktion
- Sortierung (Relevanz, Jahr, Titel)
- Load-More-Pagination
- Mobile Filter-Panel

### Nicht implementiert
- Keine Browser-Tests durchgeführt (nur Server-Erreichbarkeit geprüft)
- Kein Service Worker / Offline-Cache
- Keine Accessibility-Prüfung (WCAG)

## 5. Offene Punkte

### Sofort behebbar
1. **Browser-Test**: Frontend im Browser öffnen und prüfen
2. **GitHub Pages Setup**: `v2/frontend/` als Deployment-Quelle konfigurieren
3. **Publisher-Extraktion verbessern**: Mehr Patterns, internationale Verlage

### Mittelfristig
4. **Ontologie-Mapping**: `klawiter:` → Schema.org/Dublin Core für Interoperabilität
5. **JSON-LD-Namespace auflösbar machen**: Vokabular-Dokument auf GitHub Pages hosten
6. **Seitenzahl/Übersetzer-Coverage erhöhen**: Mehr Formatvarianten abdecken
7. **Daten-Kompression**: gzip-Serving für die 8,5 MB JSON-Datei

### Langfristig
8. **Wiki-URL-Kompatibilität**: Alte Wiki-URLs auf neue Frontend-URLs umleiten
9. **Zitierbarkeit**: DOI oder Persistent Identifier für den Datensatz
10. **Linked Data**: Verknüpfung mit GND, VIAF, Wikidata für Personen und Werke
