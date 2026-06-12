---
title: Frontend
aliases: [design, ui-design, user-stories, frontend design]
tags: [frontend, design, ui]
created: 2026-03-29
updated: 2026-06-12
---

# Frontend

Design specification, user stories, and implementation for the Klawiter Bibliography frontend. Part of the Zweig Forschungsverbund design family — see [[about#stefan-zweig-digital-and-the-forschungsverbund]].

---

## Design System

### Color Palette

Aligned to Stefan Zweig Digital on GAMS (the reference design):

| Token | Hex | Usage |
|-------|-----|-------|
| `--sz-burgundy` | `#631a34` | Header background, primary links, field labels |
| `--sz-burgundy-dark` | `#4A1228` | Header hover states, active navigation |
| `--sz-burgundy-light` | `#7A2D45` | Lighter burgundy for secondary states |
| `--sz-gold` | `#C2A360` | Section headings, accent elements, search icon |
| `--sz-gold-light` | `#D4B87A` | Hover on gold elements, highlight |
| `--sz-cream` | `#FAF8F3` | Page background (warm off-white) |
| `--sz-white` | `#FFFFFF` | Card backgrounds, content areas |
| `--sz-text` | `#2D2D2D` | Body text |
| `--sz-text-light` | `#6B6B6B` | Secondary text, metadata |
| `--sz-border` | `#E0D8CC` | Card borders, dividers (warm gray) |
| `--sz-border-light` | `#EDE8DF` | Subtle separators |

No blue anywhere. Burgundy for interactive elements, gold for accents. The Klawiter site is "gold-forward" (gold section headings), while SZD GitHub is "burgundy-forward" (burgundy section headings).

### Typography

Source Serif 4 + Source Sans 3 via Google Fonts (modern open-source equivalents of SZD's Bauer Bodoni + Source Sans Pro).

| Element | Font | Weight | Size | Style |
|---------|------|--------|------|-------|
| Site title | Source Serif 4, serif | 400 | 1rem | uppercase, letter-spacing 0.12em |
| Navigation | Source Sans 3, sans-serif | 500 | 0.8125rem | uppercase, letter-spacing 0.08em |
| Section headings (h2) | Source Serif 4, serif | 400 | 1.25rem | uppercase, gold color, letter-spacing 0.1em |
| Card title (h3) | Source Serif 4, serif | 600 | 1rem | normal case |
| Body text | Source Serif 4, serif | 400 | 0.9375rem | line-height 1.6 |
| Field labels | Source Serif 4, serif | 400 | 0.875rem | burgundy color |
| Field values | Source Sans 3, sans-serif | 400 | 0.9375rem | dark text |
| Badges | Source Sans 3, sans-serif | 600 | 0.6875rem | uppercase |
| Small/meta | Source Sans 3, sans-serif | 400 | 0.75rem | light text |

### Entry Type Badges

Warm-toned, desaturated pill-shaped badges:

| Type | Background | Text |
|------|-----------|------|
| fiction | `#EDE4D4` | `#7A1B2D` |
| essay | `#F5EDD8` | `#8B6914` |
| poetry | `#E8E0EF` | `#5B3A7A` |
| drama | `#F0DDE4` | `#7A1B2D` |
| correspondence | `#DDE8E0` | `#2D5B3A` |
| film | `#EDDDDD` | `#7A2D1B` |
| historical-study | `#E0E0ED` | `#3A3A7A` |
| secondary-literature | `#EDE8E0` | `#5B5040` |
| collected-works | `#F0EBD8` | `#6B5A14` |
| foreword | `#DDE8E4` | `#2D5B4A` |
| translation | `#E0EDDD` | `#3A5B2D` |
| symposium | `#F0E4DD` | `#7A4A1B` |
| dramatic-reading | `#EDDDEE` | `#6B1B6E` |
| newspaper | `#E8E4E0` | `#5B504A` |
| other | `#E8E4E0` | `#6B6B6B` |

---

## Layout

### Page Structure

```
+--------------------------------------------------+
|  HEADER (burgundy background)                    |
|  Logo . Navigation . Search . Language           |
+--------------------------------------------------+
|  BREADCRUMB / FILTER CHIPS (if active)           |
+------------+-------------------------------------+
|  SIDEBAR   |  CONTENT                            |
|  Facets    |  Dashboard / Results / Detail        |
|  (240px)   |                                      |
+------------+-------------------------------------+
|  FOOTER                                          |
|  Credits . Links . License                       |
+--------------------------------------------------+
```

- Max width: `1200px`, centered
- Cream background (`--sz-cream`)
- Content cards: white background, warm border

### Header

Burgundy bar, sticky. Left: "KLAWITER BIBLIOGRAPHIE" in uppercase cream text. Center: navigation links (uppercase, cream, spaced). Right: search input (cream border, gold search icon). Navigation mirrors SZD's structure.

### Footer

Light gray/cream background. Three columns:
1. **Project**: "Klawiter Bibliography — A data rescue project" + link to Stefan Zweig Digital
2. **Credits**: Dr. Randolph J. Klawiter, University of Notre Dame, Stefan Zweig Centre Salzburg
3. **Technical**: GitHub repo link, license, "Built with" note

---

## Personas & User Stories

User stories for the Klawiter Bibliography frontend. Derived from the target audience (Zweig scholars, librarians, DH researchers) and the data structure (4,751 entries, 15 types, 41 languages, 395 locations). The original Klawiter bibliography was a MediaWiki. Users are familiar with category-based browsing and expect to navigate by topic, not by statistics.

User stories were written in German during the design phase and are preserved in their original language.

### Personas

**Anna** — Germanistik-Professorin, forscht zu Zweigs Novellistik. Nutzte das Klawiter-Wiki regelmäßig. Will schnell alle Belletristik-Einträge zu einem bestimmten Werk finden und vollständige bibliographische Daten für Zitationen.

**Carlos** — Bibliothekar an einer Romanistik-Fakultät. Sucht spanische Zweig-Übersetzungen für den Bestandsaufbau. Braucht Verlag, Ort, Jahr in exportierbarer Form.

**Mei** — DH-Forscherin, untersucht die globale Rezeption deutschsprachiger Literatur. Interessiert sich für Verteilung nach Sprache, Zeitraum und Geographie. Will die Daten als JSON-LD für eigene Analysen.

### Startseite: Orientierung (S1-S3)

> **S1**: Als Wiki-gewohnte Nutzerin will ich auf der Startseite sofort sehen, welche **Kategorien** von Einträgen es gibt (Belletristik, Essays, Lyrik, ...), damit ich mich wie im alten Wiki zurechtfinde.

> **S2**: Als Erstbesucherin will ich einen kurzen **Einführungstext** lesen, der erklärt, was die Klawiter-Bibliographie ist und was ich hier finden kann.

> **S3**: Als Nutzerin will ich direkt von der Startseite aus **suchen** können, ohne erst navigieren zu müssen.

**Daten-Check**: 15 entryTypes mit Counts verfügbar. Einführungstext wird redaktionell erstellt. Suche über FlexSearch-Index wie bisher.

### Stöbern & Suchen: Finden (S4-S8)

> **S4**: Als Forscherin will ich alle Einträge eines **Typs** sehen (z.B. "alle Belletristik"), um einen Überblick über Zweigs Prosawerk zu bekommen.

> **S5**: Als Bibliothekar will ich nach **Sprache** filtern (z.B. "Spanisch"), um Übersetzungen in einer bestimmten Sprache zu finden.

> **S6**: Als Nutzerin will ich **mehrere Filter kombinieren** (z.B. Typ + Sprache + Zeitraum), um gezielt zu suchen.

> **S7**: Als Nutzerin will ich die Ergebnisse nach **Jahr, Titel oder Relevanz** sortieren können.

> **S8**: Als Nutzerin will ich sehen, **wie viele Ergebnisse** mein Filter liefert, und aktive Filter als **Chips** sehen und einzeln entfernen können.

**Daten-Check**: Alle Facetten (Typ, Sprache, Zeitraum, Ort) sind als Felder vorhanden. 41 Sprachen, 395 Orte, 5 Zeiträume. Kombinierte Filter funktionieren über Array-Intersection.

### Detailansicht: Verstehen (S9-S13)

> **S9**: Als Forscherin will ich **alle verfügbaren Metadaten** eines Eintrags in einer strukturierten Übersicht sehen (Titel, Jahr, Verlag, Ort, Sprache, Seitenzahl, Übersetzer).

> **S10**: Als Nutzerin will ich den **vollständigen bibliographischen Eintrag** im Originalformat sehen, so wie er im Klawiter stand.

> **S11**: Als Forscherin will ich **Nachdrucke und Übersetzungen** eines Werks sehen, um die Publikationsgeschichte zu verfolgen.

> **S12**: Als Nutzerin will ich über **Querverweise** ("Siehe auch") zu verwandten Einträgen navigieren können.

> **S13**: Als Nutzerin will ich den **Inhalt** von Sammelbänden sehen (Inhaltsverzeichnis).

**Daten-Check**: reprints 418 (8.8%), translations 177 (3.7%), contentItems 936 (19.7%), seeAlso 683 (14.4%).

### Export & Teilen (S14-S17)

> **S14**: Als Bibliothekarin will ich einen Eintrag als **BibTeX oder RIS** exportieren, um ihn in meine Literaturverwaltung zu importieren.

> **S15**: Als DH-Forscherin will ich einen Eintrag als **JSON-LD** herunterladen, um ihn in meinem Linked-Data-Workflow zu verwenden.

> **S16**: Als Nutzerin will ich einen **Permalink** zu einem Eintrag kopieren und teilen können.

> **S17**: Als DH-Forscherin will ich den **gesamten Datensatz** als JSON-LD herunterladen.

### Statistiken: Analysieren (S18-S20)

> **S18**: Als DH-Forscherin will ich die **Verteilung nach Jahrzehnt** sehen, um Publikationswellen zu erkennen.

> **S19**: Als Forscherin will ich die **Sprachverteilung** sehen, um die globale Zweig-Rezeption zu verstehen.

> **S20**: Als Forscherin will ich auf einen **Statistik-Wert klicken**, um die dahinterliegenden Einträge zu sehen.

**Primary user journey**: Startseite -> Kategorie-Klick -> Stöbern -> Eintrag

---

## Tech Stack & File Structure

| Component | Technology | Source |
|-----------|-----------|--------|
| Layout/Styling | Custom CSS (SZD design) | `css/styles.css` |
| Full-text search | FlexSearch 0.7 | CDN |
| Visualizations | D3.js v7 | CDN |
| Routing | Hash-based (`#entry=123`) | Custom code |
| Data | `klawiter.json` (~9 MB) | Generated by [[pipeline]] |

```
docs/
  index.html          HTML structure (4 views, semantic elements, meta tags)
  .nojekyll           Prevents Jekyll processing on GitHub Pages
  css/styles.css      Full custom CSS (SZD burgundy/gold/cream palette)
  js/
    constants.js         Shared COLORS, CHART_DIMS, type/period labels, category groups
    utils.js             esc(), hl(), countByField(), downloadBlob()
    export.js            BibTeX, RIS, JSON-LD, permalink, full dataset
    app.js               State, routing, search, event delegation, expandable cards
    home.js              Category portal landing page
    facets.js            Faceted navigation (type, language, period, location)
    detail.js            Inline detail rendering (metadata table, provenance badges)
    edit.js              Expert-in-the-Loop curation (localhost only, JSON patch export)
    explore.js           Shared explore controller (mode tabs, detail panel, tooltips)
    explore-timeline.js  D3.js timeline (Bars/Sparklines/Ranks modes, year x language, brushing, annotations)
    explore-geography.js D3.js bubble map (dual projection globe/flat, semantic zoom, Wikidata-linked locations)
    explore-network.js   Force-directed graph of seeAlso cross-references
    jsonld-playground.js JSON-LD interactive explorer (compact/expanded/triples)
    pages.js             Static content pages (About, Methodology, Help, Data, Imprint, JSON-LD Playground)
  data/
    klawiter.json     5,179 total entries (4,751 ns0 displayed) + 1,210 resolved redirects
    locations.json    382 geocoded locations with Wikidata Q-IDs (94.2% coverage)
  vocab/
    index.html        Vocabulary namespace documentation
```

---

## Views & Routing

| URL | View | Primary Stories |
|-----|------|----------------|
| `#` | Landing Page (category portal) | S1, S2, S3 |
| `#browse` | All entries unfiltered | S4-S8 |
| `#q=zweig` | Search results | S4-S8 |
| `#type=fiction` | Type filter | S4-S8 |
| `#category=Fiction / Volumes (German)` | Subcategory filter | S4-S8 |
| `#language=German` | Language filter | S5 |
| `#q=amok&type=fiction` | Combined filters | S6 |
| `#entry=1234` | Detail view (page_id) | S9-S16 |
| `#title=Old+Name` | Redirect resolution | — |
| `#stats` | Exploration interface | S18-S20 |
| `#about`, `#methodology`, `#help`, `#data`, `#imprint`, `#jsonld` | Content pages | — |

### Landing Page (`#`)

Expandable category portal. 16 entry types as expandable rows grouped by Works / Reception & Impact / Editions. Each row expands to show subcategories parsed from `entry.categories`. Summary stats line at bottom. Large search field below intro text.

### Browse (`#browse`, `#q=...`, `#type=...`)

Faceted sidebar (left, 240px): Type, Language, Time period, Location. Section headings in gold uppercase. Active items with thin burgundy left-border. Mobile: bottom sheet via filter button.

Result cards: white card, warm border, type badge + year + language + location, title in serif, publisher + pages, snippet from fullBibliographicEntry. Cards expand inline to show full metadata.

### Detail View (`#entry=1234`)

Two-column metadata table (label in burgundy serif, value in dark sans-serif). Conditional sections: reprints, translations, content items, see-also. Action bar: BibTeX, RIS, JSON-LD, permalink. Provenance footer: page_id, text_id, blob_id.

### Content Pages

6 static content pages rendered by `pages.js`, routed via hash. Navigation: "About" as direct header link, "More" dropdown for remaining pages. All linked from footer. Mobile: accessible via footer.

| Page | Route | Purpose |
|------|-------|---------|
| **About** | `#about` | Klawiter's work, original wiki history, rescue project, SZD connection |
| **Methodology** | `#methodology` | Pipeline steps, encoding repair, LLM enrichment, quality assurance |
| **Help** | `#help` | Search, filtering, sorting, exports, permalinks, FAQ |
| **Data Access** | `#data` | Full dataset download, field documentation, vocabulary, license |
| **JSON-LD Playground** | `#jsonld` | Interactive JSON-LD explorer (compact/expanded/triples) |
| **Imprint** | `#imprint` | Credits, citation recommendation, license, contact |

---

## Data Display Strategy

**Result cards** — enough to identify and decide whether to click:
- Entry type badge, title, year, language + location, publisher + page count, snippet (first 150 chars)

**Detail view** — everything available, structured in sections:
1. **Core metadata** (table): title, original title, year + period, publisher, location, language, page count, translator, categories
2. **Full bibliographic entry** (monospace block): original wiki content
3. **Related content** (conditional): reprints, translations, content items, see-also cross-references
4. **Provenance** (small, bottom): page_id, text_id, blob_id

**Empty fields**: Never show a field row with empty value. If `translator` is null, omit the row entirely.

**Namespace filter**: Only show namespace 0 entries (4,751 bibliography entries) in search/browse.

---

## Interaction Patterns

1. **Startseite** (`#`): Category portal — orient, then browse or search
2. **Kategorie-Klick**: Click a tile -> `#type=fiction` -> Browse with that filter
3. **Suche**: Type in header search -> `#q=amok` -> Browse with search results
4. **Facetten**: Click sidebar facet -> adds/toggles filter
5. **Ergebnis-Klick**: Click a result card -> `#entry=1234` -> Detail view
6. **Zurück**: Browser back -> returns to Browse with scroll position preserved
7. **Statistiken**: Click nav link -> `#stats` -> Charts (click chart -> Browse)
8. **Home**: Click logo/title -> `#` -> back to Startseite

Cross-references: `seeAlso` entries link to other detail views. Category links activate the type facet filter. Redirect resolution via the redirects map.

---

## EIL Curation Interface

Expert-in-the-Loop curation for manual validation and correction. See [[about#eil-curation-interface]] for the conceptual overview.

- **edit.js**: Localhost-only edit mode (`location.hostname === 'localhost'`)
- **Provenance badges**: Visual indicators (regex/llm/missing) on publisher, location, translator, pageCount
- **JSON patch export**: Edits collected as patches, not written directly to the dataset
- **GitHub Actions validation**: `.github/workflows/validate-patch.yml`

---

## Zweig Forschungsverbund

Three sites form a visual family, all using the GAMS reference palette:

| Site | Role | Primary Accent | URL |
|------|------|---------------|-----|
| SZD GAMS | Edition (reference) | Burgundy `#631a34` + Gold `#C2A360` | stefanzweig.digital |
| Klawiter | Bibliography (gold-forward) | Gold for section headings | chpollin.github.io/klawiter-rescue |
| SZD GitHub | Ontology (burgundy-forward) | Burgundy for section headings | chpollin.github.io/SZD |

**Shared elements**: Verbund navigation bar at top connecting all three sites. Source Serif 4 + Source Sans 3 fonts. Identical color tokens.

**Constraints**: GitHub Pages = static files only. No shared authentication. Different domain (github.io vs university hosting). Must work standalone if SZD is unavailable.

---

## Stable URIs

Every bibliography entry needs a stable, shareable URL. Current scheme: `#entry={page_id}`.

**Options considered**:
1. **Hash-based** (chosen): `site.github.io/#entry=1234` — simple, works without server config
2. **Path-based with 404.html**: Cleaner URLs, but fragment identifiers not sent to server
3. **Hybrid**: Path-based canonical, hash-based fallback

All support `<link rel="canonical">`, old wiki title resolution via redirect map, and stable page_id-based identifiers.

---

## Citation Export

Each entry offers citation export in:
- **BibTeX**: Standard for academic tools (Zotero, Mendeley, LaTeX)
- **RIS**: Broader compatibility (EndNote, RefWorks)
- **JSON-LD**: Structured data for Linked Data workflows
- **Permalink**: Stable URL for sharing

Implementation: Client-side generation from JSON-LD data.

---

## Performance

- `klawiter.json`: ~9 MB (minified, no whitespace)
- GitHub Pages serves with gzip -> ~1.5 MB transfer (estimated)
- Entire dataset loaded on first visit, then cached

Start with gzip-only. Measure real-world load times. Only split data if mobile performance is unacceptable.

---

## Accessibility

Minimum target: WCAG 2.1 AA.

- Color contrast: verify all text/background combinations (especially badges)
- Keyboard navigation: all interactive elements reachable via Tab
- Screen reader: ARIA landmarks, labels for search, facets, pagination
- Focus management: when navigating between views, focus moves to content
- Skip navigation link for keyboard users

---

## Resolved Design Decisions

- **Landing page**: Category portal (wiki-style), not search-first
- **SZD design**: Fully implemented via custom CSS — burgundy/gold/cream palette, serif/sans-serif typography. No SZD CSS assets needed.
- **Exploration**: D3.js v7 interactive visualization with 3 modes (Timeline, Geography, Connections). See [[exploration]] for design concept.
- **Authority data display**: Wikidata-linked locations are shown in the Geography mode (reconciled Q-IDs). Inventing bibliographic *values* not present in the source stays out of scope — see [[about#data-integrity-principle]].
