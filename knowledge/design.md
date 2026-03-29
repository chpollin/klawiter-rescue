# Design Specification

Visual design for the Klawiter Bibliography frontend, derived from Stefan Zweig Digital.
Not a 1:1 copy, but the same visual language so both sites feel like parts of one project.

---

## Color Palette

Extracted from Stefan Zweig Digital screenshots:

| Token | Hex | Usage |
|-------|-----|-------|
| `--sz-burgundy` | `#7A1B2D` | Header background, primary links, field labels in detail view |
| `--sz-burgundy-dark` | `#5C1422` | Header hover states, active navigation |
| `--sz-gold` | `#B8963E` | Section headings, accent elements, search icon, active states |
| `--sz-gold-light` | `#D4B463` | Hover on gold elements, highlight |
| `--sz-cream` | `#FAF8F3` | Page background (warm off-white) |
| `--sz-white` | `#FFFFFF` | Card backgrounds, content areas |
| `--sz-text` | `#2D2D2D` | Body text |
| `--sz-text-light` | `#6B6B6B` | Secondary text, metadata |
| `--sz-border` | `#E0D8CC` | Card borders, dividers (warm gray) |
| `--sz-border-light` | `#EDE8DF` | Subtle separators |

No blue anywhere. The current Tailwind blue (`#3b82f6`) is replaced entirely by burgundy for interactive elements and gold for accents.

---

## Typography

Stefan Zweig Digital uses serif fonts throughout, giving it an academic/archival feel.

| Element | Font | Weight | Size | Style |
|---------|------|--------|------|-------|
| Site title | Georgia, serif | 400 | 1.125rem | uppercase, letter-spacing 0.15em |
| Navigation | system sans-serif | 500 | 0.8125rem | uppercase, letter-spacing 0.08em |
| Section headings (h2) | Georgia, serif | 400 | 1.5rem | uppercase, gold color, letter-spacing 0.1em |
| Card title (h3) | Georgia, serif | 600 | 1rem | normal case |
| Body text | Georgia, serif | 400 | 0.9375rem | line-height 1.6 |
| Field labels | Georgia, serif | 400 | 0.875rem | burgundy color |
| Field values | system sans-serif | 400 | 0.9375rem | dark text |
| Badges | system sans-serif | 600 | 0.6875rem | uppercase |
| Small/meta | system sans-serif | 400 | 0.75rem | light text |

The contrast between serif labels and sans-serif values mirrors Stefan Zweig Digital's detail view.

---

## Layout

### Page Structure

```
┌──────────────────────────────────────────────────┐
│  HEADER (burgundy background)                    │
│  Logo · Navigation · Search · Language           │
├──────────────────────────────────────────────────┤
│  BREADCRUMB / FILTER CHIPS (if active)           │
├────────────┬─────────────────────────────────────┤
│  SIDEBAR   │  CONTENT                            │
│  Facets    │  Dashboard / Results / Detail        │
│  (240px)   │                                      │
│            │                                      │
└────────────┴─────────────────────────────────────┘
│  FOOTER                                          │
│  Credits · Links · License                       │
└──────────────────────────────────────────────────┘
```

- Max width: `1200px`, centered
- Cream background (`--sz-cream`)
- Content cards: white background, warm border

### Header

Burgundy bar, sticky. Contains:
- **Left**: Zweig logo mark (stylized "S" in gold/cream) + "KLAWITER BIBLIOGRAPHIE" in uppercase cream text
- **Center**: Navigation links (uppercase, cream, spaced): ÜBERSICHT · SUCHE · STATISTIKEN
- **Right**: Search input (cream border, gold search icon)

Navigation mirrors Stefan Zweig Digital's structure but with 3 items for our simpler scope.

### Footer

Light gray/cream background. Three columns:
1. **Project**: "Klawiter Bibliography — A data rescue project" + link to Stefan Zweig Digital
2. **Credits**: Dr. Randolph J. Klawiter, University of Notre Dame, Stefan Zweig Centre Salzburg
3. **Technical**: GitHub repo link, license, "Built with" note

---

## Views

Four views, routed by hash. See `knowledge/user-stories.md` for the user stories behind each view.

### 1. Startseite — Category Portal (`#`)

The landing page orients users who are accustomed to the old wiki. It shows what categories exist and invites browsing — like a wiki main page, not a SaaS dashboard.

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  STEFAN ZWEIG BIBLIOGRAPHIE                         │
│  (KLAWITER)                                         │
│                                                     │
│  Introductory paragraph (3-4 sentences):            │
│  Die Klawiter-Bibliographie verzeichnet über 4.700  │
│  Publikationen von und über Stefan Zweig. Sie       │
│  wurde von Dr. Randolph J. Klawiter (University     │
│  of Notre Dame) kompiliert und hier als             │
│  durchsuchbare digitale Ausgabe bereitgestellt.     │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  [Suchfeld: In 4.751 Einträgen suchen...] 🔍│    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  WERKE                           (gold, uppercase)  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │Belletrist.│ │  Essays  │ │  Lyrik   │            │
│  │  1.118    │ │   905    │ │   275    │            │
│  └──────────┘ └──────────┘ └──────────┘            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Dramatik │ │  Briefe  │ │Hist. Stud│            │
│  │    43    │ │   109    │ │   535    │            │
│  └──────────┘ └──────────┘ └──────────┘            │
│  ┌──────────┐                                       │
│  │Vor-/Nach-│                                       │
│  │worte  36 │                                       │
│  └──────────┘                                       │
│                                                     │
│  REZEPTION & WIRKUNG             (gold, uppercase)  │
│  ┌──────────────────┐ ┌──────────┐ ┌──────────┐    │
│  │Sekundärliteratur │ │Film/Oper │ │Symposien │    │
│  │     1.406        │ │    92    │ │    39    │    │
│  └──────────────────┘ └──────────┘ └──────────┘    │
│  ┌──────────────────┐ ┌──────────┐                  │
│  │Dramat. Lesungen  │ │ Zeitung  │                  │
│  │       18         │ │    1     │                  │
│  └──────────────────┘ └──────────┘                  │
│                                                     │
│  EDITIONEN                       (gold, uppercase)  │
│  ┌──────────┐ ┌──────────────────┐                  │
│  │Ges. Werke│ │  Übersetzungen   │                  │
│  │   114    │ │  (von SZ)  56    │                  │
│  └──────────┘ └──────────────────┘                  │
│                                                     │
│  ┌──────────┐                                       │
│  │ Sonstige │                                       │
│  │    4     │                                       │
│  └──────────┘                                       │
│                                                     │
│  ── Kurzstatistik ──────────────────────────────    │
│  4.751 Einträge · 41 Sprachen · 402 Orte ·         │
│  Zeitraum 1815–2020                                 │
│  → Ausführliche Statistiken                         │
└─────────────────────────────────────────────────────┘
```

**Category tiles**: White cards with warm border. Entry type name in serif (card title), count in burgundy (large number). Hover: subtle gold left-border. Click → navigates to `#type=fiction` etc.

**Grouping**: Categories are grouped semantically into "Werke" (primary works by Zweig), "Rezeption & Wirkung" (secondary/reception), and "Editionen" (collected works, translations by Zweig). This mirrors how scholars think about the material.

**Search**: Large, prominent search field below the intro — the most common action.

**Kurzstatistik**: One-line summary at the bottom with a link to the full statistics page.

### 2. Stöbern — Search & Results (`#type=fiction`, `#q=amok`, etc.)

Activated when user types in search, clicks a category tile, or clicks a facet.

**Sidebar facets** (left, 240px):
- Section headings in gold uppercase (TYP · SPRACHE · ZEITRAUM · ORT)
- Items: serif font, burgundy color when active, count in light text
- Thin burgundy left-border on active items (like Stefan Zweig Digital's active states)
- No background colors on facet items — clean, text-only

**Result cards**:
```
┌──────────────────────────────────────────┐
│  BELLETRISTIK  1927  German  Berlin      │  ← badge + metadata line
│  Amok. Novellen einer Leidenschaft       │  ← title (serif, medium weight)
│  Insel-Verlag · 248 S.                   │  ← publisher · pages
│  Leipzig: Insel-Verlag, 1927. 248 S...   │  ← snippet (light, truncated)
└──────────────────────────────────────────┘
```

- White card, warm border, subtle left-border in entry-type color on hover
- Badge: pill shape, muted colors (keep current palette but desaturate to match the warm aesthetic)
- Title in serif, one line (truncate with ellipsis)
- Metadata line: publisher and page count as secondary info
- Snippet: first ~150 chars of `fullBibliographicEntry`, light gray

**Result header**: "1.118 Ergebnisse" (left) + sort dropdown (right), both understated.

### 3. Detail View

This is the most important view — where scholars spend time. Modeled closely on Stefan Zweig Digital's metadata display.

```
┌──────────────────────────────────────────┐
│  ← Zurück zur Suche                     │
│                                          │
│  BELLETRISTIK                            │  ← entry type in gold, uppercase
│  Amok. Novellen einer Leidenschaft       │  ← title (large, serif)
│                                          │
│  ┌──────────────────────────────────┐    │
│  │  Titel          Amok. Novellen   │    │
│  │─────────────────────────────────│    │
│  │  Originaltitel  [if different]    │    │
│  │─────────────────────────────────│    │
│  │  Jahr           1927 — Lebensz.  │    │
│  │─────────────────────────────────│    │
│  │  Verlag         Insel-Verlag     │    │
│  │─────────────────────────────────│    │
│  │  Ort            Leipzig          │    │
│  │─────────────────────────────────│    │
│  │  Sprache        German (de)      │    │
│  │─────────────────────────────────│    │
│  │  Seitenzahl     248              │    │
│  │─────────────────────────────────│    │
│  │  Übersetzer/in  [if present]     │    │
│  │─────────────────────────────────│    │
│  │  Kategorien     Fiction / ...    │    │
│  └──────────────────────────────────┘    │
│                                          │
│  VOLLSTÄNDIGER EINTRAG                   │  ← section heading, gold
│  ┌──────────────────────────────────┐    │
│  │  [monospace block, cream bg]     │    │
│  └──────────────────────────────────┘    │
│                                          │
│  NACHDRUCKE                              │  ← if reprints exist
│  • Reprint 1 ...                         │
│  • Reprint 2 ...                         │
│                                          │
│  ÜBERSETZUNGEN                           │  ← if translations exist
│  • Translation 1 ...                     │
│                                          │
│  INHALT                                  │  ← if contentItems exist
│  1. Chapter one ...                      │
│  2. Chapter two ...                      │
│                                          │
│  SIEHE AUCH                              │  ← if seeAlso exist
│  Link 1, Link 2                          │
│                                          │
│  ──────────────────────────────────      │
│  [Zitieren]  [JSON-LD]  [Permalink]      │  ← action bar
│  Page ID: 1234 · Text: 5678 · Blob: 2   │  ← provenance (small)
└──────────────────────────────────────────┘
```

**Key design decisions for detail view:**

- **Two-column metadata table**: Label left (burgundy, serif), value right (dark, sans-serif). Thin horizontal rules between rows — exactly like Stefan Zweig Digital.
- **Section headings**: Gold, uppercase, serif. Used for "Vollständiger Eintrag", "Nachdrucke", "Übersetzungen", etc.
- **Full bibliographic entry**: Monospace on a cream background block. This is the original wiki text — scholars want to see the raw citation.
- **Action bar**: Three icon-buttons at the bottom (matching SZD's quote/link/download icons): Cite (generates citation), JSON-LD (downloads structured data), Permalink (copies URL).
- **Conditional sections**: Only show sections that have data. No empty "Übersetzer: —" rows.

### 4. Statistiken (`#stats`)

Separate page, linked from navigation and from the Kurzstatistik on the Startseite. Interactive — clicking chart elements navigates to filtered results.

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  STATISTIKEN                     (gold, uppercase)  │
│                                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐
│  │   4.751    │ │     15     │ │     41     │ │  1815–   │
│  │  Einträge  │ │   Typen    │ │  Sprachen  │ │   2020   │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘
│                                                     │
│  PUBLIKATIONEN NACH JAHRZEHNT    (gold, uppercase)  │
│  ┌─────────────────────────────────────────────┐    │
│  │  [bar chart — burgundy, lifetime in gold]   │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌──────────────────────┐ ┌────────────────────┐    │
│  │ SPRACHEN             │ │ ORTE               │    │
│  │ [doughnut, top 10]   │ │ [horiz. bar, top15]│    │
│  └──────────────────────┘ └────────────────────┘    │
│                                                     │
│  EINTRAGSTYPEN                   (gold, uppercase)  │
│  ┌─────────────────────────────────────────────┐    │
│  │  [horizontal bar chart]                     │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Stat cards**: White cards, warm border. Number in burgundy (large, serif). Label in gold (small, uppercase).

**Charts**: Burgundy as primary color. Gold for Zweig lifetime (1881–1942). Earth tones for language doughnut. All chart elements are clickable → navigate to `#type=...`, `#language=...`, etc.

**Location chart**: New addition — top 15 cities as horizontal bars. Shows the geographic spread of Zweig publishing (Paris 360, Beijing 349, Berlin 297, Wien 283, ...).

---

## Component Details

### Entry Type Badges

Keep the pill-shaped badges but shift the palette toward the warm SZD aesthetic:

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

All desaturated, warm-toned. No bright primary colors.

### Search Input

- Cream/gold border (1px `--sz-gold`)
- On focus: 2px gold border, no blue ring
- Search icon: gold magnifying glass (SVG)
- Placeholder text in light gray

### Charts

- **Timeline bars**: Burgundy (`--sz-burgundy`). Zweig lifetime decades (1880–1940) highlighted in gold (`--sz-gold`)
- **Language doughnut**: Earth tones — burgundy, gold, olive, slate, terracotta, sage, sienna, sand, charcoal, dusty rose
- **Type bars**: Burgundy, horizontal
- **Chart labels**: sans-serif, small, `--sz-text-light`
- **No gridlines** on x-axis. Subtle gridlines on y-axis

### Filter Chips

- Background: `--sz-gold` at 15% opacity
- Text: burgundy
- Close button: burgundy, 60% opacity → 100% on hover
- Pill shape (fully rounded)

---

## Data Display Strategy

### What to show where

**Result cards** — enough to identify and decide whether to click:
- Entry type badge
- Title (primary identifier)
- Year
- Language + Location (geographic context)
- Publisher + Page count (if available, secondary line)
- Snippet from `fullBibliographicEntry` (first 150 chars)

**Detail view** — everything available, structured in sections:

1. **Core metadata** (always visible, table format):
   - Titel, Originaltitel, Jahr + Zeitraum, Verlag, Ort (+ weitere Orte), Sprache, Seitenzahl, Übersetzer/in, Kategorien

2. **Full bibliographic entry** (always visible, monospace block):
   - The original wiki content — primary source for scholars

3. **Related content** (conditional sections, only if data exists):
   - Nachdrucke (reprints)
   - Übersetzungen (translations)
   - Inhalt (contentItems — table of contents)
   - Siehe auch (seeAlso — cross-references as clickable links)

4. **Provenance** (small, bottom):
   - Page ID, Text ID, Blob ID — for traceability back to source

### Entries to exclude from display

The JSON contains 5,179 entries but not all are bibliography entries:
- `pageNamespace !== 0` entries (419 categories, templates, mediawiki pages, files) should be **filtered out** of the main display
- Only show namespace 0 entries (4,751 bibliography entries) in search/browse
- Category entries could be used to enrich facet descriptions (future enhancement)

### Empty fields

Never show a field row with "—" or empty value. If `translator` is null, omit the row entirely. This keeps the detail view clean and matches Stefan Zweig Digital's approach.

---

## Interaction Patterns

### Navigation flow

1. **Startseite** (`#`): Category portal — orient, then browse or search
2. **Kategorie-Klick**: Click a tile → `#type=fiction` → Stöbern with that filter
3. **Suche**: Type in header search → `#q=amok` → Stöbern with search results
4. **Facetten**: Click sidebar facet → adds/toggles filter
5. **Ergebnis-Klick**: Click a result card → `#entry=1234` → Detailansicht
6. **Zurück**: Browser back → returns to Stöbern with scroll position preserved
7. **Statistiken**: Click nav link → `#stats` → Charts (click chart → Stöbern)
8. **Home**: Click logo/title → `#` → back to Startseite

### Cross-references

- `seeAlso` entries link to other detail views within the bibliography
- Category links in detail view activate the type facet filter
- Redirect resolution: old wiki titles map to current page IDs via the redirects object (currently 0 redirects, but the mechanism stays for future use)

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `docs/css/styles.css` | Rewrite | Complete CSS with custom properties, no Tailwind |
| `docs/index.html` | Rewrite | New HTML structure with 4 views, remove Tailwind CDN |
| `docs/js/app.js` | Rewrite | 4-view routing, namespace filter, state management |
| `docs/js/home.js` | New | Startseite: category tiles, intro, search |
| `docs/js/detail.js` | Rewrite | SZD-style metadata table, conditional sections, action bar |
| `docs/js/facets.js` | Update | New styling, gold/burgundy scheme |
| `docs/js/charts.js` | Rewrite | New color scheme, location chart, click-to-filter |
