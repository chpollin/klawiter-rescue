# Datenqualität

Stand nach der v2 [[Pipeline]]-Verarbeitung. Alle Zahlen beziehen sich auf Non-Redirect-Einträge (n=4.751), sofern nicht anders angegeben.

## Feldabdeckung

| Feld | Coverage | Anmerkung |
|------|----------|-----------|
| title | 100,0% | 33 verbleibende Bracket-Titel ohne page_title-Fallback |
| categories | 99,8% | 11 Einträge ohne Kategorie |
| fullBibliographicEntry | 99,3% | 32 Einträge nur mit Kategorie-Tag, kein Inhalt |
| year | 93,2% | Nur erstes Match, keine Bereichserkennung |
| language | 89,4% | Aus Kategorie-Namen abgeleitet (z.B. "(German)") |
| pageCount | 78,4% | Pattern: `\d+ p.` und Varianten |
| location | 67,8% | Gegen Liste von ~100 bekannten Städten gematcht |
| translator | 35,1% | Nur explizite "Translated by Name"-Patterns |
| publisher | 34,5% | Schwächstes Feld — nur 3 Regex-Familien |

## Encoding

### Ausgangslage
61,1% der Einträge hatten [[Encoding-Problem|Mojibake]] — UTF-8-Bytes als Latin-1 fehlinterpretiert.

### Nach Fix
0% residuales Mojibake (verifiziert via `Ã[\x80-\xbf]` Regex-Scan über alle Einträge).

### Ehrlichkeitscheck
Der erste Encoding-Fix behauptete "0%", war aber nur bei 7 häufigen Patterns geprüft. Tatsächlich waren 9,1% (574 Einträge, 21 Patterns) noch betroffen. Der überarbeitete Fix verwendet zeilenweises `encode('latin-1').decode('utf-8')` und ist vollständig.

## Klassifikation

16 [[Entitaetstypen]], regelbasiert:
- Primär: Kategorie-Zuordnung (z.B. "Fiction" → `fiction`)
- Fallback: Content-Analyse (Keywords wie "novel", "essay", "poem")
- Catch-All: 4 Einträge (0,1%) als `other`

## Bekannte Probleme

### Publisher-Extraktion (34,5%)
Nur 3 Regex-Familien: `Verlag|Publisher|Press`, `published by`, und Namensmuster. Viele internationale Verlage werden nicht erkannt. Verbesserung braucht entweder deutlich mehr Patterns oder Named Entity Recognition.

### Translator-Extraktion (35,1%)
Bewusster Trade-off: Die alte Extraktion hatte 69% Coverage, aber 46% False Positives. Die neue hat 0% False Positives bei 35% Coverage. Fehlende Patterns: nicht-lateinische Schriften, ungewöhnliche Formulierungen.

### 33 Bracket-Titel
Sammelwerk-Einträge mit Format `'''[1922]: Insel-Verlag, Leipzig'''` als bold-Zeile. Bei 33 davon existiert kein verwertbarer page_title als Fallback.

### 1 fehlender Eintrag
1 von 6.296 Seiten konnte in keinem der 8 BLOBs gefunden werden.

## Qualitätsreport

Automatisch generiert von `06_validate.py` → `data/output/quality-report.json`:
- 32 Einträge mit Info-Level-Issues (fehlender fullBibliographicEntry)
- 1 Warning (residual encoding suspect)
- 0 Errors
