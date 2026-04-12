---
title: Exploration
aliases: [visualization, D3]
tags: [exploration, visualization]
created: 2026-03-29
updated: 2026-04-12
---

# Exploration Interface

Design concept for the interactive exploration tool of the Klawiter Bibliography.

## Research Questions

The Klawiter Bibliography documents Stefan Zweig's global literary reception across 200 years, 41 languages, and 400+ publication locations. The exploration interface should help researchers answer:

1. **Temporal**: How did publication volume evolve over time? When were the major waves of Zweig reception?
2. **Linguistic**: Which languages dominated in which era? How did Zweig spread from German to Chinese, French, Arabic?
3. **Geographic**: Where was Zweig published? How did publication centers shift over time?
4. **Typological**: What types of works dominate? How does the ratio of primary works to secondary literature change?
5. **Relational**: How are entries connected? Which works were most reprinted, translated, or referenced?

## Design Rationale

### Why not a dashboard?

Standard dashboards (4 separate charts in a grid) fail for exploratory research because:
- Each chart is isolated — no visual connection between dimensions
- No progressive drill-down — what you see is what you get
- No narrative — dashboards present facts, not stories
- No serendipity — users can't discover unexpected patterns

### Why three modes?

Different research questions require different visual encodings. A single visualization cannot optimally serve temporal, categorical, and relational analysis simultaneously. Instead, three purpose-built modes share a common state and detail panel:

| Mode | Research Focus | Visual Encoding |
|------|---------------|-----------------|
| **Timeline** | Temporal + linguistic/typological | Stacked bar chart (year x language or type) |
| **Geography** | Spatial + temporal | Bubble map with brushed linking from Timeline |
| **Connections** | Relational | Force-directed network graph |

Note: The Overview mode (4 linked small multiples) was removed in Session 14 to focus on three strong modes rather than four mediocre ones.

### Progressive disclosure

- **Default**: Timeline mode — most familiar chart type, answers the broadest question
- **On demand**: Mode tabs for Geography and Connections
- **Detail panel**: Appears on selection (not always visible) — maximizes chart space
- **Exit to browse**: Double-click or "View entries" button navigates to the faceted search

## Data Landscape

### Dimensions available

| Dimension | Cardinality | Coverage | Notes |
|-----------|------------|----------|-------|
| Year | 1815–2020 | 93.2% | Integer, sparse before 1880 |
| Language | 41 unique | 89.4% | Top: German, Chinese, French, English, Spanish |
| Location | 402 unique | 87.5% | Top: Paris, Beijing, Berlin, Wien, Frankfurt |
| Entry Type | 16 types | 100% | Secondary Lit (29%), Fiction (23%), Essays (19%) |
| Time Period | 5 buckets | 100% | Derived from year |
| Publisher | ~1,000+ | 55.6% | Weak coverage, many missing |
| Translator | ~500+ | 41.9% | Weak coverage |
| Page Count | integer | 54.1% | Previously 81.6%, corrected after pp. N-M FP removal |

### Array fields (relational data)

| Field | Entries with data | Potential |
|-------|-------------------|-----------|
| categories | ~2,000+ | Category hierarchy, subcategory faceting |
| seeAlso | 683 (13.2%) | Internal cross-references → network graph |
| contentItems | 936 (18.1%) | Collections with chapter/story breakdown |
| reprints | 418 (8.1%) | Edition history |
| translations | 177 (3.4%) | Translation chains |

### Key patterns in the data

- **Zweig's lifetime peak** (1920s–1930s): Heavy German-language output
- **Post-exile shift** (1933+): Publications move from Berlin/Leipzig to Amsterdam, London, Buenos Aires
- **Post-war wave** (1950s–1970s): Global translations expand (Chinese, Arabic, Spanish)
- **Contemporary revival** (2000s+): Largest decade by volume — secondary literature + new translations
- **Chinese boom**: Chinese becomes the #2 language after German from 2000s onward

## Visualization Techniques

### Timeline: Stacked Bar Chart

**D3 implementation**: `d3.stack()` + `rect` + `d3.brushX()`

Stacked bar chart with one bar per year showing publication volume over time. Bars (not area curves) because the data is discrete — integer counts per year, not continuous flow. Layers colored by language (default) or entry type (toggle).

**Features (Session 14):**
- **Layer toggle**: Switch between "by Language" (top 10 + Other) and "by Type" (top 10 entry types + other). Uses `Explore.colors.languages` and `Explore.colors.types`.
- **Semantic zoom**: At full extent (200 years): decade labels on x-axis. On brush to small range (<30 years): individual year labels. Dynamic tick formatting based on domain width.
- **Brush-state event**: Every brush update fires `explore:filterChange` CustomEvent on `document` with `Explore.filters.yearRange`. Consumed by Geography and Connections views for cross-view filtering, even when not visible (state applied on tab switch).
- **Provenance overlay**: Toggle "Data quality" shows semi-transparent bars per year with regex (green) / LLM (gold) / missing (burgundy) proportions. Data from `_provenance` object in each entry.
- **Annotations**: 5 markers — Born 1881, WWI 1914, Exile 1933, WWII 1939, Death 1942. Collision avoidance staggers overlapping labels. Hover shows detail text.

**Stack order**: `d3.stackOrderInsideOut` — largest category in center for visual stability.

**Zweig's lifetime**: Subtle gold band from 1881 to 1942 provides biographical context.

**Layout**: Full-width chart (no sidebar by default). Detail panel appears only on selection. Compact inline legend in controls bar above chart. Stats as text line in header ("4,751 entries . 41 languages . 15 types . 1815-2020").

### Connections: Two-Level Network

**D3 implementation**: `d3.forceSimulation()` with two view levels (semantic zoom for networks).

574 entries participate in seeAlso cross-references (~590 edges). A flat force-directed layout of all nodes is unreadable at this scale, so the visualization uses a two-level approach analogous to the Geography semantic zoom (countries → cities):

**Level 1 — Community Overview (default):** Connected components are detected via BFS and aggregated into meta-nodes. Each meta-node represents one community, sized by member count, colored distinctly (d3.schemeTableau10), and labeled with the hub title. Small communities (< 3 members) are grouped into a "Small clusters" aggregate. Cross-community edges are shown as weighted meta-links. Result: ~10-20 readable bubbles instead of 574 overlapping dots. The detail panel lists all communities with their hub and dominant type.

**Level 2 — Community Detail (click to drill down):** Clicking a community expands it into a standard force-directed layout of its members. Hub highlighting (top 10 by degree, with halo + permanent labels), degree filter slider (live transitions), and entry-type coloring. A back button returns to the overview. For large communities (100+ nodes), the degree filter starts at 2 to suppress leaf nodes.

The graph reveals structural patterns:
- Which works are most cross-referenced? (hub highlighting)
- What clusters exist in the cross-reference network? (community overview)
- How are communities connected? (meta-links between communities)

**Sub-mode 2 — Translators:** Flat force-directed graph of top 50 translators linked by shared mainCategory (unchanged, manageable scale).

## Interaction Design

### Shared across all modes

- **Detail panel** (right sidebar): Shows selected entries with full metadata
- **Tooltip on hover**: Lightweight preview without commitment
- **Double-click → browse**: Navigates to filtered results view
- **Filter chips**: Show active selections, removable with ×

### Mode-specific

| Mode | Primary interaction | Secondary |
|------|-------------------|-----------|
| Timeline | Brush time range | Click language layer |
| Overview | Click element in any view | Shift+click for multi-select |
| Connections | Click node | Drag to reposition, zoom/pan |

### Mode transitions

Switching modes preserves context where possible:
- Timeline → Overview: Brushed year range → decade filter
- Overview → Timeline: Type/language filters → highlighted streams
- Any → Connections: Selected entries' seeAlso links → highlighted nodes
- Connections → Any: Selected node's type/language/year → filters

## Technology

- **D3.js v7** via CDN — standard for academic information visualization
- **Replaces Chart.js** — D3 provides brushing, force simulation, stacked bars, bubble maps
- **4 JS modules**: `explore.js` (controller), `explore-timeline.js`, `explore-geography.js`, `explore-network.js`
- **Cross-view communication**: `explore:filterChange` CustomEvent on `document` — all views can react to filter changes from any other view
- **SVG rendering** — lightweight, exportable, accessible via DOM

## Color Palette

Extended from the existing SZD design system:

| Use | Color | Hex |
|-----|-------|-----|
| German (primary stream) | Burgundy | #7A1B2D |
| Chinese | Gold | #B8963E |
| French | Olive | #6B7A3A |
| English | Slate | #5B5040 |
| Spanish | Terracotta | #8B5C3A |
| Arabic | Purple | #5B3A7A |
| Bulgarian | Teal | #3A5B6B |
| Albanian | Sienna | #7A4A1B |
| Russian | Navy | #3A3A5B |
| Croatian | Dusty Rose | #6B3A4A |
| Other | Light Gray | #9E9585 |
| Zweig lifetime band | Gold (20% opacity) | #C2A360 |
| Grid lines | Warm gray | #EDE8DF |

## Information Seeking Mantra Assessment

The design follows Shneiderman's Visual Information Seeking Mantra (Overview first, zoom and filter, then details-on-demand) extended to seven tasks. Assessment as of Session 14 (2026-04-12):

| Task | Timeline | Overview | Geography | Connections |
|------|----------|----------|-----------|-------------|
| Overview | Good (stacked area) | Good (6 small multiples) | Weak (too many bubbles in Europe) | Weak (no aggregate level) |
| Zoom | Good (brush = semantic zoom) | N/A (fixed) | Geometric only | Geometric only |
| Filter | Good (brush, chips) | Good (cross-filter) | Good (click) | Missing |
| Details | Good (panel + tooltips) | Good | Good | Good |
| Relate | Good (cross-mode filters) | Good | Missing (no comparison) | Missing |
| History | Missing | Missing | Missing | Missing |
| Extract | JSON-LD download only | — | — | — |

### Design Decisions (2026-04-12)

**Overview-View not expanded.** The Overview (6 linked small multiples) remains as built but is not the focus of further development. Effort concentrates on three strong modes (Timeline, Geography, Connections) rather than four moderate ones.

**Personas.** Each view has an analytical identity guiding its development:
- L1 Temporal Analyst (Timeline) — time series, periodisation, trends
- L2 Spatial Analyst (Geography) — spaces, diffusion, cartography
- L3 Network Analyst (Connections) — graphs, hubs, communities, centrality

**Geography prioritisation.** A) Brushed Linking Timeline → Geography (highest impact: shows Zweig reception migration Wien/Berlin → Amsterdam/London → Beijing/Barcelona). B) Animated Playback (Play button through decades). C) Semantic Zoom (country aggregation by default, city bubbles on zoom-in).

**Brushed Linking (Geo-temporal Coupling).** The core cross-view feature: when a brush is set on the Timeline, Geography bubbles resize in real time via `explore:filterChange` events on `Explore.filters.yearRange`. This makes the spatial shift of Zweig reception visible as a continuous animation rather than a static snapshot.

### Globe Implementation (2026-04-12)

**Projection: `d3.geoOrthographic()`.** The Geography view uses an orthographic (globe) projection instead of the initially planned Natural Earth flat map. Rationale: (1) Globe is more visually impactful and presentation-ready, (2) shows only one hemisphere at a time, reducing bubble overlap, (3) drag-to-rotate is a natural interaction for exploring spatial distribution, (4) scroll-to-zoom lets users focus on individual regions (Europe, East Asia, Americas).

**Architecture:**
- Drag-to-rotate: `d3.drag()` updates `projection.rotate([λ, φ, 0])`, φ clamped to ±80°
- Scroll-to-zoom: wheel event changes `projection.scale()` (0.8× to 6× base scale)
- Visibility: `d3.geoDistance()` checks if point is on visible hemisphere (< π/2)
- Semantic zoom: at 2× base scale, switches from country-aggregated to city-level bubbles
- Bubble data: 374/382 locations geocoded with country codes in `locations.json`
- Cross-view: listens to `explore:filterChange` events, rebuilds bubbles with `d3.transition()`

**Known Issues (post-review):**
1. Click = filter is destructive (removes all other bubbles). Should dim instead (highlight + preserve context)
2. Animated Playback (Play/Slider) not functioning correctly
3. City labels missing at zoom level
4. Ocean/land contrast too low
5. No reset-rotation button
6. Legend not interactive (clicking language should filter)

## References

See [[references#information-visualization]] for full citations.
