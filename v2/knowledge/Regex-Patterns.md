# Regex-Patterns

Die [[Pipeline]] verwendet reguläre Ausdrücke zur Metadaten-Extraktion aus dem Wiki-Markup. Definiert in `pipeline/lib/patterns.py` und `pipeline/lib/wiki_parser.py`.

## Metadaten-Extraktion

### Jahr
```regex
\b(1[789]\d{2}|20[0-3]\d)\b
```
Matcht 1700–2039. Nimmt das erste Match. **Limitation**: Keine Bereichserkennung ("1952-1978"), keine Kontextvalidierung (Seitenzahlen wie "1234" könnten fälschlich als Jahre erkannt werden).

### Verlag (3 Familien)
```regex
(?:Verlag|Publisher|Press|Publishing|Éditions?|...)[\s:]+([^\n,.;()[\]]{3,80})
(?:published by|verlegt bei|...)  \s+([^\n,.;()[\]]{3,80})
\b([\w\s&.-]{2,60}(?:Verlag|Press|Publishers?|...))  \b
```
**Coverage**: 34,5%. Schwächstes Feld — erkennt nur explizit gelabelte oder namentlich endende Verlage.

### Ort
```regex
\b(Wien|Vienna|Berlin|Frankfurt|...|Tübingen|Freiburg)\b
```
Gegen eine Liste von ~100 bekannten Städten gematcht, nach Länge sortiert (längste zuerst). **Coverage**: 67,8%.

### Seitenzahl
```regex
(\d{1,5})\s*(?:pp?\.|pages?|Seiten|S\.)
pp?\.\s*(\d{1,5})
(\d{1,5})\s*p\b
```
**Coverage**: 78,4%. Erkennt `432 p.`, `pp. 9-86`, `293 Seiten`.

### Übersetzer
```regex
[Tt]ranslated\s+by\s+([A-Z][a-zA-ZÀ-ÿ\s.'-]{2,60})
[Üü]bersetzt\s+von\s+([A-Z][a-zA-ZÀ-ÿ\s.'-]{2,60})
[Tt]raduit\s+par\s+(...)
[Tt]rans\.\s+([A-Z]...)
```
8 Patterns für 5 Sprachen. Strikt: Name muss mit Großbuchstabe beginnen. **Coverage**: 35,1% bei 0% False Positives.

### Sprache
Nicht per Regex, sondern aus Kategorie-Namen:
```regex
\((\w+)\)\s*$
```
Extrahiert z.B. "German" aus `Poetry / Individual Poems (German)`. **Coverage**: 89,4%.

## Wiki-Markup-Parsing

### Redirect
```regex
^#REDIRECT\s*\[\[(.+?)\]\]
```

### Kategorie
```regex
\[\[Category:([^\]]+)\]\]
```

### Titel (Bold-Markup)
```regex
^\s*'''(.+?)'''
```
Mit Reject-Pattern für `\[\d{4}\]:` (Sammelwerk-Publikationsinfo).

### Querverweise
```regex
'''See(?:\s+also)?:?'''\s*\[\[([^\]]+)\]\]
```

### Nachdrucke
```regex
'''Reprinted in:?'''\s*(.+?)(?:\n\n'''|\n\n\[\[Category|\Z)
```

## Bekannte Fragilität

| Pattern | Risiko | Beispiel |
|---------|--------|----------|
| Jahr-Regex | False Positives bei Seitenzahlen | "1234 p." → Jahr 1234 + Seitenzahl |
| Verlag | Zu wenig Patterns | Japanische/arabische Verlage nicht erkannt |
| Ort | Statische Liste | Neue/seltene Orte fehlen |
| Übersetzer | Name muss Großbuchstabe starten | "van der Berg" → nicht erkannt |
| Titel | Fallback auf first-line | Kann Müll extrahieren bei ungewöhnlichem Format |
