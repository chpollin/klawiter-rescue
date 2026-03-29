# Entitätstypen

Die Bibliographie enthält 16 klassifizierte Entitätstypen, abgeleitet aus den MediaWiki-Kategorien. Siehe [[Datenmodell]] für das JSON-LD-Mapping.

## Verteilung

| Typ | Anzahl | Anteil | Beschreibung |
|-----|--------|--------|-------------|
| `redirect` | 1.545 | 24,5% | Weiterleitung zu anderem Eintrag |
| `secondary-literature` | 1.406 | 22,3% | Kritiken, Studien, Biografien über Zweig |
| `fiction` | 1.118 | 17,8% | Romane, Novellen, Erzählungen |
| `essay` | 905 | 14,4% | Essays, Artikel, Rezensionen |
| `historical-study` | 535 | 8,5% | Dissertationen, Monographien |
| `poetry` | 275 | 4,4% | Einzelgedichte, Sammlungen |
| `collected-works` | 114 | 1,8% | Gesammelte/Ausgewählte Werke, Anthologien |
| `correspondence` | 109 | 1,7% | Briefe, Postkarten |
| `film` | 92 | 1,5% | Verfilmungen, Opern, Performances |
| `translation` | 56 | 0,9% | Zweigs Übersetzungen anderer Autoren |
| `drama` | 43 | 0,7% | Theaterstücke, Libretti |
| `symposium` | 39 | 0,6% | Konferenzen, Ausstellungen |
| `foreword` | 36 | 0,6% | Vor-/Nachworte, editorische Beiträge |
| `dramatic-reading` | 18 | 0,3% | Dramatische Lesungen |
| `other` | 4 | 0,1% | Nicht klassifizierbar |
| `newspaper` | 1 | 0,0% | Zeitungsartikel |

## Klassifikationslogik

1. **Redirects**: Eintrag beginnt mit `#REDIRECT` → `redirect`
2. **Kategorie-Mapping**: `main_category` → Typ (z.B. "Fiction" → `fiction`, "Secondary Literature" → `secondary-literature`)
3. **Content-Fallback**: Keywords im Inhalt (z.B. "novel" → `fiction`, "essay" → `essay`)
4. **Default**: `other`

## Zeitperioden

Zusätzlich erhält jeder datierte Eintrag eine Zeitperiode:

| Periode | Bereich | Anzahl |
|---------|---------|--------|
| `pre-zweig` | vor 1881 | 61 |
| `lifetime` | 1881–1942 | 1.124 |
| `post-wwii` | 1943–1980 | 867 |
| `late-20c` | 1981–2000 | 1.050 |
| `contemporary` | ab 2001 | 1.327 |

## Sprachverteilung (Top 10)

| Sprache | Einträge |
|---------|----------|
| German | ~1.050 |
| Chinese | ~510 |
| French | ~350 |
| English | ~270 |
| Spanish | ~260 |
| Arabic | ~210 |
| Russian | ~80 |
| Portuguese | ~70 |
| Italian | ~60 |
| Hindi | ~40 |
