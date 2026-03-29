# Encoding-Problem

Das zentrale Datenqualitätsproblem der Klawiter-Bibliographie: **Mojibake** durch doppelte Encoding-Interpretation.

## Ursache

Die MediaWiki-Inhalte wurden als UTF-8 gespeichert, aber beim SQL-Dump als Latin-1 (ISO 8859-1) interpretiert. UTF-8-Multibyte-Sequenzen wurden dadurch zu falschen Latin-1-Zeichen:

| Original (UTF-8) | Bytes | Als Latin-1 gelesen |
|-------------------|-------|-------------------|
| ä | `C3 A4` | Ã¤ |
| ö | `C3 B6` | Ã¶ |
| ü | `C3 BC` | Ã¼ |
| ß | `C3 9F` | Ã (+ unsichtbares Zeichen) |
| é | `C3 A9` | Ã© |
| ø | `C3 B8` | Ã¸ |

## Umfang

- **61,1%** aller Einträge betroffen (3.849 von 6.296)
- **21 verschiedene Mojibake-Muster** identifiziert
- Betrifft: Deutsche Umlaute, romanische Akzente, skandinavische Zeichen, osteuropäische Diakritika

## Lösung

### Erster Ansatz (fehlerhaft)
Liste von 40+ expliziten Ersetzungen (`"Ã¤" → "ä"`, etc.) + Trigger-basierte Gesamttext-Reparatur.

**Problem**: Nur 7 häufige Trigger-Patterns geprüft. Texte mit ausschließlich seltenen Mojibake-Patterns (z.B. nur `á`, `í`, `ó`) wurden nicht erkannt → 9,1% residuales Mojibake.

### Überarbeiteter Ansatz (korrekt)
```python
# Universelle Erkennung: jedes Ã+Continuation-Byte
MOJIBAKE_RE = re.compile(r'Ã[\x80-\xbf]|Â[\xa0-\xff]')

# Zeilenweise Reparatur (begrenzt Blast-Radius)
for line in text.split('\n'):
    if MOJIBAKE_RE.search(line):
        fixed = line.encode('latin-1').decode('utf-8')
```

**Warum zeilenweise**: Wenn ein Text Zeilen mit korrektem UTF-8 und Zeilen mit Mojibake mischt, würde die Gesamttext-Reparatur die korrekten Zeilen zerstören.

## Verifikation

Nach dem Fix: 0 Einträge mit `Ã[\x80-\xbf]`-Pattern im gesamten Datensatz. Geprüft sowohl im intermediären CSV als auch im finalen JSON-LD.

## Lektion

Die erste "0%"-Behauptung war falsch, weil die Prüffunktion (`has_mojibake`) nur die häufigsten Patterns testete. **Die Prüfung muss breiter sein als die Reparatur.** Jetzt nutzen Prüfung und Reparatur denselben Regex.
