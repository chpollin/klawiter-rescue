# MediaWiki-Datenbank

Die ursprüngliche Quelle der Klawiter-Bibliographie. Ein stillgelegtes MediaWiki mit 6.725 Seiten, dessen Inhalte in einer 4-schichtigen Struktur gespeichert sind.

## Tabellenstruktur

```
zweig_page (6.725 Seiten)
  → page_latest → zweig_revision (Versionshistorie)
    → rev_id → zweig_slots (Content-Slots)
      → slot_content_id → zweig_content (Content-Adressen)
        → "tt:XXXXX" → Text-ID in BLOB-Dateien
```

### zweig_page
- `page_id`: Eindeutige ID
- `page_namespace`: 0 = Hauptnamespace (6.296 Seiten)
- `page_title`: Seitenname (mit Unterstrichen statt Leerzeichen)
- `page_latest`: Verweis auf aktuelle Revision

### zweig_content
- `content_address`: Format `tt:XXXXX` — Verweis auf Text-ID im BLOB

## BLOB-Dateien

8 Binärdateien (`zt_00` bis `zt_07`), zusammen 363 MB. Jede enthält SQL-INSERT-Statements:

```sql
INSERT INTO zweig_text VALUES
  (835, _binary 'Wiki-Inhalt hier...', _binary 'utf-8'),
  (848, _binary 'Nächster Eintrag...', _binary 'utf-8');
```

| Datei | Größe | Einträge |
|-------|-------|----------|
| zt_00 | ~28 MB | 2.736 |
| zt_01 | ~37 MB | 6.869 |
| zt_02 | ~35 MB | 5.841 |
| zt_03 | ~30 MB | 11.613 |
| zt_04 | ~42 MB | 10.587 |
| zt_05 | ~44 MB | 5.731 |
| zt_06 | ~35 MB | 8.217 |
| zt_07 | ~11 MB | 1.422 |

Die BLOBs enthalten nicht nur die aktuellen Versionen, sondern alle historischen Revisionen (53.016 Text-Einträge für 6.296 Seiten).

## SQL-Dump

`zweig_part_01.sql` (33 MB) enthält:
- 48 CREATE TABLE Statements (vollständiges MediaWiki-Schema)
- INSERT-Daten für alle Tabellen außer `zweig_text`
- Die `zweig_text`-Daten sind in den separaten BLOB-Dateien

## Wiki-Markup-Formate

Die Bibliographie-Einträge verwenden MediaWiki-Markup:

| Markup | Bedeutung |
|--------|-----------|
| `'''Text'''` | Fett (Werktitel, Strukturmarker) |
| `''Text''` | Kursiv (Publikationstitel) |
| `[[Ziel]]` | Interner Link |
| `[[Ziel\|Anzeige]]` | Link mit Anzeigetext |
| `[[Category:Name]]` | Kategorie-Zuordnung |
| `{{DEFAULTSORTKEY:...}}` | Sortierungsschlüssel |
| `<lst type=bracket>` | Nummerierte Liste |
| `#REDIRECT [[Ziel]]` | Weiterleitung |

### Strukturmarker

| Marker | Funktion |
|--------|----------|
| `'''Reprinted in:'''` | Nachdrucke |
| `'''See:'''` / `'''See also:'''` | Querverweise |
| `'''Translations:'''` | Übersetzungsliste |
| `'''Contents'''` | Inhaltsverzeichnis (Sammelwerke) |
