# Frontend

Statische Web-Oberfläche als Ersatz für das ursprüngliche MediaWiki. Vanilla JS, kein Build-Step, GitHub-Pages-ready.

## Tech-Stack

| Komponente | Technologie | Quelle |
|-----------|-------------|--------|
| Layout/Styling | Tailwind CSS | CDN |
| Volltextsuche | FlexSearch 0.7 | CDN |
| Visualisierungen | Chart.js 4 | CDN |
| Routing | Hash-basiert (`#entry=123`) | Eigener Code |
| Daten | `klawiter.json` (8,5 MB) | Generiert von [[Pipeline]] |

## Dateien

```
frontend/
├── index.html          — HTML-Struktur, CDN-Referenzen
├── css/styles.css      — Custom Styles (Badges, Cards, Facets)
├── js/
│   ├── app.js          — State, Routing, Suche, Events
│   ├── facets.js       — Facettierte Navigation
│   ├── detail.js       — Einzelansicht + JSON-LD-Export
│   └── charts.js       — Dashboard-Visualisierungen
├── data/
│   └── klawiter.json   — 4.751 Einträge + 1.074 Redirect-Map
└── .nojekyll           — Verhindert Jekyll-Processing auf GitHub Pages
```

## Views

### Dashboard (`#` oder leer)
- 4 Statistik-Karten (Einträge, Typen, Sprachen, Zeitraum)
- Publikations-Timeline (Dekaden, Zweigs Lebenszeit hervorgehoben)
- Sprachverteilung (Doughnut-Chart, Top 10)
- Typen-Verteilung (horizontales Balkendiagramm)

### Ergebnisliste (`#q=suchbegriff` oder `#type=fiction`)
- Eintrags-Karten mit Typ-Badge, Jahr, Sprache, Ort
- Suchbegriff-Highlighting
- Sortierung: Relevanz, Jahr, Titel
- Load-More-Pagination (50 pro Seite)

### Detailansicht (`#entry=1234`)
- Alle verfügbaren Felder des Eintrags
- Nachdrucke, Übersetzungen, Inhaltsverzeichnis (bei Sammelwerken)
- Vollständiger bibliographischer Eintrag (Monospace)
- JSON-LD-Download-Button
- Provenienz-Info (Page ID, Text ID, Blob ID)

## Facetten

Linke Sidebar mit Facetten für:
- **Typ** — 16 [[Entitaetstypen]] mit deutschen Labels
- **Sprache** — Top 15
- **Zeitraum** — 5 Perioden
- **Ort** — Top 15 Publikationsorte

Auf Mobilgeräten: Bottom-Sheet per Filter-Button.

## URL-Schema

| URL | Bedeutung |
|-----|-----------|
| `#` | Dashboard |
| `#q=zweig` | Suche nach "zweig" |
| `#type=fiction` | Filter: Belletristik |
| `#language=German` | Filter: Deutsch |
| `#q=amok&type=fiction` | Kombiniert |
| `#entry=1234` | Detailansicht für page_id 1234 |
| `#title=Alter+Name` | Redirect-Auflösung |

## Deployment

Ziel: GitHub Pages (`chpollin/klawiter-rescue`).

Optionen:
1. `gh-pages` Branch mit nur Frontend-Dateien (sauberer)
2. `docs/` Verzeichnis im main Branch (einfacher)

Benötigt: `.nojekyll` Datei (vorhanden).
